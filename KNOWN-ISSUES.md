# Known Issues & Manual Setup Notes

## arXiv API Rate Limiting (429 errors)

arXiv's API blocks Python's `urllib` HTTP/1.1 requests with HTTP 429 when the IP
has made many recent requests. `curl` (HTTP/2 + different TLS fingerprint) succeeds
from the same IP.

**Workaround applied:** `monitor.py` now uses `curl` via subprocess instead of
`urllib`. This bypasses the rate-limit discrimination.

**What still needs to be tested (do this after manual Lodestone install):**

1. `python3 monitor.py --dry-run`
   — Should print "DRY RUN — N new paper(s) found" with paper IDs and titles
   — If it prints 0 papers, `seen.json` may be pre-populated; delete it and retry

2. `python3 monitor.py`
   — Should ingest papers into Lodestone
   — Check `monitor.log` for SUCCESS/FAILURE lines
   — Lodestone stores papers in `~/.lodestone/lodestone.db`

3. Verify via Lodestone MCP search tool in Claude Code
   — Use the lodestone search tool to query for a paper title or author
   — Confirms the full pipeline is working end-to-end

## Lodestone Manual Install

The user will reinstall Lodestone manually from the GitHub repo:
https://github.com/piercelamb/lodestone

Steps:
```bash
# 1. Clone
git clone https://github.com/piercelamb/lodestone ~/.lodestone
cd ~/.lodestone
uv sync

# 2. Configure LLM (DeepSeek via OpenAI-compatible API)
mkdir -p ~/.config/lodestone
cat > ~/.config/lodestone/config.toml << 'EOF'
[llm]
provider = "openai"
model = "deepseek-chat"
temperature = 0.2
EOF

# 3. Set credentials in arxiv-monitor/.env
echo 'OPENAI_API_KEY=<your-deepseek-key>' > ~/scripts/arxiv-monitor/.env
echo 'OPENAI_BASE_URL=https://api.deepseek.com' >> ~/scripts/arxiv-monitor/.env
```

## DeepSeek JSON Schema Patch

Lodestone's `_system/llm/openai_adapter.py` requires patching to work with
DeepSeek (which doesn't support strict JSON schema mode).

The patch switches to `json_object` mode when `OPENAI_BASE_URL` is set.
See `openai_adapter.py` in `~/.lodestone/_system/llm/` — apply the same patch
after reinstalling.

**Patch location:** `~/.lodestone/_system/llm/openai_adapter.py`

**What to change in `call()`:**
```python
import os  # add at top if not present

# In the call() function, replace the client + response_format setup with:
base_url = os.environ.get("OPENAI_BASE_URL")
client = openai.OpenAI(timeout=_TIMEOUT_S, **({"base_url": base_url} if base_url else {}))
use_json_object = bool(base_url)
response_format = (
    {"type": "json_object"} if use_json_object
    else {"type": "json_schema", "json_schema": {"name": schema["name"], "schema": schema["schema"], "strict": True}}
)
system_with_hint = system if not use_json_object else (
    system + "\n\nRespond with a JSON object only. No markdown, no prose."
)
```
