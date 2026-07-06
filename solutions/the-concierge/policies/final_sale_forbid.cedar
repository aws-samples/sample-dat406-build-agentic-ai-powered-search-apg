// Participant rule: final-sale products cannot be returned through Gateway.
// The workshop helper replaces the action and gateway placeholders before applying.
forbid(
  principal,
  action == AgentCore::Action::"ACTION_TOKEN",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  context.input has product_id &&
  context.input.product_id == 37
};
