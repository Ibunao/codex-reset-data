"""Expose public NextReset APIs through the official MCP SDK."""

import json
import time
from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal
from urllib.error import URLError
from urllib.request import Request, urlopen

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

BASE = "https://nextreset.org/api/v1/"
_cache: dict[str, tuple[float, dict]] = {}
mcp = MCPServer(
    "NextReset", version="0.1.0", website_url="https://nextreset.org/",
    instructions="Read-only public Codex reset evidence, not individual account state. "
    "Distinguish lifecycle from verificationStatus: verified announcements are not confirmed resets. "
    "Keep source URLs, UTC timestamps, dataAsOf, and dataAgeSeconds with answers. "
    "Rule scores are not occurrence probabilities. NextReset is independent of OpenAI.",
)
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def read_api(endpoint: Literal["status", "events"]) -> dict[str, Any]:
    cached = _cache.get(endpoint)
    if cached and time.monotonic() - cached[0] < 300:
        return cached[1]
    request = Request(BASE + endpoint + ".json", headers={
        "User-Agent": "NextReset-MCP/0.1.0 (+https://nextreset.org/developers/)",
        "Accept": "application/json",
    })
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ToolError("NextReset public API is unavailable; no current result can be provided.") from error
    if not isinstance(payload, dict) or payload.get("schemaVersion") != "1.0":
        raise ToolError("Unsupported NextReset API schema.")
    for key in ("generatedAt", "dataAsOf"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ToolError("NextReset API is missing a UTC data timestamp.")
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    if endpoint == "events":
        if not isinstance(payload.get("events"), list) or any(
            not isinstance(event, dict) or not all(isinstance(event.get(key), str) for key in
                ("eventId", "resetType", "lifecycle", "verificationStatus", "lastSupportingEvidenceAt"))
            or not isinstance(event.get("evidence"), list)
            for event in payload["events"]
        ):
            raise ToolError("Invalid NextReset event records.")
    elif not isinstance(payload.get("globalRadar"), dict) or "freshness" not in payload:
        raise ToolError("Invalid NextReset status snapshot.")
    _cache[endpoint] = (time.monotonic(), payload)
    return payload


def metadata(payload: dict, endpoint: str) -> dict[str, Any]:
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(payload["dataAsOf"].replace("Z", "+00:00"))).total_seconds()
    return {"schemaVersion": payload["schemaVersion"], "generatedAt": payload["generatedAt"],
            "dataAsOf": payload["dataAsOf"], "dataAgeSeconds": max(0, int(age)),
            "sourceUrl": BASE + endpoint + ".json"}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def get_reset_status() -> dict[str, Any]:
    """Read current public Codex reset status, source health and Banked Reset availability signals.

    dataAsOf and dataAgeSeconds describe the age of the source, even when a cached
    snapshot's freshness label says fresh. This does not inspect any user's account.
    """
    payload = read_api("status")
    return {**payload, **metadata(payload, "status")}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_reset_events(
    reset_type: Literal["all", "automatic_global", "banked"] = "all",
    lifecycle: Literal["all", "announced", "scheduled", "rolling_out", "confirmed", "expired_unconfirmed", "cancelled", "corrected"] = "all",
    since: date | None = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """List public reset events, newest supporting evidence first, with optional filters.

    since is an inclusive UTC date applied to lastSupportingEvidenceAt. Possible
    signals are excluded. A primary_verified announcement is not a confirmed reset;
    inspect both lifecycle and verificationStatus. total is the count after filters,
    before limit. Use get_reset_event for full evidence on one event.
    """
    payload = read_api("events")
    events = [event for event in payload["events"]
              if (reset_type == "all" or event["resetType"] == reset_type)
              and (lifecycle == "all" or event["lifecycle"] == lifecycle)
              and (since is None or date.fromisoformat(event["lastSupportingEvidenceAt"][:10]) >= since)]
    events.sort(key=lambda event: (event["lastSupportingEvidenceAt"], event["eventId"]), reverse=True)
    return {**metadata(payload, "events"), "total": len(events), "events": events[:limit]}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def get_reset_event(event_id: Annotated[str, Field(min_length=1, max_length=200)]) -> dict[str, Any]:
    """Get one public reset event by exact eventId, including original evidence URLs and revision.

    Obtain eventId from list_reset_events. Raises an error if the ID is unknown;
    never treats a missing event or failed API request as a reset confirmation.
    """
    payload = read_api("events")
    for event in payload["events"]:
        if event["eventId"] == event_id:
            return {**metadata(payload, "events"), "event": event}
    raise ToolError("No public reset event has that eventId.")


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
