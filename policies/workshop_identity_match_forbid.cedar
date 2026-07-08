// Workshop exercise (optional identity rail): complete the when block, then validate and apply.
// The helper replaces the action and gateway placeholders before it talks to AgentCore Policy.
//
// Goal: the authenticated principal may only file a return for itself. AgentCore
// Policy exposes JWT claims as principal tags, so the Cognito access token's
// `username` claim is comparable against the tool input. Forbid the call when
// the token identity and the requested customer_id disagree – the Act II
// Marco-for-Theo mismatch, prevented before the tool executes.
forbid(
  principal,
  action == AgentCore::Action::"ACTION_TOKEN",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  context.input has customer_id &&
  false
};
