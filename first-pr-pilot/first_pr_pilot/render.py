"""Render a validated plan as Markdown."""


def _bullets(items, numbered=False):
    if not items:
        return "_none_"
    return "\n".join(f"{i}. {x}" if numbered else f"- {x}" for i, x in enumerate(items, 1))


def to_markdown(plan, warnings=()):
    files = "\n".join(f"- `{f['path']}` — {f['reason']}" for f in plan["files_to_inspect"]) or "_none_"
    out = [
        f"# Contribution plan\n\n{plan['summary']}\n",
        f"**Difficulty:** {plan['difficulty']}  |  **Estimate:** ~{plan['estimated_minutes']} min\n",
        "## Files to inspect\n" + files + "\n",
        "## Steps\n" + _bullets(plan["steps"], True) + "\n",
        "## Project conventions to follow\n" + _bullets(plan["conventions_to_follow"]) + "\n",
        "## Test plan\n" + _bullets(plan["test_plan"]) + "\n",
        "## Ask the maintainers\n" + _bullets(plan["questions_for_maintainers"]) + "\n",
        f"## Draft PR\n**Title:** {plan['pr_title']}\n\n{plan['pr_body']}\n",
    ]
    if warnings:
        out.append("## Warnings\n" + _bullets(list(warnings)) + "\n")
    return "\n".join(out)
