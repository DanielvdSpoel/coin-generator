# Coin Designer — implementation plan

These files are the working plan for the challenge-coin designer. They are meant to
be edited: change scope, reorder tasks, tick boxes, add notes. Nothing here is
generated from code, so keep it honest by hand.

| file | what it holds |
|---|---|
| [00-overview.md](00-overview.md) | goals, non-goals, decisions log, phase map, open questions |
| [01-architecture.md](01-architecture.md) | stack, repo layout, backend layering, frontend shape, caching, deployment |
| [02-data-model-and-api.md](02-data-model-and-api.md) | the `CoinConfig` v1 schema, icon geometry format, REST contract |
| [phase-0-scaffold.md](phase-0-scaffold.md) | repo, tooling, compose, CI |
| [phase-1-engine.md](phase-1-engine.md) | geometry engine driven by `CoinConfig`, CLI, materials, export formats |
| [phase-2-api.md](phase-2-api.md) | FastAPI wrapping, cache, container, tests |
| [phase-3-frontend-2d.md](phase-3-frontend-2d.md) | Vue skeleton, store, SVG preview, controls, JSON import/export |
| [phase-4-frontend-3d.md](phase-4-frontend-3d.md) | TresJS viewer over `/api/preview/glb` |
| [phase-5-icons.md](phase-5-icons.md) | upload, rasterise, trace, isolate, place |
| [phase-6-export-two-tone.md](phase-6-export-two-tone.md) | 3MF, filament registry, two-colour print files |
| [phase-7-validation-templates-polish.md](phase-7-validation-templates-polish.md) | printability checks, templates gallery, UX polish |
| [phase-8-deploy.md](phase-8-deploy.md) | Docker images, nginx, hardening, release |
| [backlog.md](backlog.md) | ideas that are explicitly not in a phase yet |

Source material these were derived from (in `docs/reference/`):
`coin-tool-architecture.md`, `coin-code-handoff.md`, `coin-tool-addendum.md`,
`architecture.md` (the MRA app whose layering we copy).

Conventions used in the phase files:

- Every phase has **Goal**, **Scope / out of scope**, **Tasks** (checkboxes),
  **Acceptance criteria**, **Tests**, **Risks & notes**.
- Effort is `S` (a day or less), `M` (a few days), `L` (a week or more). Rough,
  single-developer, tweak freely.
- "Engine gotcha #n" refers to the numbered list in `coin-code-handoff.md` §4.
