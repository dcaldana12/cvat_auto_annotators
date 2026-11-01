# Contributing to CVAT Auto Annotators

Thanks for your interest in improving this project. Contributions of all sizes are welcome: bug reports, documentation fixes, new serverless functions, and deployment improvements.

Please read this guide before opening an issue or pull request. By participating, you agree to follow the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Ways to contribute

- Report reproducible bugs using the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).
- Request features or new detectors using the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).
- Improve the README, troubleshooting notes, or deployment instructions.
- Add support for another model family, runtime, or OpenAI-compatible provider.
- Submit a pull request with tests, validation, or reproducibility improvements.

For security issues, **do not open a public issue**. Follow [SECURITY.md](./SECURITY.md).

## Before you start

- Search existing issues and pull requests first.
- Open an issue before starting a large change, especially a new function family or a behavior change.
- Keep pull requests focused. Separate unrelated refactors from feature work.
- Never commit API keys, tokens, model weights, private datasets, or `.env`/`config.env` files.

## Development setup

### Requirements

- Docker and Docker Compose.
- A CVAT installation started with serverless support.
- `nuctl` matching the Nuclio version used by CVAT.
- Python 3.12 for local validation.

The full CVAT/Nuclio setup is described in the [README](./README.md#1-start-cvat-with-serverless-support).

### Clone and validate

```bash
git clone https://github.com/dcaldana12/cvat_auto_annotators.git
cd cvat_auto_annotators

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

python scripts/validate_repo.py
bash -n llm/vlm_detector/deploy.sh
python -m compileall -q ultralytics llm
```

The same checks run in GitHub Actions.

## Repository conventions

Each deployable function lives in its own directory:

```text
<family>/<function>/
├── nuclio/
│   ├── function.yaml   # CVAT metadata, labels, build and runtime settings
│   └── main.py         # init_context() and handler()
└── ...                 # optional deploy helper or example config
```

Keep functions self-contained. A function should not depend on files outside its `nuclio` directory unless that dependency is explicitly documented and packaged into the image.

### Function contract

A CVAT detector function must:

1. Define `init_context(context)` to load or configure the model.
2. Define `handler(context, event)` to process one request.
3. Read the base64 image from `event.body["image"]`.
4. Return a `context.Response` containing a JSON list of detections.
5. Use CVAT shape fields such as `label`, `confidence`, `points`, `type`, and `rotation`.
6. Declare every returned label in `metadata.annotations.spec` in `function.yaml`.

For a rectangle detector, the response shape is:

```json
[
  {
    "confidence": "0.95",
    "label": "person",
    "points": [10.0, 20.0, 110.0, 220.0],
    "type": "rectangle",
    "rotation": 0.0
  }
]
```

### `function.yaml` conventions

- Use a unique, lowercase `metadata.name` (for example `yolo_detect`).
- Use `metadata.annotations.type: detector`.
- Keep label IDs and names unique.
- Keep `handler: main:handler`.
- Use a descriptive image name under `cvat/`.
- Document any new environment variables in the README and in the function's example config.
- Avoid embedding secrets in `function.yaml`.

## Adding a new function

1. Create a new directory under an appropriate family, for example:

   ```text
   ultralytics/my_detector/nuclio/
   ```

2. Copy a similar function and update:
   - `metadata.name`
   - `metadata.annotations.name` and `spec`
   - `spec.build.image`
   - the model loading and inference code
   - the README function table

3. Implement or update `init_context()` and `handler()` following the contract above.

4. Deploy and test against a real CVAT instance:

   ```bash
   nuctl deploy \
     --project-name cvat \
     --path <function-dir>/nuclio \
     --file <function-dir>/nuclio/function.yaml \
     --platform local
   ```

   Use `serverless/deploy_cpu.sh` from CVAT when it fits the standard layout. Use a dedicated deploy script when the function requires environment variables, credentials, or a custom network.

5. Document:
   - what the function does
   - required dependencies and model files
   - deployment command
   - configuration variables
   - expected output shape
   - known limitations

6. Run the validation checks and add the function to `README.md`.

## Testing checklist

Before opening a pull request, verify:

- [ ] `python scripts/validate_repo.py` passes.
- [ ] `bash -n llm/vlm_detector/deploy.sh` passes if shell scripts changed.
- [ ] `python -m compileall -q ultralytics llm` passes.
- [ ] The function deploys with the documented command.
- [ ] The function appears in CVAT's **Automatic annotation** dialog.
- [ ] At least one real image produces valid shapes.
- [ ] Missing/invalid input fails clearly rather than hanging.
- [ ] Logs do not contain secrets or full API keys.
- [ ] Documentation and examples are updated.

## Code style

- Python: follow PEP 8 where practical, use four-space indentation, and keep handlers readable.
- Shell: use `#!/usr/bin/env bash` and `set -euo pipefail`.
- YAML: use two-space indentation and keep label specs valid JSON inside the YAML block.
- Prefer clear names over abbreviations.
- Add comments only where behavior is not obvious.
- Keep dependencies minimal and explain new ones in the documentation.

## Commit and pull request guidelines

- Create a topic branch from the current default branch.
- Use descriptive commit messages, for example:
  - `Add YOLO-World detector`
  - `Fix VLM coordinate normalization`
  - `Document local Ollama setup`
- Complete the pull request template.
- Link related issues with `Closes #123` when applicable.
- Update `CHANGELOG.md` for user-visible changes.
- Keep generated files, virtual environments, model weights, and local configs out of commits.

## Secrets and local configuration

Use `llm/vlm_detector/config.env` for local VLM settings. It is ignored by git. Start from `config.env.example`:

```bash
cp llm/vlm_detector/config.env.example llm/vlm_detector/config.env
```

If you accidentally commit a secret, rotate it immediately and remove it from git history. Deleting it in a later commit is not sufficient.

## License

By contributing, you agree that your contributions are licensed under the repository's [MIT License](./LICENSE).
