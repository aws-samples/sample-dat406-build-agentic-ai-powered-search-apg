"""
Shared RDS Data API access for the Gateway tool Lambdas.

The four surface servers (search, pricing, recommend, experience) each reach
Aurora through the Data API, and each had grown its own copy of the same
plumbing: `_execute_sql` was byte-identical in three files, the transaction
helper existed twice, and the embedding helper twice. Roughly 250 of 2,159
lines were redundant.

Duplication here is not a tidiness problem. These copies had already drifted in
two recorded ways, and the drift is invisible until it produces wrong data:

  * `_execute_in_transaction` in the search server dropped `booleanValue` and
    `isNull` from its field coercion, mapping both to `None`. Its one call site
    selects a JSON column, so nothing was wrong in production, but the next
    query through that path selecting a boolean would have read `None` for
    `false` with no error anywhere.
  * The two embedding helpers carried the same warning in different words. A
    model change applied to one copy would silently put the Gateway path in a
    different vector space from the seeded catalog, which does not fail — it
    just ranks wrongly.

Everything here is transport. Nothing in this module knows a tool name, and
none of the surface files' business SQL moved: those queries differ per surface
on purpose and collapsing them would be a false abstraction.

Configuration comes from the same environment variables the surface files
already read, so the deploy path is unchanged. `deploy_lambda.py` packages this
file into every function's zip next to `common/types.py`.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ.get("REGION", "us-east-1")
DB_REGION = os.environ.get("DB_REGION", REGION)
DB_CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN = os.environ.get("SECRET_ARN", "")
DATABASE = os.environ.get("DATABASE", "postgres")
SCHEMA = "pellier"

# Non-owner runtime roles from migration 016. Both are NOBYPASSRLS, which is
# what makes the policies bind; the owner would silently bypass them.
_RUNTIME_ROLES = frozenset({"pellier_agent", "pellier_query"})

# Cohere Embed v4. MUST match the catalog seed and the in-process path
# (`pellier/backend/services/embeddings.py`): the catalog was seeded with
# Cohere Embed v4 at output_dimension=1024, so the managed Gateway path has to
# embed in the SAME vector space. Titan v2 vectors are a different space and
# would make pgvector cosine search return wrong rankings even though the
# dimension (1024) happens to match. Stated once here, on purpose: this is the
# constant that must never diverge between rails.
EMBED_MODEL_ID = os.environ.get("BEDROCK_EMBED_MODEL_ID", "us.cohere.embed-v4:0")
EMBED_DIMENSION = 1024

# Module-level clients for Lambda warm-start reuse.
rds_client = boto3.client("rds-data", region_name=DB_REGION)
bedrock_client = boto3.client("bedrock-runtime", region_name=REGION)


def row_to_dict(record: List[Dict[str, Any]], columns: List[str]) -> Dict[str, Any]:
    """Convert one Data API record into a dict keyed by column name.

    Handles every field shape the Data API returns. `booleanValue` and `isNull`
    are load-bearing: a converter that omits them coerces `false` and SQL NULL
    to the same `None`, which reads as missing data rather than as an error.

    Args:
        record: One entry from a response's ``records`` list.
        columns: Column names from ``columnMetadata``, in order.

    Returns:
        The row as a dict. Unrecognized field shapes stringify rather than
        vanish, so a new Data API type is visible instead of silently null.
    """
    row: Dict[str, Any] = {}
    for index, field in enumerate(record):
        if index >= len(columns):
            break
        if "stringValue" in field:
            row[columns[index]] = field["stringValue"]
        elif "longValue" in field:
            row[columns[index]] = field["longValue"]
        elif "doubleValue" in field:
            row[columns[index]] = field["doubleValue"]
        elif "booleanValue" in field:
            row[columns[index]] = field["booleanValue"]
        elif "isNull" in field:
            row[columns[index]] = None
        else:
            row[columns[index]] = str(field)
    return row


def _statement_args(sql: str, parameters: Optional[list]) -> Dict[str, Any]:
    """Build the common ``execute_statement`` keyword arguments."""
    args: Dict[str, Any] = {
        "resourceArn": DB_CLUSTER_ARN,
        "secretArn": SECRET_ARN,
        "database": DATABASE,
        "sql": sql,
        # Without this the Data API omits columnMetadata entirely, so columns
        # is [] and the first returned row IndexErrors (box-verified
        # 2026-06-12 — "list index out of range" on every successful SELECT).
        "includeResultMetadata": True,
    }
    if parameters:
        args["parameters"] = parameters
    return args


def execute_sql(sql: str, parameters: Optional[list] = None) -> List[Dict[str, Any]]:
    """Execute one statement via the Data API and return rows as dicts.

    Args:
        sql: A single statement. The Data API does not accept more than one
            ("Multistatements aren't supported"), which is why session settings
            need `execute_in_transaction` instead of a prepended ``SET``.
        parameters: Data API parameter dicts, or None.

    Returns:
        The result rows.
    """
    response = rds_client.execute_statement(**_statement_args(sql, parameters))
    columns = [column["name"] for column in response.get("columnMetadata", [])]
    return [row_to_dict(record, columns) for record in response.get("records", [])]


def execute_write(sql: str, parameters: Optional[list] = None) -> None:
    """Execute a statement whose rows are not the point.

    Distinct from `execute_sql` so a write and a read are different calls at
    this seam. Collapsing them would make an evidence INSERT indistinguishable
    from a catalog SELECT to anything observing the transport, including tests
    that stub reads while capturing writes.

    Args:
        sql: A single INSERT, UPDATE, or DELETE.
        parameters: Data API parameter dicts, or None.
    """
    rds_client.execute_statement(**_statement_args(sql, parameters))


def begin_transaction() -> str:
    """Open a Data API transaction and return its id.

    Transport, like everything else here, so it belongs to the module that owns
    the client. A surface server holding its own client would give the process
    two of them, and then a mutation and its audit row could be issued through
    different clients while looking like one transaction in the code.

    Returns:
        The transaction id to pass to `execute_in_transaction`, `commit`, or
        `rollback`.
    """
    return rds_client.begin_transaction(
        resourceArn=DB_CLUSTER_ARN, secretArn=SECRET_ARN, database=DATABASE
    )["transactionId"]


def commit_transaction(transaction_id: str) -> None:
    """Commit a Data API transaction."""
    rds_client.commit_transaction(
        resourceArn=DB_CLUSTER_ARN, secretArn=SECRET_ARN, transactionId=transaction_id
    )


def rollback_transaction(transaction_id: str) -> None:
    """Roll back a Data API transaction, swallowing a secondary failure.

    Called from an exception handler. Raising here would replace the error the
    caller is already reporting with a less useful one.
    """
    try:
        rds_client.rollback_transaction(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=SECRET_ARN,
            transactionId=transaction_id,
        )
    except Exception:  # pragma: no cover - best effort during failure handling
        logger.warning("rollback failed for transaction %s", transaction_id)


def execute_in_transaction(
    transaction_id: str, sql: str, parameters: Optional[list] = None
) -> List[Dict[str, Any]]:
    """Execute one statement inside an existing Data API transaction.

    Statements sharing a ``transactionId`` share a server-side transaction, so
    transaction-scoped settings established by an earlier call still apply.

    Args:
        transaction_id: From ``begin_transaction``.
        sql: A single statement.
        parameters: Data API parameter dicts, or None.

    Returns:
        The result rows.
    """
    args = _statement_args(sql, parameters)
    args["transactionId"] = transaction_id
    response = rds_client.execute_statement(**args)
    columns = [column["name"] for column in response.get("columnMetadata", [])]
    return [row_to_dict(record, columns) for record in response.get("records", [])]


def bind_runtime_principal(
    transaction_id: str,
    *,
    customer_subject: Optional[str],
    role: str = "pellier_agent",
) -> None:
    """Bind the runtime role and the customer subject inside this transaction.

    This is what makes Row-Level Security real on the Gateway rail. Without it
    the Data API executes as the secret's user, which owns the tables and
    therefore bypasses RLS entirely, so a governed write behind the Gateway was
    never actually row-scoped.

    Two things must be true at once, on the same server-side transaction:

      * the effective role is not the table owner (``SET LOCAL ROLE``);
      * ``pellier.principal_sub`` is set transaction-locally.

    Statements sharing a ``transactionId`` share one server-side transaction, so
    a setting established here still applies to the protected statement that
    follows. Issuing either one outside the transaction would be a no-op with a
    warning, and a silently unbound principal is the failure this exists to
    prevent.

    ``customer_subject`` of ``None`` binds the empty string, which the policies
    resolve to no customer scope. That denies rather than widens, and it is bound
    explicitly so the intent is legible in the transaction rather than being an
    absent setting.

    Args:
        transaction_id: From ``begin_transaction``.
        customer_subject: The Cognito subject of the CUSTOMER whose rows the
            statement touches — never the operator's. Cedar authorizes the
            operator; RLS scopes the customer.
        role: Runtime role to assume. Whitelisted rather than interpolated
            because ``SET ROLE`` takes no parameters.
    """
    if role not in _RUNTIME_ROLES:
        raise ValueError(
            f"Unknown runtime role {role!r}; expected one of "
            f"{', '.join(sorted(_RUNTIME_ROLES))}"
        )
    execute_in_transaction(transaction_id, f"SET LOCAL ROLE {role};")
    execute_in_transaction(
        transaction_id,
        "SELECT set_config('pellier.principal_sub', :subject, true);",
        [
            {
                "name": "subject",
                "value": {"stringValue": str(customer_subject or "")},
            }
        ],
    )


def write_tool_audit_independently(
    *,
    tool: str,
    args: Dict[str, Any],
    result: Dict[str, Any],
    latency_ms: float,
    session_id: str,
) -> None:
    """Write the execution receipt in its OWN transaction, so it survives.

    The audit row used to be written inside the mutation's transaction, which
    meant a rolled-back business write took its receipt with it. That makes the
    most important governance outcome unprovable: an action that Cedar allowed,
    that entered the tool, and that Aurora then refused would leave no trace at
    all, and "nothing happened" would be indistinguishable from "nothing was ever
    attempted".

    So the receipt commits independently. The ordering guarantee that matters is
    preserved by the caller: nothing writes a receipt unless the tool was
    actually entered, and a Cedar denial never reaches this module.

    This writer can only INSERT into ``pellier.tool_audit``. It cannot alter
    business state, by construction, so an audit failure can never corrupt a
    mutation and vice versa.
    """
    try:
        execute_write(
            f"INSERT INTO {SCHEMA}.tool_audit "
            "(session_id, tool, caller, args, result, latency_ms) "
            "VALUES (:session_id, :tool, 'gateway', :args::jsonb, :result::jsonb, "
            ":latency_ms);",
            [
                {"name": "session_id", "value": {"stringValue": session_id}},
                {"name": "tool", "value": {"stringValue": tool}},
                {"name": "args", "value": {"stringValue": json.dumps(args, default=str)}},
                {
                    "name": "result",
                    "value": {"stringValue": json.dumps(result, default=str)},
                },
                {"name": "latency_ms", "value": {"longValue": int(latency_ms)}},
            ],
        )
    except Exception as exc:  # noqa: BLE001 - evidence must not break the write
        logger.error("independent tool_audit write failed for %s: %s", tool, exc)


def write_tool_audit(
    transaction_id: str,
    *,
    tool: str,
    args: Dict[str, Any],
    result: Dict[str, Any],
    latency_ms: float,
    session_id: str,
) -> None:
    """Write the Gateway audit row inside the mutation's own transaction.

    On the in-process rail the FastAPI PolicyEnforcementHook writes this row.
    Behind the Gateway the tool runs in the Lambda, so the Lambda writes it.
    That is what makes the governed ALLOW proof queryable: every call that
    reaches a Lambda was already ALLOWed by AgentCore Policy at the Gateway, and
    a DENY never invokes the Lambda, so no row exists. The absence is the proof.

    The mutation and its evidence row commit or roll back together. A successful
    write without its audit row would violate the governed workshop contract,
    which is why this takes a ``transaction_id`` rather than writing on its own.

    ``session_id`` is the caller's to choose, and the two callers legitimately
    differ. The Gateway-to-Lambda event is ``{name, arguments}`` only and
    carries no session, so each surface keys on the most specific identity it
    actually has:

      * A customer-scoped tool passes ``gateway-<customer_id>``, since
        ``customer_id`` is present in its arguments. Governed queries then
        filter on ``args->>'customer_id'``.
      * An operator tool such as ``restock_inventory`` has no customer in its
        arguments at all, so it passes a role handle like
        ``gateway-stock-keeper``. Deriving ``gateway-<customer_id>`` there would
        write ``gateway-unknown`` on every row.

    Schema (scripts/migrations/002_workshop_telemetry.sql):
    ``tool_audit(session_id, tool, caller, args JSONB, result JSONB, latency_ms)``

    Args:
        transaction_id: The mutation's transaction, from ``begin_transaction``.
        tool: Tool name as published on the Gateway.
        args: Arguments the tool received.
        result: Result the tool produced.
        latency_ms: Observed tool latency.
        session_id: Queryable session handle. See the note above.
    """
    rds_client.execute_statement(
        resourceArn=DB_CLUSTER_ARN,
        secretArn=SECRET_ARN,
        database=DATABASE,
        transactionId=transaction_id,
        sql=(
            f"INSERT INTO {SCHEMA}.tool_audit "
            "(session_id, tool, caller, args, result, latency_ms) "
            "VALUES (:sid, :tool, :caller, :args::jsonb, :result::jsonb, :ms)"
        ),
        parameters=[
            {"name": "sid", "value": {"stringValue": session_id}},
            {"name": "tool", "value": {"stringValue": tool}},
            {"name": "caller", "value": {"stringValue": "gateway"}},
            {"name": "args", "value": {"stringValue": json.dumps(args, default=str)}},
            {
                "name": "result",
                "value": {"stringValue": json.dumps(result, default=str)},
            },
            {"name": "ms", "value": {"longValue": int(latency_ms)}},
        ],
    )


def query_embedding(text: str) -> List[float]:
    """Embed a live shopper query in the catalog's vector space.

    ``input_type`` is ``search_query`` because these are queries, not catalog
    documents. See `EMBED_MODEL_ID` for why the model must not diverge from the
    in-process rail.

    Args:
        text: The shopper's query text.

    Returns:
        A 1024-dimension embedding.
    """
    response = bedrock_client.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps(
            {
                "texts": [text],
                "input_type": "search_query",
                "output_dimension": EMBED_DIMENSION,
            }
        ),
    )
    return json.loads(response["body"].read())["embeddings"]["float"][0]
