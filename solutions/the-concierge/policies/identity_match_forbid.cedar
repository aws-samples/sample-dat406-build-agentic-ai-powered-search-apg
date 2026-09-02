// Required Lab 4 reference rule: the authenticated principal may only file a
// return for itself. AgentCore Policy exposes JWT claims as principal tags, so
// the Cognito access token's `username` claim is comparable against the tool
// input. The `unless` shape is fail-closed: a missing claim, missing
// customer_id, or mismatched identity is denied.
forbid(
  principal,
  action == AgentCore::Action::"pellier-concierge-experience-target___initiate_return",
  resource is AgentCore::Gateway
)
unless {
  principal.hasTag("username") &&
  context.input has customer_id &&
  (
    (principal.getTag("username") == "marco" &&
      context.input.customer_id == "CUST-MARCO") ||
    (principal.getTag("username") == "anna" &&
      context.input.customer_id == "CUST-ANNA") ||
    (principal.getTag("username") == "theo" &&
      context.input.customer_id == "CUST-THEO") ||
    (principal.getTag("username") == "jessica" &&
      context.input.customer_id == "CUST-JESSICA")
  )
};
