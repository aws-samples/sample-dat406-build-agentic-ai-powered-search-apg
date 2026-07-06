// Workshop exercise: complete the when block, then validate and apply.
// The helper replaces the action and gateway placeholders before it talks to AgentCore Policy.
forbid(
  principal,
  action == AgentCore::Action::"ACTION_TOKEN",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  context.input has product_id &&
  false
};
