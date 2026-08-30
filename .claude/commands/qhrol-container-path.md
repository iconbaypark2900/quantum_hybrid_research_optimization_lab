---
description: Wave 3 — README Quick Start step 3 is `docker-compose up -d`, and the compose file bind-mounts a prometheus config that does not exist.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`README.md:78` makes `docker-compose up -d` step 3 of Quick Start — before the entry
point, so it is the first thing a new reader runs. It cannot work.

- **A bind mount to nothing.** `docker-compose.yml:142` mounts
  `./monitoring/prometheus.yml` into the prometheus container. There is no `monitoring/`
  directory in the repository and nothing creates one, so Docker materialises a directory
  where a file is expected and prometheus fails to start.
- **A one-shot process supervised as a service.** `Dockerfile:38` is
  `CMD ["python", "main.py"]`, and `main.py` runs a demo and exits. Under a compose
  restart policy that is a crash loop, not a service.
- **The image installs a manifest that cannot install.** `requirements.txt:67` is
  `microsoft-presidio`, which does not exist on PyPI — see `/qhrol-pin-runtime`. The image
  has never built.

None of this is recorded anywhere — not in `SCAFFOLDING.md`, not in the README.

## Steps

1. Settle what the compose stack is *for*. It currently declares monitoring services for
   an application that exposes no metrics. Either drop prometheus and grafana, or add
   `monitoring/prometheus.yml` and something for it to scrape. Prefer dropping: this lab
   has no served endpoint (`/qhrol-true-claims` covers the missing API layer), so there is
   nothing to monitor.
2. Fix the entry point semantics. `main.py` is a demo that runs and exits; express that as
   a one-shot job, not a restarting service. If the compose file is meant to bring up
   databases the lab talks to, then the lab container does not belong in it at all.
3. Make the image build. It depends on `/qhrol-pin-runtime` and `/qhrol-true-claims`
   settling the manifest; install from whatever they produce, not from `requirements.txt`.
   `Dockerfile:2` already pins `python:3.11-slim`, which is the correct interpreter — keep
   it, and note that it is now enforced rather than incidental.
4. Reconcile the README. If the stack is dropped, remove Quick Start step 3 rather than
   leaving an instruction that fails before step 4 is reached.
5. Have CI build the image and run one smoke check. An image nothing builds is how this
   drifted; `/qhrol-pin-runtime` adds the workflow, so add a `docker` job to it.

## Acceptance

- `docker compose config` validates and every bind-mounted path exists.
- `docker build -t qhrol .` succeeds from a clean checkout.
- The container's default command either completes successfully as a job or serves
  something; it does not restart-loop.
- README Quick Start runs top to bottom without a dead step.

## Ordering

After `/qhrol-pin-runtime` and `/qhrol-true-claims` — both rewrite the dependency manifest
this image installs from.

## Commit convention

Imperative, in the existing style — e.g. "Drop the monitoring stack with nothing to
scrape". **No `Co-Authored-By` or `Claude-Session` trailers.**
