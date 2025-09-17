from flask import Flask, request, jsonify, send_file
import pandas as pd
import io
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def clean_csv_data(df):
    """
    Clean staff task report data and extract only specified columns.
    
    Parameters:
    df (pd.DataFrame): Input dataframe
    
    Returns:
    pd.DataFrame: Cleaned dataframe with selected columns
    """
    
    # Verify required columns exist
    required_columns = [
        'client_id', 'title', 'first_name', 'last_name', 
        'address_1', 'address_2', 'town', 'postcode',
        'employee_id', 'first_name_1', 'last_name_1',
        'start_date', 'start_time', 'end_date', 'end_time', 
        'week_number', 'client_type_text'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Create a new dataframe with only the columns we need
    cleaned_df = pd.DataFrame()
    
    # Extract and combine client name
    title = df['title'].fillna('').astype(str)
    first_name = df['first_name'].fillna('').astype(str)
    last_name = df['last_name'].fillna('').astype(str)
    
    # Combine client name parts, removing extra spaces
    cleaned_df['client_name'] = (title + ' ' + first_name + ' ' + last_name).str.strip()
    cleaned_df['client_name'] = cleaned_df['client_name'].str.replace(r'\s+', ' ', regex=True)
    
    # Extract and combine address
    address_parts = ['address_1', 'address_2', 'town', 'postcode']
    cleaned_df['address'] = df[address_parts].apply(
        lambda row: ', '.join([
            str(part).strip() 
            for part in row 
            if pd.notna(part) and str(part).strip() and str(part).strip() != 'nan'
        ]), axis=1
    )
    
    # Extract client ID
    cleaned_df['client_id'] = df['client_id']
    
    # Extract staff ID 
    cleaned_df['staff_id'] = df['employee_id']
    
    # Extract and combine staff name
    staff_first = df['first_name_1'].fillna('').astype(str)
    staff_last = df['last_name_1'].fillna('').astype(str)
    cleaned_df['staff_name'] = (staff_first + ' ' + staff_last).str.strip()
    cleaned_df['staff_name'] = cleaned_df['staff_name'].str.replace(r'\s+', ' ', regex=True)
    
    # Extract time-related columns
    cleaned_df['start_date'] = df['start_date']
    cleaned_df['start_time'] = df['start_time']
    cleaned_df['end_date'] = df['end_date'] 
    cleaned_df['end_time'] = df['end_time']
    cleaned_df['week_number'] = df['week_number']
    
    # Extract client type
    cleaned_df['client_type_text'] = df['client_type_text']
    
    # Clean up formatting
    text_columns = ['client_name', 'staff_name', 'address']
    for col in text_columns:
        if col in cleaned_df.columns:
            cleaned_df[col] = cleaned_df[col].str.strip()
            # Remove any remaining multiple spaces
            cleaned_df[col] = cleaned_df[col].str.replace(r'\s+', ' ', regex=True)
    
    # Remove completely empty rows (where all key fields are null/empty)
    cleaned_df = cleaned_df.dropna(subset=['client_id'], how='all')
    
    return cleaned_df

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "CSV Data Cleaner API",
        "version": "1.0.0",
        "endpoints": {
            "POST /clean-csv": "Upload CSV file to clean",
            "POST /clean-csv-json": "Send CSV data as JSON to clean",
            "GET /": "Health check"
        }
    })

@app.route('/clean-csv', methods=['POST'])
def clean_csv_file():
    """
    Clean CSV file uploaded via form data
    Expects: multipart/form-data with 'file' field containing CSV
    Returns: Cleaned CSV file or JSON with cleaned data
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check file extension
        if not file.filename.lower().endswith('.csv'):
            return jsonify({"error": "File must be a CSV"}), 400
        
        # Read CSV file
        try:
            df = pd.read_csv(file)
        except Exception as e:
            return jsonify({"error": f"Error reading CSV: {str(e)}"}), 400
        
        # Clean the data
        try:
            cleaned_df = clean_csv_data(df)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Error cleaning data: {str(e)}"}), 500
        
        # Determine response format
        response_format = request.form.get('format', 'csv').lower()
        
        if response_format == 'json':
            # Return as JSON
            result = {
                "status": "success",
                "original_rows": len(df),
                "cleaned_rows": len(cleaned_df),
                "columns": list(cleaned_df.columns),
                "data": cleaned_df.to_dict('records')
            }
            return jsonify(result)
        else:
            # Return as CSV file
            output = io.StringIO()
            cleaned_df.to_csv(output, index=False)
            output.seek(0)
            
            # Create a bytes buffer for the response
            mem = io.BytesIO()
            mem.write(output.getvalue().encode('utf-8'))
            mem.seek(0)
            
            return send_file(
                mem,
                as_attachment=True,
                download_name='cleaned_staff_report.csv',
                mimetype='text/csv'
            )
            
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/clean-csv-json', methods=['POST'])
def clean_csv_json():
    """
    Clean CSV data sent as JSON
    Expects: JSON with 'csv_data' field containing CSV as string
    Returns: JSON with cleaned data
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data or 'csv_data' not in data:
            return jsonify({"error": "No csv_data provided in JSON"}), 400
        
        csv_string = data['csv_data']
        
        # Read CSV from string
        try:
            df = pd.read_csv(io.StringIO(csv_string))
        except Exception as e:
            return jsonify({"error": f"Error reading CSV data: {str(e)}"}), 400
        
        # Clean the data
        try:
            cleaned_df = clean_csv_data(df)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Error cleaning data: {str(e)}"}), 500
        
        # Return cleaned data as JSON
        result = {
            "status": "success",
            "original_rows": len(df),
            "cleaned_rows": len(cleaned_df),
            "original_columns": len(df.columns),
            "cleaned_columns": len(cleaned_df.columns),
            "columns": list(cleaned_df.columns),
            "summary": {
                "unique_clients": cleaned_df['client_id'].nunique(),
                "unique_staff": cleaned_df['staff_id'].nunique(),
                "client_types": cleaned_df['client_type_text'].value_counts().dropna().to_dict()
            },
            "data": cleaned_df.to_dict('records')
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
