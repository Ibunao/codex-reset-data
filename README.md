# Codex Reset Data

An open dataset of public Codex reset announcements, confirmations, and possible signals, maintained by **[NextReset](https://nextreset.org/)**.

Also includes a **[read-only MCP server](MCP.md)** for querying current status, event history, and source evidence from local MCP clients. Install with `uvx --python 3.12 --from git+https://github.com/Ibunao/codex-reset-data@v0.1.0 nextreset-mcp`. No API key required.

**[Live tracker](https://nextreset.org/) · [中文网站](https://nextreset.org/zh/) · [Methodology](https://nextreset.org/method/) · [Developer API](https://nextreset.org/developers/)**

Independent community project. Not affiliated with or endorsed by OpenAI. These records describe public evidence, not access to individual accounts or a guarantee that any account received a reset.

## Download

| File | Contents |
| --- | --- |
| [data/events.json](data/events.json) | Structured event records, evidence links, and a separate `possibleSignals` collection |
| [data/events.csv](data/events.csv) | One row per event, including unconfirmed/expired events; possible signals are available in JSON only |

```python
import json
from urllib.request import urlopen

url = "https://raw.githubusercontent.com/Ibunao/codex-reset-data/main/data/events.json"
with urlopen(url) as response:
    dataset = json.load(response)

confirmed = [event for event in dataset["events"]
             if event["lifecycle"] == "confirmed"
             and event["verificationStatus"] == "primary_verified"]
print(len(confirmed))
```

The dataset preserves historical records; it is not limited to the website calendar's current viewing window. It is not an exhaustive record of every Codex reset. See [SCHEMA.md](SCHEMA.md) before interpreting timestamps or counting events.

## Updates

The existing NextReset pipeline collects and reviews public evidence and publishes the website API. The dataset sync reads **only** `https://nextreset.org/api/v1/events.json`; the MCP server reads the public status and events APIs. Neither scrapes X or reads the private website repository.

GitHub Actions checks hourly at minute 17 UTC and can also run manually from the Actions tab. Scheduling may be delayed by GitHub. A website update therefore usually appears here on the next hourly run, rather than immediately. The importer commits only when event metadata or possible signals change. It preserves the previous files when fetching or validation fails.

`generatedAt` and `dataAsOf` belong to the source snapshot captured at the last dataset content change. They are not the most recent GitHub polling time. Consult the [latest website API](https://nextreset.org/api/v1/events.json) and the Actions run history for current checks. GitHub may disable scheduled workflows in public repositories after 60 days without repository activity; re-enable the workflow from Actions if that happens.

No manual double entry is needed: **NextReset website publication → public API → this data repository**. This repository never writes back to the website. Corrections should be reported in an issue with the event ID and a public source link; they are reviewed upstream before the next sync.

## Scope and provenance

We publish a selected set of factual metadata: event identifiers, lifecycle, verification status, timestamps, affected plans, and evidence URLs. `primary_verified` describes the evidence; it does **not** turn an announcement or possible signal into a confirmed reset. `automatic_global` and `banked` describe different reset mechanisms and should be analyzed separately.

This export excludes post text, quoted timing phrases, copied summaries, account-specific verification notes, subscriber data, credentials, operational logs, and website/template source code. Third-party source pages retain their own rights. All timestamps ending in `Z` are UTC. A confirmation timestamp is the public source's confirmation time, not proof of the precise instant every account changed.

## Reuse and attribution

Original dataset compilation and documentation: **[CC BY 4.0](LICENSE)**. MCP server, importer, tests, packaging, and workflow code: **[MIT](LICENSE-CODE)**. No rights to third-party posts, logos, or trademarks are granted.

Suggested attribution:

> Data: [NextReset — Codex Reset Data](https://nextreset.org/), CC BY 4.0. [Dataset](https://github.com/Ibunao/codex-reset-data). Modified: describe your changes, if any.

Attribution may use other reasonable formats permitted by the license; a particular HTML link attribute is not required.

## Local maintenance

Requires Python 3.12+. The dataset exporter uses only the standard library; MCP tests need the package dependencies:

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run python scripts/sync.py
```

## 中文说明

这是 [NextReset](https://nextreset.org/zh/) 维护的公开 Codex 重置事件数据集。JSON 包含事件及独立的待确认信号；CSV 仅包含事件，也保留“公告后过期但未确认”等状态，不能把所有行都算作已完成重置。

仓库还提供[只读 MCP 服务](MCP.md)，可在支持本地 MCP 的客户端查询当前状态、历史事件和证据链接；启动方式与三个工具的说明见文档。

网站先发布数据，GitHub 每小时自动检查一次，内容变化才提交；无需手动维护两份。失败时保留上一份数据，不影响网站。时间戳对应上次内容变化时保存的源数据快照，并非每次检查时间。数据与文档采用 CC BY 4.0，脚本采用 MIT；转载时请注明 NextReset、许可和所做修改。该项目与 OpenAI 无官方关联。
