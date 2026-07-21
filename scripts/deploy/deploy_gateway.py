#!/usr/bin/env python3
"""
Deploy Pellier MCP Servers to Amazon Bedrock AgentCore Gateway.

Creates a gateway with four Lambda targets that publish the same canonical
15 tool names as the in-process Pellier agent.
Adapted from DAT403 deploy_gateway_simple.py for Pellier.
"""
import boto3
import json
import os
import sys
import time
import argparse
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# AgentCore create_gateway_target accepts only this JSON-Schema keyword subset
# per (sub)property. Anything else (default, enum, minimum, maximum, format, …)
# triggers a botocore ParamValidationError before the request is even sent.
_ALLOWED_SCHEMA_KEYS = {"type", "properties", "required", "items", "description"}


def _sanitize_tool_schema(node):
    """Recursively drop JSON-Schema keywords AgentCore's gateway target API does
    not accept, keeping only _ALLOWED_SCHEMA_KEYS. Recurses into `properties`
    (per-field dicts) and `items` (array element schema). Returns a new object;
    the source TOOL_SCHEMAS are left intact for readability."""
    if not isinstance(node, dict):
        return node
    cleaned = {}
    for key, value in node.items():
        if key not in _ALLOWED_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            cleaned[key] = {
                prop_name: _sanitize_tool_schema(prop_schema)
                for prop_name, prop_schema in value.items()
            }
        elif key == "items":
            cleaned[key] = _sanitize_tool_schema(value)
        else:
            cleaned[key] = value
    return cleaned


# Tool schemas for Pellier MCP servers
TOOL_SCHEMAS = {
    "search": {
        "target_name": "pellier-discovery-search-target",
        "description": "Pellier search and inventory MCP server",
        "tools": [
            {
                "name": "find_pieces",
                "description": "Search products by natural language query using vector similarity.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language search query"},
                        "limit": {"type": "integer", "description": "Max results", "default": 5},
                        "max_price": {"type": "number", "description": "Maximum price filter"},
                        "min_rating": {"type": "number", "description": "Minimum star rating"},
                        "category": {"type": "string", "description": "Optional category substring"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "find_pieces_hybrid",
                "description": (
                    "Hybrid retrieval: pgvector cosine + Postgres FTS merged via "
                    "RRF, then reranked by Cohere Rerank v3.5. Higher quality "
                    "than find_pieces at the cost of one extra Bedrock call."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language search query"},
                        "max_price": {"type": "number", "description": "Maximum price filter (post-rerank)"},
                        "min_rating": {"type": "number", "description": "Minimum star rating (post-rerank)", "default": 0.0},
                        "category": {"type": "string", "description": "Category substring filter (post-rerank)"},
                        "limit": {"type": "integer", "description": "Max results", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "explore_collection",
                "description": "Browse a category with rating and price filters.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "min_rating": {"type": "number", "default": 0.0},
                        "max_price": {"type": "number"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["category"],
                },
            },
            {
                "name": "floor_check",
                "description": "Check aggregate inventory or one product across warehouses.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"product_query": {"type": "string"}},
                    "required": [],
                },
            },
            {
                "name": "running_low",
                "description": "Get products with critically low stock.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "default": 5}},
                    "required": [],
                },
            },
            {
                "name": "restock_shelf",
                "description": "Restock a product (max 500 per policy).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "quantity": {"type": "integer"},
                    },
                    "required": ["product_id", "quantity"],
                },
            },
        ],
    },
    "pricing": {
        "target_name": "pellier-value-pricing-target",
        "description": "Pellier pricing analysis MCP server",
        "tools": [
            {
                "name": "price_intelligence",
                "description": "Price statistics by category.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"category": {"type": "string"}},
                    "required": [],
                },
            },
            {
                "name": "side_by_side",
                "description": "Compare two products side by side.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id_1": {"type": "integer"},
                        "product_id_2": {"type": "integer"},
                    },
                    "required": ["product_id_1", "product_id_2"],
                },
            },
        ],
    },
    "recommendation": {
        "target_name": "pellier-curation-recommendation-target",
        "description": "Pellier curation, memory, policy, and evidence MCP server",
        "tools": [
            {
                "name": "preference_snapshot",
                "description": "Read a safe customer preference, order, and memory snapshot.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "persona": {"type": "string"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": [],
                },
            },
            {
                "name": "trace_receipt",
                "description": "Read recent ALLOW receipts from pellier.tool_audit.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "tool_name": {"type": "string"},
                        "caller": {"type": "string"},
                        "limit": {"type": "integer", "default": 3},
                    },
                    "required": [],
                },
            },
            {
                "name": "whats_trending",
                "description": "Most popular products by rating and review volume.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 5},
                        "category": {"type": "string"},
                    },
                    "required": [],
                },
            },
            {
                "name": "returns_and_care",
                "description": "Look up the return and care policy for a category.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "default": "default"},
                    },
                    "required": [],
                },
            },
            {
                "name": "style_match",
                "description": "Find complementary products by vector similarity.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["product_id"],
                },
            },
        ],
    },
    "experience": {
        "target_name": "pellier-concierge-experience-target",
        "description": "Pellier experience-guide MCP server (returns + stylist handoff)",
        "tools": [
            {
                "name": "process_return",
                "description": (
                    "Process a return atomically: ownership check + INSERT into "
                    "pellier.returns + (if damaged) decrement product_catalog "
                    "quantity. Reason must be one of damaged, wrong_size, "
                    "not_as_described, changed_mind, other."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "product_id": {"type": "integer"},
                        "reason": {
                            "type": "string",
                            "enum": [
                                "changed_mind",
                                "damaged",
                                "not_as_described",
                                "other",
                                "wrong_size",
                            ],
                        },
                    },
                    "required": ["customer_id", "product_id", "reason"],
                },
            },
            {
                "name": "escalate_to_stylist",
                "description": (
                    "Hand the conversation off to a human stylist. Honest "
                    "fallback when no catalog tool can answer (cultural "
                    "dressing norms, body-image fit, out-of-policy returns)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string"},
                        "customer_id": {"type": "string"},
                    },
                    "required": [],
                },
            },
        ],
    },
}


@dataclass
class MCPTarget:
    lambda_arn: str
    server_type: str  # search, pricing, recommendation, or experience


@dataclass
class GatewayConfig:
    region: str = "us-east-1"
    gateway_name: str = "pellier-gateway"
    targets: List[MCPTarget] = field(default_factory=list)
    cognito_user_pool_id: str = None
    cognito_client_id: str = None

    @property
    def role_name(self):
        return f"{self.gateway_name}-role"


class BazaarGatewayDeployer:
    """Deploys Pellier MCP servers to AgentCore Gateway."""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.session = boto3.Session(region_name=config.region)
        self.agentcore = self.session.client("bedrock-agentcore-control")
        self.iam = self.session.client("iam")

    def deploy(self) -> Dict[str, Any]:
        logger.info("Starting Bazaar Gateway deployment...")

        lambda_arns = [t.lambda_arn for t in self.config.targets]
        role_arn = self._ensure_role(lambda_arns)

        gateway_id = self._get_existing_gateway()
        if gateway_id:
            logger.info(f"Gateway '{self.config.gateway_name}' exists: {gateway_id}")
            self._update_role_policy(lambda_arns)
        else:
            gateway_id = self._create_gateway(role_arn)

        for target in self.config.targets:
            self._add_target(gateway_id, target)

        info = self.agentcore.get_gateway(gatewayIdentifier=gateway_id)
        self.agentcore.tag_resource(
            resourceArn=info["gatewayArn"],
            tags={
                "Project": "pellier",
                "PellierWorkshopId": os.environ.get("WORKSHOP_ID", "unknown"),
            },
        )
        logger.info("Gateway deployment complete!")

        return {
            "gateway_id": gateway_id,
            "gateway_url": info.get("gatewayUrl"),
            "targets": [t.server_type for t in self.config.targets],
            "region": self.config.region,
        }

    def _get_existing_gateway(self) -> str | None:
        try:
            for gw in self.agentcore.list_gateways().get("items", []):
                if gw.get("name") == self.config.gateway_name:
                    return gw["gatewayId"]
        except Exception:
            pass
        return None

    def _role_policy_doc(self, lambda_arns: List[str]) -> dict:
        """Inline policy for the gateway execution role.

        Beyond invoking the target Lambdas + logging, the gateway role needs the
        managed-Policy EVALUATION permissions so it can enforce Cedar on every
        tool call (the 4th pillar). Per the AgentCore Policy docs + the dat403
        reference, these four must be on Resource:"*" — the eval resource path is
        ``policy-engines/<id>/target-resource/<encoded-gw-arn>``, which a narrow
        ARN pattern does NOT match (the call then fails AccessDenied, and a
        missing GetPolicyEngine fails silently even in MONITOR mode).
        """
        return {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["lambda:InvokeFunction"], "Resource": lambda_arns},
                {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"},
                {
                    "Sid": "ManagedPolicyEvaluation",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:AuthorizeAction",
                        "bedrock-agentcore:GetPolicyEngine",
                        "bedrock-agentcore:CheckAuthorizePermissions",
                        "bedrock-agentcore:PartiallyAuthorizeActions",
                    ],
                    "Resource": "*",
                },
            ],
        }

    def _ensure_role(self, lambda_arns: List[str]) -> str:
        role_name = self.config.role_name
        tags = [
            {"Key": "Project", "Value": "pellier"},
            {
                "Key": "PellierWorkshopId",
                "Value": os.environ.get("WORKSHOP_ID", "unknown"),
            },
        ]
        trust = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole"}
            ],
        }
        policy = self._role_policy_doc(lambda_arns)
        try:
            resp = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust),
                Tags=tags,
            )
            role_arn = resp["Role"]["Arn"]
            logger.info(f"Created IAM role: {role_arn}")
            time.sleep(10)
        except self.iam.exceptions.EntityAlreadyExistsException:
            resp = self.iam.get_role(RoleName=role_name)
            role_arn = resp["Role"]["Arn"]
            self.iam.tag_role(RoleName=role_name, Tags=tags)
            logger.info(f"IAM role exists: {role_arn}")

        self.iam.put_role_policy(RoleName=role_name, PolicyName=f"{role_name}-policy", PolicyDocument=json.dumps(policy))
        return role_arn

    def _update_role_policy(self, lambda_arns: List[str]):
        self.iam.put_role_policy(
            RoleName=self.config.role_name,
            PolicyName=f"{self.config.role_name}-policy",
            PolicyDocument=json.dumps(self._role_policy_doc(lambda_arns)),
        )

    def _create_gateway(self, role_arn: str) -> str:
        params = {
            "name": self.config.gateway_name,
            "roleArn": role_arn,
            "description": "Pellier MCP Gateway — search, pricing, recommendations, experience",
            "protocolType": "MCP",
            "protocolConfiguration": {"mcp": {"searchType": "SEMANTIC", "supportedVersions": ["2025-03-26"]}},
            "tags": {
                "Project": "pellier",
                "PellierWorkshopId": os.environ.get("WORKSHOP_ID", "unknown"),
            },
        }
        if self.config.cognito_user_pool_id and self.config.cognito_client_id:
            discovery = f"https://cognito-idp.{self.config.region}.amazonaws.com/{self.config.cognito_user_pool_id}/.well-known/openid-configuration"
            params["authorizerType"] = "CUSTOM_JWT"
            params["authorizerConfiguration"] = {"customJWTAuthorizer": {"discoveryUrl": discovery, "allowedClients": [self.config.cognito_client_id]}}
        else:
            params["authorizerType"] = "NONE"

        resp = self.agentcore.create_gateway(**params)
        gw_id = resp["gatewayId"]
        logger.info(f"Created gateway: {gw_id}")
        self._wait_ready(gw_id)
        return gw_id

    def _wait_ready(self, gateway_id: str, timeout: int = 300):
        logger.info("Waiting for gateway to be ready...")
        start = time.time()
        while time.time() - start < timeout:
            status = self.agentcore.get_gateway(gatewayIdentifier=gateway_id).get("status")
            logger.info(f"  status: {status}")
            if status == "READY":
                return
            if status in ("FAILED", "DELETING", "DELETED"):
                raise RuntimeError(f"Gateway failed: {status}")
            time.sleep(10)
        raise TimeoutError("Gateway not ready within timeout")

    def _add_target(self, gateway_id: str, target: MCPTarget):
        schema = TOOL_SCHEMAS.get(target.server_type)
        if not schema:
            raise ValueError(f"Unknown server type: {target.server_type}")

        target_name = schema["target_name"]
        # AgentCore's create_gateway_target validates each tool inputSchema
        # against a RESTRICTED JSON-Schema subset — only {type, properties,
        # required, items, description} are accepted per property. Common
        # keywords like "default" and "enum" are rejected with a botocore
        # ParamValidationError. We keep those keys in TOOL_SCHEMAS above for
        # human readability / source-of-truth, and strip them HERE, at the API
        # boundary, with a recursive sanitizer. This is comprehensive (any
        # disallowed keyword at any depth is dropped), so it won't regress if a
        # new tool adds minimum/maximum/format/etc. Runtime behavior is
        # unaffected: the MCP Lambdas apply their own defaults and validate
        # enums server-side; the gateway schema is only the tool advertisement.
        sanitized_tools = [
            {**tool, "inputSchema": _sanitize_tool_schema(tool["inputSchema"])}
            for tool in schema["tools"]
        ]

        target_configuration = {
            "mcp": {
                "lambda": {
                    "lambdaArn": target.lambda_arn,
                    "toolSchema": {"inlinePayload": sanitized_tools},
                }
            }
        }
        credentials = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
        existing = self.agentcore.list_gateway_targets(
            gatewayIdentifier=gateway_id
        ).get("items", [])
        existing_target = next(
            (item for item in existing if item.get("name") == target_name),
            None,
        )
        if existing_target:
            target_id = existing_target["targetId"]
            self.agentcore.update_gateway_target(
                gatewayIdentifier=gateway_id,
                targetId=target_id,
                name=target_name,
                description=schema["description"],
                targetConfiguration=target_configuration,
                credentialProviderConfigurations=credentials,
            )
            self.agentcore.synchronize_gateway_targets(
                gatewayIdentifier=gateway_id,
                targetIdList=[target_id],
            )
            logger.info("Updated target '%s'", target_name)
            return

        self.agentcore.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=target_name,
            description=schema["description"],
            targetConfiguration=target_configuration,
            credentialProviderConfigurations=credentials,
        )
        logger.info("Added target '%s'", target_name)


def main():
    parser = argparse.ArgumentParser(description="Deploy Pellier MCP servers to AgentCore Gateway")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--gateway-name", default="pellier-gateway")
    parser.add_argument("--search-lambda-arn", required=True)
    parser.add_argument("--pricing-lambda-arn", required=True)
    parser.add_argument("--recommendation-lambda-arn", required=True)
    parser.add_argument("--experience-lambda-arn", required=True)
    parser.add_argument("--cognito-user-pool-id")
    parser.add_argument("--cognito-client-id")
    args = parser.parse_args()

    config = GatewayConfig(
        region=args.region,
        gateway_name=args.gateway_name,
        targets=[
            MCPTarget(lambda_arn=args.search_lambda_arn, server_type="search"),
            MCPTarget(lambda_arn=args.pricing_lambda_arn, server_type="pricing"),
            MCPTarget(lambda_arn=args.recommendation_lambda_arn, server_type="recommendation"),
            MCPTarget(lambda_arn=args.experience_lambda_arn, server_type="experience"),
        ],
        cognito_user_pool_id=args.cognito_user_pool_id,
        cognito_client_id=args.cognito_client_id,
    )

    result = BazaarGatewayDeployer(config).deploy()

    print("\n" + "=" * 60)
    print("BAZAAR GATEWAY DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"Gateway ID:  {result['gateway_id']}")
    print(f"Gateway URL: {result['gateway_url']}")
    print(f"Targets:     {', '.join(result['targets'])}")
    print("=" * 60)

    with open("bazaar_gateway_deployment.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
