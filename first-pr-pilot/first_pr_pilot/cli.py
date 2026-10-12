"""CLI entry point: first-pr-pilot plan --issue <url|file|-> [--repo PATH]"""
import argparse
import json
import os
import sys

from . import __version__, github, llm, workflow


def _read_issue(src):
    if src == "-":
        return sys.stdin.read()
    if os.path.isfile(src):
        with open(src, encoding="utf-8") as fh:
            return fh.read()
    if src.lower().startswith("http"):
        return src  # resolved (with friendly errors) by workflow.run
    raise SystemExit(f"error: --issue must be a GitHub issue URL, a file, or '-': {src}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="first-pr-pilot", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("plan", help="generate a contribution plan for an issue")
    s.add_argument("--issue", required=True, help="GitHub issue URL, text file, or '-' for stdin")
    s.add_argument("--repo", help="local clone or GitHub repo URL (grounds the plan in real files); "
                   "omitted + issue URL = auto-clone")
    s.add_argument("--no-clone", action="store_true", help="never auto-clone the issue's repo")
    s.add_argument("--model", default=None, help=f"Ollama model (default: {llm.DEFAULT_MODEL})")
    s.add_argument("--host", default=None, help="Ollama host (default: $OLLAMA_HOST or localhost:11434)")
    s.add_argument("--json", action="store_true", help="emit raw JSON instead of Markdown")
    s.add_argument("--out", help="write output to this file")
    d = sub.add_parser("doctor", help="check that Ollama and the model are ready (run before a demo)")
    d.add_argument("--model", default=None)
    d.add_argument("--host", default=None)
    w = sub.add_parser("serve", help="start the local web UI")
    w.add_argument("--port", type=int, default=8765)
    w.add_argument("--model", default=None)
    w.add_argument("--host", default=None, help="Ollama host")
    a = p.parse_args(argv)

    if a.cmd == "doctor":
        model = a.model or llm.DEFAULT_MODEL
        try:
            have = llm.list_models(a.host)
        except llm.ModelError as e:
            print(f"FAIL  {e}", file=sys.stderr)
            return 2
        print("ok    Ollama is reachable")
        if not llm.has_model(have, model):
            print(f"FAIL  model '{model}' not pulled. Run: ollama pull {model}", file=sys.stderr)
            print("      available: " + (", ".join(have) or "(none)"), file=sys.stderr)
            return 2
        print(f"ok    model '{model}' is available")
        return 0
    if a.cmd == "serve":
        from . import server
        server.run(port=a.port, model=a.model, host=a.host)
        return 0

    issue = _read_issue(a.issue)

    def stage(key, note=""):
        if note:
            print(f"... {note}", file=sys.stderr)

    try:
        res = workflow.run(issue, repo=a.repo, model=a.model, host=a.host,
                           auto_clone=not a.no_clone, on_stage=stage)
    except github.InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except (llm.ModelError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    plan, warnings = res["plan"], res["warnings"]
    text = json.dumps({"plan": plan, "warnings": warnings}, indent=2) if a.json \
        else res["markdown"]
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {a.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
