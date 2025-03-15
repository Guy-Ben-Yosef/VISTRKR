import socket
import json
import time
import random
import datetime
import platform
import uuid
import os
import sys

# Configuration - MODIFY THESE SETTINGS
SERVER_HOST = '192.168.1.X'  # ← CHANGE THIS to your Mac's IP address
SERVER_PORT = 8000
BUFFER_SIZE = 1024
SEND_INTERVAL = 1  # seconds between data transmissions
MAX_RETRIES = 5    # number of connection retries
RETRY_DELAY = 5    # seconds between retries

# Generate a unique ID for this client
def get_client_id():
    # Try to use the MAC address
    try:
        mac = uuid.getnode()
        return f"rpi_{mac:012x}"
    except:
        # Fallback to hostname + random string
        hostname = platform.node()
        random_id = uuid.uuid4().hex[:6]
        return f"rpi_{hostname}_{random_id}"

CLIENT_ID = get_client_id()

# Function to collect data (replace with your actual data collection code)
def collect_data():
    # Example data - replace with your sensor readings or other data
    data = {
        "client_id": CLIENT_ID,
        "client_timestamp": datetime.datetime.now().isoformat(),
        "hostname": platform.node(),
        "system": platform.system(),
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(40, 60), 2),
        "pressure": round(random.uniform(990, 1010), 2),
        "cpu_temp": get_cpu_temperature(),
        "sequence": 0  # Will be incremented for each message
    }
    return data

# Get Raspberry Pi CPU temperature
def get_cpu_temperature():
    try:
        # This works on Raspberry Pi
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
            return round(temp, 2)
    except:
        pass
    return None

# Connect to server with retry logic
def connect_to_server():
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Create a socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Set timeout for operations
            client_socket.settimeout(10)
            
            # Connect to the server
            print(f"Connecting to {SERVER_HOST}:{SERVER_PORT}...")
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            print(f"Connected to server as {CLIENT_ID}")
            
            return client_socket
        
        except (socket.error, socket.timeout) as e:
            retry_count += 1
            print(f"Connection attempt {retry_count} failed: {e}")
            
            if retry_count >= MAX_RETRIES:
                print(f"Failed to connect after {MAX_RETRIES} attempts")
                return None
            
            print(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

def main():
    # Initial connection
    client_socket = connect_to_server()
    if not client_socket:
        print("Could not connect to server. Exiting.")
        sys.exit(1)
    
    sequence = 0
    
    try:
        # Main loop for sending data
        while True:
            try:
                # Collect data
                data = collect_data()
                data["sequence"] = sequence
                sequence += 1
                
                # Convert data to JSON and encode
                json_data = json.dumps(data)
                encoded_data = json_data.encode('utf-8')
                
                # Send data to the server
                client_socket.sendall(encoded_data)
                print(f"Sent data #{sequence-1}: {data}")
                
                # Wait for confirmation
                response = client_socket.recv(BUFFER_SIZE)
                decoded_response = json.loads(response.decode('utf-8'))
                print(f"Server response: {decoded_response}")
                
                # Wait before sending the next data point
                time.sleep(SEND_INTERVAL)
            
            except (socket.error, socket.timeout) as e:
                print(f"Connection error: {e}")
                print("Attempting to reconnect...")
                
                # Close old socket
                try:
                    client_socket.close()
                except:
                    pass
                
                # Try to reconnect
                client_socket = connect_to_server()
                if not client_socket:
                    print("Failed to reconnect. Exiting.")
                    break
    
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Clean up
        try:
            client_socket.close()
        except:
            pass
        print("Client closed")

if __name__ == "__main__":
    main()