#!/usr/bin/env python3
"""arXiv monitor — polls arXiv and ingests new papers into Lodestone."""

import argparse
import json
import os
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_USER_AGENT = "arxiv-lodestone-monitor/1.0 (https://github.com/local/arxiv-monitor)"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(BASE_DIR, "config.json")
DEFAULT_SEEN = os.path.join(BASE_DIR, "seen.json")
DEFAULT_LOG = os.path.join(BASE_DIR, "monitor.log")
DEFAULT_WRAPPER = os.path.join(BASE_DIR, "lodestone-ingest.sh")


def _paper_id(entry_id_url: str) -> str:
    path = entry_id_url.rstrip("/").split("/")[-1]
    return path.split("v")[0]


def fetch_papers(categories: list, keywords: list, max_results: int) -> list:
    parts = [f"cat:{c}" for c in categories] + [f"all:{k}" for k in keywords]
    query = " OR ".join(parts) if parts else "all:*"
    url = ARXIV_API + "?" + urllib.parse.urlencode({
        "search_query": query,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    result = subprocess.run(
        ["curl", "-sS", "--max-time", "30", "-A", ARXIV_USER_AGENT,
         "-w", "\n%{http_code}", url],
        capture_output=True, check=True, text=True,
    )
    body, _, status = result.stdout.rpartition("\n")
    if status.strip() != "200":
        raise RuntimeError(f"arXiv returned HTTP {status.strip()}")
    data = body.encode()
    root = ET.fromstring(data)
    papers = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        raw_id = (entry.findtext("atom:id", "", ARXIV_NS) or "").strip()
        if not raw_id:
            continue
        title = " ".join((entry.findtext("atom:title", "", ARXIV_NS) or "").split())
        papers.append({
            "id": _paper_id(raw_id),
            "title": title,
            "url": f"https://arxiv.org/abs/{_paper_id(raw_id)}",
        })
    return papers


def filter_new(papers: list, seen: set) -> list:
    return [p for p in papers if p["id"] not in seen]


def load_seen(path: str) -> set:
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_seen(path: str, seen: set) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sorted(seen), f, indent=2)
    os.replace(tmp, path)


def log_event(path: str, level: str, message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [{level}] {message}\n"
    with open(path, "a") as f:
        f.write(line)
    print(line, end="")


def ingest(paper: dict, wrapper: str, log_path: str) -> bool:
    result = subprocess.run(
        [wrapper, "--url", paper["url"]],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        log_event(log_path, "SUCCESS", f"{paper['id']} — {paper['title']}")
        return True
    log_event(log_path, "FAILURE",
              f"{paper['id']} — {paper['title']} — {result.stderr.strip()[:200]}")
    return False


def run(config: dict, seen_path: str, log_path: str, wrapper, dry_run: bool) -> None:
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
    parser.add_argument("--dry-run", action="store_true")
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
