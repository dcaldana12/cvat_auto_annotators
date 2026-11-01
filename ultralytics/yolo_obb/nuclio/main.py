"""CVAT serverless detector using an Ultralytics YOLO OBB model."""

import base64
import json
import math

import cv2
import numpy as np
from ultralytics import YOLO


def init_context(context):
    context.logger.info("Init context...  0%")

    # Change the model path to the model you want to use.
    model_path = "yolo26n-obb.pt"

    model = YOLO(model_path, task="obb")

    # Read the DL model.
    context.user_data.model = model

    context.logger.info("Init context...100%")


def handler(context, event):
    context.logger.info("Run custom YOLO-OBB model")

    data = event.body
    image = cv2.imdecode(
        np.frombuffer(base64.b64decode(data["image"]), np.uint8),
        cv2.IMREAD_COLOR,
    )

    result = context.user_data.model(image, verbose=False)[0]

    boxes = result.obb.xywhr
    confs = result.obb.conf
    clss = result.obb.cls
    class_names = result.names

    detections = []
    threshold = 0.5

    for box, conf, cls in zip(boxes, confs, clss):
        label = class_names[int(cls)]

        if conf < threshold:
            continue

        x, y, width, height, rotation = box.tolist()
        angle_deg = math.degrees(float(rotation)) % 360
        points = [x - width / 2, y - height / 2, x + width / 2, y + height / 2]

        # Must be in this format for CVAT.
        detections.append(
            {
                "confidence": str(float(conf)),
                "label": label,
                "points": points,
                "type": "rectangle",
                "rotation": angle_deg,
            }
        )

    return context.Response(
        body=json.dumps(detections),
        headers={},
        content_type="application/json",
        status_code=200,
    )
