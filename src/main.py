"""
CircuitAuris - Main Inspection Pipeline
AOI prototype: button press -> capture -> inference -> LED result

Hardware:
- USB webcam (wide AOI shot)                   -> cv2.VideoCapture(0)
- Pi Camera V3 (OCR close-up, via CSI)          -> picamera2 (TODO once wired up)
- Push button on GPIO17
- LEDs: Green=GPIO27 (PASS), Red=GPIO22 (FAIL), Yellow=GPIO23 (PROCESSING)
"""

import cv2
import time

# ---------------- GPIO PIN ASSIGNMENTS ----------------
BUTTON_PIN = 17
LED_GREEN = 27   # PASS
LED_RED = 22     # FAIL
LED_YELLOW = 23  # PROCESSING

# ---------------- YOLO MODEL (lazy-loaded once) ----------------
MODEL_PATH = "models/baseline_best.pt"
_yolo_model = None


def get_yolo_model():
    """
    Load the YOLO model once and reuse it across calls.
    Loading a model is slow (~1-2s on a Pi) - we don't want to pay that
    cost on every single inspection, only once at startup.
    """
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        print(f"Loading YOLO model from {MODEL_PATH} ...")
        _yolo_model = YOLO(MODEL_PATH)
        print("Model loaded.")
    return _yolo_model


def setup_gpio():
    """GPIO setup, called explicitly from main() - not at import time.
    This means run_yolo_inference()/run_ocr() can be tested standalone
    (e.g. from a test script) without needing GPIO hardware present."""
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_RED, GPIO.OUT)
    GPIO.setup(LED_YELLOW, GPIO.OUT)
    return GPIO


def leds_off(GPIO):
    GPIO.output(LED_GREEN, GPIO.LOW)
    GPIO.output(LED_RED, GPIO.LOW)
    GPIO.output(LED_YELLOW, GPIO.LOW)


def capture_image():
    """Capture a wide AOI shot using the USB webcam (index 0)."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam at index 0 - check connection")

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("Failed to capture frame from webcam")

    return frame


def run_yolo_inference(image):
    """
    Run YOLO inference on a captured image (numpy array, BGR - as returned
    by cv2.imread/cv2.VideoCapture).

    Returns: list of dicts, one per detection:
        {"class": str, "confidence": float, "bbox": [x1, y1, x2, y2]}
    """
    model = get_yolo_model()
    results = model(image)

    detections = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": model.names[cls_id],
                "confidence": float(box.conf[0]),
                "bbox": box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
            })

    return detections


def run_ocr(image):
    """
    TODO: Run EasyOCR on cropped component regions to read IC markings.
    Reference implementation: 4x upscale -> adaptive threshold -> denoise -> EasyOCR
    See src/ocr_pipeline.py (to be written)
    """
    raise NotImplementedError("OCR pipeline not yet implemented")


def run_inspection(GPIO):
    """Full pipeline: capture -> YOLO -> OCR -> decide PASS/FAIL"""
    leds_off(GPIO)
    GPIO.output(LED_YELLOW, GPIO.HIGH)  # PROCESSING

    try:
        image = capture_image()
        detections = run_yolo_inference(image)

        # TODO: uncomment once run_ocr is implemented
        # ocr_results = run_ocr(image)

        # TODO: combine detections + OCR results into a real PASS/FAIL decision.
        # Placeholder logic for now: any detection at all = FAIL
        passed = len(detections) == 0

        print(f"Detections: {detections}")

    except Exception as e:
        print(f"Inspection error: {e}")
        passed = False

    leds_off(GPIO)
    if passed:
        GPIO.output(LED_GREEN, GPIO.HIGH)
    else:
        GPIO.output(LED_RED, GPIO.HIGH)

    return passed


def main():
    GPIO = setup_gpio()
    print("CircuitAuris ready. Waiting for button press (Ctrl+C to exit)...")
    try:
        while True:
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # button pressed
                print("Button pressed - running inspection...")
                result = run_inspection(GPIO)
                print(f"Result: {'PASS' if result else 'FAIL'}")
                time.sleep(1)  # debounce / cooldown
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        leds_off(GPIO)
        GPIO.cleanup()


if __name__ == "__main__":
    main()
