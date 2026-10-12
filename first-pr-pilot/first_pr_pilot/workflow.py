"""End-to-end workflow shared by the CLI and the web UI."""
import os

from . import github, plan as plan_mod, render
from .github import InputError


def resolve_issue(issue):
    """Return (issue_text, (owner, repo, num) | None). Raises InputError with a fix-it message."""
    text = (issue or "").strip()
    if not text:
        raise InputError("Paste a GitHub issue URL or the issue text first.")
    if "\n" not in text and text.lower().startswith("http"):
        ref = github.parse_issue_url(text)
        if ref:
            return github.fetch_issue(text), ref
        if github.parse_repo_url(text):
            raise InputError(
                "That is a repository link, not an issue. Open the issue you want to work on "
                "and paste its URL, e.g. https://github.com/OWNER/REPO/issues/123"
            )
        raise InputError("That link isn't a GitHub issue URL. Paste the issue text instead.")
    return text, None


def resolve_repo(repo, ref, auto_clone=True):
    repo = (repo or "").strip()
    if repo:
        parsed = github.parse_repo_url(repo)
        if parsed:
            return github.clone_repo(*parsed)
        if not os.path.isdir(repo):
            raise InputError(f"Repo folder not found: {repo}")
        return repo
    if ref and auto_clone:
        return github.clone_repo(ref[0], ref[1])
    return None


def run(issue, repo=None, model=None, host=None, auto_clone=True, on_stage=None, on_token=None):
    stage = on_stage or (lambda key, note="": None)
    stage("issue", "Reading the issue")
    text, ref = resolve_issue(issue)
    stage("repo", "Getting the code (first clone can take a minute)" if (ref or repo) else "No repo given; planning from the issue only")
    path = resolve_repo(repo, ref, auto_clone)
    plan, warnings = plan_mod.generate(text, repo_path=path, model=model, host=host,
                                       on_stage=stage, on_token=on_token)
    return {
        "plan": plan,
        "warnings": warnings,
        "repo_path": path,
        "issue_title": text.splitlines()[0].lstrip("# ").strip()[:200],
        "markdown": render.to_markdown(plan, warnings),
    }
