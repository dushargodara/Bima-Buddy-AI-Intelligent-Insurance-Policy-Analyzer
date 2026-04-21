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
import gc
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

    import time
    start_time = time.time()
    
    try:
        # Task 1: Limit file size read and validate
        limit = 5 * 1024 * 1024
        file_bytes = file.read(limit + 1)

        if len(file_bytes) == 0:
            return jsonify({"status": "error", "message": "The uploaded file is empty."}), 400

        if len(file_bytes) > limit:
            return jsonify({"status": "error", "message": "File too large. Maximum size is 5MB."}), 413

        # Performance Check: Start analysis
        from backend.pipeline import run_analysis
        
        # We wrap the call with a simple timeout-check mindset
        # If the pipeline itself has guards, it will return partial results
        result = run_analysis(file_bytes)

        # Clear large object from memory
        del file_bytes
        gc.collect()

        # MASTER TIME GUARD: Fast exit if we are close to Render's limit
        elapsed = time.time() - start_time
        if elapsed > 55:
            print(f"MASTER TIMEOUT GUARD TRIGGERED: {elapsed:.2f}s")
            # If result is already structured, just flag it as partial
            if isinstance(result, dict):
                result["status"] = "partial"
                result["warnings"] = result.get("warnings", []) + ["Analysis timed out. Displaying partial results."]
                return jsonify({"status": "success", "data": result})

        if result is None:
            return jsonify({"status": "error", "message": "Analysis returned no result."}), 500

        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 422

        return jsonify({"status": "success", "data": result})

    except Exception as e:
        print(f"CRITICAL BACKEND ERROR: {str(e)}")
        # Safe fallback for UI
        return jsonify({
            "status": "success", 
            "data": {
                "status": "partial",
                "policy_summary": {"simple_summary": "Analysis failed due to document complexity or system limits."},
                "warnings": [str(e)]
            }
        })
    finally:
        gc.collect()


# ---------------------------------------------------------------------------
# Entry point for local dev  (Render uses: gunicorn api:app)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
