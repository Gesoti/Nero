# Sprint Plan — Sprints 3 & 4

**Date:** 2026-02-26
**Sprint duration:** 1 week each
**Context:** Sprints 1+2 complete. 121 tests. Blog live with 3 articles + auto monthly reports. Nero brand established. 11 commits pushed and deploying via CI/CD.

---

## Sprint 3 — Polish, Accessibility & Social Sharing

**Goal:** Make the site production-grade — fix gaps in accessibility, add social sharing assets (og:image, favicon), install Tailwind typography plugin for blog rendering, and harden test coverage.

| ID | Story | Points | Category |
|----|-------|--------|----------|
| 3.1 | **Add og:image and Twitter Card meta tags** — Create a branded OG image (1200x630) for social sharing. Add `og:image` and `twitter:card` meta to `base.html`. Dam detail pages should generate dynamic og:image description. | 3 | SEO/Social |
| 3.2 | **Add favicon and apple-touch-icon** — Create SVG favicon (water droplet motif), PNG apple-touch-icon, add `<link>` tags to `base.html`. | 2 | Branding |
| 3.3 | **Install @tailwindcss/typography plugin** — Add typography plugin to tailwind.config.js. Rebuild CSS. Verify blog post prose styling renders correctly. | 2 | Frontend |
| 3.4 | **Accessibility audit fixes** — Add `aria-label` to all `<nav>` elements, `role="progressbar"` + aria attrs to progress bars, `aria-hidden="true"` to decorative SVGs, `type="button"` to all non-submit buttons, `<label>` for year-on-year selects, `aria-label` on `<canvas>` charts. | 5 | Accessibility |
| 3.5 | **Unit tests for blog.py and dam_descriptions.py** — Test `_parse_frontmatter`, `load_post`, `load_all_posts` edge cases. Test all 17 dam names have descriptions. Test malformed YAML handling. | 3 | Testing |
| 3.6 | **Remove `'unsafe-eval'` from CSP** — Verify Chart.js and AdSense work without `unsafe-eval`. If they do, tighten the CSP. If not, document why it's needed. | 1 | Security |
| 3.7 | **Rebuild Tailwind CSS** — Full rebuild including new classes from Sprints 1-2 (dam descriptions, related dams, blog prose). Commit the built CSS. | 1 | Frontend |

**Total: 17 points**

### Acceptance criteria

- 3.1: Every page has `og:image` meta tag. Twitter card renders preview when sharing a Nero URL. Dam detail pages show dam-specific OG description.
- 3.2: Favicon visible in browser tab. Apple-touch-icon works on iOS home screen. No 404 for `/favicon.ico`.
- 3.3: Blog post headings, lists, links, bold text render with proper typography. `prose` classes apply visually.
- 3.4: axe DevTools or Lighthouse accessibility audit passes with score >= 90. All interactive elements accessible via keyboard. Screen reader can navigate all sections.
- 3.5: Test count increases by ~10+. Edge cases covered: missing frontmatter, unknown slug, empty posts dir. All 17 dam names validated.
- 3.6: CSP header no longer includes `'unsafe-eval'`, or documented exception with reasoning.
- 3.7: `tailwind.min.css` rebuilt and committed. Visual check confirms no missing styles.

---

## Sprint 4 — Growth Infrastructure & Content Velocity

**Goal:** Build growth infrastructure (newsletter, embeddable widget) and increase content velocity with more articles and auto-generated pages.

| ID | Story | Points | Category |
|----|-------|--------|----------|
| 4.1 | **Email newsletter signup (Buttondown)** — Add signup form to dashboard footer and blog sidebar. Integrate with Buttondown free tier API. Update privacy policy. | 5 | Growth |
| 4.2 | **Embeddable widget** — Create `/embed` route serving a minimal HTML widget showing current system capacity. Document in About page. Add CORS headers for cross-origin embedding. | 3 | Growth |
| 4.3 | **Blog post: "How Cyprus Dams Work"** — Educational explainer covering dam types (earth-fill, RCC), catchment areas, water cycle on the island. Evergreen content targeting informational queries. | 3 | Content |
| 4.4 | **Blog post: "Desalination vs Dams: Cyprus Water Future"** — Compare cost, capacity, environmental impact of desalination vs dam storage. Data-driven. | 3 | Content |
| 4.5 | **Auto-generated per-dam SEO pages** — For each dam, generate a `/dam/{name}/history` page with full historical data table + downloadable CSV. 17 new indexable pages. | 5 | SEO/Content |
| 4.6 | **Coverage reporting in CI** — Add `pytest --cov` to GitHub Actions workflow. Set minimum coverage threshold. | 2 | Tooling |

**Total: 21 points**

### Acceptance criteria

- 4.1: Signup form visible on dashboard and blog. Submissions reach Buttondown. Privacy policy updated with newsletter data handling.
- 4.2: `/embed` serves a self-contained HTML page. `<iframe src="https://nero.cy/embed">` works on external sites. Widget shows system percentage and last-updated timestamp.
- 4.3: Published at `/blog/how-cyprus-dams-work`. 500+ words. Links to dam pages.
- 4.4: Published at `/blog/desalination-vs-dams`. 500+ words. Data-backed comparison.
- 4.5: `/dam/Kouris/history` returns 200 with data table. CSV download link works. All 17 dams have history pages. Sitemap updated.
- 4.6: CI pipeline reports coverage %. Fails if coverage drops below threshold.

---

## Parallel Track: Manual Outreach (ongoing)

These are non-code tasks to pursue alongside development:

| Task | Channel | Priority | Status |
|------|---------|----------|--------|
| Contact Cyprus Mail | Email | High | Not started |
| Post to r/cyprus | Reddit | High | Not started |
| Post to r/dataisbeautiful | Reddit | Medium | Not started |
| Add to Wikipedia external links | Wikipedia | Medium | Not started |
| Contact Water Development Dept | Email | Low | Not started |
| Set up Twitter/X account | Social | Low | Not started |
| Submit to data.europa.eu | Portal | Low | Not started |

---

## Tooling Backlog (pick up as capacity allows)

| Item | Priority |
|------|----------|
| Pre-push git hook (test guard) | Medium |
| `/validate-templates` skill | Medium |
| `/changelog` skill | Low |
| Auto-update CLAUDE.md module table | Low |
| CSP `report-to` endpoint | Low |

---

## Metrics to Track

| Metric | Current | Sprint 3 Target | Sprint 4 Target |
|--------|---------|-----------------|-----------------|
| Tests | 121 | 135+ | 150+ |
| Blog posts | 3 + auto reports | 3 | 5 |
| Indexable pages | ~25 | ~25 | ~42 (17 history pages) |
| Lighthouse Accessibility | Unknown | >= 90 | >= 90 |
| Lighthouse Performance | Unknown | >= 85 | >= 85 |
