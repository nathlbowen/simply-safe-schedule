def clean_rota_schedule_data(rows):
    """Clean rota/schedule data (current CSV format)"""
    required = ['client_id', 'title', 'first_name', 'last_name', 'address_1', 
               'address_2', 'town', 'postcode', 'carer_id', 'start_date', 
               'start_time', 'end_date', 'end_time', 'week_number', 'client_type_text']
    
    first_row = rows[0]
    missing = [col for col in required if col not in first_row]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    cleaned_rows = []
    for row in rows:
        if not row.get('client_id'):
            continue
            
        # Combine client name
        title = (row.get('title') or '').strip()
        first_name = (row.get('first_name') or '').strip()
        last_name = (row.get('last_name') or '').strip()
        client#!/usr/bin/env python3
"""
CSV Data Cleaner API - Flexible version
Handles both Staff Task Report and Client Task Report formats
"""

from flask import Flask, request, jsonify
import csv
import io
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def detect_csv_format(first_row):
    """Detect which CSV format we're dealing with"""
    # Check for Client Task Report format
    if 'client_first_name' in first_row and 'client_last_name' in first_row and 'carer_name' in first_row:
        return 'client_task_report'
    # Check for Staff Task Report format (with staff names)
    elif 'first_name' in first_row and 'last_name' in first_row and 'first_name_1' in first_row:
        return 'staff_task_report'
    # Check for Rota/Schedule format (the current CSV)
    elif 'rota_id' in first_row and 'carer_id' in first_row and 'client_id' in first_row:
        return 'rota_schedule'
    else:
        return 'unknown'

def clean_client_task_data(rows):
    """Clean client task report data"""
    required = ['client_id', 'client_first_name', 'client_last_name', 'address', 
               'carer_name', 'task_date', 'start_time', 'end_time', 
               'week_no', 'dayname', 'client_type']
    
    first_row = rows[0]
    missing = [col for col in required if col not in first_row]
    if missing:
        # Try alternative column names that might exist
        alt_required = ['client_id', 'client_first_name', 'client_last_name', 'address']
        alt_missing = [col for col in alt_required if col not in first_row]
        if alt_missing:
            raise ValueError(f"Missing essential client columns: {alt_missing}")
    
    cleaned_rows = []
    for row in rows:
        if not row.get('client_id'):
            continue
            
        # Combine client name (NO titles)
        first_name = (row.get('client_first_name') or '').strip()
        last_name = (row.get('client_last_name') or '').strip()
        client_name = ' '.join([first_name, last_name]).strip()
        client_name = ' '.join(client_name.split())  # Remove extra spaces
        
        # Get carer name and remove titles
        carer_name = (row.get('carer_name') or '').strip()
        # Remove titles from carer name
        titles = ['Miss', 'Ms', 'Mr', 'Mrs', 'Dr', 'Prof']
        for title in titles:
            if carer_name.startswith(title + ' '):
                carer_name = carer_name[len(title):].strip()
        
        # Calculate day of week from task_date if dayname not available
        day_of_week = row.get('dayname')
        if not day_of_week and row.get('task_date'):
            try:
                from datetime import datetime
                # Assuming DD/MM/YYYY or YYYY-MM-DD format
                date_str = row.get('task_date')
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts[0]) == 4:  # YYYY/MM/DD
                        year, month, day = parts
                    else:  # DD/MM/YYYY
                        day, month, year = parts
                else:  # YYYY-MM-DD
                    year, month, day = date_str.split('-')
                
                date_obj = datetime(int(year), int(month), int(day))
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_of_week = days[date_obj.weekday()]
            except:
                pass
        
        cleaned_row = {
            'client_name': client_name,
            'address': (row.get('address') or '').strip(),
            'client_id': row.get('client_id'),
            'staff_id': None,  # Not available in this CSV format
            'staff_name': carer_name,  # Carer name without titles
            'start_date': row.get('task_date'),
            'start_time': row.get('start_time'),
            'end_date': row.get('task_date'),  # Same as start_date for single day tasks
            'end_time': row.get('end_time'),
            'week_number': row.get('week_no'),
            'day_of_week': day_of_week,
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

def clean_rota_schedule_data(rows):
    """Clean rota/schedule data (current CSV format with rota_id, carer_id)"""
    # Looking at the actual columns from the error message
    required = ['client_id', 'title', 'first_name', 'last_name', 'address_1', 
               'address_2', 'town', 'postcode', 'carer_id', 'start_date', 
               'start_time', 'end_date', 'end_time', 'week_number', 'client_type_text']
    
    first_row = rows[0]
    missing = [col for col in required if col not in first_row]
    if missing:
        # More flexible - only require essential columns
        essential = ['client_id', 'start_date', 'start_time', 'end_date', 'end_time']
        missing_essential = [col for col in essential if col not in first_row]
        if missing_essential:
            raise ValueError(f"Missing essential columns: {missing_essential}")
    
    cleaned_rows = []
    for row in rows:
        if not row.get('client_id'):
            continue
            
        # Combine client name (NOT staff name)
        title = (row.get('title') or '').strip()
        first_name = (row.get('first_name') or '').strip() 
        last_name = (row.get('last_name') or '').strip()
        client_name = ' '.join([title, first_name, last_name]).strip()
        client_name = ' '.join(client_name.split())  # Remove extra spaces
        
        # Combine address
        address_parts = []
        for part in [row.get('address_1'), row.get('address_2'), row.get('town'), row.get('postcode')]:
            if part and str(part).strip() and str(part).strip().lower() not in ['nan', '']:
                address_parts.append(str(part).strip())
        address = ', '.join(address_parts)
        
        # Calculate day of week from start_date
        day_of_week = None
        if row.get('start_date'):
            try:
                # Assuming DD/MM/YYYY format
                date_parts = row.get('start_date').split('/')
                if len(date_parts) == 3:
                    day, month, year = date_parts
                    from datetime import datetime
                    date_obj = datetime(int(year), int(month), int(day))
                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    day_of_week = days[date_obj.weekday()]
            except:
                pass
        
        cleaned_row = {
            'client_name': client_name,
            'address': address,
            'client_id': row.get('client_id'),
            'staff_id': row.get('carer_id'),  # carer_id maps to staff_id
            'staff_name': None,  # No staff name in this format, will need Airtable lookup
            'start_date': row.get('start_date'),
            'start_time': row.get('start_time'),
            'end_date': row.get('end_date'),
            'end_time': row.get('end_time'),
            'week_number': row.get('week_number'),
            'day_of_week': day_of_week,
            'client_type_text': row.get('client_type_text')
        }
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows
    """Clean staff task report data (original format)"""
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
        if not row.get('client_id'):
            continue
            
        # Combine client name
        title = (row.get('title') or '').strip()
        first_name = (row.get('first_name') or '').strip()
        last_name = (row.get('last_name') or '').strip()
        client_name = ' '.join([title, first_name, last_name]).strip()
        
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
        
        cleaned_row = {
            'client_name': ' '.join(client_name.split()),
            'address': address,
            'client_id': row.get('client_id'),
            'staff_id': row.get('employee_id'),
            'staff_name': ' '.join(staff_name.split()),
            'start_date': row.get('start_date'),
            'start_time': row.get('start_time'),
            'end_date': row.get('end_date'),
            'end_time': row.get('end_time'),
            'week_number': row.get('week_number'),
            'day_of_week': None,  # Not available in this format
            'client_type_text': row.get('client_type_text')
        }
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows

def clean_csv_data(csv_content):
    """Main function to clean CSV data - detects format automatically"""
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    if not rows:
        raise ValueError("No data found in CSV")
    
    # Detect CSV format
    csv_format = detect_csv_format(rows[0])
    
    if csv_format == 'client_task_report':
        return clean_client_task_data(rows), csv_format
    elif csv_format == 'staff_task_report':
        return clean_staff_task_data(rows), csv_format
    elif csv_format == 'rota_schedule':
        return clean_rota_schedule_data(rows), csv_format
    else:
        available_columns = list(rows[0].keys())
        raise ValueError(f"Unknown CSV format. Available columns: {available_columns}")

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "Flexible CSV Data Cleaner API",
        "status": "running",
        "version": "3.0.0",
        "supported_formats": [
            "Client Task Report (client_first_name, client_last_name, carer_name, etc.)",
            "Staff Task Report (first_name, last_name, first_name_1, last_name_1, etc.)"
        ],
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
        cleaned_data, csv_format = clean_csv_data(csv_content)
        
        # Calculate stats
        unique_clients = len(set(row['client_id'] for row in cleaned_data if row['client_id']))
        unique_staff = len(set(row['staff_name'] for row in cleaned_data if row['staff_name']))
        
        # Return results
        return jsonify({
            "status": "success",
            "csv_format_detected": csv_format,
            "original_rows": len(original_rows),
            "cleaned_rows": len(cleaned_data),
            "original_columns": original_columns,
            "cleaned_columns": len(cleaned_data[0].keys()) if cleaned_data else 0,
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
