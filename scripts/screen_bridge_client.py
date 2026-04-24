from __future__ import annotations

import argparse
import base64
import time
from io import BytesIO

import mss
import requests
from PIL import Image


def capture_jpeg_base64(monitor_index: int, quality: int = 55) -> str:
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        raw = sct.grab(monitor)
        image = Image.frombytes("RGB", raw.size, raw.rgb)
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen bridge to Sveta bot")
    parser.add_argument("--url", default="http://127.0.0.1:8081/screen")
    parser.add_argument("--every", type=float, default=12.0)
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--note", default="демонстрация экрана")
    args = parser.parse_args()

    while True:
        img64 = capture_jpeg_base64(args.monitor)
        response = requests.post(args.url, json={"image_base64": img64, "note": args.note}, timeout=30)
        print(response.status_code, response.text)
        time.sleep(args.every)


if __name__ == "__main__":
    main()
