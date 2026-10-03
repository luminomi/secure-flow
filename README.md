# Secure Flow

DevSecOps CI/CD security pipeline — SAST, secret scanning, and container scanning gated on pull requests.

## Goal

Every pull request to `main` is scanned automatically by GitHub Actions. If a security check fails, the PR cannot be merged. Security becomes a required gate in the delivery pipeline instead of an afterthought.

## Pipeline stages

| Stage | Tool | What it finds | Status |
|-------|------|---------------|--------|
| SAST (static analysis) | [Semgrep](https://semgrep.dev) | Insecure code patterns, e.g. SQL injection | ✅ Phase 1 |
| Secret scanning | [Gitleaks](https://github.com/gitleaks/gitleaks) | Hardcoded API keys, tokens, passwords (every commit in the PR) | ✅ Phase 2 |
| Container scanning | [Trivy](https://trivy.dev) | Known CVEs in the image and its dependencies | ✅ Phase 3 |
| SBOM generation | [Syft](https://github.com/anchore/syft) | Inventory of every package shipped in the image (CycloneDX JSON, downloadable from each run) | ✅ Phase 4 |

## Repository layout

```
.github/workflows/semgrep.yml   # SAST gate on pull requests to main
.github/workflows/gitleaks.yml  # Secret scanning gate on pull requests to main
.github/workflows/trivy.yml     # Container scanning gate on pull requests to main
.github/workflows/syft.yml      # SBOM generation on pull requests to main
demo-app/                       # Flask demo app, fixed version (scan target; vulnerable version is in PR #1)
    app.py
    requirements.txt
    Dockerfile
```

## Before and after

The same small Flask app, sent through the pipeline twice:

- **Before:** [PR #1](https://github.com/luminomi/secure-flow/pull/1), the intentionally vulnerable version (branch `add-vulnerable-demo-app`). Semgrep, Gitleaks and Trivy all fail, so the merge is blocked. It stays open and unmerged as a demo.
- **After:** [the fix PR](https://github.com/luminomi/secure-flow/pulls?q=is%3Apr+head%3Afix-demo-app) (branch `fix-demo-app`). Every flaw is fixed, all four checks pass, and the merge is allowed. This is the version on `main`.

| ID | Flaw (before) | Fix (after) | Proved by |
|----|---------------|-------------|-----------|
| 1 | SQL injection: user input pasted into the SQL text with an f-string | Parameterized query (`WHERE name = ?`), so input is always treated as data | Semgrep scan |
| 2 | Hardcoded secret: fake API key written in `app.py` | Key read from the `PAYMENT_API_KEY` environment variable; the app refuses to start without it. No key-like value in any commit | Gitleaks scan |
| 3 | Outdated dependencies: `requests` 2.19.1 (CVE-2018-18074) and `urllib3` 1.23 (6 CVEs) | `requests` 2.34.2 and `urllib3` 2.8.0, the lowest version that fixes all six | Trivy scan |
| 4 | Base image: `libpcre2-8-0` 10.46-1~deb13u2 (CVE-2026-103111), found by Trivy, not planted | Dockerfile upgrades that one package to Debian's fixed build. Temporary until the upstream `python:3.12-slim` image includes the fix | Trivy scan |

Syft SBOM passes in both cases: it inventories every build, safe or not.

## Running the demo app

The app needs a `PAYMENT_API_KEY` environment variable and stops with an error if it is not set. Set it in your shell to any test value first; never commit it.

Run it locally:

```bash
cd demo-app
pip install -r requirements.txt
flask --app app run
# http://127.0.0.1:5000/user?name=alice
```

Or with Docker (`-e PAYMENT_API_KEY` with no value copies the variable from your shell into the container):

```bash
docker build -t secure-flow-demo demo-app
docker run --rm -p 5000:5000 -e PAYMENT_API_KEY secure-flow-demo
```

## Merge gate

`main` is protected by a branch protection rule. Changes reach `main` only through pull requests, and these checks must pass before a pull request can be merged:

| Required check | Workflow | Fails when |
|----------------|----------|------------|
| **Semgrep scan** | `semgrep.yml` | Semgrep reports any finding in the code |
| **Gitleaks scan** | `gitleaks.yml` | Gitleaks finds a secret in any commit the pull request adds |
| **Trivy scan** | `trivy.yml` | The built `demo-app` image has a HIGH or CRITICAL CVE with a fix available (passes with a notice if the PR has no `demo-app/Dockerfile`) |
| **Syft SBOM** | `syft.yml` | The SBOM cannot be generated or uploaded. Never fails because of what is in the SBOM (passes with a notice if the PR has no `demo-app/Dockerfile`) |

## Roadmap

- [x] Phase 1: Demo app + Semgrep SAST gate
- [x] Phase 2: Gitleaks secret scanning
- [x] Phase 3: Trivy container scanning
- [x] Phase 4: Syft SBOM generation
