# First PR Pilot

> Open-weight AI that turns a GitHub issue into a plan you can actually start on.

Starting your first open-source contribution is hard: *which files matter? what does CONTRIBUTING.md
require? what should the PR say?* **First PR Pilot** answers that locally, using an open-weight model
served by [Ollama](https://ollama.com). Nothing leaves your machine except an optional issue fetch.

Built for **Hacktoberfest Hack Day Hyderabad (MLH × NIAT-KKH): Best Open-Source AI Project**.

## Why the AI matters

The open-weight model is the engine, not decoration:

```
issue + CONTRIBUTING.md ──► keyword-ranked code snippets from your clone (repo.py)
                                  │
                                  ▼
                  open-weight LLM (Ollama, JSON-schema constrained output)
                                  │
                                  ▼
          validate → auto-repair retry → verify cited paths exist (plan.py)
                                  │
                                  ▼
     Markdown plan: files to inspect · steps · conventions · tests · draft PR
```

Product logic around the model:
- **Grounding**: only real repo snippets and the project's own CONTRIBUTING text go into the prompt.
- **Structured output**: Ollama's `format` JSON schema constrains decoding; a validator + one repair retry handles misses.
- **Hallucination check**: any file path the model cites that doesn't exist in the repo is flagged in **Warnings**.
- **Clear failures**: Ollama down / model not pulled / invalid output each give an actionable message.

It ships in three forms: a **CLI**, a **local web UI**, and an **Agent Skill** (`skills/first-pr-plan/`, Agent Skills open standard).

## Quickstart

```bash
ollama pull qwen2.5-coder:7b      # Apache-2.0 open weights; any Ollama chat model works
git clone <this repo> && cd first-pr-pilot
python -m first_pr_pilot plan \
  --issue examples/sample_issue.md \
  --repo  examples/sample_repo
```

Real issue + real clone:

```bash
python -m first_pr_pilot plan \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --repo  ~/code/REPO --out plan.md
```

Options: `--model NAME`, `--host URL` (or `OLLAMA_HOST`), `--json`, `--out FILE`, `--no-clone`; `--repo` accepts a local folder or a GitHub repo URL, and is auto-cloned from the issue URL when omitted; set `GITHUB_TOKEN` for rate limits.
No dependencies beyond the Python 3.9+ standard library. `pip install .` adds a `first-pr-pilot` command.

## Pre-flight check and web UI

```bash
python -m first_pr_pilot doctor      # verifies Ollama is up and the model is pulled
python -m first_pr_pilot serve       # UI at http://127.0.0.1:8765 (localhost only)
```

In the UI, paste a **GitHub issue URL** (`https://github.com/OWNER/REPO/issues/123`) and click
**Plan my first PR**. The repo is cloned automatically (shallow, cached in `~/.first_pr_pilot/repos`;
needs `git`). You see live progress while the local model works. Pasting a plain repo link
(without `/issues/N`) is caught with a clear message.

## Use as an Agent Skill

Copy `skills/first-pr-plan/` into your agent's skills directory (e.g. `.claude/skills/`).
Ask: *"Help me start on https://github.com/OWNER/REPO/issues/123, my clone is at ~/code/REPO"*.
The agent reads `SKILL.md`, runs the script, and presents the plan.

## Tests

```bash
python -m unittest discover -s tests -v
```
Tests use a fake Ollama server, so no model is needed to verify grounding, validation, repair and path-checking.

## Challenge requirements checklist

| Requirement | Where |
|---|---|
| Open-weight AI is central | Ollama model generates the plan: `first_pr_pilot/llm.py`, `plan.py` |
| Original implementation | All code in this repo, written for this challenge, no dependencies |
| Agent skill complies with Agent Skills standard | `skills/first-pr-plan/SKILL.md` + automated check in `tests/test_all.py` |
| Open-source license | MIT, `LICENSE` |
| Public GitHub repo | Push to a public repo (see submission steps) |
| README + 2-minute demo | This file |

## 120-minute build plan mapping

| Time | Milestone | Delivered |
|---|---|---|
| 00–15 | Choose path | Model-powered tool + agent skill; one user story: "start my first PR on this issue" |
| 15–30 | Bootstrap | Repo, MIT license, Ollama client, sample issue + sample repo |
| 30–80 | Build core | Grounding → model → plan, end to end |
| 80–105 | Make it useful | JSON schema, validation + repair retry, path check, `doctor`, web UI, clear errors |
| 105–120 | Ship + demo | README, tests, CI, submission file, demo script |

## 2-minute demo script

0. Run `python -m first_pr_pilot doctor` (proves the local model is ready).
1. Show the public repo + MIT `LICENSE`.
2. Show `examples/sample_issue.md` (accent-stripping bug) and `examples/sample_repo/CONTRIBUTING.md`.
3. Run the quickstart command live; point out the plan cites `src/slugify.py`, the Conventional Commits rule and the regression-test requirement, all from the repo.
4. Show the **Warnings** section / `tests/test_all.py::test_happy_path_flags_hallucinated_path` to explain the hallucination guard.
5. Show the web UI (`serve`) and invoke the skill from an agent to show the same result.

## License

MIT, see [LICENSE](LICENSE).
# HacktoberFest-2026
