#!/usr/bin/env python3
"""
CSV Data Cleaner API - Updated for Client Task Report format
Handles the new CSV structure with client_first_name, client_last_name, etc.
"""

from flask import Flask, request, jsonify
import csv
import io
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def clean_csv_data(csv_content):
    """Clean client task report data using built-in csv module"""
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    if not rows:
        raise ValueError("No data found in CSV")
    
    # Check required columns for the new format
    required = ['client_id', 'client_first_name', 'client_last_name', 'address', 
               'carer_name', 'task_date', 'start_time', 'end_time', 
               'week_no', 'dayname', 'client_type']
    
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
        first_name = (row.get('client_first_name') or '').strip()
        last_name = (row.get('client_last_name') or '').strip()
        client_name = ' '.join([first_name, last_name]).strip()
        client_name = ' '.join(client_name.split())  # Remove extra spaces
        
        # Get address (already combined in this CSV)
        address = (row.get('address') or '').strip()
        
        # Get staff/carer name
        staff_name = (row.get('carer_name') or '').strip()
        
        cleaned_row = {
            'client_name': client_name,
            'address': address,
            'client_id': row.get('client_id'),
            'staff_id': None,  # Not available in this CSV format
            'staff_name': staff_name,
            'start_date': row.get('task_date'),
            'start_time': row.get('start_time'),
            'end_date': row.get('task_date'),  # Same as start_date for single day tasks
            'end_time': row.get('end_time'),
            'week_number': row.get('week_no'),
            'day_of_week': row.get('dayname'),
            'client_type_text': row.get('client_type'),
            # Additional fields from the new CSV
            'visit_time': row.get('visit_time'),
            'charge': row.get('charge'),
            'service_name': row.get('service_name'),
            'completed': row.get('completed'),
            'cancelled': row.get('cancelled')
        }
        
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "CSV Data Cleaner API - Client Task Report",
        "status": "running",
        "version": "2.0.0",
        "supported_format": "Client Task Report CSV",
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
        unique_staff = len(set(row['staff_name'] for row in cleaned_data if row['staff_name']))
        
        # Additional stats for the new format
        total_visits = len(cleaned_data)
        completed_visits = len([row for row in cleaned_data if row.get('completed') == 'Y'])
        cancelled_visits = len([row for row in cleaned_data if row.get('cancelled') == 'Y'])
        
        # Return results
        return jsonify({
            "status": "success",
            "original_rows": len(original_rows),
            "cleaned_rows": len(cleaned_data),
            "original_columns": original_columns,
            "cleaned_columns": len(cleaned_data[0].keys()) if cleaned_data else 0,
            "summary": {
                "unique_clients": unique_clients,
                "unique_staff": unique_staff,
                "total_visits": total_visits,
                "completed_visits": completed_visits,
                "cancelled_visits": cancelled_visits
            },
            "data": cleaned_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
