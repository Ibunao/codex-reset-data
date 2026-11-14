# Dataset schema 1.0

Source: [NextReset public events API](https://nextreset.org/api/v1/events.json). The export is a deliberately smaller schema than the source API. It removes text excerpts and internal grouping fields.

## JSON envelope

| Field | Meaning |
| --- | --- |
| `schemaVersion` | This dataset's format version, currently `1.0` |
| `source` | Public API used to obtain the snapshot |
| `license` | `CC-BY-4.0`; see LICENSE for scope |
| `generatedAt` | Source API generation timestamp for this saved snapshot |
| `dataAsOf` | Source API evidence-check timestamp for this saved snapshot; does not assert complete historical coverage |
| `events` | Event records, sorted by stable `eventId` |
| `possibleSignals` | Possible signals sorted by `signalId`; never count these as confirmed events |

## Records

Optional fields are omitted in JSON and represented by empty cells in CSV. The CSV has events only and carries no envelope metadata; use the adjacent JSON to identify its snapshot.

| Field | Meaning |
| --- | --- |
| `eventId` / `signalId` | Stable upstream identifier for an event / possible signal |
| `resetType` | `automatic_global`, `banked`, or `unknown` (possible signals may be unknown) |
| `lifecycle` | `announced`, `scheduled`, `rolling_out`, `confirmed`, `expired_unconfirmed`, `cancelled`, `corrected`, or `possible` |
| `verificationStatus` | Upstream evidence assessment, such as `primary_verified`, `unverified`, or `retracted`; independent of lifecycle |
| `revision` | Upstream event revision, when present |
| `announcementAt` | Publication time of announcement evidence |
| `expectedAt` | Expected time extracted upstream; not a confirmation |
| `confirmedAt` | Publication time of confirmation evidence; not a per-account measurement |
| `availableFrom`, `expiresAt`, `eligibilityCutoffAt` | Reported availability/expiry/eligibility times, when present |
| `cancelledAt`, `correctedAt` | Cancellation or correction timestamps, when present |
| `lastSupportingEvidenceAt` | Timestamp of the latest supporting evidence |
| `targetDay` | Upstream day label; do not infer an exact UTC reset instant from this date alone |
| `affectedPlans` | Plans explicitly recorded upstream; empty means unspecified, not all plans |
| `evidence` | JSON-only evidence array: `evidenceId`, `role`, `tier`, `verificationStatus`, `sourceUrl`, `publishedAt` |
| `sourceUrls` | CSV-only deduplicated evidence URLs separated by `|`; evidence roles and timestamps remain in JSON |

`affectedPlans` is a JSON array and a `|`-separated CSV cell. Dates ending in `Z` are UTC ISO 8601. Rows are not predictions, official OpenAI account telemetry, or guaranteed coverage. To count primary-verified confirmations, filter on **both** `lifecycle == "confirmed"` and `verificationStatus == "primary_verified"`, and split by `resetType`.
