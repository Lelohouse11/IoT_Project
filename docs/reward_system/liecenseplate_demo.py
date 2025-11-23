import base64
from pathlib import Path

import requests

API_URL = "http://labserver.sense-campus.gr:7080/vision"
API_KEY = "iot2025"  # must match a line in keys.txt inside the container

MODEL_NAME = "qwen2.5vl:3b-q4_K_M"  # or whatever you actually have in models.txt

def encode_image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def main():
    script_dir = Path(__file__).resolve().parent
    image_path = script_dir / "nummernschild_1.png"
    image_b64 = encode_image_to_base64(image_path)

    payload = {
        "model": MODEL_NAME,
        "prompt": "Return only the license plate text seen in the image; return 'none' if no plate is visible.",
        "image": image_b64,  # or "images": [image_b64] if that's how you implemented /vision
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)

    if not resp.ok:
        print("Status:", resp.status_code)
        print("Body:", resp.text)
        resp.raise_for_status()

    data = resp.json()
    print("Model:", data.get("model"))
    print("Answer:", data.get("output") or data)

if __name__ == "__main__":
    main()
