-- Pellier governed workshop - forensic incident reference
--
-- Incident:
--   Theo disputes a return he never requested. Reconstruct who the
--   Gateway allowed to call, who the tool call was for, which rail ran,
--   and what Aurora wrote.

-- 1. Find the seeded governed receipt and its linked execution row.
SELECT
    gr.receipt_id,
    gr.created_at,
    gr.principal_id AS invoking_principal,
    gr.principal_label,
    gr.decision,
    gr.caller,
    gr.tool,
    gr.args->>'customer_id' AS return_for_customer_id,
    gr.args->>'product_id' AS product_id,
    gr.args->>'reason' AS reason,
    ta.audit_id,
    ta.result->>'return_id' AS return_id
FROM pellier.governed_receipts gr
LEFT JOIN pellier.tool_audit ta
  ON ta.audit_id = gr.audit_id
WHERE gr.session_id = 'gateway-marco-for-theo-incident';

-- 2. Resolve both identities and the product/order context.
SELECT
    gr.principal_id AS invoking_principal,
    principal.name AS invoking_principal_name,
    gr.args->>'customer_id' AS return_for_customer_id,
    customer.name AS return_for_customer_name,
    pc.name AS product_name,
    o.placed_at AS original_order_at,
    gr.caller,
    gr.decision,
    gr.policy_name
FROM pellier.governed_receipts gr
JOIN pellier.customers principal
  ON principal.id = gr.principal_id
JOIN pellier.customers customer
  ON customer.id = gr.args->>'customer_id'
JOIN pellier.product_catalog pc
  ON pc.product_id = gr.args->>'product_id'
LEFT JOIN pellier.orders o
  ON o.customer_id = gr.args->>'customer_id'
 AND o.product_id = gr.args->>'product_id'
WHERE gr.session_id = 'gateway-marco-for-theo-incident';

-- Finding:
-- The Gateway/Cedar rail allowed principal CUST-MARCO to invoke
-- process_return. The tool arguments recorded customer_id='theo',
-- so the return was for Theo's Wabi-Sabi Bowl even though Marco was
-- the authenticated caller. Keeping JWT principal and tool customer_id
-- as separate evidence fields makes the mismatch visible.
