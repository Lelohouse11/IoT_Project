import base64
from pathlib import Path

import requests

API_URL = "http://labserver.sense-campus.gr:7080/vision"
API_KEY = "iot2025"  # must match a line in keys.txt inside the container

MODEL_NAME = "qwen2.5vl:3b-q4_K_M"  # or whatever you actually have in models.txt


def call_model(payload: dict, label: str):
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }

    print(f"Sending payload variant: {label}")
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)

    if not resp.ok:
        print(f"{label} failed. Status: {resp.status_code}")
        print("Body:", resp.text)
        return None

    return resp


def encode_image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def main():
    script_dir = Path(__file__).resolve().parent
    image_path = script_dir / "parking1.png"
    image_b64 = encode_image_to_base64(image_path)

    prompt_text = (
        "You are a vision-language model. Analyze the attached single image (a static surveillance camera view of a roadside/curb lane). "
        "Your task: detect contiguous empty gaps along the curb where a standard car can park, and return only one single-line result in exactly "
        "one of these two formats:\n\n"
        "- no parking spaces\n"
        "- parkingspaces: <N>\n\n"
        "Rules for detection:\n"
        "1. Count only gaps large enough for a typical car (~4.5m length). If a gap can fit one car, count 1; if it fits two cars end-to-end, count 2, etc.\n"
        "2. Consider visible occlusions (pedestrians, trash, trees) as blocking; do not count partially blocked spaces as available.\n"
        "3. If a gap is uncertain (occluded or borderline), use conservative rounding down.\n"
        "4. Ignore oncoming traffic lanes — only consider curb-side parking spaces visible in the image.\n"
        "5. Only consider horizontal curb segments clearly visible in the frame. If camera perspective skews distances, use visual cues (car lengths, lane markings) to estimate usable length.\n"
        "6. Do not produce any explanation, reasoning, or extra text—only output exactly `no parking spaces` or `parkingspaces: <N>`.\n\n"
        "Optional: If available, use camera metadata (camera angle, resolution, focal length) and known car standard length ~4.5m to improve estimation.\n\n"
        "Example valid outputs (exactly):\n"
        "parkingspaces: 3\n"
        "no parking spaces"
    )

    payload_variants = [
        (
            "image_field",
            {
                "model": MODEL_NAME,
                "prompt": prompt_text,
                "image": image_b64,
            },
        ),
        (
            "images_array_field",
            {
                "model": MODEL_NAME,
                "prompt": prompt_text,
                "images": [image_b64],
            },
        ),
    ]

    for label, payload in payload_variants:
        resp = call_model(payload, label)
        if resp is None:
            continue

        data = resp.json()
        print("Model:", data.get("model"))
        print("Answer:", data.get("output") or data)
        return

    raise SystemExit("All payload variants failed; see logs above for server responses.")


if __name__ == "__main__":
    main()
