#!/usr/bin/env python3
"""
Laptop receiver server for ESP32-CAM
Run: python3 server.py
Images saved to ./captures/ with timestamps
"""

from flask import Flask, request
from datetime import datetime
import os

app = Flask(__name__)
SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload():
    data = request.data
    if not data:
        return "No data", 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SAVE_DIR}/img_{timestamp}.jpg"

    with open(filename, "wb") as f:
        f.write(data)

    print(f"[+] Saved: {filename}  ({len(data)} bytes)")
    return "OK", 200

if __name__ == "__main__":
    print("[*] Listening on 0.0.0.0:5000 ...")
    app.run(host="0.0.0.0", port=5000)
