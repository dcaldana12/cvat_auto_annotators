import json
import base64
import io
import math

import cv2
import numpy as np
from ultralytics import YOLO

def init_context(context):
    context.logger.info("Init context...  0%")

    # Change the model path to the model you want to use
    model_path = "yolo26n-obb.pt"

    model = YOLO(model_path, task="obb")

    # Read the DL model
    context.user_data.model = model

    context.logger.info("Init context...100%")



def handler(context, event):
    context.logger.info('Run custom yolo-obb model')
    data = event.body
    image_buffer = io.BytesIO(base64.b64decode(data['image']))
    image = cv2.imdecode(np.frombuffer(image_buffer.getvalue(), np.uint8), cv2.IMREAD_COLOR)

    results = context.user_data.model(image)
    result = results[0]

    result = results[0]
    boxes = result.obb.xywhr
    confs = result.obb.conf
    clss = result.obb.cls
    class_name = result.names

    detections = []
    threshold = 0.5
    for box, conf, cls in zip(boxes, confs, clss):
        label = class_name[int(cls)]
        if conf >= threshold:
            x, y, width, height, rotation = box.tolist()
            angle_deg = math.degrees(float(rotation)) % 360
            box = [x-width/2, y-height/2, x+width/2, y+height/2]
            # must be in this format
            detections.append({
                'confidence': str(float(conf)),
                'label': label,
                'points': box,
                'type': 'rectangle',
                "rotation": angle_deg,
            })


    return context.Response(body=json.dumps(detections), headers={},
                            content_type='application/json', status_code=200)