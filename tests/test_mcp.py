import copy
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from mcp import Client

from nextreset_mcp import server

BASE = {"schemaVersion": "1.0", "generatedAt": "2026-11-14T14:00:00Z", "dataAsOf": "2026-11-14T14:00:00Z"}


def event(identifier, kind, lifecycle, day):
    return {"eventId": identifier, "resetType": kind, "lifecycle": lifecycle,
            "verificationStatus": "primary_verified", "lastSupportingEvidenceAt": day + "T10:00:00Z",
            "evidence": [{"sourceUrl": "https://x.com/example/status/1", "role": "announcement"}]}


EVENTS = {**BASE, "events": [
    event("older", "automatic_global", "confirmed", "2026-11-12"),
    event("announcement", "automatic_global", "announced", "2026-11-14"),
    event("banked", "banked", "confirmed", "2026-11-13"),
], "possibleSignals": [{"signalId": "not-an-event"}]}
STATUS = {**BASE, "freshness": "fresh", "sourceHealth": "healthy", "globalRadar": {"level": "announced"}}


class PublicApiTests(unittest.TestCase):
    def setUp(self):
        server._cache.clear()

    def test_fixed_public_url_user_agent_and_five_minute_cache(self):
        with patch.object(server, "urlopen", return_value=io.BytesIO(json.dumps(EVENTS).encode())) as fetch:
            with patch.object(server.time, "monotonic", side_effect=[100, 101]):
                self.assertEqual(server.read_api("events"), EVENTS)
                self.assertEqual(server.read_api("events"), EVENTS)
            self.assertEqual(fetch.call_count, 1)
            request = fetch.call_args.args[0]
            self.assertEqual(request.full_url, "https://nextreset.org/api/v1/events.json")
            self.assertIn("NextReset-MCP", request.get_header("User-agent"))
            self.assertEqual(fetch.call_args.kwargs["timeout"], 20)

    def test_expired_cache_does_not_hide_source_failure(self):
        server._cache["events"] = (0, EVENTS)
        with patch.object(server.time, "monotonic", return_value=301):
            with patch.object(server, "urlopen", side_effect=URLError("unavailable")):
                with self.assertRaisesRegex(server.ToolError, "unavailable"):
                    server.read_api("events")

    def test_malformed_responses_are_not_cached(self):
        for payload in ({}, {**BASE, "events": "error"}, {**BASE, "events": [{}]}, {**EVENTS, "dataAsOf": "yesterday"}):
            with self.subTest(payload=payload):
                with patch.object(server, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
                    with self.assertRaises((ValueError, server.ToolError)):
                        server.read_api("events")
                self.assertEqual(server._cache, {})


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.reader = patch.object(server, "read_api", side_effect=lambda name: copy.deepcopy(EVENTS if name == "events" else STATUS))
        self.reader.start()
        self.addCleanup(self.reader.stop)

    async def test_discovery_and_read_only_annotations_in_auto_and_legacy_modes(self):
        for mode in ("auto", "legacy"):
            async with Client(server.mcp, mode=mode) as client:
                tools = (await client.list_tools()).tools
                self.assertEqual({tool.name for tool in tools}, {"get_reset_status", "list_reset_events", "get_reset_event"})
                for tool in tools:
                    self.assertTrue(tool.annotations.read_only_hint)
                    self.assertFalse(tool.annotations.destructive_hint)

    async def test_status_and_source_age(self):
        async with Client(server.mcp) as client:
            result = await client.call_tool("get_reset_status", {})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["globalRadar"]["level"], "announced")
            self.assertEqual(result.structured_content["dataAsOf"], BASE["dataAsOf"])
            self.assertGreaterEqual(result.structured_content["dataAgeSeconds"], 0)

    async def test_filters_sort_limit_and_evidence_lookup(self):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_reset_events", {"limit": 1})
            self.assertEqual(result.structured_content["total"], 3)
            self.assertEqual(result.structured_content["events"][0]["eventId"], "announcement")
            result = await client.call_tool("list_reset_events", {"lifecycle": "confirmed", "reset_type": "banked", "since": "2026-11-13"})
            self.assertEqual([event["eventId"] for event in result.structured_content["events"]], ["banked"])
            result = await client.call_tool("get_reset_event", {"event_id": "announcement"})
            self.assertEqual(result.structured_content["event"]["lifecycle"], "announced")
            self.assertTrue(result.structured_content["event"]["evidence"][0]["sourceUrl"].startswith("https://x.com/"))

    async def test_invalid_arguments_unknown_tool_and_missing_event_are_errors(self):
        async with Client(server.mcp) as client:
            for name, args in (
                ("list_reset_events", {"limit": 0}), ("list_reset_events", {"limit": 101}),
                ("list_reset_events", {"reset_type": "made-up"}),
                ("list_reset_events", {"since": "not-a-date"}),
                ("get_reset_event", {"event_id": "unknown"}),
                ("get_reset_event", {"event_id": ""}), ("write_reset_event", {}),
            ):
                with self.subTest(name=name, args=args):
                    result = await client.call_tool(name, args)
                    self.assertTrue(result.is_error)

    async def test_upstream_failure_is_a_tool_error(self):
        with patch.object(server, "read_api", side_effect=server.ToolError("NextReset public API is unavailable")):
            async with Client(server.mcp) as client:
                result = await client.call_tool("get_reset_status", {})
                self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
