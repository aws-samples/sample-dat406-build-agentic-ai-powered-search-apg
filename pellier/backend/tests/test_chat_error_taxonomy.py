from services.chat_error_taxonomy import classify_chat_error


def test_policy_denial_requires_an_explicit_policy_marker() -> None:
    denied = classify_chat_error(
        RuntimeError("Tool call not allowed due to policy enforcement [Policy")
    )
    assert denied["code"] == "policy_denied"
    assert denied["retryable"] is False

    auth = classify_chat_error(
        RuntimeError("HTTP 401 Unauthorized: invalid bearer token")
    )
    assert auth["code"] == "authentication_required"
    assert auth["code"] != "policy_denied"


def test_transient_failures_are_retryable_and_sanitized() -> None:
    timeout = classify_chat_error(RuntimeError("Agent execution timed out"))
    throttled = classify_chat_error(
        RuntimeError("ThrottlingException: secret provider response")
    )
    unavailable = classify_chat_error(
        RuntimeError("Connection refused at internal-host.example:443")
    )

    assert timeout["code"] == "request_timeout"
    assert throttled["code"] == "rate_limited"
    assert unavailable["code"] == "service_unavailable"
    assert all(item["retryable"] for item in (timeout, throttled, unavailable))
    assert "internal-host" not in unavailable["message"]
    assert unavailable["error"] == unavailable["message"]


def test_exception_groups_are_classified_from_their_children() -> None:
    grouped = ExceptionGroup(
        "request failed",
        [RuntimeError("transport issue"), RuntimeError("AccessDeniedException")],
    )
    assert classify_chat_error(grouped)["code"] == "policy_denied"
