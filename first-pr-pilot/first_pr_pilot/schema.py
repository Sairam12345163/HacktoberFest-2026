"""JSON schema for the plan + a small hand-rolled validator (no dependencies)."""

DIFFICULTIES = ("beginner", "intermediate", "advanced")

_STR_LIST = {"type": "array", "items": {"type": "string"}}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "difficulty": {"type": "string", "enum": list(DIFFICULTIES)},
        "estimated_minutes": {"type": "integer"},
        "files_to_inspect": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["path", "reason"],
            },
        },
        "steps": _STR_LIST,
        "conventions_to_follow": _STR_LIST,
        "test_plan": _STR_LIST,
        "questions_for_maintainers": _STR_LIST,
        "pr_title": {"type": "string"},
        "pr_body": {"type": "string"},
    },
    "required": [
        "summary", "difficulty", "estimated_minutes", "files_to_inspect", "steps",
        "conventions_to_follow", "test_plan", "questions_for_maintainers",
        "pr_title", "pr_body",
    ],
}


def validate(obj):
    """Return a list of human-readable problems (empty list == valid)."""
    errs = []
    if not isinstance(obj, dict):
        return ["top-level value must be a JSON object"]
    for key in PLAN_SCHEMA["required"]:
        if key not in obj:
            errs.append(f"missing key: {key}")
    if errs:
        return errs
    for key in ("summary", "pr_title", "pr_body"):
        if not isinstance(obj[key], str) or not obj[key].strip():
            errs.append(f"{key} must be a non-empty string")
    if obj["difficulty"] not in DIFFICULTIES:
        errs.append(f"difficulty must be one of {DIFFICULTIES}")
    if not isinstance(obj["estimated_minutes"], int) or obj["estimated_minutes"] <= 0:
        errs.append("estimated_minutes must be a positive integer")
    for key in ("steps", "conventions_to_follow", "test_plan", "questions_for_maintainers"):
        v = obj[key]
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            errs.append(f"{key} must be a list of strings")
    if not obj["steps"] if isinstance(obj["steps"], list) else False:
        errs.append("steps must not be empty")
    f = obj["files_to_inspect"]
    if not isinstance(f, list) or not all(
        isinstance(x, dict) and isinstance(x.get("path"), str) and isinstance(x.get("reason"), str)
        for x in f
    ):
        errs.append("files_to_inspect must be a list of {path, reason}")
    return errs
