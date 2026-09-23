# gs3393.github.io

Source of <https://gs3393.github.io>, a [Quarto](https://quarto.org) website (built with Quarto 1.10.18).
GitHub Pages serves the rendered `docs/` folder of `main`, so **pushing `main` publishes**.

## Layout

```text
_quarto.yml               navbar, footer, site-url, share cards, theme layers
_brand.yml                color and font tokens
styles/site.scss          site-wide rules (typography, tables, figures, TOC, navbar, footer)
styles/components.scss    shared blocks: note lists, home, algorithm boxes, info boxes
_templates/               title block, note listing, starter files for new notes
index.qmd  notes.qmd  about.qmd  404.qmd
_work.qmd                 parked page; see the comment inside to reopen it
notes/_metadata.yml       defaults shared by every note
notes/<slug>.qmd          one note per file; published URLs depend on these paths
notes/assets/<slug>/      figures, data, and the scripts that produced them
assets/site/              favicon, home strip, share card
tools/                    asset generator and the QA capture script
docs/                     rendered site (committed; this is what GitHub Pages serves)
```

## Writing a note

Copy the starter that matches the kind of note from `_templates/note-*.qmd` to `notes/<slug>.qmd`.

| Field | Rule |
|---|---|
| `post-type` | Exactly one of `Fundamentals`, `Paper Review`, `Experiment`. Drives the label on the note and its section on the Notes page. A note with any other value is listed under "Other". |
| `categories` | Topics only (`Diffusion`, `Flow Matching`, `Guidance`, `Architecture`, `Evaluation`, `Editing`, `Controllable Generation`, `Few-Step Generation`, `3D & Video`). Add a topic when a note needs it. |
| `description` | One or two sentences. Used in lists and share cards. |
| `image` | Optional. Share cards need PNG or JPG; if the first figure is an SVG, point this at `/assets/site/social-card.png`. |
| `draft: true` | Keep until the note is approved. With the default `draft-mode`, a draft renders as a blank page and gets no links from navigation, lists, or search; `quarto preview` still shows it. |

`lang`, `toc`, math rendering and similar options come from `notes/_metadata.yml`; a note only sets what differs.
Do not rename or move a published note: its URL is the file path.

Figures are shown on a white plate with a hairline border, so white-background SVG and PNG files work as they are.
Shared blocks available in any note: `.algorithm-pair` with `.paper-algorithm`, `.distribution-panels`,
`.concept-route`, `.paper-info`, `.setup-info`.

## Preview and checks

```bash
quarto render --output-dir _preview                 # never touches docs/
node tools/serve-preview.mjs --dir _preview --port 8765
node tools/qa-capture.mjs --base http://127.0.0.1:8765 --out _preview-assets/shots
```

Serve the preview with `tools/serve-preview.mjs`, not `python -m http.server`: on this machine Python
sends `.js` as `text/plain`, and browsers then refuse to run Quarto's module script, so the table of
contents stops following the scroll position and reader mode and footnote tooltips disappear. The
published site is unaffected.

The email address on the About page comes from `_variables.yml`. It ships with a placeholder;
`check-links.mjs` fails until a real address replaces it.

`qa-capture.mjs` loads every page at 1360, 768 and 390 px with real device emulation, saves screenshots,
and fails if a page overflows horizontally, has a MathJax error, or has a broken image.
In Git Bash pass pages without a leading slash: `--pages notes.html,notes/<slug>.html`.

`node tools/check-links.mjs _preview` verifies every local link, image, and anchor in the rendered folder.

`node tools/make-site-assets.mjs` regenerates the home strip, the favicon, and the source page of the share card.

## Publishing

1. Render the final site: `quarto render` (writes `docs/`).
2. Review the diff, commit sources and `docs/` together.
3. Push `main` only after the content has been approved.
