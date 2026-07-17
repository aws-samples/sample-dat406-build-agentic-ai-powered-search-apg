"""Tests pinning the MANAGED AgentCore Policy contract (the 4th pillar).

Pellier replaced its local Strands ``BeforeToolCallEvent`` Cedar hook with
**managed AgentCore Policy** enforced at the Gateway. These tests pin that
migration STATICALLY (no AWS calls) so a regression back to the local
fake-Cedar gate — or a drift in the provisioning contract — trips here:

  1. The local hook + hand-rolled fake-Cedar engine are GONE (one gate only).
  2. ``scripts/deploy/deploy_policy.py`` provisions a managed Cedar engine with
     the correct GA boto3 contract (create_policy_engine / create_policy
     definition={"cedar":...} / update_gateway policyEngineConfiguration ENFORCE)
     and the correct Cedar action spelling for process_return.
  3. The experience Lambda reconstructs the ``pellier.tool_audit`` evidence row
     on the Gateway rail (so the Core Lab 3 SQL proof survives).
  4. The deploy path (provisioner + deploy_all.sh) wires the policy step.
  5. The gateway execution role gets the four policy-EVALUATION permissions.

Runnable from repo root per ``pytest.ini``.
"""
from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND = REPO_ROOT / "pellier" / "backend"
DEPLOY = REPO_ROOT / "scripts" / "deploy"

DEPLOY_POLICY = DEPLOY / "deploy_policy.py"
WORKSHOP_POLICY_RULE = DEPLOY / "workshop_policy_rule.py"
GATEWAY_PROCESS_RETURN = DEPLOY / "gateway_process_return.py"
EXPERIENCE_LAMBDA = DEPLOY / "pellier_experience_server.py"
DEPLOY_GATEWAY = DEPLOY / "deploy_gateway.py"
PROVISIONER = REPO_ROOT / "scripts" / "provision_agentcore_end_to_end.py"
DEPLOY_ALL = DEPLOY / "deploy_all.sh"
RESET_GOVERNED = REPO_ROOT / "scripts" / "reset-governed-workshop.sh"
STARTER_CEDAR = REPO_ROOT / "policies" / "workshop_final_sale_forbid.cedar"
SOLUTION_CEDAR = REPO_ROOT / "solutions" / "the-concierge" / "policies" / "final_sale_forbid.cedar"
IDENTITY_STARTER_CEDAR = REPO_ROOT / "policies" / "workshop_identity_match_forbid.cedar"
IDENTITY_SOLUTION_CEDAR = (
    REPO_ROOT / "solutions" / "the-concierge" / "policies" / "identity_match_forbid.cedar"
)

# Cedar action spelling is keyed on the Gateway TARGET name (what the Gateway
# registers tools under), NOT the Lambda function name. The live GA engine
# rejected the function-name form on a fresh account; the verified dat403
# contract is <gateway-target-name>___<tool-name> (triple _). deploy_policy.py
# tries that first, then <target>__<tool>, then defers to the engine's own
# "did you mean" hint — so the action prefix below must be the TARGET name.
EXPERIENCE_TARGET = "pellier-concierge-experience-target"
EXPECTED_ACTION = f"{EXPERIENCE_TARGET}___process_return"


# ---------------------------------------------------------------------------
# 1. The local gate is gone (single managed gate, no hybrid confusion)
# ---------------------------------------------------------------------------


def test_local_policy_hook_removed() -> None:
    assert not (BACKEND / "services" / "policy_hook.py").exists(), (
        "services/policy_hook.py (local BeforeToolCall Cedar gate) must be removed — "
        "managed AgentCore Policy at the Gateway is now the single gate."
    )


def test_fake_cedar_engine_removed() -> None:
    assert not (BACKEND / "services" / "agentcore_policy.py").exists(), (
        "services/agentcore_policy.py (hand-rolled fake-Cedar PolicyService) must be "
        "removed — Cedar is now real + managed."
    )


def test_no_dangling_local_policy_refs() -> None:
    """No backend module still imports the removed local-policy symbols."""
    offenders = []
    for py in (BACKEND).rglob("*.py"):
        if py.name.startswith("test_"):
            continue
        text = py.read_text()
        for sym in ("PolicyEnforcementHook", "attach_policy_hook",
                    "get_policy_service", "create_policy_from_natural_language"):
            # an import/use, not a comment line
            for line in text.splitlines():
                stripped = line.strip()
                if sym in stripped and not stripped.startswith("#"):
                    offenders.append(f"{py.relative_to(REPO_ROOT)}: {stripped}")
    assert not offenders, "Dangling references to removed local-policy code:\n" + "\n".join(offenders)


# ---------------------------------------------------------------------------
# 2. deploy_policy.py — the managed provisioning contract
# ---------------------------------------------------------------------------


def test_deploy_policy_exists_and_uses_ga_contract() -> None:
    assert DEPLOY_POLICY.is_file(), "scripts/deploy/deploy_policy.py must exist"
    src = DEPLOY_POLICY.read_text()
    # GA bedrock-agentcore-control verbs (NOT the preview-era shape).
    assert "bedrock-agentcore-control" in src
    assert "create_policy_engine" in src
    assert "create_policy" in src
    assert 'definition={"cedar"' in src or "'cedar'" in src, "policies must be direct Cedar"
    assert "policyEngineConfiguration" in src and "ENFORCE" in src, "must attach engine in ENFORCE mode"
    # MUST NOT use the dead preview-era natural-language definition shape.
    assert "naturalLanguage" not in src, "must not use the preview-era definition={naturalLanguage} shape"


def test_deploy_policy_gates_process_return_to_damaged() -> None:
    src = DEPLOY_POLICY.read_text()
    # The action prefix is the Gateway TARGET name (the dat403-verified contract),
    # not the Lambda function name. The literal action string is now assembled at
    # runtime from candidate_actions, so assert the target-name default is present.
    assert EXPERIENCE_TARGET in src, (
        f"Cedar action prefix must be the Gateway target name {EXPERIENCE_TARGET}"
    )
    assert "___process_return" in src, "primary candidate must be target___tool (triple _)"
    # Must NOT regress to the Lambda-function-name action that the live engine rejected.
    assert "pellier-experience-server-function___process_return" not in src, (
        "must not use the Lambda function name as the Cedar action prefix — "
        "the GA engine rejects it; key on the Gateway target name"
    )
    assert "forbid(" in src and 'reason != "damaged"' in src, (
        "must FORBID process_return unless reason == 'damaged'"
    )


def test_deploy_policy_self_corrects_action_identifier() -> None:
    """The action identifier the GA engine accepts has drifted across API
    revisions, so deploy_policy.py must self-correct: try candidates, then parse
    the engine's 'did you mean' hint and retry with the exact token."""
    src = DEPLOY_POLICY.read_text()
    assert "_extract_suggested_action" in src, (
        "must parse the engine's 'did you mean' hint to recover the accepted action"
    )
    assert "candidate_actions" in src, "must try multiple candidate action formats"


def test_deploy_policy_compiles_and_exposes_helpers() -> None:
    """Import the module and confirm the porting kept the dat403 helper shape."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("deploy_policy", DEPLOY_POLICY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for fn in ("create_or_reuse_engine", "create_or_reuse_policy",
               "create_pellier_policies", "attach_engine_to_gateway",
               "create_action_policy_with_fallback", "_extract_suggested_action"):
        assert hasattr(mod, fn), f"deploy_policy.py must define {fn}"


def test_workshop_policy_rule_is_resettable_participant_policy() -> None:
    src = WORKSHOP_POLICY_RULE.read_text()
    assert "workshop_final_sale_forbid" in src
    assert "delete_policy" in src, "participant policy must be removable by reset"
    assert "process_return" in src and "product_id" in src
    assert "FINAL_SALE_PRODUCT_ID = 37" in src
    assert "context.input.product_id ==" in src
    assert "--cedar-file" in src
    assert "validate" in src
    assert "_validate_participant_cedar" in src
    assert "create_action_policy_with_fallback" in src


def test_participant_cedar_file_contract() -> None:
    assert STARTER_CEDAR.is_file(), "starter Cedar file must ship in the participant repo"
    assert SOLUTION_CEDAR.is_file(), "solution Cedar file must ship for facilitator recovery"

    starter = STARTER_CEDAR.read_text()
    solution = SOLUTION_CEDAR.read_text()
    for text in (starter, solution):
        assert 'AgentCore::Action::"ACTION_TOKEN"' in text
        assert 'AgentCore::Gateway::"GATEWAY_ARN"' in text
        assert "context.input has product_id" in text

    assert "false" in starter, "starter must require a participant edit"
    assert "context.input.product_id == 37" in solution


def test_workshop_policy_rule_validates_authored_cedar() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("workshop_policy_rule", WORKSHOP_POLICY_RULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    starter = STARTER_CEDAR.read_text()
    solution = SOLUTION_CEDAR.read_text()

    assert "replace the starter false predicate" in "\n".join(
        mod._validate_participant_cedar(starter, product_id=37)
    )
    assert mod._validate_participant_cedar(solution, product_id=37) == []


def test_workshop_policy_rule_supports_monitor_enforce_staging() -> None:
    """The MONITOR→ENFORCE rehearsal beat rides the same helper: one `mode`
    subcommand that re-attaches the engine via deploy_policy and confirms
    the gateway reports the new mode before declaring success."""
    src = WORKSHOP_POLICY_RULE.read_text()
    assert '"mode"' in src or "'mode'" in src
    assert "MONITOR" in src and "ENFORCE" in src
    assert "attach_engine_to_gateway" in src
    # Must read the mode back (update_gateway is async) — no optimistic print.
    assert "policyEngineConfiguration" in src
    assert "GATEWAY_POLICY_MODE=" in src


def test_gateway_process_return_only_counts_authorization_errors_as_deny() -> None:
    """The Gateway replay helper must not turn transport/tool failures into
    fake Cedar DENY proofs."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("gateway_process_return", GATEWAY_PROCESS_RETURN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod._is_authorization_denial(
        RuntimeError("AuthorizeActionException: explicit deny")
    )
    assert mod._is_authorization_denial(
        RuntimeError("AccessDeniedException: principal is not authorized")
    )
    assert mod._is_authorization_denial(
        RuntimeError("access denied by policy")
    )
    assert not mod._is_authorization_denial(
        RuntimeError("Connection refused while calling Gateway")
    )

    class Grouped(Exception):
        def __init__(self, exceptions):
            super().__init__("grouped")
            self.exceptions = exceptions

    assert mod._is_authorization_denial(
        Grouped([RuntimeError("timeout"), RuntimeError("Authorization failed")])
    )
    assert not mod._is_authorization_denial(
        Grouped([RuntimeError("timeout"), RuntimeError("tool not found")])
    )

    # The verbatim GA Gateway deny message (box-verified 2026-06-12) must
    # classify as a Cedar denial even without the word "denied" surviving
    # truncation.
    assert mod._is_authorization_denial(
        RuntimeError("Tool call not allowed due to policy enforcement [Policy")
    )
    # A rejected/expired bearer token is an auth-SETUP failure (Gateway JWT
    # authorizer 401), not a Cedar decision — it must NOT count as deny.
    assert not mod._is_authorization_denial(
        RuntimeError("HTTP 401 Unauthorized: invalid bearer token")
    )
    assert not mod._is_authorization_denial(
        RuntimeError("403 Forbidden from CloudFront")
    )


def test_governed_reset_restores_enforce_mode() -> None:
    """Reset must recover from an interrupted MONITOR rehearsal."""
    src = RESET_GOVERNED.read_text()
    assert "workshop_policy_rule.py\" mode" in src
    assert "--set ENFORCE" in src
    assert "AGENTCORE_GATEWAY_ARN" in src
    assert "Gateway Policy attachment restored to ENFORCE mode" in src


def test_identity_match_rule_is_second_participant_policy() -> None:
    """The optional identity rail rides the same helper: separate policy name,
    JWT-claim tag comparison against the tool input, removable by reset."""
    src = WORKSHOP_POLICY_RULE.read_text()
    assert "workshop_identity_match_forbid" in src
    assert "--rule" in src and "identity_match" in src
    # The identity comparison must read the JWT claim from the principal tag
    # (AgentCore::OAuthUser exposes token claims as tags) — not from input.
    assert "principal.hasTag(" in src
    assert "principal.getTag(" in src
    assert "context.input.customer_id" in src
    # Both participant policies must fall inside reset's blast radius.
    assert "PARTICIPANT_POLICY_NAMES" in src


def test_identity_match_cedar_file_contract() -> None:
    assert IDENTITY_STARTER_CEDAR.is_file(), "identity starter Cedar file must ship"
    assert IDENTITY_SOLUTION_CEDAR.is_file(), "identity solution Cedar file must ship"

    starter = IDENTITY_STARTER_CEDAR.read_text()
    solution = IDENTITY_SOLUTION_CEDAR.read_text()
    for text in (starter, solution):
        assert 'AgentCore::Action::"ACTION_TOKEN"' in text
        assert 'AgentCore::Gateway::"GATEWAY_ARN"' in text
        assert "context.input has customer_id" in text

    assert "false" in starter, "identity starter must require a participant edit"
    assert 'principal.hasTag("username")' in solution
    assert 'principal.getTag("username") != context.input.customer_id' in solution


def test_identity_match_validator_accepts_solution_rejects_starter() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("workshop_policy_rule", WORKSHOP_POLICY_RULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    starter = IDENTITY_STARTER_CEDAR.read_text()
    solution = IDENTITY_SOLUTION_CEDAR.read_text()

    starter_errors = "\n".join(mod._validate_identity_cedar(starter, claim_tag="username"))
    assert "replace the starter false predicate" in starter_errors
    assert mod._validate_identity_cedar(solution, claim_tag="username") == []
    # The final-sale validator must NOT accept the identity file (distinct rules).
    assert mod._validate_participant_cedar(solution, product_id=37) != []


# ---------------------------------------------------------------------------
# 3. Experience Lambda reconstructs the tool_audit evidence row
# ---------------------------------------------------------------------------


def test_experience_lambda_writes_tool_audit() -> None:
    src = EXPERIENCE_LAMBDA.read_text()
    assert "_write_tool_audit" in src, "experience Lambda must write tool_audit on the Gateway rail"
    assert "INSERT INTO" in src and "tool_audit" in src
    # JSONB columns must be cast so args->>'reason' / result->>'return_id' work.
    assert "::jsonb" in src
    # Only the audited write tool gets a row.
    assert 'tool_name == "process_return"' in src
    # The Gateway-rail row MUST carry caller="gateway" — it's the discriminator
    # that separates managed-rail writes from the in-process caller="agent"
    # rows. Guard against a silent regression to "agent" or a blank caller.
    assert '"gateway"' in src or "'gateway'" in src, (
        "experience Lambda must write caller='gateway' on the managed rail"
    )


# ---------------------------------------------------------------------------
# 4. Deploy path wires the policy step
# ---------------------------------------------------------------------------


def test_provisioner_invokes_deploy_policy() -> None:
    src = PROVISIONER.read_text()
    assert "deploy_policy.py" in src, "provisioner must call deploy_policy.py after the gateway"
    assert "POLICY_ENGINE_ID" in src, "provisioner must capture the policy engine id"


def test_deploy_all_invokes_deploy_policy() -> None:
    src = DEPLOY_ALL.read_text()
    assert "deploy_policy.py" in src and "ENFORCE" in src


# ---------------------------------------------------------------------------
# 5. Gateway role gets the policy-evaluation permissions
# ---------------------------------------------------------------------------


def test_gateway_role_has_policy_eval_perms() -> None:
    src = DEPLOY_GATEWAY.read_text()
    for action in ("bedrock-agentcore:AuthorizeAction",
                   "bedrock-agentcore:GetPolicyEngine",
                   "bedrock-agentcore:CheckAuthorizePermissions",
                   "bedrock-agentcore:PartiallyAuthorizeActions"):
        assert action in src, f"gateway role must grant {action} for invoke-time Cedar eval"
