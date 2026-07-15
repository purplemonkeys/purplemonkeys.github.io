# En clair

*L'actualité en français simple* — real news, retold at A1/A2, with a
breakdown of every sentence.

Open `index.html` in a browser, or read it on a Kobo. Tap any French sentence
to see what it means and how it's built. Mark stories read from the card
corner; read stories collapse into a "Déjà lu" section.

## Repo layout

| file | what it is |
|---|---|
| `index.html` | **generated** — the reader. Never hand-edit. |
| `shell.html` | the reader's CSS + ES5 JS (the framework) |
| `stories/NN-id.json` | one story per file — the content |
| `build.py` | `shell.html` + `stories/*.json` → `index.html` |
| `CLAUDE.md` | working instructions (build rules, Kobo constraints, story recipe) |

## Build

```bash
python3 build.py
```

Validates every story (JSON, required fields, duplicate ids), refuses to build
if ES6 has crept into the shell (the Kobo browser is ES5-only), and writes
`index.html`.

## Add a story

1. Write `stories/NN-id.json` (schema and recipe in `CLAUDE.md`).
2. `python3 build.py`
3. Commit the JSON **and** the regenerated `index.html`.

## Reading on the Kobo

`index.html` is fully self-contained, so sideloading the single file is enough:
connect the Kobo by USB and copy `index.html` onto it, then open it in the
Kobo's browser (Beta Features → Web Browser). No network needed; the web fonts
degrade gracefully to system fonts offline.

## Notes

- Reading progress is stored per-device in the browser (`localStorage`), keyed
  by story `id`. It does not sync across devices, and story ids must therefore
  never change once published.
- The reader is a single self-contained file by design: it has to work offline
  on an e-reader.
