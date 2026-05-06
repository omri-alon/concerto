"""State machine tracking via structured GUS work item comments."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("concerto.tracking")

STATE_PATTERN = re.compile(r"<!-- (?:concerto|stokowski):state ({.*?}) -->")
GATE_PATTERN = re.compile(r"<!-- (?:concerto|stokowski):gate ({.*?}) -->")


def make_state_comment(state: str, run: int = 1) -> str:
    """Build a structured state-tracking comment."""
    payload = {
        "state": state,
        "run": run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    machine = f"<!-- concerto:state {json.dumps(payload)} -->"
    human = f"**[Concerto]** Entering state: **{state}** (run {run})"
    return f"{machine}\n\n{human}"


def make_gate_comment(
    state: str,
    status: str,
    prompt: str = "",
    rework_to: str | None = None,
    run: int = 1,
) -> str:
    """Build a structured gate-tracking comment."""
    payload: dict[str, Any] = {
        "state": state,
        "status": status,
        "run": run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if rework_to:
        payload["rework_to"] = rework_to

    machine = f"<!-- concerto:gate {json.dumps(payload)} -->"

    if status == "waiting":
        human = f"**[Concerto]** Awaiting human review: **{state}**"
        if prompt:
            human += f" — {prompt}"
    elif status == "approved":
        human = f"**[Concerto]** Gate **{state}** approved."
    elif status == "rework":
        human = (
            f"**[Concerto]** Rework requested at **{state}**. "
            f"Returning to: **{rework_to}**"
        )
        if run > 1:
            human += f" (run {run})"
    elif status == "escalated":
        human = (
            f"**[Concerto]** Max rework exceeded at **{state}**. "
            f"Escalating for human intervention."
        )
    else:
        human = f"**[Concerto]** Gate **{state}** status: {status}"

    return f"{machine}\n\n{human}"


def parse_latest_tracking(comments: list[dict]) -> dict[str, Any] | None:
    """Parse comments (oldest-first) to find the latest state or gate tracking entry.

    Returns a dict with keys:
        - "type": "state" or "gate"
        - Plus all fields from the JSON payload

    Returns None if no tracking comments found.
    """
    latest: dict[str, Any] | None = None

    for comment in comments:
        body = comment.get("body", "")

        state_match = STATE_PATTERN.search(body)
        if state_match:
            try:
                data = json.loads(state_match.group(1))
                data["type"] = "state"
                latest = data
            except json.JSONDecodeError:
                pass

        gate_match = GATE_PATTERN.search(body)
        if gate_match:
            try:
                data = json.loads(gate_match.group(1))
                data["type"] = "gate"
                latest = data
            except json.JSONDecodeError:
                pass

    return latest


def get_last_tracking_timestamp(comments: list[dict]) -> str | None:
    """Find the timestamp of the latest tracking comment."""
    latest_ts: str | None = None

    for comment in comments:
        body = comment.get("body", "")
        for pattern in (STATE_PATTERN, GATE_PATTERN):
            match = pattern.search(body)
            if match:
                try:
                    data = json.loads(match.group(1))
                    ts = data.get("timestamp")
                    if ts:
                        latest_ts = ts
                except json.JSONDecodeError:
                    pass

    return latest_ts


def get_comments_since(
    comments: list[dict], since_timestamp: str | None
) -> list[dict]:
    """Filter comments to only those after a given timestamp.

    Returns comments that are NOT concerto tracking comments and
    were created after the given timestamp.
    """
    result = []
    since_dt = None
    if since_timestamp:
        try:
            since_dt = datetime.fromisoformat(
                since_timestamp.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            pass

    for comment in comments:
        body = comment.get("body", "")
        if "<!-- concerto:" in body or "<!-- stokowski:" in body:
            continue

        if since_dt:
            created = comment.get("createdAt", "")
            if created:
                try:
                    created_dt = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    )
                    if created_dt <= since_dt:
                        continue
                except (ValueError, AttributeError):
                    pass

        result.append(comment)

    return result
