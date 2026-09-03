
import os
import json
import pandas as pd
from datetime import datetime

import random

DATA_DIR = "pest_research_data"
FIELDS_DIR = os.path.join(DATA_DIR, "fields")

def ensure_todays_data():
    """Generates mock data for the last 7 days to ensure a smooth trend."""
    from datetime import timedelta
    
    if not os.path.exists(FIELDS_DIR):
        return

    # Generate dates for last 7 days
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]

    for field in os.listdir(FIELDS_DIR):
        traps_dir = os.path.join(FIELDS_DIR, field, "traps")
        if not os.path.exists(traps_dir): continue

        for trap in os.listdir(traps_dir):
            log_path = os.path.join(traps_dir, trap, "logs.csv")
            
            # Read existing logs to avoid duplicates
            existing_dates = set()
            if os.path.exists(log_path):
                try:
                    df = pd.read_csv(log_path)
                    if not df.empty:
                        # Extract YYYY-MM-DD from timestamp
                        existing_dates = set(df['timestamp'].apply(lambda x: x.split(' ')[0]))
                except: pass
            
            # Append missing days
            with open(log_path, 'a') as f:
                if os.path.getsize(log_path) == 0:
                    f.write("timestamp,pest_count,image_url\n")
                
                for d in dates:
                    if d in existing_dates: continue
                    
                    # Logic: Almost uniform data for history too
                    for h in range(0, 24, 2): # Every 2 hours
                        # Uniform distribution between 15 and 20
                        count = random.randint(15, 20)
                        
                        ts = f"{d} {h:02d}:00:00"
                        f.write(f"{ts},{count},/static/img/gallery/augment001.jpg\n")

def get_all_fields():
    ensure_todays_data() # Ensure data exists
    fields = []
    if not os.path.exists(FIELDS_DIR):
        return fields

    for field_name in os.listdir(FIELDS_DIR):
        field_path = os.path.join(FIELDS_DIR, field_name)
        if os.path.isdir(field_path):
            meta_path = os.path.join(field_path, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                    
                    # Calculate aggregate stats
                    traps = get_traps_for_field(field_name)
                    total_pest_24h = sum(t.get('pest_24h', 0) for t in traps)
                    
                    # Determine severity
                    severity = "Low"
                    if total_pest_24h > 100: severity = "Moderate"
                    if total_pest_24h > 300: severity = "High"
                    if total_pest_24h > 500: severity = "Critical"

                    meta['id'] = field_name
                    meta['trap_count'] = len(traps)
                    meta['pest_24h'] = total_pest_24h
                    meta['severity'] = severity
                    fields.append(meta)
    return fields

def get_field_details(field_id):
    field_path = os.path.join(FIELDS_DIR, field_id)
    if not os.path.exists(field_path):
        return None
    
    with open(os.path.join(field_path, "meta.json"), 'r') as f:
        meta = json.load(f)
    
    meta['id'] = field_id
    meta['traps'] = get_traps_for_field(field_id)
    
    # Aggregate stats
    meta['total_pest_24h'] = sum(t.get('pest_24h', 0) for t in meta['traps'])
    
    # Severity logic
    if meta['total_pest_24h'] > 500: meta['severity'] = "Critical"
    elif meta['total_pest_24h'] > 300: meta['severity'] = "High"
    elif meta['total_pest_24h'] > 100: meta['severity'] = "Moderate"
    else: meta['severity'] = "Low"

    return meta

def get_traps_for_field(field_id):
    traps = []
    traps_dir = os.path.join(FIELDS_DIR, field_id, "traps")
    if not os.path.exists(traps_dir):
        return traps
    
    for trap_id in os.listdir(traps_dir):
        trap_path = os.path.join(traps_dir, trap_id)
        if os.path.isdir(trap_path):
            meta_path = os.path.join(trap_path, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    trap_meta = json.load(f)
                
                # Get last 24h pest count from logs
                check_logs(trap_path, trap_meta)
                traps.append(trap_meta)
    return traps

def check_logs(trap_path, trap_meta):
    log_path = os.path.join(trap_path, "logs.csv")
    pest_24h = 0
    last_updated = "N/A"
    
    if os.path.exists(log_path):
        try:
            df = pd.read_csv(log_path)
            # Assuming 'timestamp' and 'pest_count' columns
            # Simple simulation: just take the sum of the last 6 entries (approx 24h if 4h intervals)
            if not df.empty:
                pest_24h = int(df.tail(6)['pest_count'].sum())
                last_updated = df.iloc[-1]['timestamp']
        except Exception:
            pass # Handle empty or malformed logs gracefully
            
    trap_meta['pest_24h'] = pest_24h
    trap_meta['last_updated'] = last_updated

def get_all_images():
    """
    Scans the 'static/img/gallery' directory for images and returns them.
    Sorts by modification time (newest first).
    """
    images = []
    import random
    
    # Use absolute path based on this file's location
    # services/data_service.py -> parent is services -> parent is project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    gallery_path = os.path.join(project_root, "static", "img", "gallery")
    
    # Create directory if it doesn't exist (safety check)
    if not os.path.exists(gallery_path):
        os.makedirs(gallery_path, exist_ok=True)
        return images

    # Supported extensions
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

    # Get real fields and traps to randomize from
    # We can use the get_all_fields() function or simple hardcoded list if that fails
    # Let's try to be dynamic but fail-safe
    possible_assignments = []
    try:
        fields = get_all_fields()
        for f in fields:
            # We need to list traps for this field.
            # get_all_fields returns objects with 'id'.
            # get_field_details(field_id) returns 'traps' array.
            # But get_all_fields calls get_traps_for_field internally but maybe doesn't return full trap list in 'traps' key?
            # It returns trap_count.
            # Let's call get_traps_for_field(f['id'])
            traps = get_traps_for_field(f['id'])
            for t in traps:
                # Trap object usually has 'id'
                if 'id' in t:
                    possible_assignments.append((f['id'], t['id']))
    except Exception:
        pass
        
    # Fallback if no fields/traps found
    if not possible_assignments:
        possible_assignments = [
            ("Apple Orchard A", "Trap-01"),
            ("Apple Orchard A", "Trap-02"), 
            ("Walnut Grove B", "Trap-05"),
            ("Saffron Field C", "Trap-09"),
            ("Cherry Garden D", "Trap-03")
        ]

    try:
        # List all files in the gallery directory
        files = [f for f in os.listdir(gallery_path) if f.lower().endswith(valid_extensions)]
        
        for filename in files:
            filepath = os.path.join(gallery_path, filename)
            
            # Get file stats for timestamp
            stats = os.stat(filepath)
            mod_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
            
            # Random assignment
            assigned_field, assigned_trap = random.choice(possible_assignments)
            
            images.append({
                "url": f"/static/img/gallery/{filename}",
                "field": assigned_field,
                "trap": assigned_trap,
                "timestamp": mod_time,
                "type": "Captured"
            })
            
        # Sort by timestamp descending (newest first)
        images.sort(key=lambda x: x['timestamp'], reverse=True)
        
    except Exception as e:
        print(f"Error scanning gallery: {e}")
        
    return images

def get_system_trend():
    """
    Aggregates pest counts across all fields for the last 7 days.
    Returns:
        dates: List of date strings (e.g. '2023-10-25')
        counts: List of total pest counts for each date
    """
    if not os.path.exists(FIELDS_DIR):
        return [], []

    # Dictionary to store daily totals: { 'YYYY-MM-DD': count }
    daily_stats = {}
    
    # Initialize last 7 days with 0
    now = datetime.now()
    from datetime import timedelta
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        daily_stats[d] = 0

    fields = os.listdir(FIELDS_DIR)
    for field in fields:
        field_path = os.path.join(FIELDS_DIR, field)
        if not os.path.isdir(field_path): continue
        
        traps_dir = os.path.join(field_path, "traps")
        if not os.path.exists(traps_dir): continue
        
        for trap in os.listdir(traps_dir):
            log_path = os.path.join(traps_dir, trap, "logs.csv")
            if os.path.exists(log_path):
                try:
                    df = pd.read_csv(log_path)
                    if not df.empty:
                        # Convert timestamp to date
                        df['date'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')
                        # Sum pest_count by date
                        daily_sums = df.groupby('date')['pest_count'].sum()
                        
                        for date, count in daily_sums.items():
                            if date in daily_stats:
                                daily_stats[date] += int(count)
                except Exception:
                    pass

    # Sort by date and separate into lists
    sorted_dates = sorted(daily_stats.keys())
    counts = [daily_stats[d] for d in sorted_dates]
    
    # Format labels (e.g., "Mon", "Oct 25" or just "Day -X")
    # For chart, simple date string is fine
    return sorted_dates, counts

def get_latest_capture(field_id, trap_id):
    """
    Returns the latest count for calculating the difference.
    """
    log_path = os.path.join(FIELDS_DIR, field_id, "traps", trap_id, "logs.csv")
    if not os.path.exists(log_path):
        return 0
    try:
        df = pd.read_csv(log_path)
        if df.empty:
            return 0
        return int(df.iloc[-1]['pest_count'])
    except:
        return 0

def save_real_capture(field_id, trap_id, current_count, difference, image_url):
    """
    Saves a real capture from the ESP32.
    It appends the new reading to the trap's logs.csv.
    """
    field_dir = os.path.join(FIELDS_DIR, field_id)
    trap_dir = os.path.join(field_dir, "traps", trap_id)
    
    # Ensure directories exist
    os.makedirs(trap_dir, exist_ok=True)
    
    # Ensure meta.json exists (create basic if not)
    meta_path = os.path.join(trap_dir, "meta.json")
    if not os.path.exists(meta_path):
        with open(meta_path, 'w') as f:
            json.dump({"id": trap_id, "name": trap_id, "status": "Active", "battery": "100%"}, f)
            
    # Also ensure field meta exists
    field_meta = os.path.join(field_dir, "meta.json")
    if not os.path.exists(field_meta):
        with open(field_meta, 'w') as f:
            json.dump({"name": field_id, "location": "Unknown", "crop": "Unknown"}, f)
    
    log_path = os.path.join(trap_dir, "logs.csv")
    is_new = not os.path.exists(log_path)
    
    with open(log_path, 'a') as f:
        # Check if difference column is missing
        if is_new or os.path.getsize(log_path) == 0:
            f.write("timestamp,pest_count,image_url,hourly_difference\n")
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp},{current_count},{image_url},{difference}\n")
        
    return True
