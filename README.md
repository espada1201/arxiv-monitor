# arxiv-monitor

Polls the arXiv API for new papers and ingests them into [Lodestone](https://github.com/piercelamb/lodestone).

## How it works

1. Queries arXiv for papers matching configured categories/keywords
2. Skips papers already seen (`seen.json`)
3. Calls `lodestone-ingest.sh` for each new paper
4. Logs successes and failures to `monitor.log`

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Lodestone installed at `~/.lodestone/` (see below)
- A cloud LLM API key (Anthropic, OpenAI, or DeepSeek) — Lodestone uses it for paper classification

## Installation

### 1. Install Lodestone

```bash
git clone https://github.com/piercelamb/lodestone ~/.lodestone
cd ~/.lodestone
uv sync
```

Then configure your LLM provider. You can do this manually:

```bash
mkdir -p ~/.config/lodestone
cat > ~/.config/lodestone/config.toml << 'EOF'
[llm]
provider = "openai"
model = "deepseek-chat"
temperature = 0.2
EOF
```

Or run the interactive doctor (requires a TTY):

```bash
uv run --project ~/.lodestone python -m _system.scripts.doctor
```

> **Note:** If you prefer to install Lodestone manually (different path, existing install, etc.), update `lodestone-ingest.sh` to match your setup — it's the only coupling point.

### 2. Clone this repo

```bash
git clone https://github.com/espada1201/arxiv-monitor ~/scripts/arxiv-monitor
cd ~/scripts/arxiv-monitor
chmod +x lodestone-ingest.sh
```

### 3. Set credentials

```bash
cp .env.example .env
# Edit .env with your API key
```

`.env` format:

```
OPENAI_API_KEY=your-key-here
OPENAI_BASE_URL=https://api.deepseek.com   # omit if using OpenAI directly
```

### 4. Configure categories

Edit `config.json`:

```json
{
  "categories": ["cs.AI", "cs.LG", "cs.CL", "cs.CV"],
  "keywords": [],
  "max_results": 25
}
```

## Usage

```bash
# Preview new papers without ingesting
python3 monitor.py --dry-run

# Ingest new papers
python3 monitor.py

# Custom paths
python3 monitor.py --config config.json --seen seen.json --log monitor.log
```

## Cron setup

```bash
# Run every 2 hours
0 */2 * * * cd ~/scripts/arxiv-monitor && python3 monitor.py >> monitor.log 2>&1
```

## Files

| File | Purpose |
|------|---------|
| `monitor.py` | Main monitor (stdlib only, no dependencies) |
| `lodestone-ingest.sh` | Sole coupling point to Lodestone CLI |
| `config.json` | Categories and keywords to watch |
| `seen.json` | Tracks ingested paper IDs (auto-created, git-ignored) |
| `monitor.log` | Run log (git-ignored) |
| `.env` | API credentials (git-ignored) |

## Tests

```bash
python3 -m pytest test_monitor.py -v
```
