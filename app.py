#!/usr/bin/env python3
"""
CSV Data Cleaner API - Complete Version with Debug
Maps current CSV format to Supabase structure
"""

from flask import Flask, request, jsonify
import csv
import io
import os
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def clean_csv_data(csv_content):
    """Clean Client Task Report CSV format and map to Supabase structure"""
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    if not rows:
        raise ValueError("No data found in CSV")
    
    # Check for Client Task Report format columns
    required = ['client_id', 'client_first_name', 'client_last_name', 'carer_name', 
               'task_date', 'start_time', 'end_time', 'week_no', 'dayname', 'address']
    
    first_row = rows[0]
    missing = [col for col in required if col not in first_row]
    if missing:
        available = list(first_row.keys())
        raise ValueError(f"Missing columns: {missing}. Available: {available}")
    
    cleaned_rows = []
    
    for row in rows:
        # Skip rows with missing essential data
        client_id_val = row.get('client_id', '').strip()
        carer_name_val = row.get('carer_name', '').strip()
        
        if not client_id_val or not carer_name_val:
            continue
        
        # Skip cancelled visits
        if row.get('cancelled', '').upper() == 'Y':
            continue
            
        # Combine client name from separate fields
        client_first = (row.get('client_first_name') or '').strip()
        client_last = (row.get('client_last_name') or '').strip()
        client_name = f"{client_first} {client_last}".strip()
        
        # Clean staff name (remove extra spaces)
        staff_name = ' '.join(carer_name_val.split())
        
        # Get address (already combined in this format)
        address = (row.get('address') or '').strip()
        
        # Get day of week (already provided)
        day_of_week = (row.get('dayname') or '').strip()
        
        # Convert date from DD/MM/YYYY to YYYY-MM-DD
        task_date = row.get('task_date', '').strip()
        start_date_formatted = task_date
        
        if task_date and '/' in task_date:
            try:
                day, month, year = task_date.split('/')
                start_date_formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except:
                pass
        
        # Convert values safely
        try:
            client_id_int = int(client_id_val) if client_id_val.strip() else 0
        except:
            client_id_int = 0
            
        try:
            week_num = int(row.get('week_no', 0)) if row.get('week_no', '').strip() else 0
        except:
            week_num = 0
        
        # Create the cleaned row in Supabase format
        cleaned_row = {
            'staff_id': None,  # Not available - will need Airtable lookup by staff_name
            'staff_name': staff_name,
            'start_date': start_date_formatted,
            'day_of_week': day_of_week,
            'start_time': row.get('start_time', ''),
            'end_time': row.get('end_time', ''),
            'client_id': client_id_int,
            'client_name': client_name,
            'address': address,
            'client_type_text': row.get('client_type', ''),
            'week_number': week_num
        }
        
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "SSCG CSV Cleaner API - Complete Version",
        "status": "running",
        "version": "6.0.0",
        "input_format": "Current business CSV format",
        "output_format": "Supabase staff_schedules table",
        "note": "Filters out uncovered visits (employee_id = -2)",
        "endpoints": {
            "POST /clean": "Process CSV file or JSON data",
            "POST /debug": "Debug CSV structure and see column names"
        }
    })

@app.route('/debug', methods=['POST'])
def debug_columns():
    """Debug endpoint to see exactly what columns are available"""
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
        
        # Parse CSV to see columns and first few rows
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        if not rows:
            return jsonify({"error": "No data found in CSV"}), 400
        
        # Show first 3 rows with data
        sample_rows = []
        for i, row in enumerate(rows[:3]):
            # Only show non-empty values
            clean_row = {k: v for k, v in row.items() if v and str(v).strip() and str(v).strip().lower() != 'nan'}
            sample_rows.append(clean_row)
        
        return jsonify({
            "status": "debug_success",
            "total_columns": len(csv_reader.fieldnames or []),
            "columns": list(csv_reader.fieldnames or []),
            "total_rows": len(rows),
            "sample_data": sample_rows,
            "client_name_detection": {
                "has_client_first_name": 'client_first_name' in (csv_reader.fieldnames or []),
                "has_client_last_name": 'client_last_name' in (csv_reader.fieldnames or []),
                "has_client_name": 'client_name' in (csv_reader.fieldnames or []),
                "has_first_name": 'first_name' in (csv_reader.fieldnames or []),
                "has_last_name": 'last_name' in (csv_reader.fieldnames or []),
                "has_title": 'title' in (csv_reader.fieldnames or [])
            },
            "note": "This shows the actual structure of your CSV being processed"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            "format": "Current business CSV processed",
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
