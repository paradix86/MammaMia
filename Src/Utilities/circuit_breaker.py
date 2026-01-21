import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_STATE = {}
_WINDOW_SECONDS = 300
_COOLDOWN_SECONDS = 1800
_STATE_CLOSED = "CLOSED"
_STATE_OPEN = "OPEN"
_STATE_HALF_OPEN = "HALF_OPEN"

# In-memory state only; resets on process restart.
# Logging policy: WARNING on state transitions, DEBUG on per-request skip decisions.
# States:
# - CLOSED: normal operation
# - OPEN: cooldown active, skip provider
# - HALF_OPEN: allow one probe after cooldown
#
# Manual test checklist (no automated tests):
# - Two consecutive failures within 5 minutes -> provider enters OPEN
# - Provider skipped during cooldown
# - After cooldown expires:
#   - First call allowed (HALF_OPEN probe)
#   - Success -> CLOSED
#   - Failure -> OPEN again


def _is_failure_trigger(reason: str = "", status_code: Optional[int] = None) -> bool:
    if status_code in (403, 429):
        return True
    reason_lower = (reason or "").lower()
    if "no_streams_returned" in reason_lower:
        return True
    if any(text in reason_lower for text in ["indexerror", "keyerror", "valueerror"]):
        return True
    if "timeout" in reason_lower or "timed out" in reason_lower:
        return True
    if any(text in reason_lower for text in [
        "could not resolve host",
        "name or service not known",
        "temporary failure in name resolution",
        "nodename nor servname provided",
    ]):
        return True
    return False


def _get_state(provider: str) -> dict:
    state = _STATE.get(provider)
    if not state:
        state = {
            "state": _STATE_CLOSED,
            "failure_count": 0,
            "last_failure_ts": 0,
            "cooldown_until_ts": 0,
            "probe_in_flight": False,
        }
        _STATE[provider] = state
    return state


def should_skip(provider: str) -> bool:
    state = _get_state(provider)
    now = time.monotonic()
    if state["state"] == _STATE_OPEN:
        cooldown_until = state.get("cooldown_until_ts", 0)
        if cooldown_until > now:
            logger.debug(f"CB: {provider} OPEN until {int(cooldown_until)}")
            return True
        state["state"] = _STATE_HALF_OPEN
        state["probe_in_flight"] = False
        logger.warning(f"CB: {provider} OPEN->HALF_OPEN")
        return False
    if state["state"] == _STATE_HALF_OPEN:
        if state.get("probe_in_flight"):
            logger.debug(f"CB: {provider} HALF_OPEN probe in flight")
            return True
        state["probe_in_flight"] = True
        return False
    return False


def record_success(provider: str) -> None:
    state = _get_state(provider)
    if state["state"] == _STATE_HALF_OPEN:
        logger.warning(f"CB: {provider} HALF_OPEN->CLOSED")
    _STATE.pop(provider, None)


def record_failure(provider: str, reason: str = "", status_code: Optional[int] = None) -> None:
    if not _is_failure_trigger(reason, status_code):
        return
    now = time.monotonic()
    state = _get_state(provider)
    if state["state"] == _STATE_HALF_OPEN:
        state["state"] = _STATE_OPEN
        state["cooldown_until_ts"] = now + _COOLDOWN_SECONDS
        state["probe_in_flight"] = False
        logger.warning(f"CB: {provider} HALF_OPEN->OPEN (reason={reason})")
        return
    if now - state["last_failure_ts"] <= _WINDOW_SECONDS:
        state["failure_count"] += 1
    else:
        state["failure_count"] = 1
    state["last_failure_ts"] = now
    if state["failure_count"] >= 2:
        state["state"] = _STATE_OPEN
        state["cooldown_until_ts"] = now + _COOLDOWN_SECONDS
        state["probe_in_flight"] = False
        logger.warning(f"CB: {provider} CLOSED->OPEN (reason={reason})")
