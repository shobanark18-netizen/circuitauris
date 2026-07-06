"""
Quick smoke test for run_ocr().
Run from the circuitauris project root:
    cd ~/circuitauris
    python3 src/test_ocr.py
"""
import sys
import os
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import run_ocr

# Update this filename to match whatever you actually saved/scp'd over
TEST_IMAGE = "data/test_images/ic_chip_testimage.jpg"


def main():
    if not os.path.exists(TEST_IMAGE):
        print(f"ERROR: test image not found at {TEST_IMAGE}")
        print("Check the filename matches what you scp'd over, and that you're running from ~/circuitauris")
        return

    image = cv2.imread(TEST_IMAGE)
    if image is None:
        print(f"ERROR: cv2 could not load image at {TEST_IMAGE}")
        return

    print(f"Image loaded OK - shape: {image.shape}")
    print("Running OCR (first run also loads EasyOCR's models, can take a minute)...")

    results = run_ocr(image)

    print(f"\nFound {len(results)} text region(s):")
    for r in results:
        print(f"  - '{r['text']}'  (confidence: {r['confidence']:.2f})")

    if not results:
        print("  (no text detected - on a mismatched test image this is fine; "
              "we're just confirming the pipeline runs without crashing)")


if __name__ == "__main__":
    main()
