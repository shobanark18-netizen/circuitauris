"""
CircuitAuris - Main Inspection Pipeline
AOI prototype: button press -> capture -> inference -> LED result

Hardware:
- Logitech C310 webcam (wide AOI shot)   -> cv2.VideoCapture(0)
- Pi Camera V3 (OCR close-up, via CSI)   -> picamera2 (TODO once camera is bought)
- Push button on GPIO17
- LEDs: Green=GPIO27 (PASS), Red=GPIO22 (FAIL), Yellow=GPIO23 (PROCESSING)
"""

import cv2
import RPi.GPIO as GPIO
import time

# ---------------- GPIO SETUP ----------------
BUTTON_PIN = 17
LED_GREEN = 27   # PASS
LED_RED = 22     # FAIL
LED_YELLOW = 23  # PROCESSING

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_GREEN, GPIO.OUT)
GPIO.setup(LED_RED, GPIO.OUT)
GPIO.setup(LED_YELLOW, GPIO.OUT)


def leds_off():
    GPIO.output(LED_GREEN, GPIO.LOW)
    GPIO.output(LED_RED, GPIO.LOW)
    GPIO.output(LED_YELLOW, GPIO.LOW)


def capture_image():
    """
    Capture a wide AOI shot using the Logitech C310 webcam.
    C310 connects via USB and should appear at index 0, same as the
    originally-planned Pi Camera V2 did -- verify this is still true
    once tested, in case other USB devices shift the index.
    """
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
    TODO: Load YOLOv8n model (baseline_best.pt from Kaggle training run)
    and run inference on the captured image.

    Should return: list of detections (defect type, confidence, bbox)
    Reference: Kaggle run wandb.ai/shobanark18-/circuitauris/runs/5tgh704e
               weights at baseline_best.pt (mAP50 = 0.9406)
    """
    # from ultralytics import YOLO
    # model = YOLO("models/baseline_best.pt")
    # results = model(image)
    # return results
    raise NotImplementedError("YOLO inference not yet implemented")


def run_ocr(image):
    """
    TODO: Run EasyOCR on cropped component regions to read IC markings.
    Reference implementation in original PDF guide:
    4x upscale -> adaptive threshold -> denoise -> EasyOCR
    See src/ocr_pipeline.py (to be written)
    """
    # from src.ocr_pipeline import read_component_text
    # return read_component_text(image)
    raise NotImplementedError("OCR pipeline not yet implemented")


def run_inspection():
    """Full pipeline: capture -> YOLO -> OCR -> decide PASS/FAIL"""
    leds_off()
    GPIO.output(LED_YELLOW, GPIO.HIGH)  # PROCESSING

    try:
        image = capture_image()

        # TODO: uncomment once run_yolo_inference is implemented
        # detections = run_yolo_inference(image)

        # TODO: uncomment once run_ocr is implemented
        # ocr_results = run_ocr(image)

        # TODO: combine detections + OCR results into a final PASS/FAIL decision
        passed = True  # placeholder until real logic is in place

    except Exception as e:
        print(f"Inspection error: {e}")
        passed = False

    leds_off()
    if passed:
        GPIO.output(LED_GREEN, GPIO.HIGH)
    else:
        GPIO.output(LED_RED, GPIO.HIGH)

    return passed


def main():
    print("CircuitAuris ready. Waiting for button press (Ctrl+C to exit)...")
    try:
        while True:
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # button pressed
                print("Button pressed - running inspection...")
                result = run_inspection()
                print(f"Result: {'PASS' if result else 'FAIL'}")
                time.sleep(1)  # debounce / cooldown
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        leds_off()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
