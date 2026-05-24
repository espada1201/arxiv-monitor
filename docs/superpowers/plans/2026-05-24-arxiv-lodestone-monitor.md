# arXiv → Lodestone Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone arXiv monitor at `~/scripts/arxiv-monitor/` that polls for new papers and ingests them into Lodestone, runnable as a cron job.

**Architecture:** Phase 1 installs Lodestone by cloning it to `~/.lodestone/` and running `uv sync` + first-run config. Phase 2 builds `monitor.py` + wrapper script + config, verified end-to-end with `--dry-run` then a live ingest. The wrapper script `lodestone-ingest.sh` is the only file that knows Lodestone's CLI path, so upstream changes only require touching one file.

**Tech Stack:** Python 3.14, uv (already installed), stdlib only for monitor (no external deps), Lodestone CLI via `uv run`, arXiv Atom XML feed via `http.client` + `xml.etree.ElementTree`, JSON for state file.

---

## Phase 0: Allowed APIs (Documentation-Verified)

**arXiv API:**
- Endpoint: `http://export.arxiv.org/api/query`
- Params: `search_query=cat:cs.AI+OR+cat:cs.LG`, `max_results=25`, `sortBy=submittedDate`, `sortOrder=descending`
- Response: Atom XML, namespace `{'atom': 'http://www.w3.org/2005/Atom'}`
- Paper ID: from `<id>` element URL path, e.g. `https://arxiv.org/abs/2403.12345` → `2403.12345`

**Lodestone CLI (README: CLI Ingestion section):**
- `uv run --project ~/.lodestone python -m _system.scripts.ingest --url <arxiv_url>`
- First run requires TTY or pre-written `~/.config/lodestone/config.toml`
- Config file format:
  ```toml
  [llm]
  provider = "anthropic"
  model = "claude-sonnet-4-6"
  temperature = 0.2
  ```
- DB auto-created at `~/.lodestone/lodestone.db` (directory must exist)
- Exit code 0 = success; non-zero = failure

**Anti-patterns:**
- Do NOT call lodestone MCP tools directly from monitor — only via wrapper script
- Do NOT modify lodestone source
- Do NOT use `export LODESTONE_DB` in shell rc (README warning)

---

## Phase 1: Install Lodestone

### Task 1: Clone Lodestone to `~/.lodestone/`

**Files:**
- Creates: `~/.lodestone/` (git repo)
- Creates: `~/.config/lodestone/config.toml`

- [ ] **Step 1: Clone the repo**

```bash
git clone https://github.com/piercelamb/lodestone.git ~/.lodestone
```

Expected: `Cloning into '/Users/Michael/.lodestone'...` then `done.`

- [ ] **Step 2: Install dependencies with uv**

```bash
cd ~/.lodestone && uv sync
```

Expected: output ending in `Installed N packages` (takes 30–90s). A `.venv/` directory appears inside `~/.lodestone/`.

- [ ] **Step 3: Verify binary exists**

```bash
ls ~/.lodestone/.venv/bin/lodestone-mcp
```

Expected: path printed without error.

- [ ] **Step 4: Create lodestone DB directory**

```bash
mkdir -p ~/.lodestone
```

(Already exists after clone — this is a no-op guard.)

- [ ] **Step 5: Write lodestone config (headless — skips interactive picker)**

The first CLI ingest requires a TTY to run the LLM provider picker, or a pre-written config. Write it now so the monitor can run headlessly:

```bash
mkdir -p ~/.config/lodestone
cat > ~/.config/lodestone/config.toml << 'EOF'
[llm]
provider = "anthropic"
model = "claude-sonnet-4-6"
temperature = 0.2
EOF
```

Expected: file written, no error.

- [ ] **Step 6: Verify config written**

```bash
cat ~/.config/lodestone/config.toml
```

Expected:
```
[llm]
provider = "anthropic"
model = "claude-sonnet-4-6"
temperature = 0.2
```

- [ ] **Step 7: Smoke-test CLI ingest (dry verification)**

Run a real ingest of one well-known paper to confirm the full pipeline works. This also confirms `ANTHROPIC_API_KEY` is available and the classifier runs:

```bash
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY uv run --project ~/.lodestone \
  python -m _system.scripts.ingest --url https://arxiv.org/abs/2305.10601
```

Expected: output showing pipeline stages (fetch → convert → split → classify → index). Final line should indicate success. Takes 1–3 minutes.

- [ ] **Step 8: Verify paper is searchable**

```bash
uv run --project ~/.lodestone python -m _system.scripts.search --search "chain of thought"
```

Expected: at least one result returned mentioning the paper (arXiv:2305.10601 is "Tree of Thoughts").

- [ ] **Step 9: Commit lodestone install record**

```bash
cd ~/scripts/arxiv-monitor
git init
git add eidos/ docs/
git commit -m "chore: init project with spec and plan"
```

Expected: commit created.

---

## Phase 2: Build the Wrapper Script

### Task 2: Create `lodestone-ingest.sh`

**Files:**
- Create: `~/scripts/arxiv-monitor/lodestone-ingest.sh`

- [ ] **Step 1: Write the wrapper script**

```bash
cat > ~/scripts/arxiv-monitor/lodestone-ingest.sh << 'EOF'
#!/bin/bash
uv run --project ~/.lodestone python -m _system.scripts.ingest "$@"
EOF
chmod +x ~/scripts/arxiv-monitor/lodestone-ingest.sh
```

- [ ] **Step 2: Verify wrapper is executable**

```bash
ls -la ~/scripts/arxiv-monitor/lodestone-ingest.sh
```

Expected: `-rwxr-xr-x` permissions.

- [ ] **Step 3: Test wrapper with a known paper**

```bash
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ~/scripts/arxiv-monitor/lodestone-ingest.sh --url https://arxiv.org/abs/1706.03762
```

Expected: pipeline output, success. (This is "Attention Is All You Need" — should ingest cleanly.)

- [ ] **Step 4: Commit**

```bash
cd ~/scripts/arxiv-monitor
git add lodestone-ingest.sh
git commit -m "feat: add lodestone-ingest.sh wrapper"
```

---

## Phase 3: Build `config.json`

### Task 3: Create monitor configuration file

**Files:**
- Create: `~/scripts/arxiv-monitor/config.json`

- [ ] **Step 1: Write config.json**

```bash
cat > ~/scripts/arxiv-monitor/config.json << 'EOF'
{
  "categories": ["cs.AI", "cs.LG", "cs.CL", "cs.CV"],
  "keywords": [],
  "max_results": 25
}
EOF
```

`categories`: arXiv category codes to monitor. `keywords`: optional free-text search terms (empty = category-only). `max_results`: papers fetched per run.

- [ ] **Step 2: Verify**

```bash
python3 -c "import json; c = json.load(open('$HOME/scripts/arxiv-monitor/config.json')); print(c)"
```

Expected: `{'categories': ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV'], 'keywords': [], 'max_results': 25}`

- [ ] **Step 3: Commit**

```bash
cd ~/scripts/arxiv-monitor
git add config.json
git commit -m "feat: add monitor config (cs.AI/LG/CL/CV, 25 results)"
```

---

## Phase 4: Build `monitor.py`

### Task 4: Write the monitor

**Files:**
- Create: `~/scripts/arxiv-monitor/monitor.py`
- Creates at runtime: `~/scripts/arxiv-monitor/seen.json`, `~/scripts/arxiv-monitor/monitor.log`

- [ ] **Step 1: Write the failing test**

Create `~/scripts/arxiv-monitor/test_monitor.py`:

```python
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.expanduser("~/scripts/arxiv-monitor"))

SAMPLE_ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2405.00001v1</id>
    <title>Test Paper Alpha</title>
    <summary>An abstract about testing.</summary>
    <category term="cs.AI"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2405.00002v1</id>
    <title>Test Paper Beta</title>
    <summary>Another abstract.</summary>
    <category term="cs.LG"/>
  </entry>
</feed>"""


class TestFetchPapers(unittest.TestCase):
    def test_fetch_returns_paper_list(self):
        from monitor import fetch_papers
        mock_resp = MagicMock()
        mock_resp.read.return_value = SAMPLE_ATOM
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            papers = fetch_papers(["cs.AI"], [], max_results=25)
        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["id"], "2405.00001")
        self.assertEqual(papers[0]["title"], "Test Paper Alpha")
        self.assertEqual(papers[1]["id"], "2405.00002")

    def test_fetch_deduplicates_seen(self):
        from monitor import filter_new
        papers = [{"id": "2405.00001", "title": "A"}, {"id": "2405.00002", "title": "B"}]
        seen = {"2405.00001"}
        new = filter_new(papers, seen)
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["id"], "2405.00002")

    def test_dry_run_does_not_write_seen(self):
        from monitor import run
        with tempfile.TemporaryDirectory() as tmpdir:
            seen_path = os.path.join(tmpdir, "seen.json")
            log_path = os.path.join(tmpdir, "monitor.log")
            config = {"categories": ["cs.AI"], "keywords": [], "max_results": 5}
            mock_resp = MagicMock()
            mock_resp.read.return_value = SAMPLE_ATOM
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            with patch("urllib.request.urlopen", return_value=mock_resp):
                run(config=config, seen_path=seen_path, log_path=log_path,
                    wrapper=None, dry_run=True)
            self.assertFalse(os.path.exists(seen_path))

    def test_live_run_writes_seen_on_success(self):
        from monitor import run
        with tempfile.TemporaryDirectory() as tmpdir:
            seen_path = os.path.join(tmpdir, "seen.json")
            log_path = os.path.join(tmpdir, "monitor.log")
            config = {"categories": ["cs.AI"], "keywords": [], "max_results": 5}
            mock_resp = MagicMock()
            mock_resp.read.return_value = SAMPLE_ATOM
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            with patch("urllib.request.urlopen", return_value=mock_resp):
                with patch("subprocess.run") as mock_sub:
                    mock_sub.return_value = MagicMock(returncode=0)
                    run(config=config, seen_path=seen_path, log_path=log_path,
                        wrapper="/bin/true", dry_run=False)
            seen = json.loads(open(seen_path).read())
            self.assertIn("2405.00001", seen)
            self.assertIn("2405.00002", seen)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd ~/scripts/arxiv-monitor
python3 test_monitor.py 2>&1 | head -5
```

Expected: `ModuleNotFoundError: No module named 'monitor'`

- [ ] **Step 3: Write `monitor.py`**

```python
#!/usr/bin/env python3
"""arXiv monitor — polls arXiv and ingests new papers into Lodestone."""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_API = "http://export.arxiv.org/api/query"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(BASE_DIR, "config.json")
DEFAULT_SEEN = os.path.join(BASE_DIR, "seen.json")
DEFAULT_LOG = os.path.join(BASE_DIR, "monitor.log")
DEFAULT_WRAPPER = os.path.join(BASE_DIR, "lodestone-ingest.sh")


def _paper_id(entry_id_url: str) -> str:
    """Extract bare arXiv ID from URL like https://arxiv.org/abs/2405.00001v1."""
    path = entry_id_url.rstrip("/").split("/")[-1]
    return path.split("v")[0]  # strip version suffix


def fetch_papers(categories: list[str], keywords: list[str], max_results: int) -> list[dict]:
    """Query arXiv API and return list of paper dicts with id, title, url."""
    parts = [f"cat:{c}" for c in categories]
    parts += [f"all:{k}" for k in keywords]
    query = "+OR+".join(parts) if parts else "all:*"
    url = (
        f"{ARXIV_API}?search_query={query}"
        f"&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    papers = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        raw_id = (entry.findtext("atom:id", "", ARXIV_NS) or "").strip()
        if not raw_id:
            continue
        paper_id = _paper_id(raw_id)
        title = " ".join((entry.findtext("atom:title", "", ARXIV_NS) or "").split())
        papers.append({
            "id": paper_id,
            "title": title,
            "url": f"https://arxiv.org/abs/{paper_id}",
        })
    return papers


def filter_new(papers: list[dict], seen: set[str]) -> list[dict]:
    """Return papers whose IDs are not in seen."""
    return [p for p in papers if p["id"] not in seen]


def load_seen(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_seen(path: str, seen: set[str]) -> None:
    with open(path + ".tmp", "w") as f:
        json.dump(sorted(seen), f, indent=2)
    os.replace(path + ".tmp", path)


def log_event(path: str, level: str, message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [{level}] {message}\n"
    with open(path, "a") as f:
        f.write(line)
    print(line, end="")


def ingest(paper: dict, wrapper: str, log_path: str) -> bool:
    """Call wrapper script with --url. Returns True on success."""
    result = subprocess.run(
        [wrapper, "--url", paper["url"]],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        log_event(log_path, "SUCCESS", f"{paper['id']} — {paper['title']}")
        return True
    else:
        log_event(log_path, "FAILURE", f"{paper['id']} — {paper['title']} — {result.stderr.strip()[:200]}")
        return False


def run(
    config: dict,
    seen_path: str,
    log_path: str,
    wrapper: str | None,
    dry_run: bool,
) -> None:
    papers = fetch_papers(
        config.get("categories", []),
        config.get("keywords", []),
        config.get("max_results", 25),
    )
    seen = load_seen(seen_path)
    new_papers = filter_new(papers, seen)

    if dry_run:
        print(f"DRY RUN — {len(new_papers)} new paper(s) found (seen: {len(seen)}):")
        for p in new_papers:
            print(f"  [{p['id']}] {p['title']}")
        return

    log_event(log_path, "INFO", f"Run start — {len(new_papers)} new paper(s) to ingest")
    for paper in new_papers:
        if ingest(paper, wrapper, log_path):
            seen.add(paper["id"])
            save_seen(seen_path, seen)

    log_event(log_path, "INFO", "Run complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="arXiv → Lodestone monitor")
    parser.add_argument("--dry-run", action="store_true", help="Print new papers without ingesting")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--seen", default=DEFAULT_SEEN)
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--wrapper", default=DEFAULT_WRAPPER)
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    run(
        config=config,
        seen_path=args.seen,
        log_path=args.log,
        wrapper=args.wrapper if not args.dry_run else None,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
cd ~/scripts/arxiv-monitor
python3 test_monitor.py -v
```

Expected:
```
test_dry_run_does_not_write_seen ... ok
test_fetch_deduplicates_seen ... ok
test_fetch_returns_paper_list ... ok
test_live_run_writes_seen_on_success ... ok

Ran 4 tests in 0.XXXs

OK
```

- [ ] **Step 5: Commit**

```bash
cd ~/scripts/arxiv-monitor
git add monitor.py test_monitor.py
git commit -m "feat: add monitor.py with arXiv fetch, dedup, and ingest loop"
```

---

## Phase 5: End-to-End Verification

### Task 5: Verify the full pipeline

**Files:**
- No new files — verification only.

- [ ] **Step 1: Dry-run test**

```bash
cd ~/scripts/arxiv-monitor
python3 monitor.py --dry-run
```

Expected: prints `DRY RUN — N new paper(s) found` with paper IDs and titles. N ≥ 1. `seen.json` does NOT exist after this.

- [ ] **Step 2: Live ingest (first real run)**

```bash
cd ~/scripts/arxiv-monitor
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY python3 monitor.py
```

Expected:
- Log lines appear: `INFO Run start`, `SUCCESS <id> — <title>` (for each paper), `INFO Run complete`
- `seen.json` is created containing ingested paper IDs
- Takes 1–5 minutes depending on paper count

- [ ] **Step 3: Verify seen.json written**

```bash
python3 -c "import json; ids=json.load(open('$HOME/scripts/arxiv-monitor/seen.json')); print(f'{len(ids)} papers seen'); print(ids[:3])"
```

Expected: `N papers seen` where N ≥ 1, plus first 3 IDs.

- [ ] **Step 4: Verify idempotence (second run skips already-seen papers)**

```bash
cd ~/scripts/arxiv-monitor
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY python3 monitor.py
```

Expected: `INFO Run start — 0 new paper(s) to ingest` (all already seen).

- [ ] **Step 5: Verify paper is searchable in Lodestone via MCP**

Use the `mcp__lodestone__search` tool in Claude Code with a keyword from one of the ingested paper titles. Confirm ≥ 1 result is returned.

- [ ] **Step 6: Set up cron job**

```bash
(crontab -l 2>/dev/null; echo "0 */2 * * * cd $HOME/scripts/arxiv-monitor && ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY $HOME/scripts/arxiv-monitor/monitor.py >> $HOME/scripts/arxiv-monitor/monitor.log 2>&1") | crontab -
```

Verify:
```bash
crontab -l | grep arxiv
```

Expected: the cron line appears.

- [ ] **Step 7: Final commit**

```bash
cd ~/scripts/arxiv-monitor
git add seen.json monitor.log
git commit -m "chore: add initial seen.json and log after first live run"
```

---

## Definition of Done Checklist

- [ ] `python3 ~/scripts/arxiv-monitor/monitor.py --dry-run` prints ≥1 paper title
- [ ] A live run ingests ≥1 paper (SUCCESS log line present)
- [ ] `mcp__lodestone__search` can find an ingested paper by keyword
- [ ] `seen.json` exists and contains ≥1 paper ID
- [ ] Second run produces 0 new ingests (idempotent)
- [ ] Cron entry installed and verified with `crontab -l`
