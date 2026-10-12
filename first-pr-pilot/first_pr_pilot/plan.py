"""Core workflow: ground -> prompt open-weight model -> validate/repair -> verify paths."""
import json

from . import llm, repo as repo_mod
from .schema import PLAN_SCHEMA, validate

SYSTEM = """You are a patient open-source mentor helping a first-time contributor.
Given an issue, the project's CONTRIBUTING guide and real code snippets from the repo, produce a
practical contribution plan as JSON matching the provided schema.
Rules:
- Only cite file paths that appear in the provided repo context. Never invent paths.
- Steps must be concrete, ordered and small enough for one sitting.
- conventions_to_follow must come from the CONTRIBUTING text (commit style, tests, lint, PR rules).
- If something is unclear, put it in questions_for_maintainers instead of guessing.
- pr_title/pr_body must be ready to paste; reference the issue."""


def build_prompt(issue, contributing, candidates, files):
    parts = ["## ISSUE\n" + issue.strip()[:6000]]
    parts.append("## CONTRIBUTING GUIDE\n" + (contributing.strip()[:6000] or "(none found)"))
    if candidates:
        snip = "\n\n".join(f"### {c['path']}\n{c['snippet']}" for c in candidates)
        parts.append("## RELEVANT CODE (ranked by keyword match)\n" + snip)
    if files:
        parts.append("## REPO FILES\n" + "\n".join(files))
    return "\n\n".join(parts)


def generate(issue, repo_path=None, contributing=None, model=None, host=None, retries=1,
             on_stage=None, on_token=None):
    """Return (plan_dict, warnings_list). Raises llm.ModelError on hard failure."""
    stage = on_stage or (lambda key, note="": None)
    stage("scan", "Scanning the repo for files that match the issue" if repo_path else "Skipping file scan (no repo)")
    candidates, files = [], []
    if repo_path:
        candidates = repo_mod.search(repo_path, repo_mod.keywords(issue))
        files = repo_mod.tree(repo_path)
        if contributing is None:
            contributing = repo_mod.find_contributing(repo_path)
    prompt = build_prompt(issue, contributing or "", candidates, files)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]

    plan, errs = None, ["no attempt made"]
    for attempt in range(retries + 1):
        stage("model", "Asking the local model" if attempt == 0 else "Model reply was invalid; asking it to fix it")
        raw = llm.chat(messages, model=model, host=host, schema=PLAN_SCHEMA, on_token=on_token)
        try:
            plan = json.loads(raw)
            errs = validate(plan)
        except json.JSONDecodeError as e:
            plan, errs = None, [f"invalid JSON: {e}"]
        if not errs:
            break
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "That reply was invalid: " + "; ".join(errs)
             + ". Return ONLY corrected JSON matching the schema."},
        ]
    if errs:
        raise llm.ModelError("Model output failed validation: " + "; ".join(errs))

    stage("verify", "Checking that every cited file exists")
    warnings = []
    if repo_path:
        known = set(repo_mod.tree(repo_path, limit=10_000))
        for f in plan["files_to_inspect"]:
            if f["path"] not in known:
                f["reason"] += " [unverified: path not found in repo]"
                warnings.append(f"Model cited a path not in the repo: {f['path']}")
    return plan, warnings
