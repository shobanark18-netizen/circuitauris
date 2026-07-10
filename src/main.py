"""
CircuitAuris - Main Inspection Pipeline
AOI prototype: button press -> capture -> inference -> LED result

Hardware:
- USB webcam (wide AOI shot)                   -> cv2.VideoCapture(2)
- Pi Camera V3 (OCR close-up, via CSI)          -> picamera2
- Push button on GPIO17
- LEDs: Green=GPIO27 (PASS), Red=GPIO22 (FAIL), Yellow=GPIO23 (PROCESSING)
"""

import cv2
import time
import shutil

# ---------------- GPIO PIN ASSIGNMENTS ----------------
BUTTON_PIN = 17
LED_GREEN = 27   # PASS
LED_RED = 22     # FAIL
LED_YELLOW = 23  # PROCESSING

# ---------------- YOLO MODEL (lazy-loaded once) ----------------
MODEL_PATH = "models/baseline_best.pt"
_yolo_model = None

# ---------------- OCR READER (lazy-loaded once) ----------------
_ocr_reader = None


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


def get_ocr_reader():
    """
    Load the EasyOCR reader once and reuse it.
    gpu=False is important - the Pi has no GPU.
    """
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        print("Loading EasyOCR reader...")
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
        print("OCR reader loaded.")
    return _ocr_reader


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
    """
    Capture a wide AOI shot using the USB webcam.
    Index 2 because Pi Camera V3 (CSI) occupies /dev/video0 and /dev/video1.
    Saves a copy to data/test_images/last_usb_capture.jpg for inspection.
    """
    cap = cv2.VideoCapture(2, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam at index 2 - check connection")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Give camera time to initialize
    time.sleep(2)

    # Warm up with dummy reads
    for _ in range(5):
        cap.read()

    ret, frame = cap.read()
    if ret:
        cv2.imwrite('data/test_images/last_usb_capture.jpg', frame)
    cap.release()

    if not ret:
        raise RuntimeError("Failed to capture frame from webcam")

    return frame


def capture_ocr_image():
    """
    Capture a close-up shot using the Pi Camera V3 (CSI ribbon, picamera2).
    Used for OCR on IC markings.
    Position camera 10-15cm from the component for best results.
    Saves a copy to data/test_images/last_v3_capture.jpg for inspection.
    """
    from picamera2 import Picamera2
    from libcamera import controls

    picam2 = Picamera2()
    picam2.start()
    time.sleep(2)
    picam2.set_controls({'AfMode': controls.AfModeEnum.Continuous})
    time.sleep(3)  # wait for autofocus to lock
    picam2.capture_file('/tmp/ocr_capture.jpg')
    picam2.stop()

    # Save a copy for viewing
    shutil.copy('/tmp/ocr_capture.jpg', 'data/test_images/last_v3_capture.jpg')

    image = cv2.imread('/tmp/ocr_capture.jpg')
    if image is None:
        raise RuntimeError("Failed to read captured OCR image")

    return image


def run_yolo_inference(image, confidence_threshold=0.5):
    """
    Run YOLO inference on a captured image (numpy array, BGR).
    Returns: list of dicts, one per detection:
        {"class": str, "confidence": float, "bbox": [x1, y1, x2, y2]}
    """
    model = get_yolo_model()
    results = model(image, conf=confidence_threshold)

    detections = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": model.names[cls_id],
                "confidence": float(box.conf[0]),
                "bbox": box.xyxy[0].tolist(),
            })

    return detections


def run_ocr(image):
    """
    Run EasyOCR on a close-up image to read IC markings.
    Pipeline: grayscale -> size cap -> 4x upscale -> adaptive threshold -> denoise -> EasyOCR
    """
    reader = get_ocr_reader()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Cap size before upscaling to avoid OOM on Pi
    h, w = gray.shape
    max_dim = 300
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    upscaled = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    thresh = cv2.adaptiveThreshold(
        upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    denoised = cv2.fastNlMeansDenoising(thresh, h=10)

    results = reader.readtext(denoised)

    text_results = []
    for (bbox, text, confidence) in results:
        text_results.append({
            "text": text,
            "confidence": float(confidence),
            "bbox": bbox,
        })

    return text_results


def run_inspection(GPIO):
    """Full pipeline: capture -> YOLO -> OCR -> decide PASS/FAIL"""
    leds_off(GPIO)
    GPIO.output(LED_YELLOW, GPIO.HIGH)  # PROCESSING

    try:
        # Wide shot via USB webcam -> YOLO defect detection
        image = capture_image()
        detections = run_yolo_inference(image)

        # Close-up shot via Pi Camera V3 -> OCR component verification
        ocr_image = capture_ocr_image()
        try:
            ocr_results = run_ocr(ocr_image)
        except NotImplementedError:
            ocr_results = []
            print("OCR not yet implemented - skipping")

        # TODO: replace with real decision logic once dataset is ready
        # For now: any YOLO detection = FAIL
        passed = len(detections) == 0

        print(f"Detections: {detections}")
        print(f"OCR Results: {ocr_results}")

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
