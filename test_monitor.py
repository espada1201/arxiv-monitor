import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

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


def _mock_urlopen(data):
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestFetchPapers(unittest.TestCase):
    def test_fetch_returns_paper_list(self):
        from monitor import fetch_papers
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_ATOM)):
            papers = fetch_papers(["cs.AI"], [], max_results=25)
        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["id"], "2405.00001")
        self.assertEqual(papers[0]["title"], "Test Paper Alpha")
        self.assertEqual(papers[1]["id"], "2405.00002")

    def test_filter_new_deduplicates_seen(self):
        from monitor import filter_new
        papers = [{"id": "2405.00001", "title": "A"}, {"id": "2405.00002", "title": "B"}]
        new = filter_new(papers, {"2405.00001"})
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["id"], "2405.00002")

    def test_dry_run_does_not_write_seen(self):
        from monitor import run
        with tempfile.TemporaryDirectory() as tmpdir:
            seen_path = os.path.join(tmpdir, "seen.json")
            log_path = os.path.join(tmpdir, "monitor.log")
            config = {"categories": ["cs.AI"], "keywords": [], "max_results": 5}
            with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_ATOM)):
                run(config=config, seen_path=seen_path, log_path=log_path,
                    wrapper=None, dry_run=True)
            self.assertFalse(os.path.exists(seen_path))

    def test_live_run_writes_seen_on_success(self):
        from monitor import run
        with tempfile.TemporaryDirectory() as tmpdir:
            seen_path = os.path.join(tmpdir, "seen.json")
            log_path = os.path.join(tmpdir, "monitor.log")
            config = {"categories": ["cs.AI"], "keywords": [], "max_results": 5}
            with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_ATOM)):
                with patch("subprocess.run") as mock_sub:
                    mock_sub.return_value = MagicMock(returncode=0)
                    run(config=config, seen_path=seen_path, log_path=log_path,
                        wrapper="/bin/true", dry_run=False)
            seen = json.loads(open(seen_path).read())
            self.assertIn("2405.00001", seen)
            self.assertIn("2405.00002", seen)


if __name__ == "__main__":
    unittest.main()
