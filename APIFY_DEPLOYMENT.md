# Apify deployment

Use the root `.actor` for the primary Actor, or link `main:apify-actors/<actor-name>` for a specific Actor.
Each nested `.actor/actor.json` uses `dockerContextDir: ".."` relative to that definition, preserving an independent build context.

## Enable automatic deployment

Create the repository Actions secret `APIFY_TOKEN` using your own Apify token, then rerun `Test and deploy Apify Actors`.
The workflow never commits or logs the token. Without this secret, it tests and validates but explicitly skips cloud deployment.

## Default behavior and billing

No-input runs are live-first. `OFFLINE_MODE=1` explicitly requests free labeled fallback examples. Total upstream failure also permits free fallback; empty successful feeds do not.
The billing guard checks demo/fixture markers before charging either startup or a result. Default Dataset writes must remain free.
Normal real results use `actor-start` plus their configured per-item event, with durable per-run idempotency receipts.

Public trend keywords have null product prices. Real product-page extraction can be selected using `startUrls`.
The security Actor computes findings on submitted/default code without executing it, reports CWE mappings, and leaves CVE IDs empty unless verified matching exists.
