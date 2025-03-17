import os
import json
import datetime
import time
import argparse
from prettytable import PrettyTable

# Configuration
DATA_DIR = 'client_data'  # Same as in the server script

def list_clients():
    """List all clients that have connected to the server"""
    if not os.path.exists(DATA_DIR):
        print(f"Data directory '{DATA_DIR}' not found.")
        return
    
    files = os.listdir(DATA_DIR)
    # Look for both .txt files (from original server) and .json files
    client_files = [f for f in files if f.startswith('client_') and (f.endswith('.txt') or f.endswith('.json'))]
    
    if not client_files:
        print("No client data found.")
        return
    
    print(f"Found {len(client_files)} clients:")
    table = PrettyTable()
    table.field_names = ["#", "Client ID", "Hostname", "Last Update", "Data Size (KB)", "File Type"]
    
    for i, file in enumerate(client_files, 1):
        client_id = file.replace('client_', '').replace('.json', '').replace('.txt', '')
        file_path = os.path.join(DATA_DIR, file)
        file_type = "JSON" if file.endswith('.json') else "Text"
        
        # Get file size and modification time
        size = os.path.getsize(file_path)
        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # Try to get the client hostname from the data
        hostname = "Unknown"
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if file.endswith('.json'):
                    if content.startswith('[') and content.endswith(']'):
                        # Find first complete JSON object
                        data = json.loads(content)[0] if content != '[]' else {}
                        hostname = data.get('hostname', data.get('node', 'Unknown'))
                else:  # .txt file from original server
                    # Try to find a JSON string in the text file
                    for line in content.split('\n')[:10]:  # Look at first 10 lines
                        if '] {' in line:
                            json_part = line.split('] ', 1)[1]
                            try:
                                data = json.loads(json_part)
                                hostname = data.get('node', 'Unknown')
                                break
                            except:
                                continue
        except Exception as e:
            hostname = f"Error: {str(e)[:20]}..."
        
        table.add_row([i, client_id, hostname, mod_time, f"{size / 1024:.2f}", file_type])
    
    print(table)

def convert_txt_to_json(txt_file):
    """Convert a .txt file from the original server format to a .json file"""
    file_path = os.path.join(DATA_DIR, txt_file)
    json_path = os.path.join(DATA_DIR, txt_file.replace('.txt', '.json'))
    
    if not os.path.exists(file_path):
        print(f"File '{txt_file}' not found.")
        return None
    
    try:
        with open(file_path, 'r') as f:
            content = f.read().strip()
        
        json_entries = []
        for line in content.split('\n'):
            if '] {' in line:
                try:
                    # Extract timestamp and JSON part
                    timestamp_part, json_part = line.split('] ', 1)
                    timestamp = timestamp_part.strip('[')
                    
                    data = json.loads(json_part)
                    
                    # Add server timestamp to the data
                    data['server_timestamp'] = timestamp
                    
                    json_entries.append(data)
                except Exception as e:
                    print(f"Error parsing line: {e}")
                    continue
        
        # Write JSON data
        with open(json_path, 'w') as f:
            json.dump(json_entries, f, indent=2)
        
        print(f"Successfully converted {txt_file} to {txt_file.replace('.txt', '.json')}")
        print(f"Processed {len(json_entries)} entries")
        return json_path
    except Exception as e:
        print(f"Error converting file: {e}")
        return None

def view_client_data(client_file, entries=10, live=False):
    """View the most recent data for a specific client"""
    # Check file extension
    if not (client_file.endswith('.json') or client_file.endswith('.txt')):
        # Try both extensions
        json_path = os.path.join(DATA_DIR, f"{client_file}.json")
        txt_path = os.path.join(DATA_DIR, f"{client_file}.txt")
        
        if os.path.exists(json_path):
            client_file = f"{client_file}.json"
        elif os.path.exists(txt_path):
            client_file = f"{client_file}.txt"
        else:
            print(f"Client file '{client_file}' not found with either .json or .txt extension.")
            return
    
    file_path = os.path.join(DATA_DIR, client_file)
    
    if not os.path.exists(file_path):
        print(f"Client file '{client_file}' not found.")
        return
    
    # Convert .txt to .json if needed
    if client_file.endswith('.txt'):
        json_file = convert_txt_to_json(client_file)
        if json_file:
            file_path = json_file
        else:
            print("Could not convert text file to JSON. Displaying raw content:")
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                print(content)
            except Exception as e:
                print(f"Error reading file: {e}")
            return
    
    def display_data():
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content or content == '[]':
                    print("No data available for this client.")
                    return
                
                # Load JSON data
                data = json.loads(content)
                if not isinstance(data, list):
                    data = [data]  # Convert to list if it's a single object
                
                # Get the latest entries
                latest_entries = data[-entries:] if len(data) > entries else data
                
                # Create a table with common fields
                table = PrettyTable()
                
                # Determine columns dynamically from the first entry
                if latest_entries:
                    first_entry = latest_entries[0]
                    
                    # Basic columns - always show these if available
                    base_columns = ['server_timestamp', 'client_id', 'node']
                    columns = [col for col in base_columns if col in first_entry]
                    
                    # Important metrics - always show these if available
                    metric_columns = ['cpu_percent', 'memory_percent', 'temperature', 'disk_usage']
                    columns.extend([col for col in metric_columns if col in first_entry])
                    
                    # Add other sensor data columns (excluding system info)
                    excluded_fields = columns + ['system', 'release', 'version', 'machine', 'processor', 
                                              'timestamp', 'client_timestamp', 'hostname']
                    sensor_columns = [k for k in first_entry.keys() if k not in excluded_fields]
                    columns.extend(sensor_columns)
                    
                    # Set the table columns
                    table.field_names = columns
                    
                    # Add rows
                    for entry in latest_entries:
                        row = []
                        for col in columns:
                            value = entry.get(col, "N/A")
                            # Format numbers to be more readable
                            if isinstance(value, float):
                                row.append(f"{value:.2f}")
                            else:
                                row.append(value)
                        table.add_row(row)
                    
                    # Set alignment for numeric columns
                    for col in columns:
                        if any(metric in col for metric in ['percent', 'temp', 'usage', 'humid']):
                            table.align[col] = 'r'
                    
                    # Get client info for header
                    latest = latest_entries[-1]
                    hostname = latest.get('hostname', latest.get('node', 'Unknown'))
                    system_info = latest.get('system', '') + ' ' + latest.get('release', '')
                    
                    # Print with header
                    print(f"\n=== Client Data: {hostname} ===")
                    if system_info.strip():
                        print(f"System: {system_info.strip()}")
                    print(f"Entries: {len(latest_entries)} of {len(data)} total")
                    print(table)
                    
                    # Print timestamp of last update
                    if 'server_timestamp' in latest:
                        print(f"Last server update: {latest['server_timestamp']}")
                    elif 'timestamp' in latest:
                        print(f"Last client update: {datetime.datetime.fromtimestamp(latest['timestamp'])}")
                else:
                    print("No data available.")
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print("Try running with --convert option to fix the file format")
        except Exception as e:
            print(f"Error reading data: {e}")
    
    # Display once or continuously
    if live:
        print("Live monitoring mode (Ctrl+C to exit)...")
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')  # Clear screen
                display_data()
                print("\nRefreshing every 2 seconds... (Ctrl+C to exit)")
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nExiting live mode.")
    else:
        display_data()

def analyze_client_data(client_file):
    """Analyze client data to show trends and statistics"""
    file_path = os.path.join(DATA_DIR, client_file)
    
    if not os.path.exists(file_path):
        # Try adding extension
        if not client_file.endswith('.json'):
            client_file += '.json'
            file_path = os.path.join(DATA_DIR, client_file)
        
        if not os.path.exists(file_path):
            print(f"Client file '{client_file}' not found.")
            return
    
    try:
        with open(file_path, 'r') as f:
            content = f.read().strip()
        
        data = json.loads(content)
        if not isinstance(data, list):
            data = [data]
        
        if not data:
            print("No data available for analysis.")
            return
        
        # Identify numeric metrics for analysis
        metrics = {}
        for key in data[0].keys():
            if key not in ['server_timestamp', 'client_id', 'node', 'system', 'hostname', 'release', 
                          'version', 'machine', 'processor', 'timestamp', 'client_timestamp']:
                # Check if this is a numeric field
                for entry in data:
                    if key in entry and isinstance(entry[key], (int, float)):
                        if key not in metrics:
                            metrics[key] = []
                        metrics[key].append(entry[key])
        
        # Print analysis
        print(f"\n=== Data Analysis for {client_file} ===")
        print(f"Total data points: {len(data)}")
        if data[0].get('timestamp') and data[-1].get('timestamp'):
            start_time = datetime.datetime.fromtimestamp(data[0]['timestamp'])
            end_time = datetime.datetime.fromtimestamp(data[-1]['timestamp'])
            duration = end_time - start_time
            print(f"Time span: {duration} ({start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')})")
        
        print("\nMetric Analysis:")
        table = PrettyTable()
        table.field_names = ["Metric", "Min", "Max", "Avg", "Latest"]
        
        for metric, values in metrics.items():
            if values:
                min_val = min(values)
                max_val = max(values)
                avg_val = sum(values) / len(values)
                latest = values[-1]
                
                table.add_row([
                    metric,
                    f"{min_val:.2f}" if isinstance(min_val, float) else min_val,
                    f"{max_val:.2f}" if isinstance(max_val, float) else max_val,
                    f"{avg_val:.2f}" if isinstance(avg_val, float) else avg_val,
                    f"{latest:.2f}" if isinstance(latest, float) else latest
                ])
        
        print(table)
    
    except Exception as e:
        print(f"Error analyzing data: {e}")

def main():
    parser = argparse.ArgumentParser(description='View and analyze data from Raspberry Pi clients')
    parser.add_argument('--list', action='store_true', help='List all clients')
    parser.add_argument('--view', type=str, help='View data for a specific client')
    parser.add_argument('--entries', type=int, default=10, help='Number of entries to display')
    parser.add_argument('--live', action='store_true', help='Enable live monitoring mode')
    parser.add_argument('--analyze', type=str, help='Analyze client data to show trends')
    parser.add_argument('--convert', type=str, help='Convert a .txt file to .json format')
    
    args = parser.parse_args()
    
    # Install required package if not available
    try:
        import prettytable
    except ImportError:
        print("Installing required package: prettytable")
        os.system('pip install prettytable')
        print("Please run the command again.")
        return
    
    if args.list:
        list_clients()
    elif args.view:
        client_file = args.view
        # Add client_ prefix if not present
        if not client_file.startswith('client_'):
            client_file = f"client_{client_file}"
        view_client_data(client_file, args.entries, args.live)
    elif args.analyze:
        client_file = args.analyze
        if not client_file.startswith('client_'):
            client_file = f"client_{client_file}"
        if not client_file.endswith('.json'):
            client_file = f"{client_file}.json"
        analyze_client_data(client_file)
    elif args.convert:
        txt_file = args.convert
        if not txt_file.startswith('client_'):
            txt_file = f"client_{txt_file}"
        if not txt_file.endswith('.txt'):
            txt_file = f"{txt_file}.txt"
        convert_txt_to_json(txt_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()