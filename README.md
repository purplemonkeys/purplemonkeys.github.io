# En clair

*L'actualité en français simple* — real news, retold at A1/A2, with a breakdown
of every sentence.

Open `index.html` in a browser, or read it on a Kobo. Tap any French sentence to
see what it means and how it's built.

## Reading progress: M1 / M2

A small toggle on the index picks which "read" memory to show. It's a
preference, not a login. Default is **M2**.

- **M2** — this device only (browser storage). Tap a card corner (or the
  in-story button) to mark read; read stories collapse into "Déjà lu".
- **M1** — shared progress from `progress/m1.json`, the same on every device.
  Read-only in the reader: you update it by editing that file and committing.
  Loads over the web only, so on a sideloaded Kobo (opened as a local file) M1
  shows empty — use the site URL for M1, or just use M2 on the device.

Edit `progress/m1.json` like:
```json
{ "read": ["vibe-lawyering", "euv-machine"] }
```

## Repo layout

| file | what it is |
|---|---|
| `index.html` | **generated** — the reader. Never hand-edit. |
| `zh.html` | **generated** — the Chinese reader. Never hand-edit. |
| `shell-zh.html` | the Chinese reader's CSS + ES5 JS |
| `articles-zh/` | Chinese articles: `.txt` (by script), `.auto.json` (generated), `.notes.json` |
| `tools/` | `zh_prepare.py` intake script + word-split lists |
| `progress/m1-zh.json` | shared M1 read-list for the Chinese reader |
| `shell.html` | the reader's CSS + ES5 JS (the framework) |
| `stories/NN-id.json` | one story per file — the content |
| `progress/m1.json` | shared M1 read-list |
| `build.py` | `shell.html` + `stories/*.json` → `index.html` |
| `CLAUDE.md` | working instructions for Claude Code |

## Build

```bash
python3 build.py
```

Validates every story, refuses to build if ES6 crept into the shell (Kobo is
ES5-only), and writes `index.html`.

## Add a story

1. Write `stories/NN-id.json` (schema/recipe in `CLAUDE.md`); number the title.
2. `python3 build.py`
3. Commit the JSON **and** the regenerated `index.html`.

## Reading on the Kobo

`index.html` is self-contained: connect by USB, copy it onto the Kobo, open it
in the browser (Beta Features → Web Browser). No network needed; web fonts
degrade gracefully to system fonts offline. (M1 needs the network; M2 works
offline.)

## En Clair 中文

`zh.html` is a second reader for **original** simplified-Chinese articles
(news and official notices), built from the same repo. Tap 中 (top right) on
En Clair to get there, FR to come back.

- 拼音 toggle: 关 / 难词 (formal words only) / 全部. Remembered per device.
- Tap any word: pinyin, meaning, and the everyday equivalent of formal words.
- Tap ▸ after a sentence for its breakdown (selected sentences).
- Every article ends with register notes, a quiz, an honesty note, and its source.

Add an article (details in `CLAUDE.md`):

```bash
pip install jieba pypinyin pycccedict opencc-python-reimplemented   # once, intake only
python3 tools/zh_prepare.py "SOURCE.docx|.rtf|.txt" articles-zh/NN-id
# write articles-zh/NN-id.notes.json
python3 build.py
```
