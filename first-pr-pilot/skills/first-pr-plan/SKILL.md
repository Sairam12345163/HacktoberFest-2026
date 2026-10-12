---
name: first-pr-plan
description: Turns a GitHub issue plus a local repository's CONTRIBUTING guide into a grounded, step-by-step contribution plan (files to inspect, conventions, tests, draft PR) using a local open-weight model via Ollama. Use when a user wants help starting work on an open-source issue or preparing a first pull request.
license: MIT
compatibility: Requires Python 3.9+ and a running Ollama server with an open-weight model pulled (default qwen2.5-coder:7b). No network needed except for fetching issue URLs.
metadata:
  author: first-pr-pilot
  version: "0.1.0"
---

# First PR Plan

Use this skill when the user wants to start contributing to an open-source issue.

## Inputs
- An issue: a GitHub issue URL, a path to a text/markdown file, or pasted text (save to a temp file).
- Optionally, a local clone of the project (strongly recommended: it grounds the plan in real files).

## Steps
1. Confirm Ollama is running (`ollama list`). If not, tell the user to run `ollama serve` and `ollama pull qwen2.5-coder:7b`.
2. Run the bundled script:
   ```bash
   python scripts/first_pr_plan.py --issue <URL|FILE> --repo <PATH_TO_CLONE>
   ```
   Add `--model <name>` to use another Ollama model, or `--json` for machine-readable output.
3. Present the Markdown plan to the user. Highlight anything under **Warnings**: those are file paths the model cited that don't exist in the repo, so don't rely on them.
4. Offer to start on step 1 of the plan, and to open the files listed under **Files to inspect**.

## Notes
- The plan is a starting point, not authoritative. Verify against CONTRIBUTING.md before opening a PR.
- If the script exits with code 2, the message on stderr explains the model problem (not running / not pulled / invalid output).
