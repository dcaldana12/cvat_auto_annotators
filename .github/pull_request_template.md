## Summary

Describe the change and the problem it solves.

## Type of change

- [ ] Bug fix
- [ ] New detector or function
- [ ] Deployment or configuration change
- [ ] Documentation
- [ ] Validation, CI, or refactor
- [ ] Breaking change

## Related issues

Closes #

## Testing

Describe how you tested the change. If applicable, include the CVAT/Nuclio versions and a sample of the function logs.

- [ ] `python scripts/validate_repo.py`
- [ ] `bash -n llm/vlm_detector/deploy.sh` (if shell scripts changed)
- [ ] `python -m compileall -q ultralytics llm`
- [ ] Deployed the affected function and ran automatic annotation in CVAT
- [ ] Verified at least one real image produces valid shapes

## Documentation

- [ ] Updated `README.md` for user-visible behavior or setup changes
- [ ] Updated `CHANGELOG.md`
- [ ] Updated `config.env.example` for new VLM settings
- [ ] Added or updated comments/docstrings for non-obvious behavior

## Checklist

- [ ] The change is focused and does not include unrelated refactors.
- [ ] No API keys, tokens, private data, model weights, or local config files are committed.
- [ ] New labels are declared in `function.yaml` with unique IDs and names.
- [ ] The function still returns a valid CVAT detection response.
- [ ] I have read the [contributing guide](../CONTRIBUTING.md).
