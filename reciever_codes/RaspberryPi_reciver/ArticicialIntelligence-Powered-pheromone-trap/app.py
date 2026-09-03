
from flask import Flask, render_template, request, jsonify
from services.data_service import get_all_fields, get_field_details, get_all_images, get_system_trend, get_latest_capture, save_real_capture
import os
import uuid
from datetime import datetime
import cv2
from ultralytics import YOLO

app = Flask(__name__)

# Initialize ML model
# Wait for best.pt to be placed here, or fallback to yolov8n.pt if not found just to not crash
MODEL_PATH = "pest_model/weights/best.pt"
try:
    if os.path.exists(MODEL_PATH):
        model = YOLO(MODEL_PATH)
        print("Loaded customized YOLO model from", MODEL_PATH)
    else:
        model = YOLO("yolov8n.pt")
        print("Fallback to base yolov8n.pt")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

@app.route('/')
def landing():
    return render_template('landing.html', page='landing')

@app.route('/dashboard')
def dashboard():
    fields = get_all_fields()
    
    # System-wide stats
    total_fields = len(fields)
    total_traps = sum(f['trap_count'] for f in fields)
    total_pest_24h = sum(f['pest_24h'] for f in fields)
    
    severity = "Low"
    if total_pest_24h > 200: severity = "Moderate"
    if total_pest_24h > 600: severity = "High"
    if total_pest_24h > 1000: severity = "Critical"
    
    stats = {
        "total_fields": total_fields,
        "total_traps": total_traps,
        "pest_24h": total_pest_24h,
        "severity": severity
    }
    
    trend_dates, trend_counts = get_system_trend()
    
    return render_template('dashboard.html', page='dashboard', stats=stats, trend_labels=trend_dates, trend_data=trend_counts)

@app.route('/technology')
def technology():
    return render_template('technology.html', page='technology')

@app.route('/fields')
def fields_list():
    fields = get_all_fields()
    return render_template('fields.html', page='fields', fields=fields)

@app.route('/fields/<field_id>')
def field_detail(field_id):
    field = get_field_details(field_id)
    if not field:
        return "Field not found", 404
    return render_template('field.html', page='fields', field=field)

@app.route('/images')
def images():
    image_list = get_all_images()
    return render_template('images.html', page='images', images=image_list)

@app.route('/developers')
def developers():
    return render_template('developers.html', page='developers')

@app.route('/upload', methods=['POST'])
def upload():
    # Real image upload from ESP32
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image part"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
        
    field_id = request.form.get('field_id', 'Unknown_Field')
    trap_id = request.form.get('trap_id', 'Unknown_Trap')
    
    # Save the original image uniquely
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gallery_dir = os.path.join(base_dir, "static", "img", "gallery")
    os.makedirs(gallery_dir, exist_ok=True)
    
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.jpg"
    filepath = os.path.join(gallery_dir, unique_filename)
    file.save(filepath)
    
    # Run YOLO Inference
    current_count = 0
    if model is not None:
        try:
            results = model.predict(filepath, conf=0.25)
            # results is a list of Results objects. We take the first one.
            result = results[0]
            current_count = len(result.boxes)
            
            # Save the image with bounding boxes drawn over it
            annotated_img = result.plot()
            cv2.imwrite(filepath, annotated_img)
        except Exception as e:
            print(f"Inference error: {e}")
            return jsonify({"status": "error", "message": f"Inference error: {e}"}), 500
    
    # Calculate difference
    previous_count = get_latest_capture(field_id, trap_id)
    difference = current_count - previous_count
    
    # Create the URL that the frontend can load to see this image
    image_url = f"/static/img/gallery/{unique_filename}"
    
    # Update the local CSV logs
    save_real_capture(field_id, trap_id, current_count, difference, image_url)
    
    return jsonify({
        "status": "success", 
        "message": "Image processed successfully",
        "current_count": current_count,
        "previous_count": previous_count,
        "difference": difference,
        "image_url": image_url
    }), 200

if __name__ == '__main__':
    # Hosted on 0.0.0.0 to be accessible via Tunnel/Network
    app.run(host='0.0.0.0', port=5001, debug=False)
