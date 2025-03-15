import socket
import json
import datetime

HOST = '0.0.0.0'  # Listen on all available interfaces
PORT = 8000
BUFFER_SIZE = 1024

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print(f"[{datetime.datetime.now()}] Server listening on {HOST}:{PORT}")

try:
    client_socket, client_address = server_socket.accept()
    print(f"[{datetime.datetime.now()}] Connected to {client_address}")
    
    while True:
        # Receive data from client
        data = client_socket.recv(BUFFER_SIZE)
        
        if not data:
            print(f"[{datetime.datetime.now()}] Client disconnected")
            break
        
        # Decode and process the data
        try:
            decoded_data = data.decode('utf-8')
            json_data = json.loads(decoded_data)
            timestamp = datetime.datetime.now()
            print(f"[{timestamp}] Received data: {json_data}")
                     
            # Send confirmation back to the client
            client_socket.sendall("Data received".encode('utf-8'))
            
        except json.JSONDecodeError:
            print(f"[{datetime.datetime.now()}] Received non-JSON data: {decoded_data}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Error processing data: {e}")

except KeyboardInterrupt:
    print("\nServer shutting down...")
finally:
    # Clean up
    if 'client_socket' in locals():
        client_socket.close()
    server_socket.close()
    print("Server closed")