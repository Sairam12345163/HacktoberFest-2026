import json
from pathlib import Path
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from first_pr_pilot import llm, plan as plan_mod, render, repo, schema

ROOT = os.path.dirname(os.path.dirname(__file__))
SAMPLE = os.path.join(ROOT, "examples", "sample_repo")
ISSUE = Path(ROOT, "examples", "sample_issue.md").read_text(encoding="utf-8")

GOOD = {
    "summary": "Transliterate accents before stripping.",
    "difficulty": "beginner",
    "estimated_minutes": 30,
    "files_to_inspect": [
        {"path": "src/slugify.py", "reason": "contains the regex"},
        {"path": "src/ghost.py", "reason": "made up"},
    ],
    "steps": ["Add unicodedata normalisation", "Add test"],
    "conventions_to_follow": ["Conventional Commits", "Regression test"],
    "test_plan": ["slugify('Café Münster') == 'cafe-munster'"],
    "questions_for_maintainers": [],
    "pr_title": "fix: transliterate accents in slugify",
    "pr_body": "Fixes #1",
}


def make_server(responses):
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            content = responses[min(len(seen) - 1, len(responses) - 1)]
            out = json.dumps({"message": {"content": content}}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen, f"http://127.0.0.1:{srv.server_port}"


class RepoTests(unittest.TestCase):
    def test_contributing_found(self):
        self.assertIn("Conventional Commits", repo.find_contributing(SAMPLE))

    def test_search_ranks_relevant_file_first(self):
        res = repo.search(SAMPLE, repo.keywords(ISSUE))
        self.assertEqual(res[0]["path"], "src/slugify.py")
        self.assertIn("re.sub", res[0]["snippet"])


class SchemaTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(schema.validate(GOOD), [])

    def test_invalid(self):
        bad = dict(GOOD, difficulty="impossible")
        self.assertTrue(schema.validate(bad))
        self.assertTrue(schema.validate({"summary": "x"}))


class PlanTests(unittest.TestCase):
    def test_happy_path_flags_hallucinated_path(self):
        srv, seen, host = make_server([json.dumps(GOOD)])
        plan, warns = plan_mod.generate(ISSUE, repo_path=SAMPLE, host=host)
        srv.shutdown(); srv.server_close()
        self.assertEqual(len(warns), 1)
        self.assertIn("ghost.py", warns[0])
        self.assertIn("format", seen[0])  # schema-constrained decoding requested
        self.assertIn("Conventional Commits", seen[0]["messages"][1]["content"])
        md = render.to_markdown(plan, warns)
        self.assertIn("## Warnings", md)

    def test_repairs_invalid_first_reply(self):
        srv, seen, host = make_server(["not json", json.dumps(GOOD)])
        plan, _ = plan_mod.generate(ISSUE, repo_path=SAMPLE, host=host)
        srv.shutdown(); srv.server_close()
        self.assertEqual(len(seen), 2)
        self.assertEqual(plan["difficulty"], "beginner")

    def test_gives_up_after_retries(self):
        srv, _, host = make_server(["nope"])
        with self.assertRaises(llm.ModelError):
            plan_mod.generate(ISSUE, repo_path=SAMPLE, host=host)
        srv.shutdown(); srv.server_close()

    def test_unreachable_model(self):
        with self.assertRaises(llm.ModelError):
            llm.chat([{"role": "user", "content": "hi"}], host="http://127.0.0.1:9", timeout=2)


class DoctorAndServerTests(unittest.TestCase):
    def _tags_server(self, names):
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                out = json.dumps({"models": [{"name": n} for n in names]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, f"http://127.0.0.1:{srv.server_port}"

    def test_doctor(self):
        from first_pr_pilot import cli
        srv, host = self._tags_server(["qwen2.5-coder:7b"])
        self.assertEqual(cli.main(["doctor", "--host", host]), 0)
        self.assertEqual(cli.main(["doctor", "--host", host, "--model", "missing"]), 2)
        srv.shutdown(); srv.server_close()

    def test_web_api_job_flow(self):
        import time
        import urllib.request
        from first_pr_pilot import server
        fake, _, ohost = make_server([json.dumps(GOOD)])
        ui = HTTPServer(("127.0.0.1", 0), server.make_handler(ollama_host=ohost))
        threading.Thread(target=ui.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{ui.server_port}"
        with urllib.request.urlopen(base + "/") as r:
            self.assertIn("Plan my first PR", r.read().decode())
        req = urllib.request.Request(base + "/api/plan", method="POST",
                                     data=json.dumps({"issue": ISSUE, "repo": SAMPLE}).encode())
        with urllib.request.urlopen(req) as r:
            job_id = json.loads(r.read())["job_id"]
        d = {}
        for _ in range(50):
            with urllib.request.urlopen(f"{base}/api/job/{job_id}") as r:
                d = json.loads(r.read())
            if d["status"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(d["status"], "done")
        self.assertEqual(d["plan"]["difficulty"], "beginner")
        self.assertEqual(len(d["warnings"]), 1)
        self.assertTrue(all(s["state"] == "done" for s in d["stages"]))
        for x in (fake, ui):
            x.shutdown(); x.server_close()

    def test_web_repo_url_gives_friendly_input_error(self):
        import time
        import urllib.request
        from first_pr_pilot import server
        ui = HTTPServer(("127.0.0.1", 0), server.make_handler())
        threading.Thread(target=ui.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{ui.server_port}"
        req = urllib.request.Request(base + "/api/plan", method="POST", data=json.dumps(
            {"issue": "https://github.com/spotdl/spotify-downloader"}).encode())
        with urllib.request.urlopen(req) as r:
            job_id = json.loads(r.read())["job_id"]
        for _ in range(50):
            with urllib.request.urlopen(f"{base}/api/job/{job_id}") as r:
                d = json.loads(r.read())
            if d["status"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(d["status"], "error")
        self.assertEqual(d["kind"], "input")
        self.assertIn("repository link", d["error"])
        ui.shutdown(); ui.server_close()


class WorkflowTests(unittest.TestCase):
    def test_link_parsing(self):
        from first_pr_pilot import github
        self.assertEqual(github.parse_issue_url("https://github.com/a/b/issues/7"), ("a", "b", "7"))
        self.assertEqual(github.parse_repo_url("https://github.com/a/b/"), ("a", "b"))
        self.assertIsNone(github.parse_repo_url("https://github.com/a/b/issues/7"))

    def test_repo_url_as_issue_rejected(self):
        from first_pr_pilot import workflow
        from first_pr_pilot.github import InputError
        with self.assertRaises(InputError):
            workflow.resolve_issue("https://github.com/spotdl/spotify-downloader")
        with self.assertRaises(InputError):
            workflow.resolve_issue("   ")

    def test_missing_repo_folder(self):
        from first_pr_pilot import workflow
        from first_pr_pilot.github import InputError
        with self.assertRaises(InputError):
            workflow.resolve_repo("/definitely/not/here", None)

    def test_streaming_chunks(self):
        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"message":{"content":"ab"},"done":false}\n'
                                 b'{"message":{"content":"cd"},"done":true}\n')

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        seen = []
        out = llm.chat([{"role": "user", "content": "x"}], host=f"http://127.0.0.1:{srv.server_port}",
                       on_token=seen.append)
        srv.shutdown(); srv.server_close()
        self.assertEqual(out, "abcd")
        self.assertEqual(seen, [1, 2])

    def test_cli_end_to_end(self):
        import tempfile
        from first_pr_pilot import cli
        srv, _, host = make_server([json.dumps(GOOD)])
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "plan.json")
            rc = cli.main(["plan", "--issue", os.path.join(ROOT, "examples", "sample_issue.md"),
                           "--repo", SAMPLE, "--host", host, "--json", "--out", out])
            data = json.loads(Path(out).read_text(encoding="utf-8"))
        srv.shutdown(); srv.server_close()
        self.assertEqual(rc, 0)
        self.assertEqual(data["plan"]["pr_title"], GOOD["pr_title"])


class SkillComplianceTests(unittest.TestCase):
    """Agent Skills open standard: dir name == name; name/description/compat constraints."""

    def test_skill_frontmatter(self):
        import re
        d = os.path.join(ROOT, "skills", "first-pr-plan")
        text = Path(d, "SKILL.md").read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(m, "SKILL.md must start with YAML frontmatter")
        fm = {}
        for line in m.group(1).splitlines():
            if re.match(r"^[A-Za-z-]+:", line):
                k, v = line.split(":", 1)
                fm[k] = v.strip()
        name = fm["name"]
        self.assertEqual(name, os.path.basename(d))
        self.assertTrue(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64)
        self.assertTrue(0 < len(fm["description"]) <= 1024)
        self.assertTrue(len(fm.get("compatibility", "")) <= 500)
        self.assertTrue(os.path.isfile(os.path.join(d, "scripts", "first_pr_plan.py")))


if __name__ == "__main__":
    unittest.main()
