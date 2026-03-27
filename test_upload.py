import requests
import os
import sys

# Change this to match the server IP and port
url = "http://localhost:5001/upload"

# Define the absolute path to a test image
base_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(base_dir, "Training_databse", "test", "images", "img_20260325_162612_jpg.rf.6efd1936de6e3240e8fb4ba8f5669e2e.jpg")

if not os.path.exists(image_path):
    print(f"Error: Image {image_path} not found.")
    sys.exit(1)

# ESP32 metadata
payload = {
    'field_id': 'Walnut Grove B',
    'trap_id': 'Trap-05'
}

# The image file as 'image' parameter
with open(image_path, 'rb') as f:
    files = {'image': (os.path.basename(image_path), f, 'image/jpeg')}
    
    print(f"Uploading {image_path} to {url}...")
    try:
        response = requests.post(url, data=payload, files=files)
        print("Response Code:", response.status_code)
        import json
        try:
            print("Response JSON:\n", json.dumps(response.json(), indent=2))
        except:
            print("Response Content:\n", response.text)
    except Exception as e:
        print("Failed to post:", e)
