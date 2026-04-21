"""
BimaBuddy AI — Flask API for Render deployment.
Frontend (Streamlit Cloud) → calls this API → backend processes PDF → returns JSON.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from Streamlit Cloud


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "service": "BimaBuddy AI API"})


# ---------------------------------------------------------------------------
# Main analysis endpoint
# ---------------------------------------------------------------------------
@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded. Send PDF as 'file' field."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"status": "error", "message": "Only PDF files are supported."}), 400

    try:
        file_bytes = file.read()

        from backend.pipeline import run_analysis
        result = run_analysis(file_bytes)

        if result is None:
            return jsonify({"status": "error", "message": "Analysis returned no result."}), 500

        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 422

        return jsonify({"status": "success", "data": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# Entry point for local dev  (Render uses: gunicorn api:app)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
