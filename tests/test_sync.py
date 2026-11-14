import copy
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("sync", Path(__file__).resolve().parents[1] / "scripts/sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "schemaVersion": "1.0", "generatedAt": "2026-11-14T14:00:00Z", "dataAsOf": "2026-11-14T14:00:00Z",
            "events": [{"eventId": "reset-test", "resetType": "automatic_global", "lifecycle": "expired_unconfirmed",
                        "verificationStatus": "primary_verified", "revision": 1, "affectedPlans": [],
                        "summary": {"en": "Third-party text must not be exported"}, "private": "secret",
                        "evidence": [{"evidenceId": "post-test", "role": "announcement", "tier": "primary",
                                      "verificationStatus": "primary_verified", "sourceUrl": "https://x.com/example/status/1",
                                      "publishedAt": "2026-11-13T00:00:00Z", "body": "Not public in this dataset"}]}],
            "possibleSignals": [],
        }

    def test_preserves_uncertainty_and_excludes_unlisted_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sync.export(self.payload, root)
            text = (root / "events.json").read_text()
            self.assertNotIn("secret", text)
            self.assertNotIn("Third-party", text)
            self.assertNotIn("body", text)
            rows = list(csv.DictReader((root / "events.csv").read_text().splitlines()))
            self.assertEqual(rows[0]["lifecycle"], "expired_unconfirmed")
            self.assertEqual(rows[0]["confirmedAt"], "")

    def test_timestamp_only_refresh_keeps_snapshot_but_content_change_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sync.export(self.payload, root)
            before = (root / "events.json").read_bytes()
            self.payload["generatedAt"] = self.payload["dataAsOf"] = "2026-11-14T15:00:00Z"
            sync.export(self.payload, root)
            self.assertEqual(before, (root / "events.json").read_bytes())
            self.payload["events"][0]["revision"] = 2
            sync.export(self.payload, root)
            self.assertNotEqual(before, (root / "events.json").read_bytes())

    def test_bad_payload_does_not_overwrite_published_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sync.export(self.payload, root)
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            for mutate in (
                lambda p: p.update(schemaVersion="2.0"),
                lambda p: p.update(events=[]),
                lambda p: p["events"].append(copy.deepcopy(p["events"][0])),
                lambda p: p["events"][0].update(evidence=[]),
                lambda p: p["events"][0]["evidence"][0].update(sourceUrl="https://unreviewed.example/post"),
                lambda p: p.update(dataAsOf="not-a-date"),
                lambda p: p.update(dataAsOf="2026-11-13T00:00:00Z"),
            ):
                invalid = copy.deepcopy(self.payload)
                mutate(invalid)
                with self.assertRaises(ValueError):
                    sync.export(invalid, root)
                self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})


if __name__ == "__main__":
    unittest.main()
