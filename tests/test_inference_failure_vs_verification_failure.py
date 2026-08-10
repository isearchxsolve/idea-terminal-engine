from engine.agents.runners import (
    InferenceCallError, VerificationFailureError, classify_error,
)
from engine.pacing.limiter import RateLimiter


def test_distinct_failure_classes():
    assert classify_error(InferenceCallError("429 throttled")) == "inference"
    assert classify_error(VerificationFailureError("no evidence")) == "verification"
    assert classify_error(ValueError("other")) == "unknown"


def test_inference_failure_gets_backoff_not_verdict():
    # Throttling is an inference-call failure: handled by capped backoff,
    # never recorded as a verification verdict.
    lim = RateLimiter()
    assert lim.backoff_delay(0) == 2.0
    assert lim.backoff_delay(1) == 4.0
    assert lim.backoff_delay(10) == 60.0  # capped
