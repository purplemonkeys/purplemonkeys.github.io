#!/usr/bin/env python3
"""Assemble the En clair reader from shell.html + stories/*.json -> index.html

Add a story:  write stories/NN-id.json, then run `python3 build.py`.
Never hand-edit index.html: it is generated and will be overwritten.

Data is injected at a sentinel that must appear exactly once in shell.html,
which prevents story data leaking into comments (a real bug this guards).
"""
import json, glob, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHELL = os.path.join(HERE, "shell.html")
STORIES_DIR = os.path.join(HERE, "stories")
OUT = os.path.join(HERE, "index.html")
TOKEN = "/*STORIES_DATA_SENTINEL*/[]"

# Tokens that break Kobo's old WebKit (ES5 only). Checked against the script.
ES6_BANNED = ["=>", "const ", "let ", "`", "new Set", "new Map",
              "Object.assign", "includes(", "...", "async ", "await "]

def check_es5(shell_src):
    """Warn loudly if ES6 creeps into the shell script: Kobo runs ES5 only."""
    start = shell_src.find("<script>")
    end = shell_src.rfind("</script>")
    if start < 0 or end < 0:
        return []
    script = shell_src[start:end]
    # strip comments so prose like "let the page scroll" doesn't false-positive
    out, i, n = [], 0, len(script)
    while i < n:
        if script.startswith("//", i):
            j = script.find("\n", i); i = n if j < 0 else j
        elif script.startswith("/*", i):
            j = script.find("*/", i); i = n if j < 0 else j + 2
        else:
            out.append(script[i]); i += 1
    code = "".join(out)
    return [t for t in ES6_BANNED if t in code]

def main():
    files = sorted(glob.glob(os.path.join(STORIES_DIR, "*.json")))
    if not files:
        sys.exit("No stories found in stories/*.json")

    stories, ids = [], set()
    for f in files:
        name = os.path.basename(f)
        try:
            with open(f, encoding="utf-8") as fh:
                s = json.load(fh)
        except json.JSONDecodeError as e:
            sys.exit(f"Invalid JSON in {name}: {e}")
        for key in ("id", "title", "gist", "body"):
            if key not in s:
                sys.exit(f"{name} missing required field: {key}")
        if s["id"] in ids:
            sys.exit(f"Duplicate story id: {s['id']} ({name})")
        ids.add(s["id"])
        for pi, para in enumerate(s["body"]):
            for si, sent in enumerate(para):
                if "fr" not in sent or "bd" not in sent:
                    sys.exit(f"{name}: body[{pi}][{si}] needs both 'fr' and 'bd'")
                bd = sent["bd"]
                if "meaning" not in bd:
                    sys.exit(f"{name}: body[{pi}][{si}].bd missing 'meaning'")
        stories.append(s)

    shell = open(SHELL, encoding="utf-8").read()
    n = shell.count(TOKEN)
    if n != 1:
        sys.exit(f"Data sentinel must appear exactly once in shell.html, found {n}. Aborting.")

    bad = check_es5(shell)
    if bad:
        sys.exit("ES6 syntax found in shell.html script: " + ", ".join(repr(b) for b in bad) +
                 "\nKobo's browser runs ES5 only. Rewrite using var/function.")

    out = shell.replace(TOKEN, json.dumps(stories, ensure_ascii=False, separators=(",", ":")))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out)

    sents = sum(len(p) for s in stories for p in s["body"])
    print(f"Built {OUT}")
    print(f"  {len(stories)} stories, {sents} sentences, {len(out)//1024} KB")
    for i, s in enumerate(stories, 1):
        print(f"  {i}. {s['id']} ({s.get('level','A1')})")

if __name__ == "__main__":
    main()
