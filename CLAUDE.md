# En clair — repo guide

A French A1/A2 reader that turns real English news into simplified French with
per-sentence breakdowns. Read on desktop, phone, and **a Kobo e-reader** (this
last one drives most of the hard constraints below).

## The one-paragraph model

`index.html` is **generated**. It is built by `build.py` from `shell.html`
(the reader: CSS + logic) plus `stories/*.json` (the content, one file per
story). Adding a story = write one new JSON file + run the build. Everything
bundles into a single self-contained `index.html` because it must work when
sideloaded onto a Kobo with no network.

```
shell.html        the reader — CSS + ES5 JS + docs. Rarely changes.
stories/NN-id.json  one story per file. This is what grows.
build.py          shell + stories -> index.html  (validates, guards ES5)
index.html        GENERATED. Never hand-edit.
```

## Hard rules

1. **Never hand-edit `index.html`.** It is overwritten by every build. Edits
   go to `shell.html` or `stories/*.json`.
2. **Always run `python3 build.py` after changing a story or the shell**, and
   commit the regenerated `index.html` together with the source change. The
   committed `index.html` is what GitHub Pages serves and what gets sideloaded
   to the Kobo, so a stale one is a real bug.
3. **ES5 ONLY in `shell.html`.** The Kobo browser is an old WebKit: no arrow
   functions, no `const`/`let`, no template literals, no `Set`/`Map`, no
   spread, no `async`/`await`, no `.includes()`. Use `var` and `function`.
   `build.py` fails the build if it finds ES6 in the script — that guard is
   deliberate, do not weaken or bypass it. (Prose in comments is exempt.)
4. **Never change a story's `id` once committed.** Read-state is stored in the
   browser keyed by `id`; renaming one silently marks that story unread again.
   The `NN-` filename prefix sets order and may change; the `id` may not.
5. **Data is injected at a sentinel** in `shell.html`:
   `var STORIES = /*STORIES_DATA_SENTINEL*/[];`
   It must appear **exactly once**. Never paste story data into `shell.html`.
   (An earlier bug duplicated the entire dataset into a doc comment and nearly
   doubled the file — the build now aborts if the sentinel count is wrong.)

## Kobo constraints (why the code looks the way it does)

- **No dev console.** `shell.html` installs a `window.onerror` handler that
  paints errors into a red box on-screen. Keep it — it is the only debugging
  channel on the device.
- **Unreliable synthetic clicks.** Taps go through the `addTap(el, handler)`
  helper, which listens for `touchend`, ignores movement over ~12px (that's a
  scroll, not a tap), and suppresses the delayed duplicate click. Use `addTap`
  for any new tappable element; a bare `click` listener may not fire.
- **E-ink.** Avoid animation-dependent affordances; state must be legible in a
  static greyscale frame. Keep contrast high and hit targets large.
- **Offline.** No runtime `fetch`. Everything ships inside `index.html`.
  (The Google Fonts `<link>` is the one external dependency; it degrades to
  system serif/sans when offline, which is fine and intended.)

## Adding a story (the main workflow)

1. Read the English article the user provides.
2. Simplify it to **A1** (default; use A2 only if asked). Keep it short and
   concrete: tell the human story, drop specialist vocabulary that has no
   high-frequency French equivalent. Standard (international) French, never
   Quebecois. It's a *retelling*, not a translation — strip editorial tone and
   stay neutral.
3. Write the JSON (schema below), one breakdown per sentence, matching the
   existing stories' style exactly. Read `stories/01-vibe-lawyering.json` as
   the reference before writing a new one.
4. Save as `stories/NN-id.json` with the next number.
5. Run `python3 build.py`. It validates and reports.
6. Commit the new JSON **and** the regenerated `index.html`.

### Story JSON schema

```jsonc
{
  "id": "kebab-case-stable-forever",
  "chip": "Short label",              // shown under the card title
  "kicker": "Topic · Topic",          // uppercase eyebrow
  "title": "French headline",
  "level": "A1",
  "gist": "2-3 sentences of English summary — what the story says.",
  "body": [                            // array of PARAGRAPHS
    [                                  // paragraph = array of SENTENCES
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
  *meaningful unit*. Group words that work together (`aller au tribunal`,
  `de plus en plus de gens`, the verb inside `n'ont pas`). Not every word:
  ~2–5 per sentence. The English side is a short gloss plus an optional
  micro-note after a dash or in parentheses, e.g.
  `"a lawyer (un becomes de after a negative; de becomes d')"`.
- **key** — exactly ONE takeaway, the highest-leverage pattern in that
  sentence. Bold pattern-name lead, then one plain sentence, French set in
  italic via `<span class='bd-fr-i'>...</span>`. Never list two keys.
- Tie keys to the learner's known structural keys wherever possible:
  `aller` + plain verb = future; `avoir`/`être` + past participle = past;
  the `ne … pas` (and `ne … plus`) sandwich; adjective after/agreeing with the
  noun; helper + plain verb (`pouvoir/vouloir/devoir`); the little words
  (`le/la/les/des`); `à` + city; `on` = people/you/we; `c'est`; `il y a`.
- Tone: concise, phone-tight, jargon-light. Name a grammar term once, then
  explain it plainly. Don't pad with grammar the sentence doesn't contain.
- Allowed inline HTML in `meaning`/`key`/`en`/`flag`/glosses: `<b>`,
  `<span class='bd-fr-i'>`, `<span class='fr'>`.

### The learner (write for this person)

High-beginner (A1, touching A2). Canadian, reads business/world news (FT,
Economist, NYT). Wants **communication-first** learning: comprehensible input,
structural "keys" over conjugation drills, easy material over hard. Grammar in
plain language. Standard French as the base.

**Always be honest about French you're unsure of.** Every story's `flag` should
say what was compressed away and name any phrasing a native might say
differently. Never present AI-generated French as guaranteed-perfect.

## Git conventions

- Work on a branch; open a PR rather than pushing to `main`.
- One story per commit where practical: `add story: <id>`.
- Always include the rebuilt `index.html` in the same commit as its source.
