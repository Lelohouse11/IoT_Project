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
   - Detection sensitivity: lower `--conf` (default 0.15) to get more boxes, raise to filter
   - Custom camera/GPS metadata: `python yolov8_tests/run_detection.py --camera-id cam-42 --gps-lat 48.14 --gps-lon 11.58`

## Outputs
- Annotated images: `yolov8_tests/outputs/images`
- Annotated videos: `yolov8_tests/outputs/videos/<videoname>/`
- Metadata JSON (created when detections occur):
  - Images: `yolov8_tests/outputs/images/<name>_yolov8n.json`
  - Videos: `yolov8_tests/outputs/videos/<videoname>/metadata.json`
  - Parking area occupancy (upper-half region):
    - Images: `yolov8_tests/outputs/images/<name>_parking_area.json` (+ annotated image with line)
    - Videos: `yolov8_tests/outputs/videos/<videoname>/events/*_parking.json` (+ frame snapshots)

Note: The first run automatically downloads the `yolov8n.pt` weights.

## Roadside parking spot detection
- Current simplified approach: counts vehicles whose bounding boxes intersect the upper half of the frame and writes occupancy metadata. A yellow line on outputs shows the boundary of that area.
