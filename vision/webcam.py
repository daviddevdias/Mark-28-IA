import base64
import logging
from io import BytesIO
from typing import Optional

log = logging.getLogger("vision.webcam")

JPEG_QUALITY = 42
MAX_WIDTH = 960


def capturar_webcam_base64(device: int = 0) -> Optional[str]:
    try:
        import cv2
        from PIL import Image
    except ImportError:
        log.warning("opencv ou pillow ausente para webcam.")
        return None
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        return None
    try:
        ok, frame = cap.read()
        if not ok or frame is None:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        if img.width > MAX_WIDTH:
            img.thumbnail((MAX_WIDTH, 720), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log.error("webcam: %s", e)
        return None
    finally:
        cap.release()
