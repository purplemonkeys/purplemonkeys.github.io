# En clair — repo guide

A French A1/A2 reader that turns real English news into simplified French with
per-sentence breakdowns. Read on desktop, phone, and **a Kobo e-reader** (this
last one drives most of the hard constraints below).

The repo also hosts **En Clair 中文** (`zh.html`), a reader for original
Chinese articles. Its workflow and rules are in the Chinese section below.

## The one-paragraph model

`index.html` is **generated**. `build.py` builds it from `shell.html` (the
reader: CSS + logic) plus `stories/*.json` (the content, one file per story).
Adding a story = write one new JSON file + run the build. Everything bundles
into a single self-contained `index.html` because it must work when sideloaded
onto a Kobo with no network.

```
shell.html          the reader — CSS + ES5 JS + docs. Rarely changes.
stories/NN-id.json  one story per file. This is what grows.
progress/m1.json    shared "read" list for M1 memory (see below).
build.py            shell + stories -> index.html  (validates, guards ES5)
index.html          GENERATED. Never hand-edit.

shell-zh.html       the Chinese reader (CSS + ES5 JS). Same rules as shell.html.
articles-zh/        NN-id.txt (text, by script) + .auto.json (generated) + .notes.json (Claude)
tools/              zh_prepare.py (intake) + zh_userdict.txt / zh_split.txt (word splits)
progress/m1-zh.json shared "read" list for the Chinese reader.
zh.html             GENERATED. Never hand-edit.
```

## Hard rules

1. **Never hand-edit `index.html` or `zh.html`.** It is overwritten by every build. Edits go
   to `shell.html` or `stories/*.json`.
2. **Always run `python3 build.py` after changing a story or the shell**, and
   commit the regenerated `index.html` with the source change. The committed
   `index.html` is what GitHub Pages serves and what gets sideloaded to the
   Kobo, so a stale one is a real bug.
3. **ES5 ONLY in `shell.html`.** The Kobo browser is an old WebKit: no arrow
   functions, no `const`/`let`, no template literals, no `Set`/`Map`, no spread,
   no `async`/`await`, no `.includes()`, no `fetch` (use `XMLHttpRequest`). Use
   `var` and `function`. `build.py` fails the build if it finds ES6 in the
   script — that guard is deliberate, do not weaken or bypass it. (Comment prose
   is exempt.)
4. **Never change a story's `id` once committed.** Read-state (both M1 and M2)
   is keyed by `id`; renaming one silently marks that story unread again. The
   `NN-` filename prefix sets order and may change; the `id` may not.
5. **Data is injected at a sentinel** in `shell.html`:
   `var STORIES = /*STORIES_DATA_SENTINEL*/[];` — it must appear **exactly
   once**. Never paste story data into `shell.html`. (An earlier bug duplicated
   the whole dataset into a comment; the build now aborts on a bad count.)

## Title numbering

Each story's `title` starts with its number: `"1. …"`, `"2. …"`, matching the
`NN-` filename order. This is plain text in the JSON — when you add story 9,
title it `"9. …"`. Nothing in the code derives it, so keep the prefix in sync
with the filename number by hand.

## Memory modes M1 / M2 (reading progress)

The reader has a small **M1 / M2** toggle on the index. It is a per-device
preference, **not a login** — it just picks which "read" data to show. Default
on a fresh device is **M2**.

- **M2** — this device only, stored in the browser (`localStorage`). Fully
  interactive: tap a card corner or the in-story button to mark read; read
  stories drop into "Déjà lu". This is the original behaviour, unchanged.
- **M1** — shared memory read from `progress/m1.json`. **Read-only in the
  reader**: the mark controls still appear but taps do nothing. You update M1 by
  editing `progress/m1.json` and committing — then it is the same on every
  device that loads the site. M1 is loaded over the network, so it works on the
  GitHub Pages URL but **not** over `file://` on a sideloaded Kobo (there it
  shows empty; that is expected).

### Editing `progress/m1.json`

```json
{ "read": ["vibe-lawyering", "euv-machine"] }
```

List the ids of stories that are read. The id is the part after the number in
each `stories/NN-<id>.json` filename. A bare array (`["id1","id2"]`) also works.
Do not add ids that don't exist as stories — harmless, but pointless.

## Adding a story (the main workflow)

1. Read the English article the user provides.
2. Simplify it to **A1** (default; A2 only if asked). Short and concrete: tell
   the human story, drop specialist vocabulary with no high-frequency French
   equivalent. Standard (international) French, never Quebecois. It's a
   *retelling*, not a translation — strip editorial tone, stay neutral.
3. Write the JSON (schema below), one breakdown per sentence, matching the
   existing stories' style exactly. Read `stories/01-vibe-lawyering.json` first
   as the reference.
4. Save as `stories/NN-id.json` with the next number, and number the title.
5. Run `python3 build.py`. It validates and reports.
6. Commit the new JSON **and** the regenerated `index.html`.

### Story JSON schema

```jsonc
{
  "id": "kebab-case-stable-forever",
  "chip": "Short label",
  "kicker": "Topic · Topic",
  "title": "N. French headline",       // number prefix matches the filename
  "level": "A1",
  "gist": "2-3 sentences of English summary.",
  "body": [                             // array of PARAGRAPHS
    [                                   // paragraph = array of SENTENCES
      {
        "fr": "French sentence with {{word|english meaning}} marks.",
        "bd": {
          "meaning": "One natural-English sentence for the whole line.",
          "chunks": [["French chunk", "english gloss (+ micro-note)"]],
          "key": "<b>Pattern name:</b> one plain sentence."
        }
      }
    ]
  ],
  "grammar": [ { "fr": "example", "en": "plain explanation" } ],
  "quiz": { "q": "French question ?", "a": "French answer (English gloss)" },
  "flag": "Honesty note: what you compressed, what you're unsure of."
}
```

### The breakdown recipe (match this exactly)

- **meaning** — ONE natural-English sentence for the whole line. Not
  word-for-word.
- **chunks** — the sentence in order, one `[French, English]` pair per
  *meaningful unit* (group words that work together: `aller au tribunal`, the
  verb inside `n'ont pas`). ~2–5 per sentence. English side = short gloss plus
  an optional micro-note after a dash or in parentheses.
- **key** — exactly ONE takeaway: bold pattern-name lead, then one plain
  sentence, French in italic via `<span class='bd-fr-i'>…</span>`. Never two.
- Tie keys to known structural keys: `aller`+plain verb = future;
  `avoir`/`être`+past participle = past; the `ne … pas` / `ne … plus` sandwich;
  adjective after/agreeing with the noun; helper+plain verb; the little words
  (`le/la/les/des`); `à`+city; `on` = people/you/we; `c'est`; `il y a`.
- Tone: concise, phone-tight, jargon-light. Don't pad with absent grammar.
- Allowed inline HTML in meaning/key/en/flag/glosses: `<b>`,
  `<span class='bd-fr-i'>`, `<span class='fr'>`.

### The learner (write for this person)

High-beginner (A1, touching A2). Canadian, reads business/world news. Wants
**communication-first** learning: comprehensible input, structural keys over
conjugation drills, easy material over hard, grammar in plain language, standard
French. **Always be honest about French you're unsure of** — every story's
`flag` should say what was compressed and name any phrasing a native might say
differently. Never present AI French as guaranteed-perfect.

## En Clair 中文 — the Chinese reader (`zh.html`)

A second reader in the same repo, linked by the round top-right buttons (中 on
En Clair, FR on the Chinese page). It shows **original simplified-Chinese
articles, unchanged** (no rewriting, no CEFR level), with:

- a pinyin toggle: 关 off / 难词 hard words only / 全部 all (HTML `<ruby>`);
- a tap-for-meaning card on every word: pinyin, English, and the everyday
  equivalent of formal words (载明 → 写明);
- breakdowns (▸) on selected sentences, in the En Clair format;
- register notes (正式 → 口语), a quiz, an honesty flag, and the source line.

Same hard rules as French: `zh.html` is generated (never hand-edit), ES5 only
in `shell-zh.html` (build.py checks both shells), article ids are permanent,
and the data sentinel `/*ARTICLES_DATA_SENTINEL*/[]` appears exactly once.

### The learner (Chinese)

Native speaker of casual Mandarin who reads only everyday characters (texting
level). The gap is **written / formal register**: news, official notices,
business and legal Chinese. Pinyin unlocks words he already knows by ear;
`casual` equivalents bridge formal words (其 → 他的, 若 → 如果). Simplified
characters only. Flag anything uncertain (pinyin of polyphonic characters,
glosses that are judgement calls) — never present it as guaranteed-perfect.

### Copyright rules (hard)

1. **Claude never writes article text.** `articles-zh/NN-id.txt` is produced
   only by `tools/zh_prepare.py` from Jack's file. Don't retype it, paste it
   into chat, or write it into notes.
2. **Breakdown chunks point at word positions** (`[from, to]`, or a list of
   ranges shown as 甲……乙). The page shows the article's own words. For news,
   build.py rejects typed Chinese in chunks.
3. **No fixed number of breakdowns.** Government documents (`kind: "gov"`:
   laws, regulations, notices of state organs — PRC Copyright Law Art. 5) may
   have every sentence broken down. Copyrighted news (`kind: "news"`) gets a
   *selection* chosen for the formal patterns it teaches, never every
   sentence, so the English meanings don't add up to a translation. build.py
   warns above about a third. Any other sentence can be explained in chat.
4. **Attribution is always shown.** `source.name` is required (e.g. "BBC中文").
   `url` and `date` only when Jack gives them — don't go looking. The page
   cites the source and the article's headline.

### Adding a Chinese article (the workflow)

1. Jack drops a `.docx`, `.rtf` or `.txt` in his inbox folder
   (`French Learning/En Clair Chinese/Chinese Articles/`, outside this repo —
   the source file itself is not committed) and names the source.
2. Run `python3 tools/zh_prepare.py "<source file>" articles-zh/NN-id`
   (next NN). It extracts the text, converts traditional → simplified (OpenCC
   t2s, character-level; reports the count; `--keep-traditional` skips it),
   splits sentences and words (jieba), adds pinyin (pypinyin) and CC-CEDICT
   glosses, and prints every sentence split into words.
3. Fix bad word splits **at intake**, then re-run step 2: add to
   `tools/zh_userdict.txt` (keep together: `二十国集团 5000 nt`) or
   `tools/zh_split.txt` (keep apart: `还 有待`). Never hand-edit `.txt` or
   `.auto.json`.
4. Write `articles-zh/NN-id.notes.json` (schema below). References:
   `01-…notes.json` (gov) and `02-…notes.json` (news).
5. Run `python3 build.py`. It checks the .txt ↔ .auto.json alignment, that
   every word note and breakdown points at a real word / sentence / range,
   and ES5.
6. Commit the `.txt`, `.auto.json`, `.notes.json` and rebuilt `zh.html` together
   (`add article: <id>`).

Intake needs `pip install jieba pypinyin pycccedict opencc-python-reimplemented`
(pycccedict bundles CC-CEDICT, CC BY-SA 4.0). `build.py` needs nothing.

### `notes.json` schema

```jsonc
{
  "id": "kebab-case-stable-forever",      // must equal the id in NN-id
  "chip": "Short label",
  "kicker": "来源 · 话题",
  "kind": "gov",                          // "gov" | "news"
  "register": "官方公告",                  // 官方公告 / 新闻 / 社论 …
  "gist": "2-4 English sentences.",
  "source": { "name": "BBC中文", "url": "optional", "date": "optional" },
  "words": [                              // article-wide, or one sentence with "s"
    { "w": "载明", "py": "zǎimíng", "en": "to state in writing", "casual": "写明", "hard": true },
    { "s": 7, "w": "为", "py": "wéi", "en": "into", "casual": "成" }
  ],
  "breakdowns": [
    { "s": 9,
      "meaning": "ONE natural-English sentence for the whole line.",
      "chunks": [ [[4, 11], "gloss (+ micro-note)"],
                  [[[18, 18], [24, 29]], "two ranges, shown as 甲……乙"] ],
      "key": "<b>Pattern name:</b> one plain sentence, Chinese in <span class='bd-zh-i'>…</span>." }
  ],
  "register_notes": [ { "formal": "若", "casual": "如果", "en": "if" } ],
  "quiz": { "q": "中文问题？", "a": "中文答案。(English.)" },
  "flag": "Honesty note: pinyin fixes, judgement calls, what is unchecked."
}
```

- The title number comes from the file name; the headline is the .txt's first line.
- Positions are 0-based word indices within the sentence, as printed by
  zh_prepare.py (punctuation tokens count).
- `hard: true` = formal / written-register word (gets pinyin in 难词 mode).
  Give `casual` wherever an everyday equivalent exists.
- Check polyphonic characters (为 wèi/wéi, 得, 只, 还, 载, 重, 行 …) and add `py` fixes.
- Breakdown keys: one register or structure takeaway (formal → casual,
  于 = 在, 由 X 支付, 若 … 才 …). Same tone as the French recipe.
- `kind: "gov"` may use typed Chinese strings in chunks; `news` may not.

### Memory (Chinese)

M1/M2 work as in French but are separate: browser keys `enclairzh:*`, and the
shared M1 list is `progress/m1-zh.json` (same format as `progress/m1.json`).

## Git conventions

- Work on a branch; open a PR rather than pushing to `main`.
- One story per commit where practical: `add story: <id>`.
- Always include the rebuilt `index.html` in the same commit as its source.
