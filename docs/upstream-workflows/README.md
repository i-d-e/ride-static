# Upstream sender workflows

The site build lives in `ride-static`, but the content lives in two other
repositories: the published corpus in `i-d-e/ride`, work-in-progress in
`i-d-e/ride-editors`. A push to either of those does not reach
`ride-static` on its own — each content repository needs a small sender
workflow that notifies `ride-static` via `repository_dispatch`. The
receiving side is already wired: `.github/workflows/build.yml` in
`ride-static` accepts the event types `corpus-updated` and
`editors-updated`.

This directory holds the two sender workflows as copy-ready templates.
Installing one is a one-time, two-step task:

1. **Copy the file** into the content repository as
   `.github/workflows/trigger-site-build.yml`
   (`ride-trigger-build.yml` → `i-d-e/ride`,
   `ride-editors-trigger-build.yml` → `i-d-e/ride-editors`).
2. **Create the token secret.** Generate a fine-grained personal access
   token (GitHub → Settings → Developer settings → Fine-grained tokens)
   scoped to the single repository `i-d-e/ride-static` with
   **Contents: Read and write** permission — that is the permission
   `repository_dispatch` requires. Store it in the content repository
   under Settings → Secrets and variables → Actions as
   `RIDE_STATIC_DISPATCH_TOKEN`.

Both repositories can share one token. When the token expires, builds
silently stop being triggered — the sender run fails visibly in the
content repository's Actions tab, so check there first if the site stops
updating.

Install `ride-trigger-build.yml` now: publication (moving a review into
`ride`) must rebuild the live site. Install
`ride-editors-trigger-build.yml` once the preview environment decision is
made (see `knowledge/staging.md` in ride-static) — until the build
consumes drafts, the event triggers a rebuild that changes nothing.
