# cvat_auto_annotators

A collection of [Nuclio](https://nuclio.io/) serverless functions that add automatic annotation models to [CVAT](https://github.com/cvat-ai/cvat). The functions are built on [Ultralytics YOLO](https://docs.ultralytics.com/) and can be selected from CVAT's **Automatic annotation** dialog.

This repository assumes CVAT is already installed and running. If not, follow the [official installation guide](https://docs.cvat.ai/docs/administration/basics/installation/) first.

## Available functions

| Function | Directory | Output | Description |
| --- | --- | --- | --- |
| **YOLO OBB** | [`ultralytics/yolo_obb`](./ultralytics/yolo_obb) | Rotated rectangles | Oriented bounding boxes (OBB) for rotated objects. |
| **YOLO Detect** | [`ultralytics/yolo_detect`](./ultralytics/yolo_detect) | Axis-aligned rectangles | Standard object detection with axis-aligned boxes. |

Each function contains:

```
ultralytics/<function>/
└── nuclio/
    ├── function.yaml   # Nuclio config, model classes and deployment settings
    └── main.py         # Inference handler
```

## How it works

CVAT talks to Nuclio through its serverless integration. When you launch automatic annotation, CVAT sends the image to the deployed function, and the function returns a JSON list of detections that CVAT converts into shapes.

```text
CVAT UI ──▶ CVAT server ──▶ Nuclio function ──▶ YOLO model
                                   │
                                   └── detections (JSON) ──▶ CVAT shapes
```

The setup is based on the official CVAT documentation:

- [Deploy CVAT's auto-annotation tool](https://docs.cvat.ai/docs/administration/advanced/installation_automatic_annotation/)
- [Creating your auto-annotation function](https://docs.cvat.ai/docs/manual/advanced/serverless-tutorial/)
- [Using automatic annotation](https://docs.cvat.ai/docs/manual/advanced/automatic-annotation/)

## Prerequisites

- A working CVAT installation (Docker Compose deployment).
- Docker and Docker Compose.
- Administrative access to the machine running CVAT.
- Internet access for the first function build (dependencies and, by default, model weights are downloaded).

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

## 5. Run automatic annotation in CVAT

1. Open a CVAT task or job.
2. Select **Automatic annotation** from the menu.
3. Pick the deployed model (for example `YOLO OBB` or `YOLO DETECT`).
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

Deployed functions are listed by their `metadata.name` (`yolo_obb` and `yolo_detect`).

## Important note on memory usage

Deployed Nuclio functions keep a model loaded in memory and can consume a significant amount of RAM. Monitor memory usage, especially on machines that also run the rest of CVAT.

If the system becomes unresponsive:

1. Open <http://localhost:8070> (requires the override file) or use `nuctl`.
2. Delete the functions that are not currently needed.
3. Redeploy them later with `./serverless/deploy_cpu.sh`.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `http://localhost:8070` is unreachable | Make sure the override file is passed **last** with `-f`, then run `docker compose ... up -d` again to recreate the `nuclio` container. Check with `docker compose ps`. |
| `nuctl` cannot connect to Docker or permission denied | Run the deploy script with `sudo`, or add your user to the `docker` group and log in again. |
| `nuctl` version mismatch errors | Install the `nuctl` version matching the `nuclio/dashboard` image in `components/serverless/docker-compose.serverless.yml`. |
| Function not listed in CVAT | Confirm CVAT was started with `components/serverless/docker-compose.serverless.yml` and that `CVAT_SERVERLESS=1` is set. Check the function logs in the Nuclio dashboard. |
| Build fails on first deploy | Check internet access from the machine; the image build installs `ultralytics` and downloads the model on first use. |
| Image too large / request rejected | Nuclio's HTTP trigger is limited to 32 MB per request in `function.yaml` (`maxRequestBodySize`). |

## License

See [LICENSE](./LICENSE).
