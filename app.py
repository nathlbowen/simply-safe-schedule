#!/usr/bin/env python3
"""
CSV Data Cleaner API - No Pandas Version
Simple CSV processing without pandas dependency
"""

from flask import Flask, request, jsonify
import csv
import io
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def clean_csv_data(csv_content):
    """Clean staff task report data using built-in csv module"""
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    if not rows:
        raise ValueError("No data found in CSV")
    
    # Check required columns
    required = ['client_id', 'title', 'first_name', 'last_name', 'address_1', 
               'address_2', 'town', 'postcode', 'employee_id', 'first_name_1', 
               'last_name_1', 'start_date', 'start_time', 'end_date', 'end_time', 
               'week_number', 'client_type_text']
    
    first_row = rows[0]
    missing = [col for col in required if col not in first_row]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    cleaned_rows = []
    
    for row in rows:
        # Skip rows with missing client_id
        if not row.get('client_id'):
            continue
            
        # Combine client name
        title = (row.get('title') or '').strip()
        first_name = (row.get('first_name') or '').strip()
        last_name = (row.get('last_name') or '').strip()
        client_name = ' '.join([title, first_name, last_name]).strip()
        client_name = ' '.join(client_name.split())  # Remove extra spaces
        
        # Combine address
        address_parts = []
        for part in [row.get('address_1'), row.get('address_2'), row.get('town'), row.get('postcode')]:
            if part and str(part).strip() and str(part).strip().lower() != 'nan':
                address_parts.append(str(part).strip())
        address = ', '.join(address_parts)
        
        # Combine staff name
        staff_first = (row.get('first_name_1') or '').strip()
        staff_last = (row.get('last_name_1') or '').strip()
        staff_name = ' '.join([staff_first, staff_last]).strip()
        staff_name = ' '.join(staff_name.split())  # Remove extra spaces
        
        cleaned_row = {
            'client_name': client_name,
            'address': address,
            'client_id': row.get('client_id'),
            'staff_id': row.get('employee_id'),
            'staff_name': staff_name,
            'start_date': row.get('start_date'),
            'start_time': row.get('start_time'),
            'end_date': row.get('end_date'),
            'end_time': row.get('end_time'),
            'week_number': row.get('week_number'),
            'client_type_text': row.get('client_type_text')
        }
        
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "CSV Data Cleaner API",
        "status": "running",
        "version": "1.0.0",
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
            "original_rows": len(original_rows),
            "cleaned_rows": len(cleaned_data),
            "original_columns": original_columns,
            "cleaned_columns": 11,
            "summary": {
                "unique_clients": unique_clients,
                "unique_staff": unique_staff
            },
            "data": cleaned_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
