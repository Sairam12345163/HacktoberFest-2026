"""Local repo grounding: find CONTRIBUTING docs and keyword-relevant code snippets.

This is what keeps the model honest: it only sees (and may only cite) real files.
"""
import os
import re

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".next"}
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".c", ".h",
            ".cpp", ".cs", ".php", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".sh"}
STOPWORDS = set("""the a an and or but if then else when where which who what why how this that these those is are
was were be been being to of in on at for from by with without as it its into than so not no can could should
would will just also have has had do does did i we you they he she them our your my me us there here about
over under up down out off again once only own same too very s t don now bug issue error please fix add
support feature expected actual steps reproduce version using use""".split())
MAX_FILE_BYTES = 200_000


def find_contributing(repo):
    """Return text of the first CONTRIBUTING file found (root, .github, docs)."""
    for sub in ("", ".github", "docs"):
        d = os.path.join(repo, sub)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if name.lower().startswith("contributing"):
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        return fh.read()
    return ""


def keywords(text, limit=20):
    """Cheap keyword extraction: frequent non-stopword tokens, identifiers favoured."""
    toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text)
    counts = {}
    for t in toks:
        low = t.lower()
        if low in STOPWORDS:
            continue
        w = 2 if ("_" in t or (t != t.lower() and t != t.capitalize())) else 1
        counts[low] = counts.get(low, 0) + w
    return [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]


MAX_FILES = 20_000


def iter_files(repo):
    seen = 0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in TEXT_EXT:
                p = os.path.join(root, f)
                try:
                    if os.path.getsize(p) <= MAX_FILE_BYTES:
                        seen += 1
                        if seen > MAX_FILES:
                            return
                        yield p
                except OSError:
                    continue


def search(repo, kws, max_files=5, context=2):
    """Rank files by keyword hits; return [{path, score, snippet}]."""
    results = []
    for p in iter_files(repo):
        rel = os.path.relpath(p, repo).replace(os.sep, "/")
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        score, hit_lines = 0, []
        for i, line in enumerate(lines):
            low = line.lower()
            n = sum(1 for k in kws if k in low)
            if n:
                score += n
                hit_lines.append((n, i))
        score += sum(2 for k in kws if k in rel.lower())  # path matches matter
        if re.search(r"(^|/)(tests?|spec|__tests__)/|test_|_test\.|\.md$", rel):
            score = score * 0.5  # prefer implementation files over tests/docs
        if score == 0:
            continue
        hit_lines.sort(key=lambda x: (-x[0], x[1]))
        snippet = ""
        if hit_lines and len(lines) <= 40:  # small file: give the model all of it
            snippet = "\n".join(f"{n + 1}: {l}" for n, l in enumerate(lines))
        elif hit_lines:
            keep = set()
            for _, i in hit_lines[:3]:
                keep.update(range(max(0, i - context), min(len(lines), i + context + 1)))
            rows, prev = [], None
            for n in sorted(keep):
                if prev is not None and n != prev + 1:
                    rows.append("...")
                rows.append(f"{n + 1}: {lines[n]}")
                prev = n
            snippet = "\n".join(rows)
        results.append({"path": rel, "score": score, "snippet": snippet})
    results.sort(key=lambda r: (-r["score"], r["path"]))
    return results[:max_files]


def tree(repo, limit=60):
    """Flat list of relative file paths (for 'does this path exist' checks and context)."""
    out = [os.path.relpath(p, repo).replace(os.sep, "/") for p in iter_files(repo)]
    return sorted(out)[:limit]
