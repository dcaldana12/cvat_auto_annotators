# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/) for releases.

## [Unreleased]

### Added

- Public contribution, security, and code-of-conduct documentation.
- Issue and pull request templates.
- Repository validation script and CI workflow.
- Project structure, compatibility, and third-party licensing notes in the README.

## [0.1.0] - 2026-11-01

### Added

- YOLO OBB Nuclio function for oriented bounding boxes.
- YOLO Detect Nuclio function for axis-aligned bounding boxes.
- OpenAI-compatible VLM detector with label allow-listing, coordinate normalization, and configurable prompt.
- `deploy.sh` wrapper and `config.env.example` for VLM settings.
- Optional Docker Compose override exposing the Nuclio dashboard on `127.0.0.1:8070`.
- README setup, deployment, local-model, management, and troubleshooting guides.

### Fixed

- VLM endpoint normalization for bare `host:port` values.
- Clearer VLM connection errors and loopback guidance.
- Duplicate label IDs in the VLM label specification.
