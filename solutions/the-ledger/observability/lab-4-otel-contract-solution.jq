[
  .[]
  | .["@message"]
  | if type == "string" then fromjson else . end
  | select(.traceId == $trace)
] as $spans
| {
    traceId: $trace,
    runtimeSession: $session,
    spanCount: ($spans | length),
    # === WORKSHOP · AgentCore OTEL · trace contract: START ===
    agentSpan: any(
      $spans[];
      (.name // "") | startswith("invoke_agent")
    ),
    modelSpan: any(
      $spans[];
      .name == "chat"
      and (.attributes["gen_ai.request.model"] // "") != ""
    ),
    toolSpan: any(
      $spans[];
      ((.name // "") | startswith("execute_tool"))
      and (.attributes["gen_ai.tool.name"] // "") != ""
    ),
    sessionCorrelated: any(
      $spans[];
      (.attributes["session.id"] // "") == $session
    )
    # === WORKSHOP · AgentCore OTEL · trace contract: END ===
  }
| . + {
    allPassed: (
      .spanCount >= 3
      and .agentSpan
      and .modelSpan
      and .toolSpan
      and .sessionCorrelated
    )
  }
