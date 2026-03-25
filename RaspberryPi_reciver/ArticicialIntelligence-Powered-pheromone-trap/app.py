
from flask import Flask, render_template, request, jsonify
from services.data_service import get_all_fields, get_field_details, get_all_images, get_system_trend

app = Flask(__name__)

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
    # Stub for image upload from ESP32
    return jsonify({"status": "success", "message": "Image received (mock)"}), 200

if __name__ == '__main__':
    # Hosted on 0.0.0.0 to be accessible via Tunnel/Network
    app.run(host='0.0.0.0', port=5001, debug=False)
