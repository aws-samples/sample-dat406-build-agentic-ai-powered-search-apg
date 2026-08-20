"""
Collectorless span export to the CloudWatch X-Ray OTLP endpoint.

Stage 1 of the governed-search design. `services/evidence_spans.py` defines
*what* a governed turn records; this module gets those spans off the box so an
operator can reconstruct a turn without shelling into the process.

Why not the documented `opentelemetry-instrument` launcher
---------------------------------------------------------

The AWS recipe for collectorless Python export wraps the process:

    opentelemetry-instrument python app.py

That installs ADOT's own `TracerProvider`. Pellier already installs one
through `StrandsTelemetry()` in `app.py`'s lifespan, and the `/inspector`
waterfall reads finished spans back out of it via
`services/otel_trace_extractor.py`. Adopting the launcher would replace that
provider, break the in-process span capture the inspector depends on, and
change the launch command in dev, bootstrap, and the Runtime image at once.

So this module takes the in-process route instead: attach a second span
processor to the provider that already exists. One provider, two
destinations — CloudWatch for durable operator evidence, the in-memory
exporter for the inspector. Both read the same spans, so the two surfaces
cannot disagree.

Signing
-------

The X-Ray OTLP endpoint authenticates with SigV4 only (bearer tokens are
supported for logs and metrics, not traces).

ADOT ships an `OTLPAwsSpanExporter` that does exactly this, and an earlier
revision imported it. It is not used here, because `aws-opentelemetry-distro`
is not in the participant dependency set and adding it resolves to 58
additional packages — around 40 auto-instrumentations for frameworks Pellier
does not run (Django, Flask, aio-pika, Redis...) — to obtain one exporter
class. On a fresh Workshop Studio box, install time is a live-event risk.

Worse, the import was silently unsatisfiable: the distro appears only in
`pyproject.toml`, which is the AgentCore Runtime CodeZip bundle, never in
`requirements.txt`/`requirements.lock`, which is what the box installs. So
this module reported "Could not attach the signing exporter: No module named
'amazon'" on every box, and Stage 1 export was inert while looking wired.

Instead the standard `OTLPSpanExporter` from
`opentelemetry-exporter-otlp-proto-http` — already in the lock, pulled by
`strands-agents[otel]` — is handed a `requests.Session` whose `auth` hook
signs with botocore. Signing at the `auth` hook rather than around it means
the bytes signed are the bytes sent, including compression the exporter
applied, and a refreshable credentials object re-resolves per request so an
instance role rotating mid-workshop does not break export.

The distro stays in `pyproject.toml`: AgentCore Runtime's managed
observability auto-instruments the bundle when it is present, which is a
separate mechanism from this exporter.

Sampling
--------

The OpenTelemetry SDK default is `parentbased_always_on` — 100% of traces.
That is deliberately left alone: the workshop's reconstruction exercise asks
a participant to find *one specific turn* by `turn_id`, and a 5% ratio
sampler would make that exercise fail 19 times out of 20. Transaction Search
is configured for 100% indexing to match (see `bootstrap-labs.sh` STEP 13b).
If an operator has set a ratio sampler we do not override it — that is their
call — but we report it, because it silently breaks the proof.

Degradation
-----------

Failing to observe must never fail the thing being observed. Every failure
path here leaves a reason string and returns; startup continues. Callers
surface `unavailable` with the reason rather than implying spans exist.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Service name SigV4 signs the traces endpoint with.
_SIGV4_SERVICE = "xray"

# CloudWatch log group Transaction Search writes indexed spans to. Named here
# because it is the group a participant queries; it is not configurable.
SPANS_LOG_GROUP = "aws/spans"

# Env var that makes ADOT extract LLM prompt/response content onto telemetry.
# Left off on purpose: spec invariant 11 keeps payloads off spans, and this
# switch is the one thing that would put them there.
_AGENT_OBSERVABILITY_ENV = "AGENT_OBSERVABILITY_ENABLED"


# Content type the OTLP/HTTP protobuf exporter posts. Named here because it is
# one of the headers the signature covers, so it cannot be guessed at.
_PROTOBUF_CONTENT_TYPE = "application/x-protobuf"


def traces_endpoint_for_region(region: str) -> str:
    """Return the X-Ray OTLP traces endpoint for a region."""
    return f"https://xray.{region}.amazonaws.com/v1/traces"


class SigV4RequestSigner:
    """Sign each prepared OTLP request for the X-Ray traces endpoint.

    Installed as a `requests` auth hook, so it runs once per export attempt on
    the fully prepared request. Two properties follow from that placement and
    both matter:

    * The signature covers the body actually transmitted. Signing around the
      exporter instead would miss compression applied after the fact and every
      export would return 403.
    * Credentials are read per request. A `RefreshableCredentials` resolves on
      attribute access, so an instance role that rotates during a long
      workshop keeps exporting rather than failing after an hour.

    Only `content-type` is signed alongside the host and date. Headers
    `requests` and `urllib3` add later (`User-Agent`, `Accept-Encoding`,
    connection management) are deliberately excluded: SigV4 verification uses
    the `SignedHeaders` list, so including a header the transport may still
    rewrite is what breaks a signature, not omitting it.
    """

    def __init__(self, credentials: Any, region: str) -> None:
        """Store the credential source and the region to sign for.

        Args:
            credentials: A botocore credentials object. Not frozen on purpose.
            region: AWS region whose X-Ray endpoint receives the spans.
        """
        self._credentials = credentials
        self._region = region

    def __call__(self, request: Any) -> Any:
        """Add SigV4 headers to a prepared request and return it."""
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        signable = AWSRequest(
            method=request.method,
            url=request.url,
            data=request.body,
            headers={
                "Content-Type": request.headers.get(
                    "Content-Type", _PROTOBUF_CONTENT_TYPE
                )
            },
        )
        SigV4Auth(self._credentials, _SIGV4_SERVICE, self._region).add_auth(signable)
        request.headers.update(dict(signable.headers))
        return request


def build_signing_exporter(
    *, endpoint: str, region: str, credentials: Any
) -> Any:
    """Return an OTLP/HTTP span exporter that SigV4-signs every request.

    Args:
        endpoint: Full traces endpoint to post to.
        region: AWS region SigV4 signs for.
        credentials: botocore credentials used for signing.

    Returns:
        A configured `OTLPSpanExporter`.
    """
    import requests
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    http_session = requests.Session()
    http_session.auth = SigV4RequestSigner(credentials, region)
    return OTLPSpanExporter(endpoint=endpoint, session=http_session)


@dataclass(frozen=True)
class SpanExportState:
    """Outcome of an export-attachment attempt.

    Attributes:
        attached: True only when a signing processor is on the live provider.
        endpoint: Endpoint the exporter targets, when one was resolved.
        region: Region SigV4 signs for, when one was resolved.
        sampler: repr of the active sampler, for the operator surface.
        reason: Why export is unavailable. Empty when attached.
    """

    attached: bool
    endpoint: Optional[str] = None
    region: Optional[str] = None
    sampler: Optional[str] = None
    reason: str = ""

    def as_dict(self) -> dict:
        """Serialize for the readiness/operator payload."""
        return {
            "attached": self.attached,
            "endpoint": self.endpoint,
            "region": self.region,
            "sampler": self.sampler,
            "spans_log_group": SPANS_LOG_GROUP if self.attached else None,
            "reason": self.reason,
        }


_STATE = SpanExportState(
    attached=False,
    reason="CloudWatch span export not initialized yet — init_cloudwatch_span_export() has not run.",
)


def export_state() -> SpanExportState:
    """Return the current export state for readiness and operator surfaces."""
    return _STATE


def _sdk_provider() -> Any:
    """Return the active SDK TracerProvider, or None.

    A non-SDK provider is the API's no-op default: it accepts spans and drops
    them, and it has no `add_span_processor`. Attaching to it would report
    success while exporting nothing.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    provider = trace.get_tracer_provider()
    return provider if isinstance(provider, TracerProvider) else None


def _describe_sampler(provider: Any) -> Optional[str]:
    """Return a readable sampler description, tolerating SDK differences."""
    sampler = getattr(provider, "sampler", None)
    if sampler is None:
        return None
    description = getattr(sampler, "get_description", None)
    if callable(description):
        try:
            return str(description())
        except Exception:  # pragma: no cover - defensive
            pass
    return type(sampler).__name__


def init_cloudwatch_span_export(
    *,
    enabled: bool,
    region: str,
    endpoint: Optional[str] = None,
) -> SpanExportState:
    """Attach a SigV4-signing OTLP span processor to the active provider.

    Safe to call once per process during startup. Never raises: every failure
    resolves to a `SpanExportState` carrying an operator-readable reason.

    Args:
        enabled: Operator opt-out. False records a state and attaches nothing.
        region: AWS region whose X-Ray OTLP endpoint receives spans.
        endpoint: Full endpoint override. Defaults to the region endpoint.

    Returns:
        The resulting state, also retrievable later via `export_state()`.
    """
    global _STATE

    if not enabled:
        _STATE = SpanExportState(
            attached=False,
            reason="Disabled by configuration (OTEL_CLOUDWATCH_TRACES_ENABLED=false).",
        )
        return _STATE

    resolved_endpoint = endpoint or traces_endpoint_for_region(region)

    try:
        provider = _sdk_provider()
    except Exception as exc:  # pragma: no cover - absent SDK is a degraded path
        _STATE = SpanExportState(
            attached=False,
            endpoint=resolved_endpoint,
            region=region,
            reason=f"OpenTelemetry SDK unavailable: {exc}",
        )
        logger.warning("CloudWatch span export unavailable: %s", _STATE.reason)
        return _STATE

    if provider is None:
        _STATE = SpanExportState(
            attached=False,
            endpoint=resolved_endpoint,
            region=region,
            reason=(
                "No SDK TracerProvider is active, so spans would be discarded. "
                "Initialize StrandsTelemetry before calling this."
            ),
        )
        logger.warning("CloudWatch span export unavailable: %s", _STATE.reason)
        return _STATE

    sampler = _describe_sampler(provider)

    try:
        from botocore.session import Session

        session = Session()
        # Resolve credentials up front. Without this the BatchSpanProcessor
        # would attach cleanly and then fail every export on a background
        # thread, which reads to an operator as "export works" while nothing
        # arrives. An unresolvable chain is a reportable state, not a retry.
        credentials = session.get_credentials()
        if credentials is None:
            _STATE = SpanExportState(
                attached=False,
                endpoint=resolved_endpoint,
                region=region,
                sampler=sampler,
                reason=(
                    "No AWS credentials resolved, so spans cannot be signed. "
                    "Attach an instance role or configure the credential chain."
                ),
            )
            logger.warning("CloudWatch span export unavailable: %s", _STATE.reason)
            return _STATE

        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = build_signing_exporter(
            endpoint=resolved_endpoint,
            region=region,
            credentials=credentials,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    except Exception as exc:
        _STATE = SpanExportState(
            attached=False,
            endpoint=resolved_endpoint,
            region=region,
            sampler=sampler,
            reason=f"Could not attach the signing exporter: {exc}",
        )
        logger.warning(
            "CloudWatch span export unavailable: %s", _STATE.reason, exc_info=True
        )
        return _STATE

    _STATE = SpanExportState(
        attached=True,
        endpoint=resolved_endpoint,
        region=region,
        sampler=sampler,
    )
    logger.info(
        "✅ Spans → %s (SigV4 service=%s, indexed into %s)",
        resolved_endpoint,
        _SIGV4_SERVICE,
        SPANS_LOG_GROUP,
    )

    if os.environ.get(_AGENT_OBSERVABILITY_ENV, "").lower() in {"1", "true"}:
        # Not fatal, but it contradicts the payload prohibition, so it must
        # not pass silently.
        logger.warning(
            "%s is enabled — ADOT will extract model prompt and response "
            "content onto telemetry, which the evidence-span contract "
            "prohibits. Unset it unless that is intended.",
            _AGENT_OBSERVABILITY_ENV,
        )

    if sampler and "always_on" not in sampler.lower():
        logger.warning(
            "Trace sampler is %r, not 100%%. Turn-by-turn reconstruction "
            "needs every turn present; a sampled turn cannot be found by "
            "pellier.turn_id.",
            sampler,
        )

    return _STATE
