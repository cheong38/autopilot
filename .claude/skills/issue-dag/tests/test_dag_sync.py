#!/usr/bin/env python3
"""Unit tests for dag-sync.sh helper functions and structured output.

Tests provider detection, Wiki URL generation, local fallback,
and structured output parsing. Uses subprocess to source and
call bash functions.

Uses only Python standard library. No external packages.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "dag-sync.sh")
DAG_ANALYZE = str(Path(__file__).parent.parent / "scripts" / "dag-analyze.py")


def run_bash_func(func_call, env_overrides=None):
    """Source dag-sync.sh and run a function, return stdout.

    Sources with set +eu to avoid pipefail/unset errors during sourcing,
    then runs the function call.
    """
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    cmd = f'set +eu; source "{SCRIPT}"; set -eu; {func_call}'
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True, text=True, env=env
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def parse_sync_result(stdout):
    """Parse DAG_SYNC_RESULT_BEGIN/END block into a dict."""
    result = {}
    in_block = False
    for line in stdout.splitlines():
        if line.strip() == "DAG_SYNC_RESULT_BEGIN":
            in_block = True
            continue
        if line.strip() == "DAG_SYNC_RESULT_END":
            in_block = False
            continue
        if in_block and "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


class TestDetectProvider(unittest.TestCase):
    """Test detect_provider() function."""

    def test_github_ssh(self):
        rc, out, _ = run_bash_func(
            'detect_provider "git@github.com:owner/repo.git"'
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "github")

    def test_github_https(self):
        rc, out, _ = run_bash_func(
            'detect_provider "https://github.com/owner/repo.git"'
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "github")

    def test_gitlab_ssh(self):
        rc, out, _ = run_bash_func(
            'detect_provider "git@gitlab.com:group/project.git"'
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "gitlab")

    def test_gitlab_https(self):
        rc, out, _ = run_bash_func(
            'detect_provider "https://gitlab.com/group/project.git"'
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "gitlab")

    def test_gitlab_selfhosted(self):
        rc, out, _ = run_bash_func(
            'detect_provider "https://gitlab.mycompany.com/team/repo.git"'
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "gitlab")

    def test_bitbucket_unknown(self):
        rc, out, _ = run_bash_func(
            'detect_provider "git@bitbucket.org:owner/repo.git"'
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "unknown")

    def test_custom_host_unknown(self):
        rc, out, _ = run_bash_func(
            'detect_provider "https://git.internal.corp/team/repo.git"'
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "unknown")


class TestExtractRepo(unittest.TestCase):
    """Test extract_repo() function."""

    def test_github_ssh(self):
        rc, out, _ = run_bash_func(
            'extract_repo "git@github.com:owner/repo.git" "github"'
        )
        self.assertEqual(out, "owner/repo")

    def test_github_https(self):
        rc, out, _ = run_bash_func(
            'extract_repo "https://github.com/owner/repo.git" "github"'
        )
        self.assertEqual(out, "owner/repo")

    def test_github_no_git_suffix(self):
        rc, out, _ = run_bash_func(
            'extract_repo "https://github.com/owner/repo" "github"'
        )
        self.assertEqual(out, "owner/repo")

    def test_gitlab_ssh(self):
        rc, out, _ = run_bash_func(
            'extract_repo "git@gitlab.com:group/project.git" "gitlab"'
        )
        self.assertEqual(out, "group/project")

    def test_gitlab_https(self):
        rc, out, _ = run_bash_func(
            'extract_repo "https://gitlab.com/group/project.git" "gitlab"'
        )
        self.assertEqual(out, "group/project")

    def test_gitlab_subgroup(self):
        rc, out, _ = run_bash_func(
            'extract_repo "https://gitlab.com/group/subgroup/project.git" "gitlab"'
        )
        self.assertEqual(out, "group/subgroup/project")

    def test_unknown_returns_empty(self):
        rc, out, _ = run_bash_func(
            'extract_repo "git@bitbucket.org:owner/repo.git" "unknown"'
        )
        self.assertEqual(out, "")


class TestBuildWikiUrl(unittest.TestCase):
    """Test build_wiki_url() function."""

    def test_github_ssh(self):
        rc, out, _ = run_bash_func(
            'build_wiki_url "git@github.com:owner/repo.git" "github" "owner/repo"'
        )
        self.assertEqual(out, "git@github.com:owner/repo.wiki.git")

    def test_github_https(self):
        rc, out, _ = run_bash_func(
            'build_wiki_url "https://github.com/owner/repo.git" "github" "owner/repo"'
        )
        self.assertEqual(out, "https://github.com/owner/repo.wiki.git")

    def test_gitlab_ssh(self):
        rc, out, _ = run_bash_func(
            'build_wiki_url "git@gitlab.com:group/project.git" "gitlab" "group/project"'
        )
        self.assertEqual(out, "git@gitlab.com:group/project.wiki.git")

    def test_gitlab_https(self):
        rc, out, _ = run_bash_func(
            'build_wiki_url "https://gitlab.com/group/project.git" "gitlab" "group/project"'
        )
        self.assertEqual(out, "https://gitlab.com/group/project.wiki.git")

    def test_gitlab_selfhosted_https(self):
        rc, out, _ = run_bash_func(
            'build_wiki_url "https://gitlab.mycompany.com/team/repo.git" "gitlab" "team/repo"'
        )
        self.assertEqual(out, "https://gitlab.mycompany.com/team/repo.wiki.git")

    def test_unknown_returns_empty(self):
        rc, out, _ = run_bash_func(
            'build_wiki_url "git@bitbucket.org:owner/repo.git" "unknown" "owner/repo"'
        )
        self.assertEqual(out, "")


class TestEmitResult(unittest.TestCase):
    """Test emit_result() function and output parsing."""

    def test_basic_emit(self):
        rc, out, _ = run_bash_func(
            'emit_result "ACTION=pull" "STATUS=ok" "REPO=owner/repo"'
        )
        self.assertEqual(rc, 0)
        parsed = parse_sync_result(out)
        self.assertEqual(parsed["ACTION"], "pull")
        self.assertEqual(parsed["STATUS"], "ok")
        self.assertEqual(parsed["REPO"], "owner/repo")

    def test_emit_with_backend(self):
        rc, out, _ = run_bash_func(
            'emit_result "ACTION=pull" "STATUS=ok" "BACKEND=local"'
        )
        parsed = parse_sync_result(out)
        self.assertEqual(parsed["BACKEND"], "local")

    def test_emit_error(self):
        rc, out, _ = run_bash_func(
            'emit_result "ACTION=pull" "STATUS=error" "ERROR_REASON=clone_failed"'
        )
        parsed = parse_sync_result(out)
        self.assertEqual(parsed["STATUS"], "error")
        self.assertEqual(parsed["ERROR_REASON"], "clone_failed")

    def test_emit_skipped(self):
        rc, out, _ = run_bash_func(
            'emit_result "ACTION=pull" "STATUS=skipped" "SKIP_REASON=non_supported_provider"'
        )
        parsed = parse_sync_result(out)
        self.assertEqual(parsed["STATUS"], "skipped")
        self.assertEqual(parsed["SKIP_REASON"], "non_supported_provider")


class TestReadDagBackendConfig(unittest.TestCase):
    """Test read_dag_backend_config() function."""

    def _run_in_repo(self, tmpdir, func_call):
        """Run a bash function inside a temp git repo."""
        cmd = f'cd "{tmpdir}" && set +eu && source "{SCRIPT}" && set -eu && {func_call}'
        result = subprocess.run(
            ["bash", "-c", cmd], capture_output=True, text=True
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    def test_no_config_returns_auto(self):
        """No issue.yaml → returns 'auto'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", tmpdir], capture_output=True)
            rc, out, _ = self._run_in_repo(tmpdir, "read_dag_backend_config")
            self.assertEqual(out, "auto")

    def test_config_with_backend(self):
        """issue.yaml with dag.backend: local → returns 'local'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", tmpdir], capture_output=True)
            claude_dir = os.path.join(tmpdir, ".claude")
            os.makedirs(claude_dir)
            config = os.path.join(claude_dir, "issue.yaml")
            with open(config, "w") as f:
                f.write("tracker: github\ndag:\n  backend: local\n")
            rc, out, _ = self._run_in_repo(tmpdir, "read_dag_backend_config")
            self.assertEqual(out, "local")

    def test_config_with_gitlab_wiki(self):
        """issue.yaml with dag.backend: gitlab-wiki → returns 'gitlab-wiki'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", tmpdir], capture_output=True)
            claude_dir = os.path.join(tmpdir, ".claude")
            os.makedirs(claude_dir)
            config = os.path.join(claude_dir, "issue.yaml")
            with open(config, "w") as f:
                f.write("tracker: gitlab\ndag:\n  backend: gitlab-wiki\n")
            rc, out, _ = self._run_in_repo(tmpdir, "read_dag_backend_config")
            self.assertEqual(out, "gitlab-wiki")


class TestLocalFallback(unittest.TestCase):
    """Test local fallback behavior end-to-end."""

    def test_setup_local_fallback_creates_dag(self):
        """setup_local_fallback should create DAG file and UL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", tmpdir], capture_output=True)
            cmd = (
                f'cd "{tmpdir}" && '
                f'set +eu && source "{SCRIPT}" && set -eu && '
                f'setup_local_fallback "pull"'
            )
            result = subprocess.run(
                ["bash", "-c", cmd], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            parsed = parse_sync_result(result.stdout)
            self.assertEqual(parsed["STATUS"], "ok")
            self.assertEqual(parsed["BACKEND"], "local")
            self.assertIn("DAG_FILE", parsed)
            dag_file = parsed["DAG_FILE"]
            self.assertTrue(os.path.exists(dag_file), f"DAG file not created: {dag_file}")
            with open(dag_file) as f:
                dag = json.load(f)
            self.assertEqual(dag["version"], 1)

    def test_local_push_is_noop(self):
        """Push in local mode should output ok with local backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", tmpdir], capture_output=True)
            subprocess.run(
                ["git", "-C", tmpdir, "remote", "add", "origin",
                 "https://bitbucket.org/owner/repo.git"],
                capture_output=True
            )
            # First pull (creates local DAG)
            result_pull = subprocess.run(
                ["bash", "-c", f'cd "{tmpdir}" && bash "{SCRIPT}" pull'],
                capture_output=True, text=True
            )
            self.assertEqual(result_pull.returncode, 0, f"pull failed: {result_pull.stderr}")
            # Then push
            result_push = subprocess.run(
                ["bash", "-c", f'cd "{tmpdir}" && bash "{SCRIPT}" push "test message"'],
                capture_output=True, text=True
            )
            parsed = parse_sync_result(result_push.stdout)
            self.assertEqual(parsed.get("BACKEND"), "local")
            self.assertEqual(parsed.get("STATUS"), "ok")


class TestWikiActivationHint(unittest.TestCase):
    """Test wiki_activation_hint() function."""

    def test_github_hint(self):
        rc, out, _ = run_bash_func(
            'wiki_activation_hint "github" "owner/repo"'
        )
        self.assertIn("github.com", out)
        self.assertIn("Wiki", out)

    def test_gitlab_hint(self):
        rc, out, _ = run_bash_func(
            'wiki_activation_hint "gitlab" "group/project"'
        )
        self.assertIn("Wiki", out)
        self.assertIn("Settings", out)


class TestParseSyncResult(unittest.TestCase):
    """Test the Python parse_sync_result helper."""

    def test_parse_full_result(self):
        text = (
            "INFO: some message\n"
            "DAG_SYNC_RESULT_BEGIN\n"
            "ACTION=pull\n"
            "STATUS=ok\n"
            "REPO=owner/repo\n"
            "DAG_FILE=/tmp/test/issue-dag.json\n"
            "BACKEND=github-wiki\n"
            "DAG_SYNC_RESULT_END\n"
        )
        parsed = parse_sync_result(text)
        self.assertEqual(parsed["ACTION"], "pull")
        self.assertEqual(parsed["STATUS"], "ok")
        self.assertEqual(parsed["REPO"], "owner/repo")
        self.assertEqual(parsed["BACKEND"], "github-wiki")

    def test_parse_error_result(self):
        text = (
            "DAG_SYNC_RESULT_BEGIN\n"
            "ACTION=pull\n"
            "STATUS=error\n"
            "ERROR_REASON=clone_failed\n"
            "HINT=Go to settings\n"
            "DAG_SYNC_RESULT_END\n"
        )
        parsed = parse_sync_result(text)
        self.assertEqual(parsed["STATUS"], "error")
        self.assertEqual(parsed["ERROR_REASON"], "clone_failed")


if __name__ == "__main__":
    unittest.main()
