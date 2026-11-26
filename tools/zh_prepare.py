#!/usr/bin/env python3
"""En Clair 中文 intake: source file -> articles-zh/NN-id.txt + NN-id.auto.json

Usage:
    python3 tools/zh_prepare.py SOURCE articles-zh/NN-id [--keep-traditional]
    python3 tools/zh_prepare.py articles-zh/NN-id.txt articles-zh/NN-id   (re-run on existing text)

- SOURCE may be .docx, .rtf (e.g. TextEdit) or .txt. .docx and .rtf are read
  with the standard library; one paragraph per line.
- Traditional characters are converted to simplified with OpenCC ('t2s',
  character-level: regional vocabulary such as 軟體 is NOT changed to 软件).
  The script reports how many characters it converted. --keep-traditional skips it.
- Claude never types or edits article text: the .txt is this script's output.
- The automatic layer (sentences -> words -> [word, pinyin, dictionary gloss])
  goes to NN-id.auto.json. Never hand-edit it; corrections go in NN-id.notes.json.
- Needs: pip install jieba pypinyin pycccedict opencc-python-reimplemented
  (pycccedict bundles CC-CEDICT, CC BY-SA 4.0, MDBG). Only intake needs them.
"""
import html, json, os, re, sys, zipfile

import jieba
from pypinyin import Style, pinyin
from pycccedict.cccedict import CcCedict

HERE = os.path.dirname(os.path.abspath(__file__))
USERDICT = os.path.join(HERE, "zh_userdict.txt")
SPLITS = os.path.join(HERE, "zh_split.txt")
ENDS = "。；！？"
CLOSERS = "”’」』）)"
CJK = re.compile(r"[㐀-鿿]")
VOWEL_START = re.compile(r"^[aeoāáǎàēéěèōóǒò]")


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        t = "".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", p, flags=re.S))
        t = html.unescape(t).strip()
        if t:
            out.append(t)
    return "\n".join(out) + "\n"


RTF_TOKEN = re.compile(r"\\([a-z]{1,32})(-?\d{1,10})?[ ]?|\\'([0-9a-f]{2})|\\([^a-z])|([{}])|[\r\n]+|(.)", re.I | re.S)
RTF_SKIP = {"fonttbl", "colortbl", "expandedcolortbl", "stylesheet", "info", "pict", "listtable",
            "listoverridetable", "header", "footer", "headerl", "headerr", "footerl", "footerr",
            "fldinst", "object", "themedata", "datastore", "latentstyles", "generator", "rsidtbl"}
RTF_CHARS = {"emdash": "—", "endash": "–", "lquote": "‘", "rquote": "’", "ldblquote": "“",
             "rdblquote": "”", "bullet": "•", "tab": "\t"}


def rtf_text(path):
    """Plain text from RTF (TextEdit, Word, Pages exports). Standard library only."""
    data = open(path, "rb").read().decode("latin-1")
    m = re.search(r"\\ansicpg(\d+)", data)
    codepage = "cp" + (m.group(1) if m else "1252")
    out, stack, raw = [], [], bytearray()
    ignorable, ucskip, curskip = False, 1, 0

    def flush():
        if raw:
            out.append(raw.decode(codepage, errors="replace"))
            raw.clear()

    for word, arg, hexb, ch, brace, tch in RTF_TOKEN.findall(data):
        if hexb:
            if curskip > 0:
                curskip -= 1
            elif not ignorable:
                raw.append(int(hexb, 16))
            continue
        flush()
        if brace:
            curskip = 0
            if brace == "{":
                stack.append((ucskip, ignorable))
            elif stack:
                ucskip, ignorable = stack.pop()
        elif ch:
            curskip = 0
            if ch == "*":
                ignorable = True
            elif ignorable:
                pass
            elif ch in "\n\r":
                out.append("\n")
            elif ch == "~":
                out.append(" ")
            elif ch in "{}\\":
                out.append(ch)
        elif word:
            curskip = 0
            if word in RTF_SKIP:
                ignorable = True
            elif ignorable:
                pass
            elif word in ("par", "line", "sect", "page", "row"):
                out.append("\n")
            elif word == "uc":
                ucskip = int(arg or 1)
            elif word == "u":
                c = int(arg)
                out.append(chr(c + 0x10000 if c < 0 else c))
                curskip = ucskip
            elif word in RTF_CHARS:
                out.append(RTF_CHARS[word])
        elif tch:
            if curskip > 0:
                curskip -= 1
            elif not ignorable:
                out.append(tch)
    flush()
    text = "".join(out).encode("utf-16", "surrogatepass").decode("utf-16")  # rejoin astral chars
    lines = [ln.replace("\u00a0", " ").strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln) + "\n"


def to_simplified(text):
    """Traditional -> simplified (OpenCC t2s). Returns (text, number of characters changed)."""
    from opencc import OpenCC
    conv = OpenCC("t2s").convert(text)
    changed = sum(1 for a, b in zip(text, conv) if a != b)
    return conv, changed


def split_sentences(par):
    out, buf, i = [], "", 0
    while i < len(par):
        buf += par[i]
        if par[i] in ENDS:
            while i + 1 < len(par) and par[i + 1] in CLOSERS:
                i += 1
                buf += par[i]
            out.append(buf)
            buf = ""
        i += 1
    if buf:
        out.append(buf)
    return out


def word_pinyin(w):
    if not CJK.search(w):
        return ""
    sylls = [s[0] for s in pinyin(w, style=Style.TONE, heteronym=False)]
    res = ""
    for k, s in enumerate(sylls):
        if k and VOWEL_START.match(s):
            res += "'"
        res += s
    return res


def gloss(cedict, w):
    if not CJK.search(w):
        return ""
    defs = cedict.get_definitions(w)
    if not defs:
        return ""
    keep = [d for d in defs if not d.startswith(("variant of", "old variant", "surname "))] or defs
    return "; ".join(keep[:2])[:80]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keep_trad = "--keep-traditional" in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    src, stem = args
    txt_path, auto_path = stem + ".txt", stem + ".auto.json"

    low = src.lower()
    if low.endswith(".docx"):
        text = docx_text(src)
    elif low.endswith(".rtf"):
        text = rtf_text(src)
    else:
        with open(src, encoding="utf-8") as fh:
            text = fh.read()
    if not keep_trad:
        text, changed = to_simplified(text)
        print(f"Traditional -> simplified: {changed} character(s) converted"
              + (" (text was already simplified)" if not changed else ""))
    if os.path.abspath(src) != os.path.abspath(txt_path) or not keep_trad:
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(text)

    if os.path.exists(USERDICT):          # words jieba should keep together
        jieba.load_userdict(USERDICT)
    if os.path.exists(SPLITS):            # word pairs jieba should keep apart, e.g. "仍 为"
        with open(SPLITS, encoding="utf-8") as fh:
            for ln in fh:
                parts = ln.split()
                if len(parts) > 1:
                    jieba.suggest_freq(tuple(parts), True)
    jieba.setLogLevel(60)
    cedict = CcCedict()

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        sys.exit("Source has no text.")

    def tok(sentence):
        return [[w, word_pinyin(w), gloss(cedict, w)] for w in jieba.lcut(sentence, HMM=True)]

    auto = {"title": {"text": lines[0], "tok": tok(lines[0])}, "paras": []}
    n = 0
    for ln in lines[1:]:
        para = []
        for s in split_sentences(ln):
            n += 1
            para.append({"n": n, "text": s, "tok": tok(s)})
        auto["paras"].append(para)

    with open(auto_path, "w", encoding="utf-8") as fh:
        json.dump(auto, fh, ensure_ascii=False, indent=1)

    print(f"Wrote {txt_path} and {auto_path}: {n} sentences")
    for para in auto["paras"]:
        for s in para:
            print(f"S{s['n']}: " + " | ".join(f"{w}[{p}]" if p else w for w, p, _ in s["tok"]))


if __name__ == "__main__":
    main()
