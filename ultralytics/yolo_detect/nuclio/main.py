import json
import base64

import cv2
import numpy as np
from ultralytics import YOLO

def init_context(context):
    context.logger.info("Init context...  0%")

    # Change the model path to the model you want to use
    model_path = "yolo26n.pt"

    model = YOLO(model_path, task="detect")

    # Read the DL model
    context.user_data.model = model

    context.logger.info("Init context...100%")



def handler(context, event):
    context.logger.info("Run custom YOLO model")

    # Decode input image
    data = event.body
    image_bytes = base64.b64decode(data["image"])
    image = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR
    )

    # Run YOLO inference
    result = context.user_data.model(image, verbose=False)[0]

    detections = []
    threshold = 0.5

    # Extract bounding boxes
    boxes = result.boxes

    if boxes is not None:
        class_names = result.names

        for box in boxes:
            confidence = float(box.conf.item())

            if confidence < threshold:
                continue

            # Get class information
            class_id = int(box.cls.item())
            label = class_names[class_id]

            # Get axis-aligned bounding box coordinates
            x_min, y_min, x_max, y_max = box.xyxy[0].tolist()

            detections.append({
                "confidence": str(confidence),
                "label": label,
                "points": [x_min, y_min, x_max, y_max],
                "type": "rectangle",
                "rotation": 0.0
            })

    return context.Response(
        body=json.dumps(detections),
        headers={},
        content_type="application/json",
        status_code=200
    )