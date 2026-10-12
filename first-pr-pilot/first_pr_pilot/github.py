"""GitHub helpers (stdlib + git): parse links, fetch an issue, clone a repo."""
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request


class InputError(ValueError):
    """The person gave us something we can't use; the message says how to fix it."""


_ISSUE = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)/(?:issues|pull)/(\d+)")
_REPO = re.compile(r"^https?://(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?$")


def parse_issue_url(s):
    m = _ISSUE.search(s or "")
    return m.groups() if m else None


def parse_repo_url(s):
    m = _REPO.match((s or "").strip())
    return m.groups() if m else None


def is_issue_url(s):
    return parse_issue_url(s) is not None


def fetch_issue(url):
    ref = parse_issue_url(url)
    if not ref:
        raise InputError(f"Not a GitHub issue URL: {url}")
    owner, repo, num = ref
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "first-pr-pilot"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise InputError(f"Issue not found (or repo is private): {url}") from e
        if e.code in (403, 429):
            raise RuntimeError(
                "GitHub rate limit reached. Set GITHUB_TOKEN, or paste the issue text instead."
            ) from e
        raise RuntimeError(f"GitHub API error {e.code} for {url}") from e
    except OSError as e:
        raise RuntimeError(f"Could not reach GitHub: {e}") from e
    return f"# {d.get('title', '')}\n\n{d.get('body') or ''}"


def clone_repo(owner, repo, root=None):
    """Shallow-clone into a cache dir (reused on later runs). Returns the local path."""
    root = root or os.path.join(os.path.expanduser("~"), ".first_pr_pilot", "repos")
    dest = os.path.join(root, f"{owner}__{repo}")
    if os.path.isdir(os.path.join(dest, ".git")):
        return dest
    if not shutil.which("git"):
        raise InputError("git is not installed, so the repo can't be cloned. "
                         "Install git or enter the path of a local clone.")
    os.makedirs(root, exist_ok=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        r = subprocess.run(
            ["git", "clone", "--depth", "1", f"https://github.com/{owner}/{repo}.git", dest],
            capture_output=True, text=True, timeout=900, env=env,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Cloning took too long. Clone it yourself and enter the local path.") from e
    if r.returncode != 0:
        raise RuntimeError("git clone failed: " + (r.stderr.strip().splitlines() or ["unknown error"])[-1])
    return dest
