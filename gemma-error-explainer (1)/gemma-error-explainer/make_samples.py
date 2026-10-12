"""Generates the sample error screenshots and their seeded (offline) results.

Run once:  python make_samples.py
Writes samples/*.png and samples/seeded_results.json

The seeded results are pre-computed answers used ONLY by "Offline demo mode". The live path
always sends the screenshot to Gemma 4.
"""
import glob
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "samples"
OUT.mkdir(exist_ok=True)

WHITE, RED, GREEN, GREY, YELLOW = (220, 220, 220), (240, 90, 90), (120, 200, 120), (150, 150, 150), (230, 200, 90)


def load_font(size: int):
    candidates = glob.glob("/usr/share/fonts/**/DejaVuSansMono.ttf", recursive=True) + glob.glob(
        "/usr/share/fonts/**/*Mono*.ttf", recursive=True
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


FONT = load_font(20)


def shot(filename: str, title: str, lines: list[tuple[str, tuple]]):
    width = 1180
    height = 64 + 30 * len(lines) + 24
    img = Image.new("RGB", (width, height), (30, 30, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 38], fill=(52, 52, 52))
    d.text((16, 8), title, fill=(205, 205, 205), font=FONT)
    y = 56
    for text, color in lines:
        d.text((16, y), text, fill=color, font=FONT)
        y += 30
    img.save(OUT / filename)


SAMPLES = {
    "python_module_not_found": {
        "title": "Python traceback",
        "window": "Terminal - PowerShell",
        "lines": [
            ("PS C:\\Users\\sairam\\gemma-demo> python app.py", GREEN),
            ("Traceback (most recent call last):", WHITE),
            ('  File "C:\\Users\\sairam\\gemma-demo\\app.py", line 1, in <module>', WHITE),
            ("    import pandas as pd", WHITE),
            ("ModuleNotFoundError: No module named 'pandas'", RED),
        ],
        "result": {
            "tool_or_language": "Python in a Windows PowerShell terminal",
            "error_line": "ModuleNotFoundError: No module named 'pandas'",
            "error_summary": "Python can't find the pandas package, so app.py stops on its first import.",
            "likely_cause": "pandas isn't installed in the Python environment that ran app.py, or a different virtual environment is active.",
            "alternative_causes": ["pip installed pandas for a different Python version than the one running the script."],
            "severity": "blocking",
            "fix_steps": [
                "Check which Python is running with `python --version`.",
                "Activate the virtual environment you meant to use, if any.",
                "Install pandas with that same Python.",
                "Run `python app.py` again.",
            ],
            "commands": ["python -m pip install pandas", "python app.py"],
            "code_fix": "",
            "code_language": "text",
            "prevention_tips": [
                "Create one virtual environment per project and activate it before installing.",
                "Install with `python -m pip` so packages go to the interpreter you actually run.",
                "List dependencies in requirements.txt so a new machine can reinstall them in one command.",
            ],
            "if_still_stuck": "Run `python -m pip list` and confirm pandas appears in the list for this Python.",
            "confidence": "high",
        },
    },
    "js_type_error": {
        "title": "JavaScript TypeError",
        "window": "Console - Chrome DevTools",
        "lines": [
            ("Uncaught TypeError: Cannot read properties of undefined (reading 'map')", RED),
            ("    at UserList (UserList.jsx:12:23)", WHITE),
            ("    at renderWithHooks (react-dom.development.js:16305:18)", GREY),
            ("    at mountIndeterminateComponent (react-dom.development.js:20074:13)", GREY),
            ("    at beginWork (react-dom.development.js:21587:16)", GREY),
            ("The above error occurred in the <UserList> component:", YELLOW),
        ],
        "result": {
            "tool_or_language": "JavaScript (React) in the Chrome DevTools console",
            "error_line": "Uncaught TypeError: Cannot read properties of undefined (reading 'map')",
            "error_summary": "UserList calls .map() on a value that is undefined, which crashes the component.",
            "likely_cause": "At UserList.jsx line 12 the code maps over a value that has no data yet. The screenshot doesn't show which variable it is, but it is usually a prop or state that hasn't loaded or wasn't passed in.",
            "alternative_causes": ["The parent component isn't passing the prop under the name UserList expects."],
            "severity": "blocking",
            "fix_steps": [
                "Open UserList.jsx and go to line 12.",
                "Find the array being mapped and check where its value comes from.",
                "Give it a safe default so the first render doesn't crash.",
                "Confirm the parent passes the prop, or that the data fetch sets the state.",
            ],
            "commands": [],
            "code_fix": "// Replace yourArray with the value mapped on line 12\nconst items = (yourArray ?? []).map((item) => <li key={item.id}>{item.name}</li>);",
            "code_language": "jsx",
            "prevention_tips": [
                "Initialise array state with useState([]) rather than leaving it undefined.",
                "Show a loading state until fetched data exists.",
                "Add TypeScript types or PropTypes so a missing prop is caught early.",
            ],
            "if_still_stuck": "Add console.log on line 12 to print the value just before .map runs.",
            "confidence": "medium",
        },
    },
    "react_render_error": {
        "title": "React rendering error",
        "window": "Console - Chrome DevTools",
        "lines": [
            ("Error: Objects are not valid as a React child", RED),
            ("(found: object with keys {id, name, email}).", RED),
            ("If you meant to render a collection of children, use an array instead.", YELLOW),
            ("    at div", GREY),
            ("    at ProfileCard (ProfileCard.jsx:9:5)", WHITE),
            ("    at App (App.jsx:14:7)", GREY),
        ],
        "result": {
            "tool_or_language": "React in the browser console",
            "error_line": "Error: Objects are not valid as a React child (found: object with keys {id, name, email}).",
            "error_summary": "ProfileCard is trying to render a whole object as text, which React can't display.",
            "likely_cause": "Inside ProfileCard, near line 9, a JSX expression outputs an object with the keys id, name and email instead of a string or number.",
            "alternative_causes": ["A response object was passed to a component where plain text was expected."],
            "severity": "blocking",
            "fix_steps": [
                "Open ProfileCard.jsx and look near line 9 for a JSX expression that outputs the whole object.",
                "Render a specific field of the object instead.",
                "If you meant to show a list, map over it and return one element per item.",
            ],
            "commands": [],
            "code_fix": "// Render a field of the object, not the object itself\n<div>{profile.name}</div>",
            "code_language": "jsx",
            "prevention_tips": [
                "Put strings and numbers in JSX, not whole objects.",
                "Use JSON.stringify(value) only for temporary debugging output.",
                "Type your props with TypeScript so this is caught before the app runs.",
            ],
            "if_still_stuck": "Search ProfileCard.jsx for curly braces that contain a single variable and check what each one holds.",
            "confidence": "medium",
        },
    },
    "node_module_not_found": {
        "title": "Node.js module error",
        "window": "Terminal - bash",
        "lines": [
            ("$ node server.js", GREEN),
            ("node:internal/modules/cjs/loader:1228", GREY),
            ("  throw err;", GREY),
            ("  ^", GREY),
            ("", WHITE),
            ("Error: Cannot find module 'express'", RED),
            ("Require stack:", WHITE),
            ("- /home/sairam/api/server.js", WHITE),
            ("    at Module._resolveFilename (node:internal/modules/cjs/loader:1225:15) {", GREY),
            ("  code: 'MODULE_NOT_FOUND',", RED),
            ("  requireStack: [ '/home/sairam/api/server.js' ]", GREY),
            ("}", GREY),
        ],
        "result": {
            "tool_or_language": "Node.js in a bash terminal",
            "error_line": "Error: Cannot find module 'express'",
            "error_summary": "Node can't find the express package that server.js requires.",
            "likely_cause": "express isn't installed in the project's node_modules folder, or npm install was never run in /home/sairam/api.",
            "alternative_causes": ["express is installed in a different folder from the one you start node in."],
            "severity": "blocking",
            "fix_steps": [
                "Go to the project folder that contains package.json.",
                "Install the project's dependencies.",
                "If express still isn't found, add it explicitly.",
                "Run node server.js again.",
            ],
            "commands": ["cd /home/sairam/api", "npm install", "npm install express", "node server.js"],
            "code_fix": "",
            "code_language": "text",
            "prevention_tips": [
                "Run npm install after cloning a repository or pulling new changes.",
                "Keep every dependency listed in package.json so npm install can restore it.",
                "Don't commit node_modules; commit package-lock.json instead.",
            ],
            "if_still_stuck": "Run `npm ls express` to see whether npm can find the package from this folder.",
            "confidence": "high",
        },
    },
    "sql_syntax_error": {
        "title": "SQL database error",
        "window": "Terminal - mysql client",
        "lines": [
            ("mysql> SELECT name, email FROM users WHERE id = ;", GREEN),
            ("ERROR 1064 (42000): You have an error in your SQL syntax; check the manual", RED),
            ("that corresponds to your MySQL server version for the right syntax to use", RED),
            ("near '' at line 1", RED),
            ("mysql>", GREEN),
        ],
        "result": {
            "tool_or_language": "MySQL command-line client",
            "error_line": "ERROR 1064 (42000): You have an error in your SQL syntax",
            "error_summary": "MySQL can't run the query because the WHERE clause has no value after id =.",
            "likely_cause": "The condition `WHERE id = ;` is incomplete. A comparison needs a value on the right, so MySQL stops at the semicolon (near '' at line 1).",
            "alternative_causes": ["If an application built this query, the variable that should hold the id was empty."],
            "severity": "blocking",
            "fix_steps": [
                "Add the value you want to compare id with.",
                "Run the query again.",
                "If your code builds the query, find out why the id was empty.",
            ],
            "commands": [],
            "code_fix": "-- Replace 1 with the id you are looking for\nSELECT name, email FROM users WHERE id = 1;",
            "code_language": "sql",
            "prevention_tips": [
                "Use parameterised queries in application code instead of joining strings.",
                "Check that an id exists before running the query.",
                "Build long queries in small pieces so the failing clause is easy to spot.",
            ],
            "if_still_stuck": "Read the text after `near` in the error: MySQL points at where parsing stopped.",
            "confidence": "high",
        },
    },
    "api_unauthorized": {
        "title": "API authentication error",
        "window": "Terminal - bash",
        "lines": [
            ("$ curl -i https://api.example.com/v1/projects", GREEN),
            ("HTTP/2 401", RED),
            ("content-type: application/json", GREY),
            ('www-authenticate: Bearer realm="api"', YELLOW),
            ("", WHITE),
            ('{"error":"unauthorized","message":"Missing or invalid API key"}', RED),
        ],
        "result": {
            "tool_or_language": "HTTP API request with curl in bash",
            "error_line": 'HTTP/2 401 {"error":"unauthorized","message":"Missing or invalid API key"}',
            "error_summary": "The API rejected the request because no valid API key was sent.",
            "likely_cause": "The curl command sends no credentials, and the www-authenticate header shows the API expects a Bearer token.",
            "alternative_causes": ["A key was sent elsewhere but it is expired, revoked or for a different environment."],
            "severity": "blocking",
            "fix_steps": [
                "Get a valid API key or token from the API provider's dashboard.",
                "Keep it in an environment variable instead of typing it into commands.",
                "Send it in the Authorization header.",
                "Run the request again.",
            ],
            "commands": [
                'export API_KEY="your-key-here"',
                'curl -i -H "Authorization: Bearer $API_KEY" https://api.example.com/v1/projects',
            ],
            "code_fix": "",
            "code_language": "text",
            "prevention_tips": [
                "Keep keys in environment variables or a secrets manager, never in code or screenshots.",
                "Rotate any key that was pasted into a chat, a commit or a screenshot.",
                "Check the API docs for the exact header name before testing.",
            ],
            "if_still_stuck": "If you already send a key, regenerate it and check it belongs to the same environment as the URL.",
            "confidence": "high",
        },
    },
    "git_push_rejected": {
        "title": "Git push rejected",
        "window": "Terminal - bash",
        "lines": [
            ("$ git push origin main", GREEN),
            ("To https://github.com/sairam/my-project.git", WHITE),
            (" ! [rejected]        main -> main (fetch first)", RED),
            ("error: failed to push some refs to 'https://github.com/sairam/my-project.git'", RED),
            ("hint: Updates were rejected because the remote contains work that you do", YELLOW),
            ("hint: not have locally. Integrate the remote changes (e.g.", YELLOW),
            ("hint: 'git pull ...') before pushing again.", YELLOW),
        ],
        "result": {
            "tool_or_language": "Git in a bash terminal",
            "error_line": "! [rejected] main -> main (fetch first)",
            "error_summary": "GitHub refused your push because the remote main branch has commits you don't have locally.",
            "likely_cause": "Someone (or you, from another machine or the GitHub website) pushed to main after your last pull.",
            "alternative_causes": [],
            "severity": "blocking",
            "fix_steps": [
                "Pull the remote changes into your local main.",
                "Resolve any merge conflicts Git reports, then commit.",
                "Push again.",
            ],
            "commands": ["git pull origin main", "git push origin main"],
            "code_fix": "",
            "code_language": "text",
            "prevention_tips": [
                "Pull before you start work and before you push.",
                "Work on a feature branch and open a pull request instead of pushing to main.",
            ],
            "if_still_stuck": "Run `git status` to see whether a merge is half-finished, and `git log --oneline -5` to see what came in.",
            "confidence": "high",
        },
    },
    "python_indentation_error": {
        "title": "Python IndentationError",
        "window": "Terminal - VS Code",
        "lines": [
            ("PS C:\\Users\\sairam\\projects> python main.py", GREEN),
            ('  File "C:\\Users\\sairam\\projects\\main.py", line 6', WHITE),
            ('    print("Total:", total)', WHITE),
            ("    ^", RED),
            ("IndentationError: expected an indented block after 'for' statement on line 5", RED),
        ],
        "result": {
            "tool_or_language": "Python in a VS Code PowerShell terminal",
            "error_line": "IndentationError: expected an indented block after 'for' statement on line 5",
            "error_summary": "The line after the for loop on line 5 isn't indented, so Python doesn't know it belongs to the loop.",
            "likely_cause": "The body of the for loop (the print on line 6) is at the same indentation level as the for statement itself.",
            "alternative_causes": ["Tabs and spaces are mixed in main.py, so the indent isn't recognised."],
            "severity": "blocking",
            "fix_steps": [
                "Open main.py and go to line 6.",
                "Indent the line by 4 spaces so it sits inside the for loop.",
                "Use spaces only; in VS Code run 'Convert Indentation to Spaces' if unsure.",
                "Save and run again.",
            ],
            "commands": ["python main.py"],
            "code_fix": '    print("Total:", total)  # indented 4 spaces so it belongs to the loop',
            "code_language": "python",
            "prevention_tips": [
                "Let your editor handle indentation and keep it to 4 spaces.",
                "Turn on 'Render Whitespace' in VS Code to spot tabs mixed with spaces.",
            ],
            "if_still_stuck": "If the loop should do nothing for now, put `pass` on line 6 as a placeholder.",
            "confidence": "high",
        },
    },
}

# Remove screenshots from older versions that are no longer in the gallery
for old in OUT.glob("*.png"):
    if old.stem not in SAMPLES:
        old.unlink()

seeded = {}
for sample_id, spec in SAMPLES.items():
    shot(f"{sample_id}.png", spec["window"], spec["lines"])
    seeded[sample_id] = {"title": spec["title"], "result": spec["result"]}

(OUT / "seeded_results.json").write_text(json.dumps(seeded, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(SAMPLES)} screenshots + seeded_results.json to {OUT}")
