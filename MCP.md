# NextReset MCP Server

Read public Codex reset status, historical events, and original source evidence through MCP. Maintained by **[NextReset](https://nextreset.org/)**. Independent of OpenAI.

This is a **local stdio MCP server** built with the official Python SDK. It fetches the existing public NextReset API over HTTPS. No API key or NextReset account is required. It does not access account usage, subscriptions, private databases, or the website's source repository, and it has no write tools.

## Install and connect

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), which provides `uvx`. Python 3.12+ is required; uv can provision it. Start the released server with:

```sh
uvx --python 3.12 --from git+https://github.com/Ibunao/codex-reset-data@v0.1.0 nextreset-mcp
```

The process waits for MCP messages on stdin and writes protocol responses to stdout. That is expected; it is not a web server.

For MCP clients that support local command-based servers, add this configuration using the client's MCP settings:

```json
{
  "mcpServers": {
    "nextreset": {
      "command": "uvx",
      "args": [
        "--python", "3.12",
        "--from", "git+https://github.com/Ibunao/codex-reset-data@v0.1.0",
        "nextreset-mcp"
      ]
    }
  }
}
```

Use the absolute path to `uvx` if a desktop client cannot find it. Client configuration file locations vary; use the client's own documentation. This release has **no hosted MCP URL**. The website's JSON API URLs are upstream data sources, not MCP endpoints.

Example prompts:

- "Check the current public Codex reset status and show how old the evidence is."
- "List the five most recent confirmed automatic/global resets, with source links."
- "Show the original evidence and lifecycle for event ID …"

## Tools

| Tool | Inputs | Result |
| --- | --- | --- |
| `get_reset_status` | None | Status snapshot, source health, Global Radar and Banked signals |
| `list_reset_events` | `reset_type`: `all` (default), `automatic_global`, `banked`; `lifecycle`: `all` (default) or an event lifecycle; `since`: optional `YYYY-MM-DD`; `limit`: 1–100, default 20 | Events ordered by newest supporting evidence; `total` is the filtered count before limit |
| `get_reset_event` | Required `event_id` | One complete event, revision and evidence URLs; unknown IDs return an error |

`since` includes that UTC date and filters `lastSupportingEvidenceAt`. Lifecycles: `announced`, `scheduled`, `rolling_out`, `confirmed`, `expired_unconfirmed`, `cancelled`, `corrected`. Possible signals are separate from events and are not included in the event-list tool. The status tool may include public availability signals.

Every tool includes `sourceUrl`, `schemaVersion`, `generatedAt`, `dataAsOf`, and a computed `dataAgeSeconds`. Read the age even if a saved status snapshot labels itself fresh. Source endpoints are cached for up to five minutes per server process. Requests time out after 20 seconds; failed fetches and invalid schemas return tool errors, with no stale fallback after cache expiry. No arbitrary URL or hostname input is supported.

Preserve both `lifecycle` and `verificationStatus`: a primary-verified announcement is still an announcement. Public confirmation time is not proof of the exact instant every account received a reset. Rule scores are not calibrated occurrence probabilities. See [NextReset's methodology](https://nextreset.org/method/) and the [dataset schema](SCHEMA.md).

## Data updates

MCP tools query the published website API, so a new release of this package is **not** needed when event data changes. The separate hourly GitHub workflow continues maintaining JSON/CSV downloads. Neither path writes back to the website.

## Run from a checkout

```sh
git clone https://github.com/Ibunao/codex-reset-data.git
cd codex-reset-data
uv sync --locked
uv run nextreset-mcp
```

For directories that inspect a Docker build:

```sh
docker build -t nextreset-mcp .
docker run --rm -i nextreset-mcp
```

Docker also uses local stdio and requires outbound HTTPS to `nextreset.org`. The Python package and container include only the MCP implementation, not the historical dataset or private website code. Code is [MIT](LICENSE-CODE); original dataset compilation and repository documentation are [CC BY 4.0](LICENSE).

## Maintainer checks

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
```

Tests exercise MCP discovery, tool calls, input validation, lifecycle preservation, evidence lookup, source failures, and the five-minute cache. Unit tests use controlled API responses; a real stdio smoke check against the public API is a separate release acceptance step.

## 中文

这是 NextReset 的只读 MCP 服务，通过本地 stdio 连接支持命令启动的 MCP 客户端，查询网站公开 API。无须 API key。包含当前状态、历史事件筛选、单个事件及原始证据三个工具。数据由网站统一维护，MCP 最多缓存 5 分钟，不需要随每次数据更新重新发布程序。

安装与客户端配置见上文。目前没有远程 MCP 地址，不能将普通 JSON 接口填进“远程 MCP URL”栏。返回的 `dataAsOf` 与 `dataAgeSeconds` 用于判断来源新鲜度；“已公告”不等于“已确认”，公开事件也不表示某个个人账户已获得重置。
