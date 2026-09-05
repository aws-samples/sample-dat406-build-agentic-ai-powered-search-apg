# Lab 3 build artifact: replace the four false placeholders with predicates
# over $spans. The AgentCore CLI trace file remains the source of evidence.

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
    agentSpan: false,
    modelSpan: false,
    toolSpan: false,
    sessionCorrelated: false
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
