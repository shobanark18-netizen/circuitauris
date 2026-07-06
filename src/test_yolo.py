"""
Quick smoke test for run_yolo_inference().
Run from the circuitauris project root:
    cd ~/circuitauris
    python3 src/test_yolo.py
"""
import sys
import os
import cv2

# Allow "from main import ..." even though this file lives in src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import run_yolo_inference

TEST_IMAGE = "data/test_images/PCB-design_testimage.jpg"


def main():
    if not os.path.exists(TEST_IMAGE):
        print(f"ERROR: test image not found at {TEST_IMAGE}")
        print("Make sure you're running this from ~/circuitauris")
        return

    image = cv2.imread(TEST_IMAGE)
    if image is None:
        print(f"ERROR: cv2 could not load image at {TEST_IMAGE}")
        return

    print(f"Image loaded OK - shape: {image.shape}")
    print("Running YOLO inference (first run will also load the model, may take a few seconds)...")

    detections = run_yolo_inference(image)

    print(f"\nFound {len(detections)} detection(s):")
    for d in detections:
        print(f"  - {d['class']}  (confidence: {d['confidence']:.2f})  bbox: {d['bbox']}")

    if not detections:
        print("  (no detections - this is expected/fine for a smoke test; "
              "it just means the model ran without crashing)")


if __name__ == "__main__":
    main()
