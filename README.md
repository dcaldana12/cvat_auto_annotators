# CVAT Auto Annotators

[![CI](https://github.com/dcaldana12/cvat_auto_annotators/actions/workflows/ci.yml/badge.svg)](https://github.com/dcaldana12/cvat_auto_annotators/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![CVAT](https://img.shields.io/badge/CVAT-2.81-informational.svg)](https://github.com/cvat-ai/cvat)
[![Nuclio](https://img.shields.io/badge/Nuclio-1.16-informational.svg)](https://nuclio.io/)

A collection of [Nuclio](https://nuclio.io/) serverless functions that add automatic annotation models to [CVAT](https://github.com/cvat-ai/cvat). It includes [Ultralytics YOLO](https://docs.ultralytics.com/) detectors and an LLM/VLM detector that works with any OpenAI-compatible vision API. All functions can be selected from CVAT's **Automatic annotation** dialog.

This is a community project, not an official CVAT, Nuclio, or Ultralytics integration. It assumes CVAT is already installed and running. If not, follow the [official installation guide](https://docs.cvat.ai/docs/administration/basics/installation/) first. Release history is tracked in [CHANGELOG.md](./CHANGELOG.md).

## Contents

- [Available functions](#available-functions)
- [Project structure](#project-structure)
- [How it works](#how-it-works)
- [Prerequisites](#prerequisites)
- [1. Start CVAT with serverless support](#1-start-cvat-with-serverless-support)
- [2. Expose the Nuclio dashboard](#2-expose-the-nuclio-dashboard-on-localhost8070-optional)
- [3. Install `nuctl`](#3-install-nuctl)
- [4. Deploy a function](#4-deploy-a-function)
- [5. Run automatic annotation](#5-run-automatic-annotation-in-cvat)
- [Managing functions](#managing-functions)
- [Development and validation](#development-and-validation)
- [Important note on memory usage](#important-note-on-memory-usage)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Security](#security)
- [Acknowledgements](#acknowledgements)
- [License and third-party components](#license)
- [Changelog](./CHANGELOG.md)

## Available functions

| Function | Directory | Output | Description |
| --- | --- | --- | --- |
| **YOLO OBB** | [`ultralytics/yolo_obb`](./ultralytics/yolo_obb) | Rotated rectangles | Oriented bounding boxes (OBB) for rotated objects. |
| **YOLO Detect** | [`ultralytics/yolo_detect`](./ultralytics/yolo_detect) | Axis-aligned rectangles | Standard object detection with axis-aligned boxes. |
| **VLM Detector (LLM)** | [`llm/vlm_detector`](./llm/vlm_detector) | Axis-aligned rectangles | Prompts an OpenAI-compatible vision-language model. Works with OpenAI, vLLM, Ollama, LM Studio and similar endpoints. |

Each function contains a `nuclio` directory with its configuration and handler:

```text
<family>/<function>/
└── nuclio/
    ├── function.yaml   # Nuclio config, model classes and deployment settings
    └── main.py         # Inference handler
```

The VLM detector also ships a `deploy.sh` wrapper and a `config.env.example` file for local settings.

## Project structure

```text
.
├── .editorconfig
├── .github/
│   ├── ISSUE_TEMPLATE/          # Bug and feature request forms
│   ├── pull_request_template.md
│   └── workflows/ci.yml         # Manifest, documentation, and syntax checks
├── llm/
│   └── vlm_detector/
│       ├── config.env.example   # VLM endpoint, model, labels, and request settings
│       ├── deploy.sh            # Loads config.env and deploys with nuctl
│       └── nuclio/
│           ├── function.yaml
│           └── main.py
├── scripts/
│   └── validate_repo.py         # Local and CI validation
├── ultralytics/
│   ├── yolo_detect/nuclio/
│   └── yolo_obb/nuclio/
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── SECURITY.md
├── requirements-dev.txt
└── docker-compose.serverless.override.yml
```

The checked-in VLM label list contains the 80 COCO classes plus `hand` and `finger` as an example. Replace `metadata.annotations.spec` in [`llm/vlm_detector/nuclio/function.yaml`](./llm/vlm_detector/nuclio/function.yaml) with the labels for your task.

## How it works

CVAT talks to Nuclio through its serverless integration. When you launch automatic annotation, CVAT sends the image to the deployed function, and the function returns a JSON list of detections that CVAT converts into shapes.

```text
CVAT UI ──▶ CVAT server ──▶ Nuclio function ──▶ YOLO model
                                   │
                                   └── detections (JSON) ──▶ CVAT shapes
```

The VLM detector follows the same flow, but the Nuclio function calls the configured vision API instead of loading a local model.

The setup is based on the official CVAT documentation:

- [Deploy CVAT's auto-annotation tool](https://docs.cvat.ai/docs/administration/advanced/installation_automatic_annotation/)
- [Creating your auto-annotation function](https://docs.cvat.ai/docs/manual/advanced/serverless-tutorial/)
- [Using automatic annotation](https://docs.cvat.ai/docs/manual/advanced/automatic-annotation/)

## Prerequisites

- A working CVAT installation (Docker Compose deployment).
- Docker and Docker Compose.
- Administrative access to the machine running CVAT.
- Internet access for the first function build (dependencies and, by default, model weights are downloaded).
- For the VLM detector: an OpenAI-compatible vision endpoint, plus an API key if the endpoint requires authentication. The endpoint can be local if you do not want images to leave your infrastructure.

### Compatibility

| Component | Tested with |
| --- | --- |
| CVAT | `cvat/server:v2.81.0` |
| Nuclio dashboard | `1.16.3-amd64` |
| `nuctl` | `1.16.3` |
| Function runtime | Python 3.12 |
| Docker Compose | Compose v2 |

Other recent versions may work, but `nuctl` must match the Nuclio dashboard version used by CVAT.

## 1. Start CVAT with serverless support

From the root of your **CVAT** checkout, start CVAT together with the serverless component:

```bash
docker compose \
  -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  up -d
```

If CVAT is already running, you can stop it first with the same file list:

```bash
docker compose \
  -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  down
```

The serverless compose file starts Nuclio and enables `CVAT_SERVERLESS=1` on the CVAT server and annotation worker.

## 2. Expose the Nuclio dashboard on localhost:8070 (optional)

By default, CVAT's `components/serverless/docker-compose.serverless.yml` does **not** publish the Nuclio dashboard port. This repository provides [`docker-compose.serverless.override.yml`](./docker-compose.serverless.override.yml) to expose it:

```yaml
services:
  nuclio:
    ports:
      - '127.0.0.1:8070:8070'
```

The dashboard is bound to `127.0.0.1` on purpose: it can deploy and execute arbitrary containers and has access to the Docker socket, so it should not be reachable from the network.

### Apply the override

Copy `docker-compose.serverless.override.yml` to the root of your CVAT checkout (or reference it by path), then pass it **after** the other compose files so it can override the Nuclio service:

```bash
# from the root of your CVAT checkout
docker compose \
  -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.serverless.override.yml \
  up -d
```

Docker Compose recreates the `nuclio` container with the published port. Open <http://localhost:8070> to access the dashboard.

To stop everything, use the same file list:

```bash
docker compose \
  -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.serverless.override.yml \
  down
```

> **Note:** If the override file lives outside the CVAT directory, replace `docker-compose.serverless.override.yml` with its full path, e.g. `-f /path/to/docker-compose.serverless.override.yml`.
>
> If port `8070` is already in use, change the host side of the mapping (for example `127.0.0.1:8071:8070`).

## 3. Install `nuctl`

`nuctl` is the Nuclio command-line tool used to build and deploy functions on the local platform. Its version **must match** the Nuclio dashboard version used by CVAT. Check it with:

```bash
grep 'nuclio/dashboard' components/serverless/docker-compose.serverless.yml
```

For example, if the image is `quay.io/nuclio/dashboard:1.16.3-amd64`, install Nuclio `1.16.3`:

```bash
wget https://github.com/nuclio/nuclio/releases/download/1.16.3/nuctl-1.16.3-linux-amd64
sudo chmod +x nuctl-1.16.3-linux-amd64
sudo ln -sf "$(pwd)/nuctl-1.16.3-linux-amd64" /usr/local/bin/nuctl
```

Verify the installation:

```bash
nuctl version
```

## 4. Deploy a function

Copy the `ultralytics` folder from this repository into the CVAT serverless directory:

```text
<cvat-root>/serverless/pytorch/ultralytics/
├── yolo_obb/
│   └── nuclio/
└── yolo_detect/
    └── nuclio/
```

From the CVAT root, deploy one function (for example YOLO OBB) with the provided deploy script:

```bash
./serverless/deploy_cpu.sh serverless/pytorch/ultralytics/yolo_obb/
```

To deploy both functions:

```bash
./serverless/deploy_cpu.sh serverless/pytorch/ultralytics/
```

The script builds the function image, creates the `cvat` project if needed, deploys the function, and prints the list of deployed functions. The first deployment can take several minutes.

If `nuctl` reports a permission error when talking to Docker, run the script with `sudo`, or add your user to the `docker` group.

### Use a custom model

By default, the YOLO Detect function loads `yolo26n.pt`, while the YOLO OBB function loads `yolo26n-obb.pt`. Ultralytics downloads the weights automatically on first use. To use your own weights:

1. Put the model file (for example `best.pt`) next to `main.py` in the function's `nuclio` directory.
2. Update `model_path` in [`main.py`](./ultralytics/yolo_obb/nuclio/main.py) (or the corresponding `yolo_detect` file):

   ```python
   model_path = "best.pt"
   ```

   Use an **OBB-trained checkpoint** for the YOLO OBB function and keep `task="obb"` there. The YOLO Detect function uses `task="detect"`.

3. Update the classes in `metadata.annotations.spec` in [`function.yaml`](./ultralytics/yolo_obb/nuclio/function.yaml). The class order **must** match the model's output order:

   ```yaml
   metadata:
     annotations:
       spec: |
         [
           { "id": 0, "name": "my_class_0", "type": "rectangle" },
           { "id": 1, "name": "my_class_1", "type": "rectangle" }
         ]
   ```

4. Redeploy the function with the same command used above.

The detection confidence threshold is set to `0.5` in `main.py` (`threshold = 0.5`). Adjust it there if needed.

### Deploy from outside the CVAT tree

The deploy script accepts any path containing one or more `function.yaml` files, so you can also deploy directly from a clone of this repository:

```bash
cd <cvat-root>
./serverless/deploy_cpu.sh /path/to/cvat_auto_annotators/ultralytics/yolo_obb/
```

### LLM/VLM detector (OpenAI-compatible)

[`llm/vlm_detector`](./llm/vlm_detector) sends each CVAT frame to an OpenAI-compatible vision API and converts the returned boxes into CVAT rectangles. It works with cloud providers and with local OpenAI-compatible servers.

Copy the `llm` folder into `<cvat-root>/serverless/pytorch/` as with the YOLO functions, then create a local config file and use the included deploy wrapper. `serverless/deploy_cpu.sh` does not forward environment variables, so the wrapper reads `config.env` and passes the settings to `nuctl`:

```bash
cd <cvat-root>/serverless/pytorch/llm/vlm_detector
cp config.env.example config.env
# edit config.env: set LLM_API_KEY, LLM_MODEL, etc.
./deploy.sh
```

You can also deploy directly from a clone of this repository:

```bash
cd /path/to/cvat_auto_annotators/llm/vlm_detector
cp config.env.example config.env
# edit config.env
./deploy.sh
```

`config.env` is ignored by git, so it is safe to keep local API keys there. `deploy.sh` loads it automatically. To use a config file with a different name or location, pass it explicitly:

```bash
LLM_CONFIG=/path/to/my-vlm.env ./deploy.sh
```

Exported variables still work when no config file is present. If a config file is loaded, its values take precedence over exported variables.

`deploy.sh` defaults to the `cvat_cvat` Docker network. Override it with `CVAT_NETWORK` in the config file or the shell if your CVAT project uses a different name.

#### Configuration file

Copy [`config.env.example`](./llm/vlm_detector/config.env.example) to `config.env` and edit the values. The most important ones are:

```bash
LLM_BASE_URL="https://api.openai.com/v1"
LLM_MODEL="gpt-4o-mini"
LLM_API_KEY="sk-..."
LLM_LABELS=""
```

The full example file documents every supported setting. Re-run `deploy.sh` after changing `config.env`; the function receives the settings at deployment time.

#### Settings reference

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_API_KEY` / `OPENAI_API_KEY` | `not-needed` | API key for the endpoint. |
| `LLM_BASE_URL` | OpenAI default | OpenAI-compatible base URL, including `/v1`. Bare values such as `127.0.0.1:11434` are normalized to `http://127.0.0.1:11434/v1`. |
| `LLM_MODEL` | `gpt-4o-mini` | Model name understood by the endpoint. |
| `LLM_PROMPT` | built-in prompt | Detection prompt. `{labels}` is replaced with the allowed labels. |
| `LLM_LABELS` | labels from `function.yaml` | Comma-separated label allow-list. Overrides the spec list. |
| `LLM_COORDINATES` | `auto` | `auto`, `normalized`, `normalized_1000` or `pixels`. |
| `LLM_BOX_FORMAT` | `xyxy` | `xyxy` or `xywh`. |
| `LLM_THRESHOLD` | `0.5` | Fallback threshold when CVAT does not send one. |
| `LLM_TIMEOUT` | `100` | API request timeout in seconds. |
| `LLM_MAX_RETRIES` | `0` | Retries performed by the OpenAI client. |
| `LLM_MAX_TOKENS` | unset | Optional response token limit. |
| `LLM_TEMPERATURE` | unset | Optional sampling temperature. |
| `LLM_MAX_DETECTIONS` | `100` | Maximum number of shapes returned per frame. |
| `LLM_JPEG_QUALITY` | `90` | JPEG quality used when re-encoding the frame. |
| `LLM_IMAGE_DETAIL` | unset | OpenAI image detail level (`low`, `high`, `auto`). |
| `LLM_EXTRA_HEADERS` | unset | JSON object with extra HTTP headers. |

The handler reads the label names from `metadata.annotations.spec` in [`function.yaml`](./llm/vlm_detector/nuclio/function.yaml) and adds them to the prompt. To annotate custom classes, edit that list and redeploy; returned labels are matched case-insensitively and labels that are not in the list are dropped. `LLM_LABELS` overrides the list used by the handler at deploy time, but a label must still be declared in `spec` for CVAT to keep the shape.

On the local Nuclio platform, values passed with `--env` are stored in the container configuration and can be read with `docker inspect`. Use a local endpoint or a secret manager if the API key must not be exposed to other users on the host.

#### Using a local model

Point `LLM_BASE_URL` at a reachable OpenAI-compatible server. Inside the Nuclio container, `localhost` refers to the container itself, not your host. For a server on another machine, use its LAN address:

```bash
LLM_BASE_URL="http://192.168.1.10:8000/v1"
LLM_MODEL="Qwen/Qwen2.5-VL-7B-Instruct"
# LLM_API_KEY="not-needed"   # only if the server requires a key
```

Then deploy:

```bash
./llm/vlm_detector/deploy.sh
```

##### Local Ollama on the Docker host

Ollama listens on `127.0.0.1:11434` by default. A Nuclio container cannot reach that address, so make Ollama listen on an address reachable from Docker and use the CVAT Docker bridge gateway.

1. Allow Ollama to listen on all interfaces with a systemd override:

   ```bash
   sudo systemctl edit ollama
   ```

   Add:

   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```

   Then apply it:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ss -ltn | grep 11434
   ```

   The port should now be bound to `0.0.0.0:11434` (or `*:11434`). Binding to all interfaces exposes Ollama to your network; restrict port `11434` with a firewall if the machine is not on a trusted network.

2. Find the gateway of the CVAT Docker network:

   ```bash
   docker network inspect cvat_cvat \
     --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
   ```

3. Set the endpoint in `config.env`:

   ```bash
   LLM_BASE_URL="http://172.18.0.1:11434/v1"
   LLM_MODEL="qwen2.5vl:7b"   # use a vision model from `ollama list`
   LLM_API_KEY="not-needed"
   LLM_COORDINATES="auto"      # use normalized_1000 if the model returns 0-1000 boxes
   ```

4. Check connectivity from the function container before retrying CVAT:

   ```bash
   docker exec nuclio-nuclio-vlm_detector \
     curl -sS http://172.18.0.1:11434/api/tags
   ```

5. Redeploy so the new environment variables reach the function:

   ```bash
   ./llm/vlm_detector/deploy.sh
   ```

If the gateway address changes after recreating the Docker network, update `LLM_BASE_URL` and redeploy. You can also run Ollama itself as a container attached to `cvat_cvat`; in that case use its container name or service name as the host.

#### Limitations

- VLMs are usually less precise than dedicated detectors. Treat the output as pre-annotation and review it.
- CVAT does not pass a free-text prompt to detector functions, so the prompt is fixed per deployed function. Deploy separate copies with different `metadata.name` values if you need different prompts.
- Auto-annotation calls the endpoint once per frame, so cost and latency scale with the number of frames.
- Frames are sent to the configured endpoint. Use a local endpoint if the images are sensitive.
- The default `eventTimeout` is 120 s, matching CVAT's default `CVAT_NUCLIO_DEFAULT_TIMEOUT`. For slower models, increase both.
- The prompt asks for normalized `[x1, y1, x2, y2]` boxes. If a provider returns 0–1000 coordinates, set `LLM_COORDINATES=normalized_1000`.

## 5. Run automatic annotation in CVAT

1. Open a CVAT task or job.
2. Select **Automatic annotation** from the menu.
3. Pick the deployed model (for example `YOLO OBB`, `YOLO DETECT`, or `VLM Detector (LLM)`).
4. Choose whether to use the model's labels or map them to existing labels.
5. Run the annotation and review the generated shapes.

## Managing functions

### Nuclio dashboard

With the override applied, open <http://localhost:8070>. Select the `cvat` project to see all deployed functions. From there you can inspect logs, redeploy, or delete functions.

### `nuctl` commands

```bash
# List deployed functions
nuctl get function --platform local

# Delete a function by name
nuctl delete function yolo_obb --platform local
```

Deployed functions are listed by their `metadata.name` (`yolo_obb`, `yolo_detect`, and `vlm_detector`).

## Development and validation

The repository includes the same validation that runs in GitHub Actions:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

python scripts/validate_repo.py
bash -n llm/vlm_detector/deploy.sh
python -m compileall -q ultralytics llm
```

`scripts/validate_repo.py` checks every `function.yaml` for valid YAML, a detector type, unique label IDs and names, a `main:handler` entry point, and a sibling `main.py`. It also checks relative README links and ensures no local `config.env` is tracked.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the development workflow, function contract, testing checklist, and pull request guidelines.

## Important note on memory usage

Deployed Nuclio functions keep a model loaded in memory and can consume a significant amount of RAM. Monitor memory usage, especially on machines that also run the rest of CVAT.

The VLM detector does not load a model into the Nuclio container; the model runs at the configured API endpoint. Its memory footprint is therefore much smaller, but it adds network latency and per-frame API cost.

If the system becomes unresponsive:

1. Open <http://localhost:8070> (requires the override file) or use `nuctl`.
2. Delete the functions that are not currently needed.
3. Redeploy them later with `./serverless/deploy_cpu.sh` (or `llm/vlm_detector/deploy.sh` for the VLM detector).

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `http://localhost:8070` is unreachable | Make sure the override file is passed **last** with `-f`, then run `docker compose ... up -d` again to recreate the `nuclio` container. Check with `docker compose ps`. |
| `nuctl` cannot connect to Docker or permission denied | Run the deploy script with `sudo`, or add your user to the `docker` group and log in again. |
| `nuctl` version mismatch errors | Install the `nuctl` version matching the `nuclio/dashboard` image in `components/serverless/docker-compose.serverless.yml`. |
| Function not listed in CVAT | Confirm CVAT was started with `components/serverless/docker-compose.serverless.yml` and that `CVAT_SERVERLESS=1` is set. Check the function logs in the Nuclio dashboard. |
| Build fails on first deploy | Check internet access from the machine; the image build installs Python dependencies, and the YOLO functions download weights on first use. |
| Image too large / request rejected | Nuclio's HTTP trigger is limited to 32 MB per request in `function.yaml` (`maxRequestBodySize`). |
| VLM function returns `401`/`403` | Check `LLM_API_KEY` and `LLM_BASE_URL`, then redeploy with the key set in `config.env`. |
| `Request URL is missing an 'http://' or 'https://' protocol` | Add the scheme to `LLM_BASE_URL` (for example `http://172.18.0.1:11434/v1`) and redeploy. Bare values are normalized by the handler, but redeploy is required to pick up the new code. |
| VLM function returns `500` with a connection error | The endpoint is unreachable from the Nuclio container. `localhost`/`127.0.0.1` points inside the container. Use a LAN address or the Docker bridge gateway; see [Local Ollama on the Docker host](#local-ollama-on-the-docker-host). |
| Ollama is reachable on the host but not from the container | Check that Ollama listens on `0.0.0.0:11434` (`ss -ltn | grep 11434`), then test from the container with `docker exec nuclio-nuclio-vlm_detector curl -sS http://<gateway>:11434/api/tags`. |
| VLM function times out | Increase `eventTimeout` in `llm/vlm_detector/nuclio/function.yaml` and `CVAT_NUCLIO_DEFAULT_TIMEOUT`; use a faster model or lower `LLM_IMAGE_DETAIL`. |
| VLM returns no shapes | Check the labels in `function.yaml`/`LLM_LABELS`, lower the threshold, and inspect the Nuclio logs for unparsable output. |
| `Could not parse the VLM response` in the logs | The model did not return valid JSON. Use a model with vision/JSON support or provide a stricter `LLM_PROMPT`. |

## Contributing

Contributions are welcome. Bug reports, documentation fixes, new detector functions, and deployment improvements are all useful.

- Read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening a pull request.
- Use the [issue templates](./.github/ISSUE_TEMPLATE/) for bug reports and feature requests.
- Run the validation commands in [Development and validation](#development-and-validation) before submitting.
- Never commit API keys, local `config.env` files, private images, or model weights.

By participating, you agree to follow the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Security

Please do not report security vulnerabilities in a public issue. See [SECURITY.md](./SECURITY.md) for the private reporting process and deployment hardening guidance.

The most important deployment rules are:

- Keep the Nuclio dashboard bound to `127.0.0.1`.
- Do not expose Ollama, vLLM, LM Studio, or other model servers without authentication and firewall rules.
- Treat VLM images as sensitive data. They are sent to the endpoint in `LLM_BASE_URL`.
- Treat deployed environment variables as visible to other users who can inspect Docker containers on the host.

## Acknowledgements

This project builds on the work of the [CVAT](https://github.com/cvat-ai/cvat), [Nuclio](https://nuclio.io/), and [Ultralytics](https://github.com/ultralytics/ultralytics) teams. It is not affiliated with or endorsed by those projects.

## License

This repository is released under the [MIT License](./LICENSE).

### Third-party components

The MIT license applies to the code in this repository. It does not override the licenses of the software, model weights, or services it uses:

- [CVAT](https://github.com/cvat-ai/cvat) is MIT-licensed.
- [Nuclio](https://github.com/nuclio/nuclio) is Apache-2.0-licensed.
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) is available under AGPL-3.0 or a separate commercial license. Review the Ultralytics licensing terms before using this repository in a commercial or closed-source deployment.
- Model weights, OpenAI-compatible APIs, and local model servers have their own licenses and terms of service.

This repository does not bundle model weights. The YOLO functions download weights at runtime, and the VLM detector calls the endpoint you configure.
