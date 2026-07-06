"""
Flask backend for the CircuitAuris dashboard.

"Run Inspection" now takes a REAL live photo from the webcam every time
(capture_image()), runs it through real YOLO inference, and updates the
dashboard - no more static test image.

Run from the project root:
    cd ~/circuitauris
    python3 src/app.py

Then view it via VS Code's Ports tab (forward port 5000) -> localhost:5000
"""
from flask import Flask, render_template, jsonify
from datetime import datetime

from main import capture_image, run_yolo_inference

app = Flask(__name__, template_folder="../templates")

# In-memory state - resets if the server restarts, which is fine for a prototype
current_status = {
    "result": "READY",
    "timestamp": None,
    "defect_count": None,
    "defects": [],
}
inspection_log = []


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/status")
def status():
    return jsonify(current_status)


@app.route("/log")
def log():
    return jsonify(inspection_log)


@app.route("/inspect", methods=["POST"])
def inspect():
    timestamp = datetime.now().strftime("%H:%M:%S")

    try:
        image = capture_image()
        detections = run_yolo_inference(image)
        passed = len(detections) == 0
        error = None
    except Exception as e:
        # If the webcam isn't connected or capture fails for any reason,
        # surface that clearly instead of crashing the whole server
        print(f"Inspection error: {e}")
        detections = []
        passed = False
        error = str(e)

    current_status["result"] = "FAIL" if error else ("PASS" if passed else "FAIL")
    current_status["timestamp"] = timestamp
    current_status["defect_count"] = len(detections)
    current_status["defects"] = [
        {"type": d["class"], "confidence": round(d["confidence"], 2)}
        for d in detections
    ]
    if error:
        current_status["defects"] = [{"type": f"CAMERA ERROR: {error}", "confidence": 0}]

    inspection_log.append({
        "timestamp": timestamp,
        "result": current_status["result"],
        "defect_count": len(detections),
    })

    return jsonify({"status": "done"})


if __name__ == "__main__":
    # host=127.0.0.1 (default) is intentional - we're viewing this via
    # VS Code's port forwarding (Method B), not exposing it to the WiFi network
    app.run(port=5000, debug=True)
