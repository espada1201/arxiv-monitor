---
tldr: arXiv monitor polls for new papers by keyword/category and ingests them into Lodestone via a wrapper script, tracking seen IDs to avoid duplicates
---

# arXiv Monitor

## Target

Automatically discover new arXiv papers matching configured keywords/categories and ingest them into Lodestone so they are searchable via MCP. Eliminates manual paper tracking and seeds the Lodestone corpus continuously.

## Behaviour

- `monitor.py --dry-run` prints new papers found without ingesting them
- `monitor.py` (live run) ingests each new paper via `lodestone-ingest.sh` wrapper
- Papers already in `seen.json` are skipped — no duplicate ingests
- Each run updates `seen.json` with newly ingested paper IDs
- Successes and failures are logged with timestamps to `monitor.log`
- Monitor is safe to run as a cron job (no daemon required, no lock files)
- Monitor never calls lodestone directly — only via `lodestone-ingest.sh`
- `lodestone-ingest.sh` is the only coupling point to lodestone's CLI path
- No modifications to lodestone source code

## Design

### File Layout

```
~/scripts/arxiv-monitor/
├── monitor.py              # main poll + ingest loop
├── config.json             # keywords, categories, max_results
├── seen.json               # set of ingested arXiv IDs (state file)
├── monitor.log             # success/failure log
├── lodestone-ingest.sh     # wrapper — only file that knows lodestone's CLI path
└── eidos/                  # this spec
```

### arXiv API

- Endpoint: `http://export.arxiv.org/api/query`
- Protocol: Atom XML feed, parsed with `xml.etree.ElementTree`
- Namespace: `{'atom': 'http://www.w3.org/2005/Atom'}`
- Paper ID extracted from entry `<id>` URL path (e.g. `2403.12345`)
- Query params: `search_query`, `max_results`, `sortBy=submittedDate`, `sortOrder=descending`

### Lodestone Install

- Lodestone cloned to `~/.lodestone/` (source + venv)
- DB at `~/.lodestone/lodestone.db`
- Wrapper: `uv run --project ~/.lodestone python -m _system.scripts.ingest --url <arxiv_url>`

### Deduplication

- `seen.json` is a JSON array of arXiv ID strings
- Loaded at startup, saved atomically after each successful ingest
- Dry-run does not modify `seen.json`

### Config

- `config.json` controls: `categories` (list of arXiv category codes), `keywords` (list of search terms), `max_results` (int, default 25)
- Default categories: `cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`

## Verification

- `monitor.py --dry-run` prints ≥1 paper title without writing `seen.json`
- Live run: `seen.json` grows after run; `monitor.log` shows SUCCESS entries
- `mcp__lodestone__search` can find an ingested paper by title keyword

## Interactions

- Depends on: Lodestone installed at `~/.lodestone/` with venv populated
- Depends on: `ANTHROPIC_API_KEY` set (for lodestone classify step)
- Depends on: `~/.config/lodestone/config.toml` written (first-run picker)
- Produces: Lodestone corpus entries searchable via `mcp__lodestone__*` tools

## Mapping

> [[monitor.py]]
> [[lodestone-ingest.sh]]
> [[config.json]]
> [[seen.json]]
