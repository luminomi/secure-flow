# Secure Flow

Secure Flow is a CI/CD security gate built on GitHub Actions. Every pull request to `main` is checked for insecure code, leaked secrets, and vulnerable dependencies or container images, and the pull request cannot be merged until those checks pass. Think of airport security: every bag is screened before it boards, and a bag that fails screening stays on the ground no matter who is carrying it.

## Pipeline overview

| Tool | What it checks | Type | Required check name | Fails the PR? |
|------|----------------|------|---------------------|---------------|
| [Semgrep](https://semgrep.dev) | Source code for insecure patterns, e.g. SQL built from user input | SAST | `Semgrep scan` | Yes, on any finding |
| [Gitleaks](https://github.com/gitleaks/gitleaks) | Every commit the PR adds, for hardcoded secrets | Secrets | `Gitleaks scan` | Yes, on any finding |
| [Trivy](https://trivy.dev) | The built `demo-app` container image: OS packages and Python dependencies, for known CVEs | SCA | `Trivy scan` | Yes, on HIGH or CRITICAL CVEs that have a fix available |
| [Syft](https://github.com/anchore/syft) | The built `demo-app` image, to list every package it contains | SBOM | `Syft SBOM` | Only if the SBOM cannot be generated or uploaded |

## Proof: before and after

The same Flask app was sent through the pipeline twice:

- **Before:** [PR #1](https://github.com/luminomi/secure-flow/pull/1), the intentionally vulnerable version. Semgrep scan, Gitleaks scan and Trivy scan fail; Syft SBOM passes. The merge is blocked.
- **After:** [PR #5](https://github.com/luminomi/secure-flow/pull/5), the fixed version. All four checks pass, and it was merged into `main`.

| Planted flaw | Location (PR #1) | Caught by | Fix applied in PR #5 |
|--------------|------------------|-----------|----------------------|
| SQL injection: user input inserted into the SQL text with an f-string | `demo-app/app.py` line 53 | Semgrep scan (rules `tainted-sql-string` and `sql-injection-db-cursor-execute`) | Parameterized query (`WHERE name = ?`), so input is always treated as data |
| Hardcoded secret: a fake API key assigned in the code | `demo-app/app.py` line 21 | Gitleaks scan (rule `generic-api-key`) | Key read from the `PAYMENT_API_KEY` environment variable; the app exits with an error if it is not set. No key-like value in any commit |
| Outdated dependency: `requests` 2.19.1 (CVE-2018-18074), which also pulled in `urllib3` 1.23 (6 CVEs) | `demo-app/requirements.txt` | Trivy scan (7 HIGH findings) | `requests` 2.34.2 and `urllib3` 2.8.0, the lowest `urllib3` version that fixes all six |

**Unplanned finding:** Trivy also flagged a HIGH CVE in the Debian base image: `libpcre2-8-0` 10.46-1~deb13u2 (CVE-2026-103111, fixed in 10.46-1~deb13u3). No `python:3.12-slim` image with the fix had been published yet, so PR #5 upgrades that one package in the Dockerfile with a targeted `apt-get install --only-upgrade`. On PR #5, Trivy reports 0 HIGH or CRITICAL findings.

PR #1 is deliberately left open and unmerged as a frozen "before" snapshot. Because PR #5 added the fixed `demo-app/` to `main`, PR #1 now shows merge conflicts; its failed checks remain visible.

## How the merge gate works

`main` is protected by a branch protection rule:

- Changes reach `main` only through a pull request (0 approvals required, since this is a single-maintainer repo).
- Four status checks must pass: `Semgrep scan`, `Gitleaks scan`, `Trivy scan` and `Syft SBOM`.
- Nobody can bypass the rule, including repository admins. Force pushes and branch deletion are disabled.

Trivy and Syft only have something to scan when the PR contains `demo-app/Dockerfile`. They still run on every pull request: if the Dockerfile is missing, the job prints a visible notice ("nothing to scan") and passes. A `paths:` filter would skip the workflow entirely, and a required check that never reports leaves the pull request stuck as "Expected", waiting for a status that never arrives. The trade-off is that a green Trivy or Syft check can mean "nothing to scan" rather than "scanned and clean", including on a PR that deletes the Dockerfile.

## Design decisions

**Gitleaks scans only the PR's own commits.** It runs with `--log-opts="${BASE_SHA}..${HEAD_SHA}"`, using the base and head commits of the pull request. The first version used `fetch-depth: 0` without a range; Gitleaks then scanned every fetched branch and failed [PR #2](https://github.com/luminomi/secure-flow/pull/2) on PR #1's fake key. The full history is still fetched, because both commits must be present to compute the range.

**Pinned, verified tools.** Gitleaks 8.30.1, Trivy 0.74.0 and Syft 1.51.1 are downloaded as release binaries at fixed versions, and each download is checked against the release's published SHA-256 checksums before it runs. No third-party wrapper actions are used. In `syft.yml`, `actions/checkout` and `actions/upload-artifact` are pinned to full commit SHAs, because a tag can be moved to different code and a commit SHA cannot. A checksum proves the file matches what the release published; it does not prove the release itself is trustworthy, which is why the cooldown below also applies.

**Release cooldown.** New releases are adopted only after they have been out for several weeks, giving the community time to spot a broken or malicious release. Trivy 0.74.0 and Syft 1.51.1 were chosen over newer releases for this reason. The one deliberate exception is `urllib3` 2.8.0, which was only a few weeks old: it is the only version that fixes CVE-2026-97689, and a known HIGH CVE outweighs the unknown risk of a new release.

**The SBOM is an inventory, not a verdict.** Syft never fails because of what is in the image; judging packages is Trivy's job. The job fails only if the SBOM cannot be generated or uploaded, so it is a required check that guards the pipeline itself. The SBOM is written in CycloneDX JSON and uploaded as the workflow artifact `sbom-demo-app-cyclonedx`, kept for 30 days. On PR #1 it lists `requests` 2.19.1 and `urllib3` 1.23; on PR #5, `requests` 2.34.2 and `urllib3` 2.8.0.

**Semgrep rulesets.** Semgrep runs with `p/python` (general Python security rules), `p/flask` (Flask-specific rules, such as request data reaching SQL) and `p/secrets` (known credential formats), and `--error` makes any finding fail the check. The registry rulesets need no Semgrep account or token. On PR #1, `p/secrets` did not flag the fake key, which uses a generic format; Gitleaks did. This is one reason for having a dedicated secret scanner.

## Known limitations and next steps

- `semgrep.yml`, `gitleaks.yml` and `trivy.yml` reference `actions/checkout@v5` by tag, not by commit SHA, and `semgrep.yml` uses the `semgrep/semgrep` container image without a version tag. All four workflows use `runs-on: ubuntu-latest`. A hardening PR is planned to pin these.
- The `python:3.12-slim` base image is referenced by tag, not by digest.
- The `libpcre2-8-0` upgrade in the Dockerfile is temporary and should be removed once the upstream `python:3.12-slim` image includes the fix.
- There is no DAST or runtime scanning; all checks are static and run before merge.

## Repository layout

```
.github/workflows/
    semgrep.yml     # SAST: Semgrep scan
    gitleaks.yml    # Secrets: Gitleaks scan
    trivy.yml       # SCA: Trivy scan of the built image
    syft.yml        # SBOM: Syft SBOM of the built image
demo-app/           # Flask demo app (fixed version; the vulnerable version is in PR #1)
    app.py
    requirements.txt
    Dockerfile
.gitignore
LICENSE
README.md
```

## Run the demo app locally

The app needs a `PAYMENT_API_KEY` environment variable and exits with an error if it is not set. Any test value works. The commands below prompt for it, so the value never appears in your files or shell history.

With Python (bash):

```bash
cd demo-app
pip install -r requirements.txt
read -rsp "PAYMENT_API_KEY: " PAYMENT_API_KEY && export PAYMENT_API_KEY
flask --app app run
```

With Python (PowerShell):

```powershell
cd demo-app
pip install -r requirements.txt
$env:PAYMENT_API_KEY = Read-Host "PAYMENT_API_KEY"
flask --app app run
```

Then open `http://127.0.0.1:5000/user?name=alice`.

With Docker, after setting `PAYMENT_API_KEY` in your shell as above (`-e PAYMENT_API_KEY` with no value copies it from your shell into the container):

```bash
docker build -t secure-flow-demo demo-app
docker run --rm -p 5000:5000 -e PAYMENT_API_KEY secure-flow-demo
```

## Security note

The demo app was intentionally vulnerable on the `add-vulnerable-demo-app` branch (PR #1): it contained a SQL injection, a hardcoded API key and outdated dependencies with known CVEs. The key was fake and grants access to nothing. The demo app exists only to exercise the pipeline. Do not deploy it, in either version.
