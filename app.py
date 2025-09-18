#!/usr/bin/env python3
"""
CSV Data Cleaner API - Final Correct Version
Simple field mapping for FinalSSCG.csv to Supabase format
"""

from flask import Flask, request, jsonify
import csv
import io
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def clean_csv_data(csv_content):
    """Clean FinalSSCG CSV data - simple field mapping"""
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    if not rows:
        raise ValueError("No data found in CSV")
    
    # Check for FinalSSCG format
    required = ['client_id', 'client_first_name', 'client_last_name', 'client_type', 
               'address', 'week_no', 'dayname', 'task_date', 'start_time', 'end_time',
               'staff_ID', 'staff_name']
    
    first_row = rows[0]
    missing = [col for col in required if col not in first_row]
    if missing:
        available = list(first_row.keys())
        raise ValueError(f"Missing columns: {missing}. Available: {available}")
    
    cleaned_rows = []
    
    for row in rows:
        # Skip rows with missing essential data
        if not row.get('client_id') or not row.get('staff_ID'):
            continue
            
        # Combine client name (first_name + last_name)
        first_name = (row.get('client_first_name') or '').strip()
        last_name = (row.get('client_last_name') or '').strip()
        client_name = f"{first_name} {last_name}".strip()
        
        # Get staff name (remove any titles if present)
        staff_name = (row.get('staff_name') or '').strip()
        titles = ['Miss', 'Ms', 'Mr', 'Mrs', 'Dr', 'Prof']
        for title in titles:
            if staff_name.startswith(title + ' '):
                staff_name = staff_name[len(title):].strip()
        
        # Convert date format from DD/MM/YYYY to YYYY-MM-DD for Supabase
        start_date = row.get('task_date', '')
        if '/' in start_date:
            try:
                day, month, year = start_date.split('/')
                start_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except:
                pass  # Keep original if conversion fails
        
        cleaned_row = {
            'staff_id': int(float(row.get('staff_ID', 0))),  # Convert float to int
            'staff_name': staff_name,
            'start_date': start_date,
            'day_of_week': row.get('dayname', ''),
            'start_time': row.get('start_time', ''),
            'end_time': row.get('end_time', ''),
            'client_id': int(row.get('client_id', 0)),
            'client_name': client_name,
            'address': row.get('address', ''),
            'client_type_text': row.get('client_type', ''),
            'week_number': int(row.get('week_no', 0))
        }
        
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "SSCG CSV Cleaner API",
        "status": "running",
        "version": "4.0.0",
        "expected_format": "FinalSSCG.csv",
        "output_format": "Supabase staff_schedules table",
        "endpoints": {
            "POST /clean": "Upload CSV file or send as JSON"
        }
    })

@app.route('/clean', methods=['POST'])
def clean_data():
    try:
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename and file.filename.endswith('.csv'):
                csv_content = file.read().decode('utf-8')
            else:
                return jsonify({"error": "Please upload a CSV file"}), 400
                
        # Handle JSON data
        elif request.is_json:
            data = request.get_json()
            if 'csv_data' in data:
                csv_content = data['csv_data']
            else:
                return jsonify({"error": "Send csv_data in JSON"}), 400
        else:
            return jsonify({"error": "Send CSV file or JSON data"}), 400
        
        # Parse original data for stats
        original_reader = csv.DictReader(io.StringIO(csv_content))
        original_rows = list(original_reader)
        original_columns = len(original_reader.fieldnames) if original_reader.fieldnames else 0
        
        # Clean the data
        cleaned_data = clean_csv_data(csv_content)
        
        # Calculate stats
        unique_clients = len(set(row['client_id'] for row in cleaned_data if row['client_id']))
        unique_staff = len(set(row['staff_id'] for row in cleaned_data if row['staff_id']))
        
        # Return results in format ready for Supabase
        return jsonify({
            "status": "success",
            "format": "FinalSSCG.csv processed",
            "original_rows": len(original_rows),
            "cleaned_rows": len(cleaned_data),
            "original_columns": original_columns,
            "cleaned_columns": 11,  # Fixed number for Supabase table
            "summary": {
                "unique_clients": unique_clients,
                "unique_staff": unique_staff,
                "date_range": f"{min(row['start_date'] for row in cleaned_data if row['start_date'])} to {max(row['start_date'] for row in cleaned_data if row['start_date'])}" if cleaned_data else "No dates"
            },
            "data": cleaned_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
