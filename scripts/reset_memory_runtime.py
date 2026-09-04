#!/usr/bin/env python3
"""Remove engineering runtime data from AgentCore Memory. Narrow by construction.

WHY A DATABASE RESET IS NOT ENOUGH
----------------------------------

`reset-governed-workshop.sh` restores Aurora to the canonical workshop baseline. It
cannot touch AgentCore Memory, and Memory is where two kinds of engineering residue
accumulate:

  * SHORT-TERM EVENTS, one per conversational turn, under the session's actor;
  * LONG-TERM USER_PREFERENCE records, which the strategy extracts from those turns
    into the namespace ``/pellier/preferences/{actorId}/``.

That namespace is ACTOR-scoped. Measured on 2026-08-27, the authenticated Operator
subject had 6 sessions, 16 events and 4 extracted preference records, all derived from
Operator Concierge engineering runs. Their content:

    "Prefers in-stock items"                        from a replacement-search test
    "requested a return for a product described     from a draft-note test
     as 'under-filled'"
    "an interest in ... suede chelsea boots"         from a replacement-search test

Those are a CLIENT's situation recorded as the OPERATOR's personal preference. Because
the workshop signs in as the same Operator subject, the first Concierge turn after a
clean Aurora reset would recall them, and a new session id changes nothing: session
scoping does not isolate an actor-scoped namespace.

WHAT THIS SCRIPT DOES NOT DO
----------------------------

  * It never deletes or reconfigures the Memory RESOURCE. No control-plane write.
  * It never touches an actor outside the Pellier memory id it is given.
  * It preserves the seeded persona actors. `seed-sample-preferences.sh` signs in as
    marco, anna and theo and posts their preference bundles, so `CUST-MARCO`,
    `CUST-ANNA` and `CUST-THEO` hold canonical baseline records that a fresh box also
    has. Deleting them would make the reset cluster emptier than a fresh one.

Dry run by default. Nothing is deleted without ``--apply``.

EXIT CODES
----------

  0  the Memory runtime is clean.
  1  at least one delete call failed.
  2  a delete pass completed and a re-list still found events or preference records.
  3  AgentCore Memory is NOT PROVISIONED here, so there is nothing to clean.

3 is separate from 1 on purpose. The reset quarantines a box on a failed Memory leg,
and only a full successful reset lifts that marker, so treating an absent Memory
resource as a failure would strand a box that can never produce one.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any, Dict, List

# Actors whose memory is canonical seeded baseline, not engineering residue. Written as
# a frozen set rather than a prefix rule: a prefix rule would silently start preserving
# a future `CUST-` actor nobody seeded.
PRESERVE_ACTORS = frozenset({"CUST-MARCO", "CUST-ANNA", "CUST-THEO"})

PREFERENCE_NAMESPACE = "/pellier/preferences/{actor}/"

# "This box has no Memory resource", which the reset must not confuse with
# "cleaning it failed". See EXIT CODES in the module docstring.
EXIT_NOT_PROVISIONED = 3


def _env() -> Dict[str, str]:
    """Read the backend .env. Refuses to guess a memory id.

    Returns:
        The dotenv values, which are guaranteed to carry ``AGENTCORE_MEMORY_ID``.

    Raises:
        SystemExit: With :data:`EXIT_NOT_PROVISIONED` when no memory id is
            configured. That is an absent resource, not a cleanup failure.
    """
    from dotenv import dotenv_values

    root = pathlib.Path(__file__).resolve().parents[1]
    for candidate in (root / ".env", root / "pellier" / "backend" / ".env"):
        if candidate.exists():
            values = {k: v for k, v in dotenv_values(candidate).items() if v}
            if values.get("AGENTCORE_MEMORY_ID"):
                return values
    print(
        "No .env with AGENTCORE_MEMORY_ID found. AgentCore Memory is not provisioned "
        "here, so there is no runtime data to clean and nothing to guess at.",
        file=sys.stderr,
    )
    raise SystemExit(EXIT_NOT_PROVISIONED)


def _client(region: str):
    """The DATA-plane client. Memory actors, sessions, events and records live here.

    Guarded before it is built: this script's whole value is the narrow per-item delete,
    and an SDK whose model lacks `DeleteMemoryRecord` would let the survey succeed and
    every deletion fail, reporting a cleaned Memory that still holds the previous
    participant's preferences.
    """
    import boto3

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "deploy"))
    from sdk_preflight import require_memory_runtime_support

    require_memory_runtime_support()
    return boto3.client("bedrock-agentcore", region_name=region)


def _paginate(call: Any, key: str, **kwargs: Any) -> List[Dict[str, Any]]:
    """Every item under ``key`` across all pages of a data-plane list call.

    Each list operation pages on ``nextToken``. A single ``maxResults=100`` call
    surveyed the first hundred items, deleted those, and reported a cleaned Memory
    that still held the rest.

    Args:
        call: The bound client method, for example ``client.list_events``.
        key: The response member holding the page's items.
        **kwargs: The call's own parameters, repeated on every page.

    Returns:
        The concatenated items from every page, in service order.
    """
    items: List[Dict[str, Any]] = []
    token: Any = None
    while True:
        params = dict(kwargs)
        if token:
            params["nextToken"] = token
        page = call(**params)
        items.extend(page.get(key, []))
        token = page.get("nextToken")
        if not token:
            return items


def survey(client: Any, memory_id: str) -> List[Dict[str, Any]]:
    """Every actor in this memory resource, with what it holds and how it is classified."""
    actors: List[Dict[str, Any]] = []
    for summary in _paginate(
        client.list_actors, "actorSummaries", memoryId=memory_id, maxResults=100
    ):
        actor = str(summary["actorId"])
        sessions: List[Dict[str, Any]] = []
        for session in _paginate(
            client.list_sessions, "sessionSummaries",
            memoryId=memory_id, actorId=actor, maxResults=100,
        ):
            events = _paginate(
                client.list_events, "events",
                memoryId=memory_id, actorId=actor,
                sessionId=session["sessionId"], maxResults=100,
            )
            sessions.append({
                "sessionId": session["sessionId"],
                "eventIds": [e["eventId"] for e in events],
            })
        records = _paginate(
            client.list_memory_records, "memoryRecordSummaries",
            memoryId=memory_id,
            namespace=PREFERENCE_NAMESPACE.format(actor=actor),
            maxResults=100,
        )
        actors.append({
            "actorId": actor,
            "preserve": actor in PRESERVE_ACTORS,
            "sessions": sessions,
            "eventCount": sum(len(s["eventIds"]) for s in sessions),
            "records": [
                {
                    "memoryRecordId": r["memoryRecordId"],
                    "text": ((r.get("content") or {}).get("text") or "")[:160],
                }
                for r in records
            ],
        })
    return actors


def apply_cleanup(
    client: Any, memory_id: str, actors: List[Dict[str, Any]], *, apply: bool
) -> Dict[str, int]:
    """Delete events and preference records for every non-preserved actor.

    Per-event and per-record, using the narrowest operations the SDK exposes
    (``delete_event`` and ``delete_memory_record``). No bulk or namespace-wide delete,
    so a mistake costs one row rather than an actor's whole history.
    """
    counts = {"events": 0, "records": 0, "actors": 0, "failures": 0}
    for entry in actors:
        if entry["preserve"]:
            continue
        counts["actors"] += 1
        for session in entry["sessions"]:
            for event_id in session["eventIds"]:
                counts["events"] += 1
                if not apply:
                    continue
                try:
                    client.delete_event(
                        memoryId=memory_id, actorId=entry["actorId"],
                        sessionId=session["sessionId"], eventId=event_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    counts["failures"] += 1
                    print(f"  ! event {event_id}: {exc}", file=sys.stderr)
        for record in entry["records"]:
            counts["records"] += 1
            if not apply:
                continue
            try:
                client.delete_memory_record(
                    memoryId=memory_id, memoryRecordId=record["memoryRecordId"]
                )
            except Exception as exc:  # noqa: BLE001
                counts["failures"] += 1
                print(f"  ! record {record['memoryRecordId']}: {exc}", file=sys.stderr)
    return counts


def residue(actors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Non-preserved actors that still hold DATA: events or preference records.

    Run over a fresh survey after the delete pass. The pass counts its own calls;
    only a re-list proves the service agrees.

    A listed session or actor is deliberately NOT residue. The data plane exposes
    no delete for either: both are derived from events, so an emptied session can
    keep being listed with nothing in it. Counting that would quarantine a box whose
    Memory is genuinely clean, and only a full successful reset lifts the marker,
    so the box could never recover. Sessions are still surveyed and printed, because
    naming which session held the leftover events is what makes the report usable.

    Args:
        actors: A survey taken after the delete pass.

    Returns:
        The survey entries that still carry events or preference records.
    """
    return [
        entry for entry in actors
        if not entry["preserve"] and (entry["eventCount"] or entry["records"])
    ]


def _report_residue(client: Any, memory_id: str) -> List[Dict[str, Any]]:
    """Re-survey after the delete pass and print one RESIDUE line per leftover actor."""
    leftovers = residue(survey(client, memory_id))
    for entry in leftovers:
        print(
            f"RESIDUE actor={entry['actorId']} sessions={len(entry['sessions'])} "
            f"events={entry['eventCount']} records={len(entry['records'])}"
        )
    if leftovers:
        print(
            f"residue: {len(leftovers)} actor(s) still hold runtime data after the "
            "delete pass; this Memory is NOT clean",
            file=sys.stderr,
        )
    return leftovers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Perform the deletions. Dry run without it.")
    parser.add_argument("--json", metavar="PATH",
                        help="Write the survey to PATH for the reset plan.")
    args = parser.parse_args()

    env = _env()
    memory_id = env["AGENTCORE_MEMORY_ID"]
    region = env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION") or "us-east-1"
    os.environ.setdefault("AWS_DEFAULT_REGION", region)
    client = _client(region)

    print(f"memory resource : {memory_id}")
    print(f"region          : {region}")
    print("The RESOURCE is never modified. Only runtime data is removed.\n")

    actors = survey(client, memory_id)
    kept = [a for a in actors if a["preserve"]]
    drop = [a for a in actors if not a["preserve"]]

    print(f"{'actor':52} {'events':>7} {'prefs':>6}  disposition")
    for entry in sorted(actors, key=lambda a: (not a["preserve"], a["actorId"])):
        verdict = "PRESERVE (seeded baseline)" if entry["preserve"] else "remove"
        print(f"{entry['actorId']:52} {entry['eventCount']:>7} "
              f"{len(entry['records']):>6}  {verdict}")

    print(f"\npreserved actors: {len(kept)}   removed actors: {len(drop)}")
    counts = apply_cleanup(client, memory_id, actors, apply=args.apply)
    verb = "deleted" if args.apply else "would delete"
    print(f"{verb}: {counts['events']} event(s), {counts['records']} preference "
          f"record(s) across {counts['actors']} actor(s)")
    if counts["failures"]:
        print(f"failures: {counts['failures']}", file=sys.stderr)

    # Exit 2 is the verified-residue signal the reset quarantines on. It is
    # distinct from exit 1 (a delete call failed) because the delete pass can
    # report every call succeeded and the service still hold a record.
    leftovers = _report_residue(client, memory_id) if args.apply else []

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"memoryId": memory_id, "region": region, "actors": actors,
             "counts": counts, "applied": bool(args.apply), "residue": leftovers},
            indent=2, default=str,
        ) + "\n")
        print(f"survey written to {args.json}")

    if not args.apply:
        print("\nDry run. Re-run with --apply to delete.")
    if leftovers:
        return 2
    return 1 if counts["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
