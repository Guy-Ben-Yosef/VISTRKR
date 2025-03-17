import socket
import json
import time
import datetime
import argparse
import os

def read_data_from_file(csv_file):
    """Generator function to read data from CSV file line by line."""
    with open(csv_file, 'r') as file:
        for line in file:
            parts = line.strip().split(',')
            if len(parts) == 3:
                try:
                    timestamp, x, y = float(parts[0]), int(parts[1]), int(parts[2])
                    yield timestamp, x, y
                except ValueError:
                    print(f"Skipping invalid line: {line.strip()}")

def run_client(server_host, server_port, station_id, buffer_size=1024):
    """Run the client to send detection data to the server."""
    # Determine the CSV file name based on station_id
    csv_file = f'detection_{station_id}.csv'
    
    # Check if the CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found.")
        return
    
    # Create a socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect to the server
        print(f"Connecting to {server_host}:{server_port}...")
        client_socket.connect((server_host, server_port))
        print(f"Connected to server. Reading data from {csv_file}")
        
        data_stream = read_data_from_file(csv_file)
        first_timestamp = None
        
        for timestamp, x, y in data_stream:
            if first_timestamp is None:
                first_timestamp = timestamp
            
            # Wait until the correct time to send the data
            current_time = time.time()
            if current_time < timestamp:
                wait_time = timestamp - current_time
                if wait_time > 0.001:  # Only print for noticeable waits
                    print(f"Waiting {wait_time:.3f} seconds until {timestamp}")
                time.sleep(max(0, wait_time))
            
            # Create data packet
            data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "utc_timestamp": timestamp,
                "x": x,
                "y": y,
                "station_id": station_id
            }
            
            # Convert data to JSON and encode
            json_data = json.dumps(data)
            encoded_data = json_data.encode('utf-8')
            
            # Send data to the server
            client_socket.sendall(encoded_data)
            print(f"Sent data: x={x}, y={y}, time={timestamp}")
            
            # Wait for confirmation
            try:
                response = client_socket.recv(buffer_size)
                print(f"Server response: {response.decode('utf-8')}")
            except socket.error:
                print("No response from server, continuing...")
        
        print(f"Finished processing all data in {csv_file}")
    
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except ConnectionRefusedError:
        print(f"Connection to {server_host}:{server_port} refused. Is the server running?")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        client_socket.close()
        print("Client closed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detection data client")
    parser.add_argument("--server", default="192.168.1.149", help="Server IP address")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--station", required=True, help="Station ID (required)")
    
    args = parser.parse_args()
    
    run_client(args.server, args.port, args.station)