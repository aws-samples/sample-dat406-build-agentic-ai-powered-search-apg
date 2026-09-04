# Close: defend the architecture from your own evidence

The last seven minutes are not a recap. Participants have spent two hours
producing evidence; this is where they are asked to read it, including a case
where the evidence does not say what it appears to say.

Run it in three moves: the contradiction, the four questions, the translation.

---

## Move 1 — The contradiction (3 minutes)

Put this evidence set on screen. It is deliberately incomplete.

```text
Policy decision      ALLOW
tool_audit           row present   (audit_id 4127)
write_operations     no matching row
Domain state         pellier.returns unchanged
```

Ask the room:

> **Did the return happen?**

Let them answer before you do. The instinctive answer is yes: the action was
authorized and the tool ran. Both halves of that are true, and the conclusion
still does not follow.

The correct answer:

> The invocation was authorized and reached the tool boundary. **No durable
> business effect is proven.** Something between the tool call and the commit
> did not complete, and an ALLOW says nothing about it.

This is the anti-lesson the whole workshop is built around: **authorization,
execution, and commit are three separate state transitions**, and each one needs
its own evidence. A single green check that spanned all three would be the most
dangerous thing on the screen.

### Produce it from live evidence

Better than a slide. This finds real turns with that exact shape, if any exist:

```sql
-- Authorized, reached the tool, left no durable effect.
SELECT gr.receipt_id,
       gr.decision,
       ta.audit_id,
       ta.tool,
       wo.idempotency_key,
       wo.completed_at
  FROM pellier.governed_receipts gr
  JOIN pellier.tool_audit ta ON ta.audit_id = gr.audit_id
  LEFT JOIN pellier.write_operations wo
         ON wo.idempotency_key = ta.args->>'idempotency_key'
 WHERE gr.decision = 'ALLOW'
   AND (wo.idempotency_key IS NULL OR wo.completed_at IS NULL)
 ORDER BY gr.receipt_id DESC
 LIMIT 5;
```

An empty result is also a good outcome, and worth saying out loud: on this box
every authorized execution did commit. The query is what makes that a finding
rather than an assumption.

---

## Move 2 — Four questions, answered from their own receipt (3 minutes)

Have participants run:

```bash
receipt
```

Then ask each question and have them point at the line that answers it. The
receipt reports `PROVED`, `NOT YET`, or `UNCHECKED`, and the third one matters
here: "I could not look" is not "it did not happen".

| Question | What answers it | Why that and not something else |
|---|---|---|
| What established Marco's inventory truth? | `01.execution_row` — a `tool_audit` row for `check_inventory` | The answer text is not evidence. The audit row proves the typed tool ran; it does not prove the *stock figure*, which comes from the inventory tables. |
| What excluded Anna's ineligible result? | `02.hybrid_receipt` — a receipt carrying vector ranks, lexical ranks, and their fusion | A relevant-looking result list proves ranking happened. Only the deterministic eligibility gate proves the ineligible candidate was excluded on purpose rather than by luck of ordering. |
| What proved your Runtime revision executed? | The build fingerprint on the managed receipt | A successful invocation proves the service answered. Only the fingerprint comparison distinguishes your package from the previous deployment, because `qualifier=DEFAULT` reads the same for both. |
| What separated Theo's policy decision from PostgreSQL's outcome? | `04.deny_did_not_execute` beside `04.durable_effect` | Cedar decided whether the action was permitted. PostgreSQL decided, independently, whether the row was allowed to change. Either can refuse, and the two refusals are different evidence. |

If a participant's receipt says `NOT YET` on one of these, that is a better
teaching moment than a full set. Ask what evidence would have to exist, and
where it would live.

---

## Move 3 — Make it portable (2 minutes)

Nobody in the room is going home to build a boutique. The boundaries transfer;
the domain does not.

| Pellier boundary | The same boundary elsewhere |
|---|---|
| Warehouse inventory tool | Account entitlement, claim status, bed capacity, part availability |
| Product eligibility gate | Coverage rules, compliance constraints, tenant scope |
| Managed Runtime deployment | A hosted operational or support agent |
| Governed return | Refund, credit, claim adjustment, access grant |
| `tool_audit` ledger | Any append-only record of what an agent actually invoked |
| Cedar DENY with no execution row | Any "we refused, and here is proof nothing ran" |

Close on the question the workshop exists to answer:

> Can an agent use live evidence, cross a managed execution boundary, attempt a
> consequential action, and prove which human, policy, application, and
> PostgreSQL controls governed the outcome?

Participants have now done all four, and have a receipt that says which ones
they can prove.

---

## What this close still does not prove

Say this part. It is the most L400 thing in the session.

- **One box is not a fleet.** Everything proved here ran against one Aurora
  cluster with one participant's traffic. Nothing observed today speaks to
  contention, replica lag, or policy evaluation under load.
- **A receipt is a record, not an attestation.** The evidence rows prove what
  the system recorded. They are not signed, and a sufficiently privileged actor
  could write them directly. The workshop's trust boundary is the database role
  model, which is exactly why Lab 4 tests the role rather than the policy text.
- **Absence of an execution row is evidence only where the row was searched
  for.** That is why the receipt distinguishes `NOT YET` from `UNCHECKED`, and
  why the identity-boundary script keys its absence check rather than
  time-windowing it.
- **A green invocation is not a deployed revision** — until the fingerprints
  match. That is the one participants are most likely to forget first.
