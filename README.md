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
| SBOM generation | [Syft](https://github.com/anchore/syft) | Inventory of every package shipped in the image | 🔜 Planned |

## Repository layout

```
.github/workflows/semgrep.yml   # SAST gate on pull requests to main
.github/workflows/gitleaks.yml  # Secret scanning gate on pull requests to main
.github/workflows/trivy.yml     # Container scanning gate on pull requests to main
demo-app/                       # Intentionally vulnerable Flask app (scan target)
    app.py
    requirements.txt
    Dockerfile
```

## The demo app (intentionally vulnerable)

> ⚠️ `demo-app/` is deliberately insecure. Do not deploy it. The secret in it is fake.

| ID | Flaw | Location | Expected to be caught by |
|----|------|----------|--------------------------|
| VULN-1 | SQL injection (f-string query) | `demo-app/app.py` | Semgrep |
| VULN-2 | Hardcoded secret (fake API key) | `demo-app/app.py` | Gitleaks |
| VULN-3 | Outdated dependency: `requests==2.19.1` (CVE-2018-18074) | `demo-app/requirements.txt` | Trivy |

Run it locally:

```bash
cd demo-app
pip install -r requirements.txt
flask --app app run
# http://127.0.0.1:5000/user?name=alice
```

Or with Docker:

```bash
docker build -t secure-flow-demo demo-app
docker run --rm -p 5000:5000 secure-flow-demo
```

## Merge gate

`main` is protected by a branch protection rule. Changes reach `main` only through pull requests, and these checks must pass before a pull request can be merged:

| Required check | Workflow | Fails when |
|----------------|----------|------------|
| **Semgrep scan** | `semgrep.yml` | Semgrep reports any finding in the code |
| **Gitleaks scan** | `gitleaks.yml` | Gitleaks finds a secret in any commit the pull request adds |
| **Trivy scan** | `trivy.yml` | The built `demo-app` image has a HIGH or CRITICAL CVE with a fix available (passes with a notice if the PR has no `demo-app/Dockerfile`) |

## Roadmap

- [x] Phase 1: Demo app + Semgrep SAST gate
- [x] Phase 2: Gitleaks secret scanning
- [x] Phase 3: Trivy container scanning
- [ ] Phase 4: Syft SBOM generation
