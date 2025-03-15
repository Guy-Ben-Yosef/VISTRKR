import socket
import json
import time
import datetime

SERVER_HOST = '192.168.1.149'  # ← CHANGE THIS to your Mac's IP address
SERVER_PORT = 8000
BUFFER_SIZE = 1024
CSV_FILE = 'detection_X3.csv'

def read_data_from_file():
    """Generator function to read data from CSV file line by line."""
    with open(CSV_FILE, 'r') as file:
        for line in file:
            parts = line.strip().split(',')
            if len(parts) == 3:
                timestamp, x, y = float(parts[0]), int(parts[1]), int(parts[2])
                yield timestamp, x, y

# Create a socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # Connect to the server
    print(f"Connecting to {SERVER_HOST}:{SERVER_PORT}...")
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    print("Connected to server")
    
    data_stream = read_data_from_file()
    first_timestamp = None
    
    for timestamp, x, y in data_stream:
        if first_timestamp is None:
            first_timestamp = timestamp
        
        # Wait until the correct time to send the data
        while time.time() < timestamp:
            time.sleep(0.001)  # Sleep a little to prevent busy-waiting
        
        # Create data packet
        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "x": x,
            "y": y
        }
        
        # Convert data to JSON and encode
        json_data = json.dumps(data)
        encoded_data = json_data.encode('utf-8')
        
        # Send data to the server
        client_socket.sendall(encoded_data)
        print(f"Sent data: {data}")
        
        # Wait for confirmation (optional)
        response = client_socket.recv(BUFFER_SIZE)
        print(f"Server response: {response.decode('utf-8')}")

except KeyboardInterrupt:
    print("\nClient shutting down...")
except ConnectionRefusedError:
    print(f"Connection to {SERVER_HOST}:{SERVER_PORT} refused. Is the server running?")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up
    client_socket.close()
    print("Client closed")
