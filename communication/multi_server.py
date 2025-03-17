import socket
import threading
import json
import time
from datetime import datetime
import os

class DataServer:
    def __init__(self, host='0.0.0.0', port=5000):
        """Initialize the server with host and port"""
        self.host = host  # Listen on all available interfaces
        self.port = port
        self.server_socket = None
        self.clients = {}  # Dictionary to track connected clients
        self.data_directory = "client_data"
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)
    
    def start(self):
        """Start the server and listen for connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set socket option to reuse address
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                self.server_socket.bind((self.host, self.port))
            except socket.error as e:
                if e.errno == 48:  # Address already in use
                    print(f"[-] Error: Port {self.port} is already in use.")
                    print(f"[-] Try a different port or kill the process using port {self.port}.")
                    print(f"[-] On macOS, you can run: lsof -i :{self.port}")
                    print(f"[-] Then terminate the process with: kill -9 <PID>")
                    return
                else:
                    raise
                    
            self.server_socket.listen(10)  # Allow up to 10 queued connections
            print(f"[*] Server started on {self.host}:{self.port}")
            
            # Get the local IP address to share with clients
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            print(f"[*] Local IP address: {local_ip}")
            print("[*] Share this IP address with your Raspberry Pi clients")
            
            # Accept connections in a loop
            while True:
                client_socket, addr = self.server_socket.accept()
                print(f"[+] Accepted connection from {addr[0]}:{addr[1]}")
                
                # Start a new thread to handle the client
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_handler.daemon = True
                client_handler.start()
                
        except Exception as e:
            print(f"[-] Error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def handle_client(self, client_socket, addr):
        """Handle communication with a connected client"""
        client_id = f"{addr[0]}_{addr[1]}"
        self.clients[client_id] = {
            "socket": client_socket,
            "address": addr,
            "connected_time": datetime.now(),
            "last_data_time": None
        }
        
        # Create a file for this client's data
        client_file = os.path.join(self.data_directory, f"client_{addr[0]}.txt")
        
        try:
            while True:
                # Receive data from the client
                data = client_socket.recv(4096)
                if not data:
                    break  # Client disconnected
                
                # Process the received data
                try:
                    decoded_data = data.decode('utf-8')
                    # Try to parse as JSON (assuming clients send JSON-formatted data)
                    try:
                        json_data = json.loads(decoded_data)
                        print(f"[*] Received from {addr[0]}: {json_data}")
                        
                        # Save data to file with timestamp
                        with open(client_file, 'a') as f:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            f.write(f"[{timestamp}] {json.dumps(json_data)}\n")
                        
                        # Update last data time
                        self.clients[client_id]["last_data_time"] = datetime.now()
                        
                        # Send acknowledgment back to client
                        response = {"status": "success", "timestamp": timestamp}
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        
                    except json.JSONDecodeError:
                        # Not JSON, treat as plain text
                        print(f"[*] Received from {addr[0]}: {decoded_data}")
                        
                        # Save data to file with timestamp
                        with open(client_file, 'a') as f:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            f.write(f"[{timestamp}] {decoded_data}\n")
                        
                        # Update last data time
                        self.clients[client_id]["last_data_time"] = datetime.now()
                        
                        # Send acknowledgment back to client
                        response = {"status": "success", "timestamp": timestamp}
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        
                except UnicodeDecodeError:
                    # Handle binary data
                    print(f"[*] Received binary data from {addr[0]}, length: {len(data)} bytes")
                    
                    # Save binary data to a separate file
                    binary_file = os.path.join(self.data_directory, f"client_{addr[0]}_binary_{int(time.time())}.bin")
                    with open(binary_file, 'wb') as f:
                        f.write(data)
                    
                    # Update last data time
                    self.clients[client_id]["last_data_time"] = datetime.now()
                    
                    # Send acknowledgment back to client
                    response = {"status": "success", "binary_received": True}
                    client_socket.send(json.dumps(response).encode('utf-8'))
        
        except Exception as e:
            print(f"[-] Error handling client {addr[0]}: {e}")
        finally:
            # Clean up when client disconnects
            print(f"[-] Client {addr[0]} disconnected")
            client_socket.close()
            if client_id in self.clients:
                del self.clients[client_id]
    
    def print_connected_clients(self):
        """Print information about all connected clients"""
        print("\n=== Connected Clients ===")
        if not self.clients:
            print("No clients connected")
        else:
            for client_id, info in self.clients.items():
                ip, port = info["address"]
                connected_time = info["connected_time"].strftime("%Y-%m-%d %H:%M:%S")
                last_data = "Never" if not info["last_data_time"] else info["last_data_time"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"Client {ip}:{port} - Connected: {connected_time}, Last data: {last_data}")
        print("========================\n")

# Run the server if this file is executed directly
if __name__ == "__main__":
    import argparse
    
    # Create argument parser for command-line options
    parser = argparse.ArgumentParser(description="Data Server for Raspberry Pi clients")
    parser.add_argument("--port", type=int, default=5000, 
                        help="Port to listen on (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", 
                        help="Host to bind to (default: 0.0.0.0, all interfaces)")
    
    args = parser.parse_args()
    
    try:
        # Create server with specified or default parameters
        server = DataServer(host=args.host, port=args.port)
        
        # Start a thread to periodically show connected clients
        def status_loop():
            while True:
                time.sleep(60)  # Show status every minute
                server.print_connected_clients()
                
        status_thread = threading.Thread(target=status_loop)
        status_thread.daemon = True
        status_thread.start()
        
        # Start the server (blocking call)
        server.start()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down...")