# Upstream sender workflows

The site is built by this repository (`ride-static`), which also holds the
published TEI corpus. Two companion repositories contribute content whose
changes do not reach this repository on their own:

- **`i-d-e/ride`** holds the figure images (`issues/issue{NN}/{slug}/pictures/`).
  When images are added or replaced there, the site must rebuild so the
  new files are copied in — otherwise review pages keep showing the old
  (or no) figures until the next unrelated build.
- **`i-d-e/ride-editors`** holds reviews in preparation. Once the preview
  environment is in place (see the staging section of `knowledge/pipeline.md`), a push there
  should regenerate the preview.

GitHub's mechanism for this is `repository_dispatch`: a small workflow in
the companion repository sends a notification, and the build workflow in
`ride-static` (`.github/workflows/build.yml`) listens for it. The
receiving side is already wired; it accepts the event types
`corpus-updated` (from `ride`) and `editors-updated` (from `ride-editors`).

This directory holds the two sender workflows as copy-ready templates.
Installing one is a one-time, two-step task:

1. **Copy the file** into the companion repository as
   `.github/workflows/trigger-site-build.yml`
   (`ride-trigger-build.yml` → `i-d-e/ride`,
   `ride-editors-trigger-build.yml` → `i-d-e/ride-editors`).
2. **Create the access token.** Generate a fine-grained personal access
   token (GitHub → Settings → Developer settings → Fine-grained tokens)
   scoped to the single repository `i-d-e/ride-static` with
   **Contents: Read and write** permission — the permission
   `repository_dispatch` requires. Store it in the companion repository
   under Settings → Secrets and variables → Actions as
   `RIDE_STATIC_DISPATCH_TOKEN`.

Both repositories can share one token. When the token expires, the
notification silently stops working — the sender run then fails visibly
in the companion repository's Actions tab, so check there first if the
site stops picking up image changes.

Install `ride-trigger-build.yml` now: publishing a review usually
includes pushing its images to `i-d-e/ride`, and without the sender those
images only appear on the site after the next unrelated build. Install
`ride-editors-trigger-build.yml` once the preview environment decision is
made (staging section of `knowledge/pipeline.md`) — until the build consumes drafts, the
event triggers a rebuild that changes nothing.
