import socket
import json
import time
import random
import platform
import psutil
import threading
import os
from datetime import datetime

class DataClient:
    def __init__(self, server_host, server_port=5000, client_id=None):
        """Initialize the client with server details and optional client ID"""
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        self.connected = False
        self.client_id = client_id or f"rpi_{platform.node()}_{os.getpid()}"
        self.reconnect_delay = 5  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 60  # Maximum reconnect delay
        self.stop_flag = False  # Flag to stop the client
    
    def connect(self):
        """Connect to the server"""
        try:
            if self.client_socket:
                self.client_socket.close()
                
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.reconnect_delay = 5  # Reset reconnect delay on successful connection
            print(f"[+] Connected to server at {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"[-] Failed to connect to server: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.connected = False
        print("[-] Disconnected from server")
    
    def send_data(self, data):
        """Send data to the server"""
        if not self.connected:
            print("[-] Not connected to server. Attempting to reconnect...")
            if not self.connect():
                return False
        
        try:
            # Convert data to JSON and send
            if isinstance(data, dict) or isinstance(data, list):
                # Add client identifier and timestamp to the data
                if isinstance(data, dict):
                    data["client_id"] = self.client_id
                    data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                json_data = json.dumps(data)
                self.client_socket.send(json_data.encode('utf-8'))
            else:
                # Send as string
                self.client_socket.send(str(data).encode('utf-8'))
            
            # Wait for acknowledgment
            response_data = self.client_socket.recv(1024)
            if response_data:
                try:
                    response = json.loads(response_data.decode('utf-8'))
                    if response.get("status") == "success":
                        print(f"[+] Data sent successfully, server timestamp: {response.get('timestamp', 'unknown')}")
                        return True
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"[-] Error sending data: {e}")
            self.connected = False
            return False
    
    def send_binary_data(self, binary_data):
        """Send binary data to the server"""
        if not self.connected:
            print("[-] Not connected to server. Attempting to reconnect...")
            if not self.connect():
                return False
        
        try:
            # Send binary data directly
            self.client_socket.send(binary_data)
            
            # Wait for acknowledgment
            response_data = self.client_socket.recv(1024)
            if response_data:
                try:
                    response = json.loads(response_data.decode('utf-8'))
                    if response.get("status") == "success":
                        print(f"[+] Binary data sent successfully")
                        return True
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"[-] Error sending binary data: {e}")
            self.connected = False
            return False
    
    def collect_system_data(self):
        """Collect system metrics from the Raspberry Pi"""
        try:
            data = {
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
                "temperature": self._get_cpu_temperature(),
                "timestamp": time.time()
            }
            return data
        except Exception as e:
            print(f"[-] Error collecting system data: {e}")
            return {"error": str(e)}
    
    def _get_cpu_temperature(self):
        """Get CPU temperature on Raspberry Pi"""
        try:
            # Try to get CPU temperature from thermal zone
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return temp
        except:
            try:
                # Alternative method using vcgencmd
                import subprocess
                output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
                return float(output.replace('temp=', '').replace("'C", ''))
            except:
                return None
    
    def start_data_collection(self, interval=60):
        """Start collecting and sending data at regular intervals"""
        def collection_loop():
            while not self.stop_flag:
                if not self.connected:
                    try:
                        if not self.connect():
                            # Exponential backoff for reconnection attempts
                            print(f"[*] Reconnecting in {self.reconnect_delay} seconds...")
                            time.sleep(self.reconnect_delay)
                            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                            continue
                    except Exception as e:
                        print(f"[-] Reconnection error: {e}")
                        time.sleep(self.reconnect_delay)
                        continue
                
                try:
                    # Collect and send system data
                    system_data = self.collect_system_data()
                    if not self.send_data(system_data):
                        print("[-] Failed to send system data")
                        self.connected = False
                        continue
                    
                    # Wait for the next interval
                    time.sleep(interval)
                except Exception as e:
                    print(f"[-] Error in collection loop: {e}")
                    self.connected = False
                    time.sleep(5)
        
        # Start the collection thread
        self.stop_flag = False
        collection_thread = threading.Thread(target=collection_loop)
        collection_thread.daemon = True
        collection_thread.start()
        return collection_thread
    
    def stop(self):
        """Stop the client and disconnect"""
        self.stop_flag = True
        self.disconnect()

# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Raspberry Pi data client")
    parser.add_argument("--server", required=True, help="Server IP address")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--interval", type=int, default=60, help="Data collection interval in seconds (default: 60)")
    args = parser.parse_args()
    
    try:
        client = DataClient(args.server, args.port)
        print(f"[*] Starting data collection (interval: {args.interval}s)")
        collection_thread = client.start_data_collection(args.interval)
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Stopping client...")
            client.stop()
    except Exception as e:
        print(f"[-] Error: {e}")