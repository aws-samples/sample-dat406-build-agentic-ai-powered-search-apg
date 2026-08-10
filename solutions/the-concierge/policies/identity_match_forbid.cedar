// Required Lab 4 reference rule: the authenticated principal may
// only file a return for itself. AgentCore Policy exposes JWT claims as
// principal tags, so the Cognito access token's `username` claim (marco/anna/
// theo – lowercase, matching the pellier.customers convention used in tool
// args) is comparable against the tool input.
//
// This shape is deliberately fail-open for the workshop: if the engine
// revision does not emit the claim tag, hasTag() is false, the forbid does not
// fire, and the room's damaged-return happy path stays green. The
// production-hardened variant is the fail-closed `unless` shape:
//
//   forbid(...) unless {
//     principal.hasTag("username") &&
//     context.input has customer_id &&
//     principal.getTag("username") == context.input.customer_id
//   };
//
// which denies when the claim is missing instead of allowing.
forbid(
  principal,
  action == AgentCore::Action::"ACTION_TOKEN",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  context.input has customer_id &&
  principal.hasTag("username") &&
  principal.getTag("username") != context.input.customer_id
};
