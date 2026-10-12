"""Local web UI (stdlib only). Binds to 127.0.0.1; plans run as background jobs with live progress."""
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import github, llm, workflow

UI_FILE = Path(__file__).with_name("ui.html")
ROOT = Path(__file__).resolve().parent.parent
STAGES = [
    ("issue", "Read the issue"),
    ("repo", "Get the code"),
    ("scan", "Find relevant files"),
    ("model", "Ask the local model"),
    ("verify", "Check the plan"),
]


class Job:
    def __init__(self):
        self.id = uuid.uuid4().hex[:12]
        self.start = time.time()
        self.status = "running"
        self.states = {k: "pending" for k, _ in STAGES}
        self.notes = {}
        self.tokens = 0
        self.active = None
        self.result = None
        self.error = None
        self.kind = None

    def stage(self, key, note=""):
        if self.active and self.active != key:
            self.states[self.active] = "done"
        self.active = key
        self.states[key] = "active"
        if note:
            self.notes[key] = note

    def fail(self, kind, msg):
        if self.active:
            self.states[self.active] = "failed"
        self.status, self.kind, self.error = "error", kind, msg

    def snapshot(self):
        d = {
            "id": self.id, "status": self.status, "elapsed": round(time.time() - self.start, 1),
            "tokens": self.tokens, "error": self.error, "kind": self.kind,
            "stages": [{"key": k, "label": l, "state": self.states[k], "note": self.notes.get(k, "")}
                       for k, l in STAGES],
        }
        if self.result:
            d.update(self.result)
        return d


def make_handler(model=None, ollama_host=None):
    jobs, lock = {}, threading.Lock()

    def work(job, issue, repo, mdl):
        try:
            res = workflow.run(
                issue, repo=repo, model=mdl or model, host=ollama_host,
                on_stage=job.stage, on_token=lambda n: setattr(job, "tokens", n),
            )
            for k in job.states:
                job.states[k] = "done"
            job.result, job.status = res, "done"
        except github.InputError as e:
            job.fail("input", str(e))
        except llm.ModelError as e:
            job.fail("model", str(e))
        except RuntimeError as e:
            job.fail("error", str(e))
        except Exception as e:  # never leave the page spinning
            job.fail("error", f"Unexpected error: {type(e).__name__}: {e}")

    class H(BaseHTTPRequestHandler):
        def _json(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                data = UI_FILE.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif self.path == "/api/health":
                want = model or llm.DEFAULT_MODEL
                out = {"model": want, "ok": False, "error": None, "sample": None}
                try:
                    have = llm.list_models(ollama_host)
                    out["ok"] = llm.has_model(have, want)
                    if not out["ok"]:
                        out["error"] = f"Model '{want}' is not downloaded. Run: ollama pull {want}"
                except llm.ModelError as e:
                    out["error"] = str(e)
                issue, repo = ROOT / "examples" / "sample_issue.md", ROOT / "examples" / "sample_repo"
                if issue.is_file() and repo.is_dir():
                    out["sample"] = {"issue": issue.read_text(encoding="utf-8"), "repo": str(repo)}
                self._json(200, out)
            elif self.path.startswith("/api/job/"):
                job = jobs.get(self.path.rsplit("/", 1)[1])
                self._json(200, job.snapshot()) if job else self._json(404, {"error": "unknown job"})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/plan":
                return self._json(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except (ValueError, TypeError):
                return self._json(400, {"error": "Bad request."})
            issue = (body.get("issue") or "").strip()
            if not issue:
                return self._json(400, {"error": "Paste a GitHub issue URL or the issue text first.", "kind": "input"})
            job = Job()
            with lock:
                if len(jobs) > 50:
                    jobs.pop(next(iter(jobs)))
                jobs[job.id] = job
            threading.Thread(target=work, daemon=True, args=(
                job, issue, (body.get("repo") or "").strip() or None, (body.get("model") or "").strip() or None,
            )).start()
            self._json(202, {"job_id": job.id})

        def log_message(self, *a):
            pass

    return H


def run(port=8765, model=None, host=None):
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(model, host))
    print(f"First PR Pilot UI: http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
