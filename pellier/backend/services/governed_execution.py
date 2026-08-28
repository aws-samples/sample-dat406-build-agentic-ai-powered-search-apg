"""Governed execution of a confirmed operator review.

Prompt 3 ended at "a human said yes". This module answers the next question:
*is the system actually allowed to do it?* — and keeps the four answers separate.

Two principals, two boundaries
------------------------------

The discovery that shapes this module is that a governed operator action has two
identities, and overloading one field with both meanings would hide the lesson:

    ACTOR PRINCIPAL     the authenticated operator
                        → what AgentCore Policy / Cedar authorizes
                        → "may this person attempt this operation?"

    CUSTOMER SUBJECT    the client whose rows the action touches
                        → what Aurora Row-Level Security scopes
                        → "may this operation touch these rows?"

They are different questions with different answers. An operator can be fully
authorized to attempt a return and still be outside the data scope of the client
it belongs to — verified read-only against the live cluster, where an operator
subject sees zero of Theo's orders.

The customer subject is resolved **server-side** from the approved review, never
accepted from the caller. That is the whole reason the resolution lives here and
not in the route: a client that could name its own RLS principal could read and
write any customer's rows while still passing every other check.

Three independent controls
--------------------------

    Cedar        may this principal attempt this action?
    RLS          may this session touch these rows?
    CHECK        is this mutation valid regardless of who asked?

Each can fail while the others pass. The assurance axes this module returns are
derived from separate artifacts, never from one another.

What this module will not do
----------------------------

It will not report a policy verdict that no policy engine produced. On a rail
where Cedar is not consulted, the policy axis says ``NOT_EVALUATED`` and carries
the reason. A convenient ``ALLOW`` there would be the single most damaging lie
this surface could tell.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

RAIL_GATEWAY = "gateway-mcp"
RAIL_IN_PROCESS = "in-process"

# Policy axis. ALLOW / DENY / WOULD_DENY come only from a real policy engine
# response; NOT_EVALUATED means nothing was asked, which is a fact rather than a
# failure.
POLICY_ALLOW = "ALLOW"
POLICY_DENY = "DENY"
POLICY_WOULD_DENY = "WOULD_DENY"
POLICY_NOT_EVALUATED = "NOT_EVALUATED"

# Aurora axis.
AURORA_PERMITTED = "PERMITTED"
AURORA_DENIED = "DENIED"
AURORA_NOT_REACHED = "NOT_REACHED"
AURORA_NOT_ENFORCED = "NOT_ENFORCED"

# Evidence axis. Each value names what actually exists.
EVIDENCE_RECEIPTED = "RECEIPTED"
EVIDENCE_POLICY_PROOF = "POLICY_PROOF"
EVIDENCE_ATTEMPT_RECEIPT = "ATTEMPT_RECEIPT"
EVIDENCE_NO_EXECUTION = "NO_EXECUTION"
EVIDENCE_PENDING = "PENDING"


class ExecutionError(Exception):
    """An execution refused before any governed call was attempted."""

    def __init__(self, code: str, status_code: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass
class ExecutionOutcome:
    """One governed execution attempt, with each axis resolved separately."""

    rail: str
    execution_turn_id: str
    idempotency_key: str
    operator_sub: str
    customer_subject: Optional[str]
    policy: str
    aurora: str
    evidence: str
    tool: str
    result: Dict[str, Any] = field(default_factory=dict)
    # Human-readable reason per axis, so a surface never has to infer why.
    notes: Dict[str, str] = field(default_factory=dict)

    def as_payload(self) -> Dict[str, Any]:
        return {
            "rail": self.rail,
            "executionTurnId": self.execution_turn_id,
            "idempotencyKey": self.idempotency_key,
            "actorPrincipal": self.operator_sub,
            "customerSubject": self.customer_subject,
            "assurance": {
                "human": "CONFIRMED",
                "policy": self.policy,
                "aurora": self.aurora,
                "evidence": self.evidence,
            },
            "notes": dict(self.notes),
            "tool": self.tool,
            "result": self.result,
        }


# ---------------------------------------------------------------------------
# Trusted customer-subject resolution
# ---------------------------------------------------------------------------

_SUBJECT_SELECT = """
    SELECT principal_sub
      FROM pellier.principal_customers
     WHERE customer_id = %s
     ORDER BY principal_sub
     LIMIT 1
"""


async def resolve_customer_subject(db: Any, customer_id: str) -> Optional[str]:
    """The RLS subject for a customer, from the authorization mapping table.

    ``pellier.principal_customers`` is authorization configuration, not turn
    evidence. Returning ``None`` when a customer has no mapping is deliberate and
    is not an error: RLS then resolves no scope and denies, which is the correct
    fail-closed outcome for a client whose identity was never linked.

    This is the ONLY way an execution obtains an RLS subject. Nothing reads it
    from a request body.
    """
    try:
        row = await db.fetch_one(_SUBJECT_SELECT, str(customer_id))
    except Exception as exc:  # noqa: BLE001
        logger.error("customer-subject resolution failed for %s: %s", customer_id, exc)
        return None
    if not row:
        logger.info(
            "customer %s has no principal_customers mapping; RLS will fail closed",
            customer_id,
        )
        return None
    value = row["principal_sub"] if isinstance(row, Mapping) else row[0]
    return str(value) if value else None


# ---------------------------------------------------------------------------
# Confirmation integrity
# ---------------------------------------------------------------------------


def verify_confirmation(review: Mapping[str, Any]) -> Dict[str, Any]:
    """Recompute the fingerprint from the persisted args and require a match.

    The stored hash is what a human was shown and agreed to. Re-deriving it from
    the row's own arguments proves the two still agree, so the action about to
    execute is materially the action that was confirmed. A mismatch means the row
    was edited after confirmation, and no policy or database call may follow.

    Returns the material parameters to execute with. Those come from the review,
    never from the caller.
    """
    import hmac

    from services import operator_review as rv

    status = str(review.get("status") or "")
    if status == rv.STATUS_PENDING:
        raise ExecutionError("review_not_confirmed", 409)
    if status != rv.STATUS_CONFIRMED:
        raise ExecutionError("review_declined", 409)

    action = str(review.get("action") or "")
    if action not in rv.REVIEWABLE_ACTIONS:
        raise ExecutionError("action_not_executable", 422)

    args = review.get("args")
    if isinstance(args, str):
        import json

        try:
            args = json.loads(args)
        except ValueError:
            raise ExecutionError("stored_parameters_invalid", 409) from None
    if not isinstance(args, Mapping):
        raise ExecutionError("stored_parameters_invalid", 409)

    stored = str(review.get("action_hash") or "").strip()
    if not stored:
        raise ExecutionError("confirmation_missing_fingerprint", 409)

    try:
        recomputed = rv.action_fingerprint(action, args)
    except rv.ReviewError:
        raise ExecutionError("stored_parameters_invalid", 409) from None

    if not hmac.compare_digest(stored, recomputed):
        raise ExecutionError("confirmation_invalid", 409)

    return dict(args)


def execution_idempotency_key(review_id: int, action_hash: str) -> str:
    """The write key for one confirmed action, derived deterministically.

    Derived rather than generated so every retry of the same confirmed review
    claims the same key and collapses through the existing
    ``pellier.write_operations`` claim / replay / conflict machinery. A fresh
    ``uuid4`` per request — which the older operator endpoints use — would make
    "Retry" a second business mutation.

    The fingerprint is included so that a review whose parameters somehow changed
    could never silently reuse the previous key. Truncated to keep the value
    inside the 128-character column while staying collision-free in practice.
    """
    return f"operator-review:{int(review_id)}:{str(action_hash)[:32]}"


# ---------------------------------------------------------------------------
# execution_turn_id: assigned once, reused on retry
# ---------------------------------------------------------------------------

_CLAIM_EXECUTION_TURN = """
    UPDATE pellier.approvals
       SET execution_turn_id = %s
     WHERE id = %s
       AND status = 'approved'
       AND execution_turn_id IS NULL
    RETURNING execution_turn_id
"""

_READ_EXECUTION_TURN = """
    SELECT execution_turn_id
      FROM pellier.approvals
     WHERE id = %s
"""


async def claim_execution_turn(db: Any, review_id: int) -> str:
    """Return this review's execution turn, assigning one on first execution.

    Assign-once semantics live in the UPDATE's ``WHERE execution_turn_id IS
    NULL``, so two concurrent executes cannot mint two turns for one confirmed
    action: the loser reads the winner's value. The alternative — minting per
    request — would make one confirmed action look like several attempts and
    would break Observatory lineage.
    """
    from services.turn_identity import new_turn_id

    candidate = new_turn_id()
    row = await db.fetch_one(_CLAIM_EXECUTION_TURN, candidate, int(review_id))
    if row:
        value = row["execution_turn_id"] if isinstance(row, Mapping) else row[0]
        if value:
            return str(value)

    existing = await db.fetch_one(_READ_EXECUTION_TURN, int(review_id))
    if existing:
        value = (
            existing["execution_turn_id"]
            if isinstance(existing, Mapping)
            else existing[0]
        )
        if value:
            return str(value)
    # The review is not approved, or vanished. Both are refusals, not turns.
    raise ExecutionError("execution_turn_unavailable", 409)


# ---------------------------------------------------------------------------
# The policy artifact
# ---------------------------------------------------------------------------

_RECORD_RECEIPT = """
INSERT INTO pellier.execution_receipts
    (execution_turn_id, review_id, tool, gateway_action_id, rail,
     actor_principal, customer_subject, policy_outcome, aurora_outcome,
     evidence_outcome, policy_engine_id, gateway_mode, matching_forbids,
     idempotency_key, notes)
VALUES
    (%(execution_turn_id)s, %(review_id)s, %(tool)s, %(gateway_action_id)s,
     %(rail)s, %(actor_principal)s, %(customer_subject)s, %(policy_outcome)s,
     %(aurora_outcome)s, %(evidence_outcome)s, %(policy_engine_id)s,
     %(gateway_mode)s, %(matching_forbids)s, %(idempotency_key)s, %(notes)s)
RETURNING receipt_id
"""


async def record_receipt(
    db: Any,
    outcome: "ExecutionOutcome",
    *,
    review_id: int,
    engine_state: Optional["PolicyEngineState"] = None,
) -> Optional[int]:
    """Persist the verdicts for one governed execution attempt.

    Migration 021 deferred governance state to "its own artifacts: the policy
    decision, the ``tool_audit`` receipt, ``write_operations``, and the domain rows".
    Three of those existed. This writes the fourth, which is the only one that cannot
    be recovered afterwards: a Cedar DENY produces no audit row by design, claims no
    idempotency key, and touches no domain table, so before this table a denial was
    provable only from the HTTP response the operator happened to be looking at.

    Append-only, one row per attempt — see migration 025 for why a retry must not
    overwrite its predecessor.

    Never raises. The receipt is evidence ABOUT an execution that has already
    happened, so a failure to record it must not turn a successful governed write into
    an error the operator sees. It logs at warning, because a silent gap here is
    indistinguishable from an execution that never occurred.
    """
    from services.managed_policy import policy_engine_id

    params = {
        "execution_turn_id": outcome.execution_turn_id,
        "review_id": int(review_id),
        "tool": outcome.tool,
        "gateway_action_id": gateway_action_id(outcome.tool),
        "rail": outcome.rail,
        "actor_principal": outcome.operator_sub,
        "customer_subject": outcome.customer_subject,
        "policy_outcome": outcome.policy,
        "aurora_outcome": outcome.aurora,
        "evidence_outcome": outcome.evidence,
        # Attribution for the verdict. Both are None on the in-process rail, which is
        # correct: that rail consults no policy engine and its NOT_EVALUATED means
        # something different from an unreadable engine on the Gateway rail.
        "policy_engine_id": policy_engine_id() if outcome.rail == RAIL_GATEWAY else None,
        "gateway_mode": getattr(engine_state, "gateway_mode", "") or None,
        "matching_forbids": list(getattr(engine_state, "matching_forbids", ()) or ()),
        "idempotency_key": outcome.idempotency_key,
        "notes": json.dumps(outcome.notes or {}),
    }
    try:
        # Cursor rather than `db.fetch_one`, which forwards `*params` as a tuple and so
        # reports "15 placeholders but 1 parameters" for a named-placeholder statement.
        # Same shape as `operator_episodes.store_episode`.
        async with db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_RECORD_RECEIPT, params)
                row = await cur.fetchone()
    except Exception as exc:  # noqa: BLE001 - evidence must not break the write
        logger.warning(
            "execution receipt not recorded for review %s turn %s: %s",
            review_id, outcome.execution_turn_id, exc,
        )
        return None
    if not row:
        return None
    value = row["receipt_id"] if isinstance(row, Mapping) else row[0]
    return int(value) if value is not None else None


_LATEST_RECEIPT = """
SELECT r.receipt_id, r.execution_turn_id, r.review_id, r.tool, r.gateway_action_id,
       r.rail, r.actor_principal, r.customer_subject, r.policy_outcome,
       r.aurora_outcome, r.evidence_outcome, r.policy_engine_id, r.gateway_mode,
       r.matching_forbids, r.idempotency_key, r.notes, r.created_at,
       -- The domain row this execution produced, joined on the write key rather than
       -- guessed from timestamps. Without it the ReviewRecord counted the return IT
       -- had just created among the client's "previous damaged returns".
       (w.result->>'return_id')::bigint AS produced_return_id
  FROM pellier.execution_receipts r
  LEFT JOIN pellier.write_operations w
         ON w.idempotency_key = r.idempotency_key
        AND w.completed_at IS NOT NULL
 WHERE r.review_id = %s
 ORDER BY r.receipt_id DESC
 LIMIT 1
"""


_LATEST_RECEIPTS_BATCH = """
SELECT DISTINCT ON (review_id)
       receipt_id, execution_turn_id, review_id, tool, gateway_action_id, rail,
       actor_principal, customer_subject, policy_outcome, aurora_outcome,
       evidence_outcome, policy_engine_id, gateway_mode, matching_forbids,
       idempotency_key, notes, created_at
  FROM pellier.execution_receipts
 WHERE review_id = ANY(%s)
 ORDER BY review_id, receipt_id DESC
"""


async def latest_receipts(db: Any, review_ids: Any) -> Dict[int, Dict[str, Any]]:
    """The newest attempt per review, in one round trip, keyed by review id.

    For the review queue. A per-row read would make the queue's cost scale with its
    length for a column most rows do not have.

    Never raises: an unreadable receipt table must leave the queue listable. An empty
    mapping then reads as "no execution recorded", which is what the caller renders
    for the majority of reviews anyway.
    """
    ids = [int(r) for r in (review_ids or [])]
    if not ids:
        return {}
    try:
        rows = await db.fetch_all(_LATEST_RECEIPTS_BATCH, ids)
    except Exception as exc:  # noqa: BLE001 - the queue must stay listable
        logger.warning("execution receipt batch read failed: %s", exc)
        return {}
    return {int(row["review_id"]): dict(row) for row in (rows or [])}


async def latest_receipt(db: Any, review_id: int) -> Optional[Dict[str, Any]]:
    """The newest execution attempt for this review, or None if none was attempted.

    None is a real answer — most reviews have never executed — and the caller must
    render it as "not yet attempted" rather than as any particular verdict.

    Never raises: an unreadable receipt table must not make a review unviewable. The
    caller falls back to the pre-execution axes, which is the honest reading when this
    read produced nothing.
    """
    try:
        return await db.fetch_one(_LATEST_RECEIPT, int(review_id))
    except Exception as exc:  # noqa: BLE001 - a review must stay viewable
        logger.warning("execution receipt read failed for review %s: %s", review_id, exc)
        return None


# ---------------------------------------------------------------------------
# Reconstruction: the story of one governed execution, layer by layer
# ---------------------------------------------------------------------------

# The audit rows for one execution, joined on the WRITE KEY.
#
# This is the linkage `pellier.tool_audit` was missing, and it turned out to already be
# there: the Lambda behind the Gateway records the `idempotency_key` it was called with
# into the audit row's arguments, and that key is
# `operator-review:{review_id}:{hash-prefix}` — derived, deterministic, and identical to
# the one on the execution receipt. So no schema change, no new identifier family, and
# no timestamp heuristic.
#
# `session_id` cannot do this job: it holds `gateway-CUST-THEO`, which identifies the
# client, not the attempt.
_AUDIT_FOR_KEY = """
SELECT audit_id, session_id, tool, caller, latency_ms, created_at,
       args, result
  FROM pellier.tool_audit
 WHERE args->>'idempotency_key' = %s
 ORDER BY audit_id
"""

_WRITE_OPS_FOR_KEY = """
SELECT idempotency_key, operation, request_hash, created_at, completed_at, result
  FROM pellier.write_operations
 WHERE idempotency_key = %s
"""

_RECEIPTS_FOR_REVIEW = """
SELECT receipt_id, execution_turn_id, review_id, tool, gateway_action_id, rail,
       actor_principal, customer_subject, policy_outcome, aurora_outcome,
       evidence_outcome, policy_engine_id, gateway_mode, matching_forbids,
       idempotency_key, notes, created_at
  FROM pellier.execution_receipts
 WHERE review_id = %s
 ORDER BY receipt_id
"""

# Principal-scoped, exactly as `governed_receipts.principal_id` scopes the shopper rail.
# The visibility authority for an operator execution is the receipt's `actor_principal`:
# the operator AgentCore Policy authorized. Not removed, not widened — moved onto the
# artifact that actually records who acted.
_REVIEWS_FOR_PRINCIPAL = """
SELECT DISTINCT a.id AS review_id, a.customer_id, a.tool, a.status,
       a.source_turn_id, a.execution_turn_id, a.decided_at,
       r.policy_outcome, r.aurora_outcome, r.evidence_outcome, r.created_at
  FROM pellier.execution_receipts r
  JOIN pellier.approvals a ON a.id = r.review_id
 WHERE r.actor_principal = %s
   AND r.receipt_id = (
       SELECT max(receipt_id) FROM pellier.execution_receipts
        WHERE review_id = r.review_id
   )
 ORDER BY r.created_at DESC
 LIMIT %s
"""

_EPISODE_FOR_REVIEW = """
SELECT episode_id, episode_type, situation, resolution, human_outcome,
       policy_outcome, aurora_outcome, source_turn_id, execution_turn_id, created_at
  FROM pellier.operator_episodes
 WHERE review_id = %s
 ORDER BY episode_id
"""

# `product_id` is TEXT in pellier.returns and an integer in the review's args, so both
# sides are cast. Without it: `operator does not exist: text = smallint`.
_RETURNS_FOR_REVIEW = """
SELECT id, customer_id, product_id, order_id, reason, status, quantity, requested_at
  FROM pellier.returns
 WHERE customer_id = %s AND product_id::text = %s::text
 ORDER BY id DESC
"""


async def list_executions(
    db: Any, *, principal_sub: str, limit: int = 20
) -> List[Dict[str, Any]]:
    """Governed executions this principal performed, newest first. Never raises."""
    if not (principal_sub or "").strip():
        return []
    try:
        rows = await db.fetch_all(
            _REVIEWS_FOR_PRINCIPAL, principal_sub, max(1, min(50, int(limit)))
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("execution list read failed: %s", exc)
        return []
    return [dict(r) for r in (rows or [])]


async def reconstruct_execution(
    db: Any, *, review_id: int, principal_sub: str
) -> Optional[Dict[str, Any]]:
    """The whole story of one governed execution, as layers that may legitimately stop.

    THE SPINE IS THE RECEIPT, NOT THE TOOL. Execution evidence for a governed system
    begins at the authorization attempt, not at the tool call:

        approval            a human agreed to exact terms
          -> receipt        the attempt, and what each layer decided
            -> tool_audit   present only if the tool was entered
            -> write_ops    present only if the tool claimed its key
              -> domain     present only if the write applied

    An absent downstream layer is EVIDENCE, not missing data. Rachel's execution has no
    audit row and no idempotency claim, and that is precisely what proves Cedar refused
    her action before the tool ran. A reconstruction that required a `tool_audit` row
    could not render her at all — which is why the previous query, rooted at
    `tool_audit` and joined through `governed_receipts`, returned nothing for the entire
    operator rail.

    Returns None when this principal did not perform this execution, or when no
    execution has been attempted. Never raises.
    """
    try:
        receipts = await db.fetch_all(_RECEIPTS_FOR_REVIEW, int(review_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("reconstruction receipt read failed for %s: %s", review_id, exc)
        return None
    receipts = [dict(r) for r in (receipts or [])]
    if not receipts:
        return None
    # Authorization: the operator who acted is the one who may read it back.
    if not any(str(r.get("actor_principal") or "") == principal_sub for r in receipts):
        return None

    latest = receipts[-1]
    key = str(latest.get("idempotency_key") or "")

    review = await db.fetch_one(
        "SELECT id AS review_id, customer_id, tool, args, status, source_turn_id,"
        " execution_turn_id, action_hash, decided_by, requested_at, decided_at"
        " FROM pellier.approvals WHERE id = %s",
        int(review_id),
    )
    review = dict(review) if review else {}
    args = review.get("args") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {}

    audit = [dict(r) for r in (await db.fetch_all(_AUDIT_FOR_KEY, key) or [])] if key else []
    writes = [dict(r) for r in (await db.fetch_all(_WRITE_OPS_FOR_KEY, key) or [])] if key else []
    episodes = [dict(r) for r in (await db.fetch_all(_EPISODE_FOR_REVIEW, int(review_id)) or [])]
    domain: List[Dict[str, Any]] = []
    if review.get("customer_id") and args.get("product_id") is not None:
        domain = [dict(r) for r in (await db.fetch_all(
            _RETURNS_FOR_REVIEW,
            str(review["customer_id"]),
            str(args["product_id"]),
        ) or [])]

    return {
        "review": {**review, "args": args},
        "receipts": receipts,
        "latestReceipt": latest,
        "toolAudit": audit,
        "writeOperations": writes,
        "domain": domain,
        "episodes": episodes,
        "layers": describe_layers(latest, audit, writes, domain, episodes),
    }


def describe_layers(
    receipt: Dict[str, Any],
    audit: List[Dict[str, Any]],
    writes: List[Dict[str, Any]],
    domain: List[Dict[str, Any]],
    episodes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Each layer, with why it is present or absent. Absence is never "missing data".

    Rendering "Missing data" where Rachel has no audit row would describe a gap in the
    evidence. There is no gap: the tool was never entered, and the reason is the layer
    above.
    """
    policy = str(receipt.get("policy_outcome") or "")
    aurora = str(receipt.get("aurora_outcome") or "")
    claimed = bool(writes)
    completed = any(w.get("completed_at") for w in writes)

    def layer(key: str, label: str, present: bool, detail: str) -> Dict[str, Any]:
        return {"key": key, "label": label, "present": present, "detail": detail}

    return [
        layer("review", "Human decision", True,
              "A person agreed to these exact parameters."),
        layer("receipt", "Authorization attempt", True,
              f"AgentCore Policy answered {policy}; the gateway was "
              f"{receipt.get('gateway_mode') or 'in an unrecorded mode'}."),
        layer(
            "tool_audit", "Tool execution", bool(audit),
            f"{len(audit)} execution receipt(s) on the write key."
            if audit else
            ("Tool not entered. AgentCore Policy denied the action before execution."
             if policy == POLICY_DENY else
             "No execution receipt on this write key."),
        ),
        layer(
            "write_operations", "Idempotency claim", claimed,
            ("Claimed and completed: the write applied exactly once."
             if completed else
             "Claimed and released: the tool was entered and the write did not apply.")
            if claimed else
            ("No claim was made, because the tool was never entered."
             if policy == POLICY_DENY else
             "No claim was made on this key."),
        ),
        layer(
            "domain", "Database effect", bool(domain) and completed,
            f"{len(domain)} row(s) in pellier.returns for this client and piece."
            if domain and completed else
            ("Row-level security refused the read the write depended on, so nothing "
             "changed." if aurora == AURORA_DENIED else
             "No domain row resulted from this execution."),
        ),
        layer(
            "episode", "Remembered", bool(episodes),
            "Recorded in Aurora episodic memory, and recallable later."
            if episodes else
            "No episode: this outcome was not terminal.",
        ),
    ]


# ---------------------------------------------------------------------------
# Rail selection
# ---------------------------------------------------------------------------


def gateway_action_id(tool: str) -> str:
    """The Gateway-qualified Cedar action id for a published tool."""
    from services.agentcore_gateway import GATEWAY_TARGET_FOR_TOOL

    target = GATEWAY_TARGET_FOR_TOOL.get(tool)
    if not target:
        raise ExecutionError(f"tool_not_published:{tool}", 422)
    return f"{target}___{tool}"


def select_rail(access_token: Optional[str]) -> str:
    """Gateway when it is configured and we hold the caller's token, else local.

    Identity passthrough is the point of the managed rail: the Gateway must see
    the operator's own JWT so Cedar authorizes a person rather than a service.
    Without a token there is nothing to authorize, so the managed rail is not
    merely unavailable — it would be meaningless.
    """
    from config import settings

    gateway_url = str(getattr(settings, "AGENTCORE_GATEWAY_URL", "") or "").strip()
    if gateway_url and access_token:
        return RAIL_GATEWAY
    return RAIL_IN_PROCESS


# ---------------------------------------------------------------------------
# Policy-denial classification
# ---------------------------------------------------------------------------

# Verbatim Gateway deny markers, box-verified 2026-06-12 and reused here rather
# than re-derived: "Tool call not allowed due to policy enforcement [Policy
# evaluation denied due to <policy>-...]".
#
# Deliberately NOT matched: bare AccessDenied / Unauthorized / Forbidden. Those
# describe IAM, JWT, or target failures, and treating them as Cedar denials would
# make a broken Gateway look like a successful governance proof — the single
# easiest way to fake this whole lesson.
_DENIAL_MARKERS = (
    "authorizeactionexception",
    "not allowed due to policy",
    "policy enforcement",
    "policy evaluation denied",
)


def is_policy_denial(error: BaseException | str) -> bool:
    """True only for a Gateway/Cedar authorization denial."""
    if isinstance(error, BaseException):
        children = getattr(error, "exceptions", None)
        if children:
            return any(is_policy_denial(child) for child in children)
        haystack = f"{error.__class__.__name__}: {error}".lower()
    else:
        haystack = str(error).lower()
    return any(marker in haystack for marker in _DENIAL_MARKERS)


# ---------------------------------------------------------------------------
# Aurora outcome classification
# ---------------------------------------------------------------------------


def classify_aurora(result: Mapping[str, Any]) -> tuple[str, str]:
    """Map a tool envelope onto the Aurora axis, with a reason.

    Only ``denied_by: database_row_level_security`` counts as an RLS denial. The
    in-process governed rail sets it after asking the database, inside the same
    transaction, whether the customer was in scope at all — so it distinguishes
    "not authorized" from "no such order", which are different facts that the
    write function reports with the same message.
    """
    status = str(result.get("status") or "")
    denied_by = str(result.get("denied_by") or "")

    if denied_by == "database_row_level_security":
        return AURORA_DENIED, (
            "Row-Level Security refused the read the write depends on, so "
            "nothing changed."
        )
    if status == "success":
        replay = bool(result.get("idempotent_replay"))
        return AURORA_PERMITTED, (
            "The write already applied under this key; this call replayed it."
            if replay
            else "The runtime role was in scope and the transaction committed."
        )
    if status == "idempotency_conflict":
        return AURORA_PERMITTED, (
            "The key was already claimed with different parameters, so the "
            "database refused a second, different write."
        )
    if status == "policy_blocked":
        # A business-rule refusal from the tool itself (for example a reason
        # outside the canonical set). Not a database authorization outcome.
        return AURORA_NOT_REACHED, (
            "The tool refused on a business rule before reaching the "
            "protected statement."
        )
    return AURORA_NOT_REACHED, str(result.get("message") or "The write did not run.")


# The exact sentence `pellier.process_return_idempotent` emits when its ownership
# SELECT finds no row. Matched on our own write function's fixed text, not on model
# output — and only ever used to RECLASSIFY, never to invent an outcome.
_OWNERSHIP_FAILURE_MARKER = "did not order"


def is_ownership_failure(result: Mapping[str, Any]) -> bool:
    """True when the tool reported that the customer does not own the product."""
    if str(result.get("status") or "") == "success":
        return False
    return _OWNERSHIP_FAILURE_MARKER in str(result.get("message") or "").lower()


def as_rls_denial(result: Mapping[str, Any], customer_id: str) -> Dict[str, Any]:
    """Reclassify an ownership failure that could only have been a visibility failure.

    A client with no ``pellier.principal_customers`` mapping resolves NO customer
    scope, so the ownership SELECT the write depends on was guaranteed to return
    nothing whatever the orders table contains. Reporting the tool's message verbatim
    would state a falsehood about Aurora's contents — "CUST-AMARA did not order
    product 46" while order 323 exists — and would disguise an authorization boundary
    as a data fact.

    The managed Gateway rail cannot make this distinction itself: the in-process rail
    asks the database, inside the same transaction, whether the customer is in scope,
    and sets ``denied_by``. The Lambda behind the Gateway does not, so it returns the
    bare message and the Aurora axis came back NOT_REACHED with the falsehood attached.

    The original tool text is preserved under ``tool_message`` rather than dropped:
    nothing is hidden, it simply stops being presented as business truth.
    """
    out = dict(result)
    out["denied_by"] = "database_row_level_security"
    out["tool_message"] = str(result.get("message") or "")
    out["message"] = (
        f"{customer_id} is not in scope for this database session, so the row the "
        "write depends on was not visible. The order relationship itself is unchanged."
    )
    return out


def classify_evidence_for(policy: str, aurora: str, result: Mapping[str, Any]) -> str:
    """The evidence axis names what artifact exists — never what we hoped for."""
    if policy == POLICY_DENY:
        # The tool was never entered, so there is no `tool_audit` row and no
        # idempotency claim. The policy decision itself is the artifact, and it is
        # durable in `pellier.execution_receipts` — before that table existed this
        # sentence named an artifact nothing wrote.
        return EVIDENCE_POLICY_PROOF
    if aurora == AURORA_DENIED:
        return EVIDENCE_ATTEMPT_RECEIPT
    if aurora == AURORA_PERMITTED and str(result.get("status")) in (
        "success",
        "idempotency_conflict",
    ):
        return EVIDENCE_RECEIPTED
    if aurora == AURORA_NOT_REACHED:
        return EVIDENCE_NO_EXECUTION
    return EVIDENCE_PENDING


# ---------------------------------------------------------------------------
# The two executors
# ---------------------------------------------------------------------------


async def _execute_in_process(
    db: Any,
    *,
    tool: str,
    args: Mapping[str, Any],
    idempotency_key: str,
    operator_sub: str,
    customer_subject: Optional[str],
) -> Dict[str, Any]:
    """Run the governed write locally, with RLS bound to the CUSTOMER subject.

    Note which principal goes where, because it is the whole point:

      * ``principal_sub`` on the write is the **customer subject**. It selects the
        RLS data scope. Passing the operator's own subject here — which the older
        ``/actions/*`` endpoints do — scopes the transaction to the operator's own
        rows, and the write then fails for every client the operator is not
        mapped to. Verified: an operator subject sees zero of Theo's orders.

      * ``issued_by`` on a credit is the **actor**. That is attribution, and it is
        the operator, because a credit must record which person authorised the
        money movement.

    Cedar is not consulted on this rail. The caller reports the policy axis as
    NOT_EVALUATED; this function never claims a verdict.
    """
    from services.business_logic import BusinessLogic

    logic = BusinessLogic(db)
    if tool == "initiate_return":
        return await logic.initiate_return(
            customer_id=str(args["customer_id"]),
            product_id=int(args["product_id"]),
            reason=str(args["reason"]),
            idempotency_key=idempotency_key,
            principal_sub=customer_subject,
        )
    if tool == "issue_credit":
        return await logic.issue_credit(
            customer_id=str(args["customer_id"]),
            amount_cents=int(args["amount_cents"]),
            reason=str(args["reason"]),
            idempotency_key=idempotency_key,
            issued_by=operator_sub or None,
        )
    raise ExecutionError(f"action_not_executable:{tool}", 422)


async def _execute_through_gateway(
    *,
    tool: str,
    args: Mapping[str, Any],
    idempotency_key: str,
    access_token: str,
) -> tuple[str, Dict[str, Any], str]:
    """Invoke the published tool through AgentCore Gateway, deterministically.

    No model in the loop. The arguments come from the confirmed review, and the
    call names the tool directly, so Cedar authorizes exactly the action a human
    approved rather than whatever a model decided to attempt.

    Returns ``(policy_state, result_envelope, note)``. A Cedar denial raises
    inside the MCP session before the Lambda target runs, which is why a denial
    leaves no ``tool_audit`` execution row: the tool was never entered.
    """
    import json

    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from config import settings

    gateway_url = str(settings.AGENTCORE_GATEWAY_URL).strip()
    action = gateway_action_id(tool)
    payload = {**{k: v for k, v in args.items()}, "idempotency_key": idempotency_key}

    timeout = httpx.Timeout(30.0, read=300.0)
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout,
            follow_redirects=True,
        ) as http_client:
            async with streamable_http_client(
                gateway_url, http_client=http_client
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    raw = await session.call_tool(action, payload)
    except Exception as exc:  # noqa: BLE001 - classified, not swallowed
        if is_policy_denial(exc):
            return (
                POLICY_DENY,
                {
                    "status": "policy_denied",
                    "message": "AgentCore Policy denied the action before the tool ran.",
                    "denied_by": "agentcore_policy",
                },
                "Cedar denied the action; the tool was never entered.",
            )
        # A transport, token, or target failure is NOT a governance proof.
        raise ExecutionError(f"gateway_unavailable:{type(exc).__name__}", 502) from exc

    # The Gateway returned, so Cedar permitted the action (or observed it in
    # LOG_ONLY and let it through — the caller resolves which from the engine's
    # own mode, never from this response).
    envelope: Dict[str, Any] = {}
    for item in getattr(raw, "content", None) or []:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            envelope = parsed
            break
    if not envelope:
        envelope = {"status": "error", "message": "Gateway returned no tool envelope."}
    return POLICY_ALLOW, envelope, "AgentCore Policy permitted the action."


# ---------------------------------------------------------------------------
# LOG_ONLY: a call that returned is not automatically an ALLOW
# ---------------------------------------------------------------------------


@dataclass
class PolicyEngineState:
    """The engine's own declared state, as the control plane reports it.

    Enforcement is the conjunction of two scopes with different vocabularies,
    verified against the live service: a *policy* is ``ACTIVE`` or ``LOG_ONLY``,
    a *gateway attachment* is ``ENFORCE`` or ``LOG_ONLY``. Either one in LOG_ONLY
    means no denial is enforced. Code that assumes a single ENFORCE/LOG_ONLY
    vocabulary reports the wrong mode for one of the two scopes.
    """

    gateway_mode: str = ""
    # policy name -> (effect, enforcement_mode)
    policies: Dict[str, tuple[str, str]] = field(default_factory=dict)
    # Forbid policies whose Cedar statement names this action.
    matching_forbids: tuple[str, ...] = ()

    @property
    def enforcement_is_on(self) -> bool:
        return str(self.gateway_mode).upper() == "ENFORCE"

    def observed_forbid(self) -> Optional[str]:
        """A forbid policy that matches this action and is switched on.

        A forbid in LOG_ONLY is not observed either — it is simply off. Only an
        ACTIVE forbid under a LOG_ONLY gateway produces a would-deny.
        """
        for name in self.matching_forbids:
            effect, mode = self.policies.get(name, ("", ""))
            if str(effect).lower() == "forbid" and str(mode).upper() == "ACTIVE":
                return name
        return None


def resolve_permissive_policy_state(
    engine: Optional[PolicyEngineState],
) -> tuple[str, str]:
    """Classify a Gateway call that RETURNED, using the engine's declared state.

    A returned call means the tool was reached. Whether that is an authorization
    or merely an unenforced observation depends on the engine, not on the
    response, so this reads the engine's own policy set and mode:

      * enforcement on  → the action was genuinely permitted → ALLOW
      * enforcement off and an ACTIVE forbid matches → WOULD_DENY, not enforced
      * enforcement off and nothing matches → ALLOW, with the mode disclosed

    Without engine state we do not guess. Reporting ALLOW because a call
    succeeded under LOG_ONLY would be the exact lie this arc exists to prevent.
    """
    if engine is None:
        return POLICY_NOT_EVALUATED, (
            "The policy engine state could not be read, so no verdict is claimed."
        )
    if engine.enforcement_is_on:
        return POLICY_ALLOW, "AgentCore Policy evaluated the action and permitted it."
    observed = engine.observed_forbid()
    if observed:
        return POLICY_WOULD_DENY, (
            f"{observed} matched this action and would have denied it. The gateway "
            f"is {engine.gateway_mode}, so the decision was observed, not enforced."
        )
    return POLICY_ALLOW, (
        f"No forbid policy matched. The gateway is {engine.gateway_mode}, so a "
        "denial would not have been enforced in any case."
    )


# ---------------------------------------------------------------------------
# The execution boundary
# ---------------------------------------------------------------------------


async def execute_confirmed_review(
    db: Any,
    review: Mapping[str, Any],
    *,
    operator_sub: str,
    access_token: Optional[str] = None,
    engine_state: Optional[PolicyEngineState] = None,
) -> ExecutionOutcome:
    """Execute the action a human confirmed, and report each axis separately.

    The ordering is the contract:

      1. verify the confirmation against the persisted parameters;
      2. resolve the customer subject server-side;
      3. claim or reuse the execution turn;
      4. derive the deterministic write key;
      5. invoke the governed rail;
      6. classify policy, Aurora, and evidence from what actually happened;
      7. record the verdicts, so a denial is provable after the response is gone;
      8. remember the outcome, so "have we seen this before?" is answerable later.

    Nothing in that sequence reads an action parameter from a caller. Steps 7 and 8 are
    both best-effort ABOUT an execution that has already happened: raising in either
    would report a completed governed write as a failure and invite a retry.
    """
    args = verify_confirmation(review)
    tool = str(review["action"])
    review_id = int(review["review_id"])
    action_hash = str(review["action_hash"])
    customer_id = str(args["customer_id"])

    customer_subject = await resolve_customer_subject(db, customer_id)
    execution_turn_id = await claim_execution_turn(db, review_id)
    idempotency_key = execution_idempotency_key(review_id, action_hash)

    rail = select_rail(access_token)
    notes: Dict[str, str] = {}

    if rail == RAIL_GATEWAY:
        policy, result, policy_note = await _execute_through_gateway(
            tool=tool,
            args=args,
            idempotency_key=idempotency_key,
            access_token=str(access_token),
        )
        if policy == POLICY_ALLOW:
            policy, policy_note = resolve_permissive_policy_state(engine_state)
        notes["policy"] = policy_note
    else:
        policy = POLICY_NOT_EVALUATED
        notes["policy"] = (
            "This execution ran in process, so AgentCore Policy was not "
            "consulted. Only the managed Gateway rail produces a Cedar verdict."
        )
        result = await _execute_in_process(
            db,
            tool=tool,
            args=args,
            idempotency_key=idempotency_key,
            operator_sub=operator_sub,
            customer_subject=customer_subject,
        )

    if policy == POLICY_DENY:
        aurora, aurora_note = AURORA_NOT_REACHED, (
            "The tool was never entered, so no statement reached the database."
        )
    elif customer_subject is None and tool == "initiate_return":
        # Fail closed and say why. RLS resolves no scope for an unmapped client, so
        # the write finds nothing; reporting that as "no such order" would disguise an
        # authorization boundary as a data fact.
        #
        # Reclassify rather than merely annotate. The previous version prefixed an
        # honest sentence and then repeated the falsehood, and left the axis at
        # NOT_REACHED — so the canonical database-enforcement outcome reported that no
        # statement had reached the database when one had, and been refused.
        if is_ownership_failure(result):
            result = as_rls_denial(result, customer_id)
        aurora, aurora_note = classify_aurora(result)
        if aurora != AURORA_DENIED:
            aurora_note = (
                f"{customer_id} has no identity mapping, so the session resolved "
                "no customer scope. " + aurora_note
            )
    else:
        aurora, aurora_note = classify_aurora(result)

    notes["aurora"] = aurora_note
    evidence = classify_evidence_for(policy, aurora, result)

    outcome = ExecutionOutcome(
        rail=rail,
        execution_turn_id=execution_turn_id,
        idempotency_key=idempotency_key,
        operator_sub=operator_sub,
        customer_subject=customer_subject,
        policy=policy,
        aurora=aurora,
        evidence=evidence,
        tool=tool,
        result=dict(result),
        notes=notes,
    )
    # Step 7, and it is not optional. Until this existed the verdicts lived only in the
    # response body: a Cedar DENY writes no tool_audit row, claims no idempotency key
    # and touches no domain table, so closing the tab destroyed the only proof that the
    # action had been refused. Recorded after classification so the stored receipt and
    # the returned payload carry the same axes, and best-effort so evidence about a
    # completed write can never fail the write.
    receipt_id = await record_receipt(
        db, outcome, review_id=review_id, engine_state=engine_state
    )

    # Step 8: remember the outcome, if it is one.
    #
    # A DERIVED memory, not an authoritative artifact. The receipt above is the proof;
    # this is what makes "have we handled something like this before?" answerable later.
    # It is derived from the receipt just written rather than from the classification in
    # flight, so the memory and the evidence cannot disagree, and it is keyed to the
    # review so a replay adds a receipt without adding a second episode.
    await _remember_outcome(db, review, outcome, receipt_id=receipt_id)
    return outcome


async def _remember_outcome(
    db: Any,
    review: Mapping[str, Any],
    outcome: "ExecutionOutcome",
    *,
    receipt_id: Optional[int],
) -> None:
    """Record the episodic memory of a reviewed execution. Never raises.

    Reads the receipt back when one was written, so the episode is derived from the
    durable row. Falls back to the in-flight outcome when the receipt could not be
    recorded: the execution still happened, and losing the memory as well as the receipt
    would be two gaps for one failure.
    """
    from services import operator_episodes as ep

    try:
        receipt: Optional[Dict[str, Any]] = None
        if receipt_id is not None:
            receipt = await latest_receipt(db, int(review["review_id"]))
        if receipt is None:
            receipt = {
                "policy_outcome": outcome.policy,
                "aurora_outcome": outcome.aurora,
                "tool": outcome.tool,
                "execution_turn_id": outcome.execution_turn_id,
                "idempotency_key": outcome.idempotency_key,
                "rail": outcome.rail,
            }
        await ep.record_outcome_episode(
            db, review=review, receipt=receipt, result=outcome.result
        )
    except Exception as exc:  # noqa: BLE001 - memory must not fail the execution
        logger.warning(
            "episode not recorded for review %s: %s", review.get("review_id"), exc
        )
