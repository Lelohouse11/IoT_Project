# YOLOv8 nano tests

Folder for quick vehicle detection with the pretrained YOLOv8 nano (`yolov8n.pt`).

## Setup
1. Install dependencies (already done if you ran this step before):
   ```bash
   python -m pip install -r yolov8_tests/requirements.txt
   ```

## Run your own tests
1. Add your own media under `yolov8_tests/inputs/images` and `yolov8_tests/inputs/videos` (create the folders if they don't exist).
2. Run detection:
   ```bash
   python yolov8_tests/run_detection.py
   ```
   - Images only: `python yolov8_tests/run_detection.py --images`
   - Videos only: `python yolov8_tests/run_detection.py --videos`
   - GPU (if available): `python yolov8_tests/run_detection.py --device cuda:0`
   - Custom camera/GPS metadata: `python yolov8_tests/run_detection.py --camera-id cam-42 --gps-lat 48.14 --gps-lon 11.58`
   - Curbside gap threshold (meters): `--spot-threshold-m 5.5`
   - Curb proximity tolerance (normalized): `--curb-threshold 0.05`
   - Override meters-per-pixel calibration: `--meters-per-pixel 0.05`

## Outputs
- Annotated images: `yolov8_tests/outputs/images`
- Annotated videos: `yolov8_tests/outputs/videos/<videoname>/`
- Metadata JSON (created when detections occur):
  - Images: `yolov8_tests/outputs/images/<name>_yolov8n.json`
  - Videos: `yolov8_tests/outputs/videos/<videoname>/metadata.json`
  - Double parking events (videos): `yolov8_tests/outputs/videos/<videoname>/events/*.json` (+ frame snapshots)
  - Parking spot availability:
    - Images: `yolov8_tests/outputs/images/<name>_spots.json`
    - Videos: `yolov8_tests/outputs/videos/<videoname>/events/*_spot.json` (+ snapshots)

Note: The first run automatically downloads the `yolov8n.pt` weights.

## Double parking detection
- Rule: vehicle bounding box center is inside a lane polygon, outside any parking polygon, and remains stationary for at least 20 seconds. When triggered, a frame snapshot and event JSON are written under `outputs/videos/<videoname>/events/`.
- Define lane and parking areas in a normalized `zones.json` (0-1 coords relative to frame). Example template: `yolov8_tests/zones.example.json`. Copy and adjust:
  ```bash
  cp yolov8_tests/zones.example.json yolov8_tests/zones.json
  ```
- If `zones.json` is missing, double parking detection is skipped, but normal detection still runs.

## Roadside parking spot detection
- Define curb lines in `zones.json` under `curbs` as line segments (normalized coords). Optional `meters_per_pixel` per curb for better gap sizing; fallback uses `--meters-per-pixel` or a default 0.05 m/px.
- Rule: vehicles close to a curb line (within `--curb-threshold` * max image dimension) are projected onto the curb; if the gap between neighboring projected vehicles exceeds `--spot-threshold-m`, the gap is reported as an available spot.
- Outputs per image: `<name>_spots.json`; per video: events in `outputs/videos/<videoname>/events/*_spot.json` plus frame snapshots.
