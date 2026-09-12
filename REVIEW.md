# Review: pagetitle on the four newest published posts

Branch: `seo/pagetitle-last-4` (not merged).

H1 `title:`, `description:`, dates, categories, and body are unchanged.
`format.html.title-prefix: ""` kept where it already existed (CPI, jobs, PCE).
FOMC minutes had no `pagetitle`; one was added. It had no `title-prefix`; none was added.
All four already had a description, so none was written.

Prints in the new `<title>` lines match each post's existing official figures.

| Post | Chars | Old `pagetitle` | New `pagetitle` |
|---|---:|---|---|
| `posts/2026-09-12-august-cpi-energy-core-fomc/index.qmd` | 53 | August CPI Turned Up on Energy. Core Stayed Sticky. | August 2026 CPI: +0.4% as energy rebounds, core +0.3% |
| `posts/2026-09-06-august-jobs-rebound-composition/index.qmd` | 58 | The Jobs Rebound Was Restaurants and Schools | August 2026 jobs: +162,000, mostly restaurants and schools |
| `posts/2026-08-28-july-pce-jackson-hole/index.qmd` | 54 | July PCE Held at 3.7%: The Fed's Preferred Gauge Did Not Cool | July 2026 PCE: 3.7% headline, 3.3% core, spending flat |
| `posts/2026-08-21-fomc-minutes-dual-mandate/index.qmd` | 57 | *(none; browser title followed H1)* | July 2026 FOMC minutes: hike risk if inflation stays high |
