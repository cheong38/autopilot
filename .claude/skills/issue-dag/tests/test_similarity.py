#!/usr/bin/env python3
"""Unit tests for similarity and UL functions in dag-analyze.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "dag-analyze.py")


def run_cmd(*args, dag_file=None, expect_fail=False):
    cmd = [sys.executable, SCRIPT]
    if dag_file:
        cmd.extend(["--dag-file", str(dag_file)])
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not expect_fail and result.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.returncode, result.stdout, result.stderr


class SimilaritySetup(unittest.TestCase):
    """Setup DAG with issues that have keywords and paths for similarity testing."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)

        # Add nodes with keywords
        run_cmd("add-node", "--id", "1", "--title", "인증 시스템 구현",
                "--type", "story", "--keywords", "인증,로그인,auth",
                "--paths", "src/auth/*,src/middleware/*", dag_file=self.path)
        run_cmd("add-node", "--id", "2", "--title", "결제 시스템 구현",
                "--type", "story", "--keywords", "결제,payment,billing",
                "--paths", "src/payment/*", dag_file=self.path)
        run_cmd("add-node", "--id", "3", "--title", "로그인 UI 개선",
                "--type", "task", "--keywords", "로그인,UI,frontend",
                "--paths", "src/components/login/*", dag_file=self.path)

        # Create UL dictionary in same directory as DAG
        ul_path = Path(self.path).parent / "ubiquitous-language.json"
        ul = {
            "terms": [
                {"canonical": "인증", "aliases": ["auth", "authentication", "로그인 인증"], "domain": "identity"},
                {"canonical": "결제", "aliases": ["payment", "billing", "checkout"], "domain": "commerce"},
            ]
        }
        with open(ul_path, "w") as f:
            json.dump(ul, f)
        self.ul_path = str(ul_path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)
        if os.path.exists(self.ul_path):
            os.unlink(self.ul_path)


class TestSimilar(SimilaritySetup):
    def test_similar_by_keyword(self):
        """Search for 'auth' should find '인증 시스템' via UL alias mapping."""
        _, stdout, _ = run_cmd("similar", "--keywords", "auth,login",
                               dag_file=self.path)
        results = json.loads(stdout)
        ids = [r["id"] for r in results]
        self.assertIn("1", ids)  # 인증 시스템

    def test_similar_by_keyword_cross_language(self):
        """'authentication' should match '인증' via UL alias."""
        _, stdout, _ = run_cmd("similar", "--keywords", "authentication",
                               dag_file=self.path)
        results = json.loads(stdout)
        ids = [r["id"] for r in results]
        self.assertIn("1", ids)

    def test_similar_by_path(self):
        """Search by path should find issues touching same directories."""
        _, stdout, _ = run_cmd("similar", "--paths", "src/auth/*",
                               dag_file=self.path)
        results = json.loads(stdout)
        ids = [r["id"] for r in results]
        self.assertIn("1", ids)

    def test_similar_by_title(self):
        """Title token overlap should contribute to similarity."""
        # Title-only similarity produces low composite scores (0.2 weight),
        # so use a low threshold to verify title signal works.
        _, stdout, _ = run_cmd("similar", "--title", "로그인 기능 추가",
                               "--threshold", "0.01", dag_file=self.path)
        results = json.loads(stdout)
        # Should find node 3 (로그인 UI) due to title overlap
        ids = [r["id"] for r in results]
        self.assertIn("3", ids)

    def test_similar_no_match(self):
        """Unrelated query should return empty."""
        _, stdout, _ = run_cmd("similar", "--keywords", "deployment,kubernetes",
                               dag_file=self.path)
        results = json.loads(stdout)
        self.assertEqual(results, [])

    def test_similar_threshold(self):
        """High threshold should filter out low matches."""
        _, stdout, _ = run_cmd("similar", "--keywords", "auth",
                               "--threshold", "0.9", dag_file=self.path)
        results = json.loads(stdout)
        # Very high threshold should filter most results
        for r in results:
            self.assertGreaterEqual(r["score"], 0.9)

    def test_similar_without_ul(self):
        """Similarity should work even without UL dictionary (fallback)."""
        os.unlink(self.ul_path)
        _, stdout, _ = run_cmd("similar", "--keywords", "로그인",
                               dag_file=self.path)
        results = json.loads(stdout)
        # Should still find matches via direct keyword comparison
        ids = [r["id"] for r in results]
        self.assertIn("3", ids)  # 로그인 UI has "로그인" keyword


class TestUlLookup(SimilaritySetup):
    def test_lookup_canonical(self):
        _, stdout, _ = run_cmd("ul-lookup", "--term", "인증", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result["canonical"], "인증")
        self.assertIn("auth", result["aliases"])

    def test_lookup_alias(self):
        _, stdout, _ = run_cmd("ul-lookup", "--term", "auth", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result["canonical"], "인증")

    def test_lookup_not_found(self):
        _, stdout, _ = run_cmd("ul-lookup", "--term", "unknown_term", dag_file=self.path)
        result = json.loads(stdout)
        self.assertIsNone(result["canonical"])


class TestUlAdd(SimilaritySetup):
    def test_add_new_term(self):
        run_cmd("ul-add", "--canonical", "배포", "--aliases", "deploy,deployment",
                "--domain", "devops", dag_file=self.path)
        _, stdout, _ = run_cmd("ul-lookup", "--term", "deploy", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result["canonical"], "배포")

    def test_add_aliases_to_existing(self):
        """Adding to existing canonical should merge aliases."""
        run_cmd("ul-add", "--canonical", "인증", "--aliases", "login,signin",
                dag_file=self.path)
        _, stdout, _ = run_cmd("ul-lookup", "--term", "login", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result["canonical"], "인증")
        self.assertIn("login", result["aliases"])


class TestUlScan(unittest.TestCase):
    def test_scan_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dag_path = os.path.join(tmpdir, "dag.json")
            run_cmd("init", "--repo", "test/repo", "--force", dag_file=dag_path)
            _, stdout, _ = run_cmd("ul-scan", "--dir", tmpdir, dag_file=dag_path)
            results = json.loads(stdout)
            self.assertIsInstance(results, list)


if __name__ == "__main__":
    unittest.main()
