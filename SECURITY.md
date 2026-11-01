# Security Policy

## Supported versions

Security fixes are applied to the latest revision of the default branch. Older commits, forks, and locally modified deployments are not supported.

## Reporting a vulnerability

Please **do not open a public issue** for a security vulnerability.

Use GitHub's private vulnerability reporting:

1. Open the repository's **Security** tab.
2. Select **Report a vulnerability**.
3. Include a clear description, affected files or functions, reproduction steps, and impact.

If private reporting is unavailable, contact the maintainer through the contact method listed on their GitHub profile and ask for a private channel. Do not publish exploit details before a fix is available.

This is a community project maintained on a best-effort basis. There is no guaranteed response time or SLA.

## Scope

Reports are welcome for issues such as:

- Command injection or path traversal in deploy scripts.
- Secret leakage in logs, examples, container configuration, or documentation.
- Unsafe handling of uploaded images or untrusted model/API responses.
- Unexpected network exposure caused by the provided deployment examples.
- Dependency or build configuration problems that create a security risk.

The following are generally out of scope:

- Vulnerabilities in CVAT, Nuclio, Docker, Ultralytics, or third-party APIs.
- Incorrect or low-quality model predictions.
- Problems caused by exposing internal services to the public internet against the documentation's guidance.
- Issues that require an already-compromised host or Docker daemon.

## Deployment hardening

The examples in this repository are intended for a trusted development or internal environment. Before exposing a deployment to other users:

- Keep the Nuclio dashboard bound to `127.0.0.1`. It can deploy containers and has access to the Docker socket.
- Do not expose Ollama, vLLM, LM Studio, or another model server without authentication and network restrictions.
- Restrict model-server ports with a firewall when binding to `0.0.0.0`.
- Use a reverse proxy with TLS and authentication for any service reachable outside the host.
- Run CVAT and Nuclio with least-privilege Docker access.
- Keep CVAT, Nuclio, Ultralytics, Python dependencies, and model servers up to date.
- Review the licenses and data-handling terms of every model and API provider you use.

## Secrets

- `config.env` is ignored by git, but deployed environment variables can still be visible through `docker inspect` on the local Nuclio platform.
- Prefer a local model endpoint or a dedicated secret manager when API keys must not be visible to other users on the host.
- Never paste real API keys into issues, pull requests, logs, or screenshots.
- Rotate any credential that may have been exposed, even if it was removed from a later commit.

## VLM data handling

The VLM detector sends frames to the endpoint configured in `LLM_BASE_URL`. If that endpoint is a hosted service, images leave your infrastructure and are subject to the provider's retention and privacy policies. Use a local endpoint for sensitive data.

## Third-party components

This repository is not affiliated with CVAT, Nuclio, Ultralytics, OpenAI, Ollama, or any model provider. Report vulnerabilities in those projects to their respective maintainers.
