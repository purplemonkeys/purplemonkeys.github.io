#!/usr/bin/env python3
"""Assemble both readers.

  En Clair    : shell.html    + stories/*.json            -> index.html
  En Clair 中文: shell-zh.html + articles-zh/NN-id.{txt,auto.json,notes.json} -> zh.html

Add a French story:  write stories/NN-id.json, then run `python3 build.py`.
Add a Chinese article: run tools/zh_prepare.py on Jack's file, write the
notes.json, then run `python3 build.py`. See CLAUDE.md for both workflows.
Never hand-edit index.html or zh.html: they are generated and overwritten.

Data is injected at a sentinel that must appear exactly once in each shell,
which prevents data leaking into comments (a real bug this guards).
Standard library only.
"""
import glob, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- French (En Clair) ----------------
SHELL = os.path.join(HERE, "shell.html")
STORIES_DIR = os.path.join(HERE, "stories")
OUT = os.path.join(HERE, "index.html")
TOKEN = "/*STORIES_DATA_SENTINEL*/[]"

# ---------------- Chinese (En Clair 中文) ----------------
ZH_SHELL = os.path.join(HERE, "shell-zh.html")
ZH_DIR = os.path.join(HERE, "articles-zh")
ZH_OUT = os.path.join(HERE, "zh.html")
ZH_TOKEN = "/*ARTICLES_DATA_SENTINEL*/[]"
ENDS, CLOSERS = "。；！？", "”’」』）)"
NEWS_SHARE_WARN = 1 / 3   # soft guide, not a cap: warn above this share of a news article's sentences

# Tokens that break Kobo's old WebKit (ES5 only). Checked against each shell's script.
ES6_BANNED = ["=>", "const ", "let ", "`", "new Set", "new Map",
              "Object.assign", ".includes(", "...", "async ", "await "]


def check_es5(shell_src):
    """Warn loudly if ES6 creeps into the shell script: Kobo runs ES5 only."""
    start = shell_src.find("<script>")
    end = shell_src.rfind("</script>")
    if start < 0 or end < 0:
        return []
    script = shell_src[start:end]
    out, i, n = [], 0, len(script)
    while i < n:                              # strip comments so prose is exempt
        if script.startswith("//", i):
            j = script.find("\n", i); i = n if j < 0 else j
        elif script.startswith("/*", i):
            j = script.find("*/", i); i = n if j < 0 else j + 2
        else:
            out.append(script[i]); i += 1
    code = "".join(out)
    return [t for t in ES6_BANNED if t in code]


def inject(shell_path, token, data, out_path):
    name = os.path.basename(shell_path)
    shell = open(shell_path, encoding="utf-8").read()
    n = shell.count(token)
    if n != 1:
        sys.exit(f"Data sentinel must appear exactly once in {name}, found {n}. Aborting.")
    bad = check_es5(shell)
    if bad:
        sys.exit(f"ES6 syntax found in {name} script: " + ", ".join(repr(b) for b in bad) +
                 "\nKobo's browser runs ES5 only. Rewrite using var/function.")
    out = shell.replace(token, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    return out


def build_fr():
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
                if "meaning" not in sent["bd"]:
                    sys.exit(f"{name}: body[{pi}][{si}].bd missing 'meaning'")
        stories.append(s)

    out = inject(SHELL, TOKEN, stories, OUT)
    sents = sum(len(p) for s in stories for p in s["body"])
    print(f"Built {OUT}")
    print(f"  {len(stories)} stories, {sents} sentences, {len(out)//1024} KB")
    for i, s in enumerate(stories, 1):
        print(f"  {i}. {s['id']} ({s.get('level','A1')})")


# ---------------- Chinese helpers ----------------
def zh_fail(msg):
    sys.exit("Chinese build failed: " + msg)


def split_sentences(par):
    """Must match tools/zh_prepare.py exactly (the alignment check depends on it)."""
    out, buf, i = [], "", 0
    while i < len(par):
        buf += par[i]
        if par[i] in ENDS:
            while i + 1 < len(par) and par[i + 1] in CLOSERS:
                i += 1; buf += par[i]
            out.append(buf); buf = ""
        i += 1
    if buf:
        out.append(buf)
    return out


def chunk_text(ref, words, base, n, kind):
    """A breakdown chunk's Chinese side. Preferred: word positions in the sentence,
    [from, to] (inclusive, 0-based, punctuation counts), or a list of ranges shown
    joined with '……'. The page then shows the article's own words, so notes never
    retype article text. Typed Chinese strings are accepted only for non-news."""
    if isinstance(ref, str):
        if kind == "news":
            zh_fail(f"{base}: S{n} chunk '{ref}' is typed text. News chunks must use word positions [from, to].")
        return ref
    ranges = ref if ref and isinstance(ref[0], list) else [ref]
    parts = []
    for r in ranges:
        if len(r) != 2 or not (0 <= r[0] <= r[1] < len(words)):
            zh_fail(f"{base}: S{n} chunk range {r} is outside the sentence (0–{len(words) - 1})")
        parts.append(html.escape("".join(words[r[0]:r[1] + 1]).strip("，、；：。 ")))
    return "……".join(parts)


def build_zh():
    txts = sorted(glob.glob(os.path.join(ZH_DIR, "*.txt")))
    if not txts:
        print("No Chinese articles in articles-zh/ (skipping zh.html)")
        return
    arts, ids = [], set()
    for txt in txts:
        stem = txt[:-4]
        base = os.path.basename(stem)
        m = re.match(r"^(\d+)-(.+)$", base)
        if not m:
            zh_fail(f"{base}: file name must be NN-id")
        num, fid = int(m.group(1)), m.group(2)
        try:
            auto = json.load(open(stem + ".auto.json", encoding="utf-8"))
            notes = json.load(open(stem + ".notes.json", encoding="utf-8"))
        except FileNotFoundError as e:
            zh_fail(f"{base}: missing {e.filename}. Run tools/zh_prepare.py, then write the notes.")
        except json.JSONDecodeError as e:
            zh_fail(f"{base}: invalid JSON: {e}")

        for k in ("id", "chip", "kicker", "kind", "register", "gist", "source"):
            if k not in notes:
                zh_fail(f"{base}.notes.json missing {k}")
        if notes["id"] != fid:
            zh_fail(f"{base}: notes id '{notes['id']}' must match file id '{fid}'")
        if notes["id"] in ids:
            zh_fail("duplicate article id " + notes["id"])
        ids.add(notes["id"])
        # attribution is always shown: source name required; link and date only if
        # Jack supplies them (the page then cites source + headline)
        if not notes["source"].get("name"):
            zh_fail(f"{base}: source.name is required (attribution is always shown)")

        # alignment: .txt -> sentences must equal auto.json, and words must join back up
        lines = [ln.strip() for ln in open(txt, encoding="utf-8").read().splitlines() if ln.strip()]
        expected = [split_sentences(ln) for ln in lines[1:]]
        got = [[s["text"] for s in p] for p in auto["paras"]]
        if lines[0] != auto["title"]["text"] or expected != got:
            zh_fail(f"{base}: .txt and .auto.json no longer match. Re-run tools/zh_prepare.py.")
        sent_by_n = {}
        for p in auto["paras"]:
            for s in p:
                if "".join(t[0] for t in s["tok"]) != s["text"]:
                    zh_fail(f"{base}: S{s['n']} words don't join back into the sentence")
                sent_by_n[s["n"]] = s
        if "".join(t[0] for t in auto["title"]["tok"]) != auto["title"]["text"]:
            zh_fail(f"{base}: title words don't join back into the title")

        # word notes: article-wide by word, or per sentence with "s"
        all_words = {t[0] for t in auto["title"]["tok"]} | {t[0] for s in sent_by_n.values() for t in s["tok"]}
        wide, per = {}, {}
        for o in notes.get("words", []):
            if "s" in o:
                if o["s"] not in sent_by_n:
                    zh_fail(f"{base}: word note for '{o['w']}' points at missing sentence S{o['s']}")
                if o["w"] not in [t[0] for t in sent_by_n[o["s"]]["tok"]]:
                    zh_fail(f"{base}: '{o['w']}' is not a word in S{o['s']} (check the word split)")
                per[(o["s"], o["w"])] = o
            else:
                if o["w"] not in all_words:
                    zh_fail(f"{base}: word note '{o['w']}' matches no word in the article (check the word split)")
                wide[o["w"]] = o

        def merge(tok, n):
            out = []
            for w, py, en in tok:
                o = per.get((n, w)) or wide.get(w) or {}
                out.append([w, o.get("py", py), o.get("en", en), o.get("casual", ""), 1 if o.get("hard") else 0])
            return out

        bds = {}
        for b in notes.get("breakdowns", []):
            if b.get("s") not in sent_by_n:
                zh_fail(f"{base}: breakdown points at missing sentence S{b.get('s')}")
            if "meaning" not in b:
                zh_fail(f"{base}: breakdown S{b['s']} missing meaning")
            words = [t[0] for t in sent_by_n[b["s"]]["tok"]]
            chunks = [[chunk_text(c[0], words, base, b["s"], notes["kind"]), c[1]] for c in b.get("chunks", [])]
            bds[b["s"]] = {"meaning": b["meaning"], "chunks": chunks, "key": b.get("key", "")}
        if notes["kind"] == "news" and len(bds) > len(sent_by_n) * NEWS_SHARE_WARN:
            print(f"  WARNING {base}: {len(bds)} breakdowns for {len(sent_by_n)} sentences. "
                  f"For copyrighted news keep breakdowns to a selection (about a third at most), "
                  f"so together they don't amount to a translation of the article.")

        arts.append({
            "id": notes["id"], "num": num, "chip": notes["chip"], "kicker": notes["kicker"],
            "kind": notes["kind"], "register": notes["register"], "gist": notes["gist"],
            "source": notes["source"], "flag": notes.get("flag", ""), "quiz": notes.get("quiz"),
            "register_notes": notes.get("register_notes", []),
            "title": {"text": auto["title"]["text"], "tok": merge(auto["title"]["tok"], 0)},
            "paras": [[dict({"n": s["n"], "tok": merge(s["tok"], s["n"])},
                            **({"bd": bds[s["n"]]} if s["n"] in bds else {}))
                       for s in p] for p in auto["paras"]],
        })

    out = inject(ZH_SHELL, ZH_TOKEN, arts, ZH_OUT)
    print(f"Built {ZH_OUT}")
    print(f"  {len(arts)} articles, {len(out)//1024} KB")
    for a in arts:
        ns = sum(len(p) for p in a["paras"])
        nb = sum(1 for p in a["paras"] for s in p if "bd" in s)
        print(f"  {a['num']}. {a['id']} ({a['kind']}): {ns} sentences, {nb} breakdowns")


def main():
    build_fr()
    build_zh()


if __name__ == "__main__":
    main()
