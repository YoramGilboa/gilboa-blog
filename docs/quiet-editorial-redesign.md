# Quiet editorial redesign (not shipped)

**Status:** rejected for production. Cosmo on `main` stays the live look.

**Date:** 2026-08-22
**Branch:** `site/quiet-editorial-redesign`
**Parent:** `main` at `d2d346f` (July FOMC minutes post)
**Style commit:** `4a8cc44` Restyle site chrome for a quiet editorial look
**This notes commit:** documents the experiment so it can be found, previewed, or deleted later.

## What this was

A review-only restyle of **site chrome**, not charts. Goal was an FT / Stratechery feel: paper background, ink text, serif headings, quiet navy, more whitespace.

You looked at a local preview and preferred the original Bootstrap **Cosmo** site (blue navbar, system sans, title banners). Nothing was merged to `main`. Live [gilboa.blog](https://gilboa.blog) was never switched.

Charts (Calibri, house COLORS, freeze PNGs) were not restyled and were not re-frozen.

## Files on this branch (vs Cosmo `main`)

| File | Change |
|---|---|
| `theme.scss` | Paper `#f7f4ee`, ink `#1c1917`, navy `#2e4a62`. Serif heading stack (Charter / Iowan / Georgia). Light navbar CSS. No Google Fonts. |
| `styles.css` | Listing cards, post titles, category chips, TOC, callouts, homepage lede. |
| `styles-site.css` | Cache-bust comment only. |
| `_quarto.yml` | Nav title `gilboa.blog`; Writing + About; dropped duplicate Home/Blog; paper navbar background. |
| `index.qmd` | `title-block-banner: false`; one-line masthead sentence. |
| `about.qmd` | Longer editorial bio. |
| `posts/_metadata.yml` | `title-block-banner: false` for all posts (CSS only; no per-post qmd edits). |

## How to preview later

```powershell
git checkout site/quiet-editorial-redesign
quarto preview --port 4200 --no-browser
```

Then open http://127.0.0.1:4200/ , About, a recent post, and an older post.

Switch back to Cosmo:

```powershell
git checkout main
```

## How to discard later (cleanup)

Local only:

```powershell
git checkout main
git branch -D site/quiet-editorial-redesign
```

If this branch was pushed to GitHub:

```powershell
git push origin --delete site/quiet-editorial-redesign
```

Optional tag (if created): `git tag -d experiment/quiet-editorial-2026-08` and `git push origin --delete experiment/quiet-editorial-2026-08`.

Deleting the branch does not change `main` or the live site.

## How to revive later

```powershell
git checkout site/quiet-editorial-redesign
```

Do **not** merge to `main` unless you explicitly want to replace Cosmo. If `main` has moved on, rebase or merge `main` into this branch first and re-check homepage, About, and a couple of posts.

## Why keep it at all

So a future "try a quieter site" pass does not start from zero. The rejected look is the code on this branch plus this file. Cosmo production history stays linear on `main`.
