---
applyTo: "{about.qmd,index.qmd,_quarto.yml,theme.scss,styles.css,styles-site.css}"
---

# Site chrome and non-post pages

## Theme

Live site look is **Cosmo** (Bootswatch via `theme.scss`). Do not restyle the
site unless the human asks. Site experiments use branch `site/<name>` and stay
off `main` until explicit sign-off.

Chart typeface stays **Calibri** (viz kit) even when the site theme changes.
Do not restyle matplotlib to match Cosmo.

Navbar and homepage wordmark: **gilboa.blog** (not the author's personal name).

## About and other root pages

- YAML `title:` is the page H1. Do not repeat it as `# Title` in the body.
- `description:` is the HTML meta description only. Set `hide-description: true`
  so it does not render under the heading. Do not hide it with CSS.
- Short pages (`about.qmd`): `toc: false`.
- Escape at-handles in Markdown so Quarto does not treat them as citations:
  `[\@name](https://x.com/name)`.
- Do not restore a Jolla / profile About template unless the human asks.
- After editing a root `.qmd`, report its absolute path.
