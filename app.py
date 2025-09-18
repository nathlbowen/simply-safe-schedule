#!/usr/bin/env python3
"""
CSV Data Cleaner API - For Current Rota CSV Format
Maps current CSV (rota_id, carer_id, employee_id) to Supabase format
"""

from flask import Flask, request, jsonify
import csv
import io
import os
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def clean_csv_data(csv_content):
    """Clean current rota CSV format and map to Supabase structure"""
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    if not rows:
        raise ValueError("No data found in CSV")
    
    # Check for current format - these are the columns we actually have
    required = ['client_id', 'title', 'first_name', 'last_name', 'address_1', 
               'address_2', 'town', 'postcode', 'employee_id', 'start_date', 
               'start_time', 'end_date', 'end_time', 'week_number', 'client_type_text']
    
    first_row = rows[0]
    missing = [col for col in required if col not in first_row]
    if missing:
        available = list(first_row.keys())
        raise ValueError(f"Missing columns: {missing}. Available: {available}")
    
    cleaned_rows = []
    
    for row in rows:
        # Skip rows with missing essential data
        if not row.get('client_id') or not row.get('employee_id'):
            continue
        
        # Skip if employee_id is -2 (uncovered visits)
        if str(row.get('employee_id', '')).strip() == '-2':
            continue
            
        # Combine client name from title, first_name, last_name
        title = (row.get('title') or '').strip()
        first_name = (row.get('first_name') or '').strip()
        last_name = (row.get('last_name') or '').strip()
        
        # Remove title from client name (these are client titles, not staff)
        client_name = f"{first_name} {last_name}".strip()
        
        # Combine address from components
        address_parts = []
        for part in [row.get('address_1'), row.get('address_2'), row.get('town'), row.get('postcode')]:
            if part and str(part).strip() and str(part).strip().lower() not in ['nan', '']:
                address_parts.append(str(part).strip())
        address = ', '.join(address_parts)
        
        # Calculate day of week from start_date
        day_of_week = None
        start_date_formatted = row.get('start_date', '')
        
        if start_date_formatted:
            try:
                # Convert DD/MM/YYYY to YYYY-MM-DD and calculate day of week
                if '/' in start_date_formatted:
                    day, month, year = start_date_formatted.split('/')
                    date_obj = datetime(int(year), int(month), int(day))
                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    day_of_week = days[date_obj.weekday()]
                    start_date_formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except:
                pass
        
        # Create the cleaned row in Supabase format
        cleaned_row = {
            'staff_id': int(row.get('employee_id', 0)),
            'staff_name': None,  # Not available, will need lookup from Airtable
            'start_date': start_date_formatted,
            'day_of_week': day_of_week,
            'start_time': row.get('start_time', ''),
            'end_time': row.get('end_time', ''),
            'client_id': int(row.get('client_id', 0)),
            'client_name': client_name,
            'address': address,
            'client_type_text': row.get('client_type_text', ''),
            'week_number': int(row.get('week_number', 0))
        }
        
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "SSCG CSV Cleaner API - Current Format",
        "status": "running",
        "version": "5.0.0",
        "input_format": "Current rota CSV (rota_id, carer_id, employee_id)",
        "output_format": "Supabase staff_schedules table",
        "note": "Filters out uncovered visits (employee_id = -2)",
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
        
        # Return results
        return jsonify({
            "status": "success",
            "format": "Current rota CSV processed",
            "original_rows": len(original_rows),
            "cleaned_rows": len(cleaned_data),
            "filtered_out": len(original_rows) - len(cleaned_data),
            "original_columns": original_columns,
            "cleaned_columns": 11,
            "summary": {
                "unique_clients": unique_clients,
                "unique_staff": unique_staff,
                "needs_staff_lookup": "Yes - staff_name is null, requires Airtable lookup"
            },
            "data": cleaned_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
