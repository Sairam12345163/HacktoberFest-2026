# Submission: First PR Pilot — YOUR NAME

> Fill using the repo's `SUBMISSION_TEMPLATE.md` headings; this is a pre-filled draft of the content.

## Project
- **Name:** First PR Pilot
- **Challenge:** Best Open-Source AI Project
- **One-liner:** Local open-weight AI that turns a GitHub issue + CONTRIBUTING guide into a grounded contribution plan and draft PR.
- **Project repository (public):** https://github.com/YOUR_USERNAME/first-pr-pilot
- **License:** MIT

## Challenge evidence
- **Open-source / open-weight AI component:** Ollama-served open-weight model (default `qwen2.5-coder:7b`, Apache-2.0) with JSON-schema-constrained output, called from `first_pr_pilot/llm.py` and orchestrated in `plan.py`.
- **Why it matters:** The model produces the plan; grounding, validation/repair and a hallucinated-path check are built around it.
- **Type:** Model-powered tool (CLI + local web UI) + Agent Skill (`skills/first-pr-plan/SKILL.md`, Agent Skills open standard)

## Demo instructions
```bash
ollama pull qwen2.5-coder:7b
git clone https://github.com/YOUR_USERNAME/first-pr-pilot && cd first-pr-pilot
python -m first_pr_pilot plan --issue examples/sample_issue.md --repo examples/sample_repo
python -m first_pr_pilot doctor
python -m first_pr_pilot serve   # optional web UI
python -m unittest discover -s tests -v
```

## Team
- YOUR NAME
