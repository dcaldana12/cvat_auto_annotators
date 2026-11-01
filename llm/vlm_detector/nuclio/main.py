"""CVAT serverless detector backed by an OpenAI-compatible vision API."""

import base64
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import cv2
import numpy as np
import yaml
from openai import APIConnectionError, OpenAI

DEFAULT_PROMPT = (
    "You are a precise object detection assistant. "
    "Analyze the image and detect every visible object.\n"
    "Return ONLY a JSON array (no markdown fences, no explanation). "
    "Each element must be an object with these keys:\n"
    '- "label": the object class name\n'
    '- "confidence": a number between 0 and 1\n'
    '- "box": [x1, y1, x2, y2] with coordinates normalized to [0, 1] '
    "relative to the image width and height\n"
    "{labels}\n"
    "If no objects are visible, return []."
)


def _split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_base_url(value):
    """Accept bare host:port values and fill in the OpenAI-compatible path."""
    value = value.strip()
    if not value:
        return ""

    if "://" not in value:
        value = "http://" + value

    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            f"Invalid LLM_BASE_URL: {value!r}. "
            "Use a URL such as http://host:11434/v1."
        )

    path = parsed.path.rstrip("/")
    if not path:
        path = "/v1"

    return urlunparse(parsed._replace(path=path)).rstrip("/")


def _redact_url(value):
    """Hide credentials when an endpoint URL is written to the logs."""
    parsed = urlparse(value)
    if parsed.username is None and parsed.password is None:
        return value

    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"

    return urlunparse(parsed._replace(netloc=host))


def _is_loopback_url(value):
    host = (urlparse(value).hostname or "").casefold()
    return host in ("localhost", "127.0.0.1", "::1")


def _load_labels(logger):
    """Use LLM_LABELS when provided, otherwise read the CVAT label spec."""
    env_labels = _split_csv(os.getenv("LLM_LABELS", ""))
    if env_labels:
        logger.info(f"Using {len(env_labels)} labels from LLM_LABELS")
        return env_labels

    config_path = Path(__file__).with_name("function.yaml")
    try:
        with config_path.open(encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}

        spec = config.get("metadata", {}).get("annotations", {}).get("spec", "[]")
        if isinstance(spec, str):
            spec = json.loads(spec)

        labels = [str(item["name"]) for item in spec if item.get("name")]
        if labels:
            logger.info(f"Using {len(labels)} labels from function.yaml")
            return labels
    except Exception as exc:
        logger.warn(f"Could not read labels from function.yaml: {exc}")

    logger.warn("No labels configured; VLM labels will not be restricted")
    return []


def _json_candidates(text):
    text = text.strip()

    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        yield fenced.group(1).strip()

    yield text

    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            yield text[start : end + 1]


def _parse_json_response(text):
    for candidate in _json_candidates(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _extract_items(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("detections", "objects", "annotations", "boxes", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

        if any(key in payload for key in ("box", "bbox", "points")):
            return [payload]

    return []


def _as_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _box_to_xyxy(item, box_format):
    box = item.get("box") or item.get("bbox") or item.get("points")
    if not isinstance(box, (list, tuple)) or len(box) < 4:
        return None

    values = [_as_float(value) for value in box[:4]]
    if any(value is None for value in values):
        return None

    x1, y1, third, fourth = values
    if box_format == "xywh":
        return x1, y1, x1 + third, y1 + fourth

    return x1, y1, third, fourth


def _scale_box(box, width, height, mode):
    x1, y1, x2, y2 = box

    if mode == "pixels":
        return box

    if mode == "normalized":
        return x1 * width, y1 * height, x2 * width, y2 * height

    if mode == "normalized_1000":
        return (
            x1 / 1000.0 * width,
            y1 / 1000.0 * height,
            x2 / 1000.0 * width,
            y2 / 1000.0 * height,
        )

    # auto: [0, 1] coordinates are scaled, everything else is treated as pixels
    if max(abs(x1), abs(y1), abs(x2), abs(y2)) <= 1.0:
        return x1 * width, y1 * height, x2 * width, y2 * height

    return box


def init_context(context):
    context.logger.info("Init VLM detector context")

    labels = _load_labels(context.logger)
    label_instruction = (
        "Use only the following labels, with the exact spelling: " + ", ".join(labels) + "."
        if labels
        else "Use short, common English object class names."
    )

    prompt = os.getenv("LLM_PROMPT", "").strip()
    if prompt:
        prompt = prompt.replace("{labels}", label_instruction)
    else:
        prompt = DEFAULT_PROMPT.replace("{labels}", label_instruction)

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "not-needed"
    if api_key == "not-needed":
        context.logger.warn(
            "LLM_API_KEY/OPENAI_API_KEY is not set; using a placeholder. "
            "Set it when the endpoint requires authentication."
        )

    client_kwargs = {
        "api_key": api_key,
        "timeout": float(os.getenv("LLM_TIMEOUT", "100")),
        "max_retries": int(os.getenv("LLM_MAX_RETRIES", "0")),
    }

    base_url = _normalize_base_url(os.getenv("LLM_BASE_URL", ""))
    if base_url:
        if _is_loopback_url(base_url):
            context.logger.warn(
                "LLM_BASE_URL points to loopback. Inside the Nuclio container, "
                "localhost/127.0.0.1 is the container itself, not the Docker host. "
                "Use an address reachable from the container, such as the Docker "
                "bridge gateway."
            )
        client_kwargs["base_url"] = base_url

    extra_headers = os.getenv("LLM_EXTRA_HEADERS", "").strip()
    if extra_headers:
        client_kwargs["default_headers"] = json.loads(extra_headers)

    context.user_data.client = OpenAI(**client_kwargs)
    context.user_data.base_url = base_url
    context.user_data.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    context.user_data.labels = labels
    context.user_data.label_lookup = {label.casefold(): label for label in labels}
    context.user_data.prompt = prompt
    context.user_data.coordinates = os.getenv("LLM_COORDINATES", "auto").strip().lower()
    context.user_data.box_format = os.getenv("LLM_BOX_FORMAT", "xyxy").strip().lower()
    context.user_data.max_detections = int(os.getenv("LLM_MAX_DETECTIONS", "100"))
    context.user_data.jpeg_quality = int(os.getenv("LLM_JPEG_QUALITY", "90"))

    context.logger.info(f"VLM model: {context.user_data.model}")
    context.logger.info(
        "VLM endpoint: " + (_redact_url(base_url) if base_url else "OpenAI default")
    )


def handler(context, event):
    context.logger.info("Run VLM detector")

    data = event.body or {}
    if not isinstance(data, dict):
        raise ValueError("The request body must be a JSON object")

    image_b64 = data.get("image")
    if not image_b64:
        raise ValueError("The request does not contain an 'image' field")

    image_bytes = base64.b64decode(image_b64)
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        context.logger.error("Could not decode the input image")
        return context.Response(
            body=json.dumps([]),
            headers={},
            content_type="application/json",
            status_code=200,
        )

    height, width = image.shape[:2]
    ok, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), context.user_data.jpeg_quality],
    )
    if not ok:
        raise ValueError("Could not encode the input image as JPEG")

    image_url = "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
    image_content = {"url": image_url}

    image_detail = os.getenv("LLM_IMAGE_DETAIL", "").strip()
    if image_detail:
        image_content["detail"] = image_detail

    request_kwargs = {
        "model": context.user_data.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": context.user_data.prompt},
                    {"type": "image_url", "image_url": image_content},
                ],
            }
        ],
    }

    temperature = os.getenv("LLM_TEMPERATURE", "").strip()
    if temperature:
        request_kwargs["temperature"] = float(temperature)

    max_tokens = os.getenv("LLM_MAX_TOKENS", "").strip()
    if max_tokens:
        request_kwargs["max_tokens"] = int(max_tokens)

    try:
        response = context.user_data.client.chat.completions.create(**request_kwargs)
    except APIConnectionError as exc:
        endpoint = context.user_data.base_url or "the OpenAI API"
        context.logger.error(f"Could not connect to the VLM endpoint {endpoint}: {exc}")
        raise RuntimeError(
            f"Could not connect to the VLM endpoint at {endpoint}. "
            "Check that the server is running and that LLM_BASE_URL is reachable "
            "from the Nuclio container. localhost/127.0.0.1 inside the container "
            "is not the Docker host."
        ) from exc

    text = response.choices[0].message.content or ""

    payload = _parse_json_response(text)
    if payload is None:
        context.logger.error(f"Could not parse the VLM response: {text[:1000]}")
        items = []
    else:
        items = _extract_items(payload)

    threshold = _as_float(data.get("threshold"))
    if threshold is None:
        threshold = _as_float(os.getenv("LLM_THRESHOLD"), 0.5)

    detections = []
    labels = context.user_data.labels
    label_lookup = context.user_data.label_lookup

    for item in items:
        if not isinstance(item, dict):
            continue
        if len(detections) >= context.user_data.max_detections:
            break

        raw_label = item.get("label") or item.get("class") or item.get("name")
        if raw_label is None:
            continue

        raw_label = str(raw_label).strip()
        label = label_lookup.get(raw_label.casefold(), raw_label)

        if labels and label not in labels:
            context.logger.debug(f"Skipping unknown label: {raw_label}")
            continue

        box = _box_to_xyxy(item, context.user_data.box_format)
        if box is None:
            continue

        x1, y1, x2, y2 = _scale_box(
            box,
            width,
            height,
            context.user_data.coordinates,
        )

        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        x1 = min(max(x1, 0.0), float(width))
        y1 = min(max(y1, 0.0), float(height))
        x2 = min(max(x2, 0.0), float(width))
        y2 = min(max(y2, 0.0), float(height))

        if x2 - x1 < 1.0 or y2 - y1 < 1.0:
            continue

        confidence = _as_float(item.get("confidence", item.get("score", 1.0)), 1.0)
        if 1.0 < confidence <= 100.0:
            confidence /= 100.0
        confidence = min(max(confidence, 0.0), 1.0)

        if confidence < threshold:
            continue

        detections.append(
            {
                "confidence": str(confidence),
                "label": label,
                "points": [x1, y1, x2, y2],
                "type": "rectangle",
                "rotation": 0.0,
            }
        )

    context.logger.info(f"Returning {len(detections)} detections")

    return context.Response(
        body=json.dumps(detections),
        headers={},
        content_type="application/json",
        status_code=200,
    )
