"""Export allowlisted public event metadata; no website source or post text."""

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://nextreset.org/api/v1/events.json"
ROOT = Path(__file__).resolve().parents[1]
FIELDS = (
    "eventId", "signalId", "resetType", "lifecycle", "verificationStatus",
    "revision", "announcementAt", "expectedAt", "confirmedAt", "availableFrom",
    "expiresAt", "eligibilityCutoffAt", "cancelledAt", "correctedAt",
    "lastSupportingEvidenceAt", "targetDay", "affectedPlans",
)
EVIDENCE_FIELDS = ("evidenceId", "role", "tier", "verificationStatus", "sourceUrl", "publishedAt")
CSV_FIELDS = (
    "eventId", "resetType", "lifecycle", "verificationStatus", "revision",
    "announcementAt", "expectedAt", "confirmedAt", "availableFrom", "expiresAt",
    "eligibilityCutoffAt", "cancelledAt", "correctedAt", "lastSupportingEvidenceAt",
    "targetDay", "affectedPlans", "sourceUrls",
)


def timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Expected a UTC ISO 8601 timestamp")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def project_record(record, identifier):
    if not isinstance(record, dict) or not isinstance(record.get(identifier), str) or not record[identifier]:
        raise ValueError(f"Missing {identifier}")
    for key in ("resetType", "lifecycle", "verificationStatus"):
        if not isinstance(record.get(key), str) or not record[key]:
            raise ValueError(f"Missing {key}")
    if record["resetType"] not in ("automatic_global", "banked", "unknown"):
        raise ValueError("Unknown reset type")
    if record["lifecycle"] not in ("announced", "scheduled", "rolling_out", "confirmed", "expired_unconfirmed", "cancelled", "corrected", "possible"):
        raise ValueError("Unknown lifecycle")
    result = {key: record[key] for key in FIELDS if key in record}
    for key, value in result.items():
        if key.endswith("At"):
            timestamp(value)
        elif key == "affectedPlans":
            if not isinstance(value, list) or not all(isinstance(plan, str) for plan in value):
                raise ValueError("Invalid affectedPlans")
        elif not isinstance(value, (str, int)):
            raise ValueError(f"Invalid field: {key}")
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Every record must have evidence")
    result["evidence"] = []
    for item in evidence:
        if not isinstance(item, dict) or any(not isinstance(item.get(key), str) for key in EVIDENCE_FIELDS):
            raise ValueError("Invalid evidence")
        if not item["sourceUrl"].startswith(("https://x.com/", "https://twitter.com/")):
            raise ValueError("Unexpected evidence source; review before publishing")
        timestamp(item["publishedAt"])
        result["evidence"].append({key: item[key] for key in EVIDENCE_FIELDS})
    return result


def project(payload):
    if not isinstance(payload, dict) or payload.get("schemaVersion") != "1.0":
        raise ValueError("Unsupported source schema")
    result = {
        "schemaVersion": "1.0",
        "source": SOURCE,
        "license": "CC-BY-4.0",
        "generatedAt": timestamp(payload.get("generatedAt")),
        "dataAsOf": timestamp(payload.get("dataAsOf")),
    }
    for key, identifier in (("events", "eventId"), ("possibleSignals", "signalId")):
        rows = payload.get(key)
        if not isinstance(rows, list) or (key == "events" and not rows):
            raise ValueError(f"Invalid or empty {key}")
        result[key] = sorted((project_record(row, identifier) for row in rows), key=lambda row: row[identifier])
        if len({row[identifier] for row in result[key]}) != len(rows):
            raise ValueError(f"Duplicate {identifier}")
    return result


def export(payload, directory):
    result = project(payload)  # Validate everything before writing either file.
    json_path = directory / "events.json"
    if json_path.exists():
        previous = json.loads(json_path.read_text())
        if datetime.fromisoformat(result["dataAsOf"].replace("Z", "+00:00")) < datetime.fromisoformat(previous["dataAsOf"].replace("Z", "+00:00")):
            raise ValueError("Source snapshot is older than published data")
        if all(previous.get(key) == result[key] for key in ("schemaVersion", "source", "license", "events", "possibleSignals")):
            result = previous  # Keep the timestamp of the last changed snapshot.
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for event in result["events"]:
        row = {key: event.get(key, "") for key in CSV_FIELDS}
        row["affectedPlans"] = "|".join(event.get("affectedPlans", []))
        row["sourceUrls"] = "|".join(dict.fromkeys(item["sourceUrl"] for item in event["evidence"]))
        writer.writerow(row)
    directory.mkdir(parents=True, exist_ok=True)
    for filename, content in (("events.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n"), ("events.csv", output.getvalue())):
        target = directory / filename
        if not target.exists() or target.read_text() != content:
            target.write_text(content, encoding="utf-8")
    print(f"Validated {len(result['events'])} events and {len(result['possibleSignals'])} possible signals; snapshot as of {result['dataAsOf']}")


if __name__ == "__main__":
    request = Request(SOURCE, headers={"User-Agent": "NextReset-OpenData/1.0 (+https://nextreset.org)", "Accept": "application/json"})
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    export(payload, ROOT / "data")
