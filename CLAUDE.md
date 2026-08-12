# En clair — repo guide

A French A1/A2 reader that turns real English news into simplified French with
per-sentence breakdowns. Read on desktop, phone, and **a Kobo e-reader** (this
last one drives most of the hard constraints below).

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
```

## Hard rules

1. **Never hand-edit `index.html`.** It is overwritten by every build. Edits go
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

## Git conventions

- Work on a branch; open a PR rather than pushing to `main`.
- One story per commit where practical: `add story: <id>`.
- Always include the rebuilt `index.html` in the same commit as its source.
