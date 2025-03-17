#!/usr/bin/env python3
"""
Real-time drone tracking system with web-based visualization
"""

import os
import json
import time
import socket
import threading
import numpy as np
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
from collections import deque
from datetime import datetime
import argparse

# Import existing project modules
from calibration import calib_functions
from estimation import estim_functions
from new_main import load_cameras_from_xml, estimate_position, DataServer

# Global variables
cameras_data = []
measurements_by_camera = {}
position_history = deque(maxlen=100)  # Keep last 100 positions
lock = threading.Lock()  # Synchronize data access
running = True  # Control server and plotting threads
web_port = 8080  # Default port for the web visualization


def position_estimation_loop():
    """Continuously estimate positions based on available measurements"""
    last_estimation_time = 0
    estimation_interval = 0.2  # seconds between estimations
    
    while running:
        current_time = time.time()
        
        # Check if it's time to perform an estimation
        if current_time - last_estimation_time >= estimation_interval:
            with lock:
                local_measurements = measurements_by_camera.copy()
            
            # Only estimate if we have measurements
            if local_measurements:
                try:
                    # Estimate the current position
                    positions = estimate_position(cameras_data, local_measurements)
                    
                    if positions is not None and len(positions) > 0:
                        # We're only interested in the most recent position (first element)
                        current_position = positions[0]
                        
                        # Add timestamp to position data
                        position_with_time = (current_time, current_position)
                        
                        # Add to history
                        with lock:
                            position_history.append(position_with_time)
                            
                        print(f"[+] Estimated position: {current_position}")
                        
                        # Update the web data
                        update_web_data()
                except Exception as e:
                    print(f"[-] Error estimating position: {e}")
            
            last_estimation_time = current_time
            
        # Sleep a bit to avoid hogging CPU
        time.sleep(0.05)


def update_web_data():
    """Update the data.json file with the latest tracking information"""
    try:
        with lock:
            # Get a copy of the position history
            history = list(position_history)
            # Get a copy of the camera data
            cams = cameras_data.copy()
            # Get a copy of the measurements
            meas = measurements_by_camera.copy()
        
        # Format position data for JSON
        positions = []
        for time_stamp, pos in history:
            positions.append({
                "time": time_stamp,
                "x": float(pos[0]),
                "y": float(pos[1]),
                "z": float(pos[2])
            })
        
        # Format camera data for JSON
        cameras = []
        for cam in cams:
            camera_data = {
                "name": cam["name"],
                "position": cam["position"],
                "azimuth": cam["azimuth"],
                "elevation": cam["elevation"]
            }
            
            # Add current measurement if available
            if cam["name"] in meas:
                camera_data["current_pixel"] = meas[cam["name"]]
            
            cameras.append(camera_data)
        
        # Create the complete data object
        data = {
            "positions": positions,
            "cameras": cameras
        }
        
        # Write to file
        with open('data.json', 'w') as f:
            json.dump(data, f)
            
    except Exception as e:
        print(f"[-] Error updating web data: {e}")


def create_web_files():
    """Create the necessary web files for visualization"""
    # Create initial data.json
    with open('data.json', 'w') as f:
        f.write('{"positions":[], "cameras":[]}')
    
    # Create index.html - tell the user we're writing this file
    print("[*] Creating index.html for web visualization")
    with open('index.html', 'w') as f:
        f.write(open('tracker_template.html', 'r').read())


def start_web_server():
    """Start the web server for visualization"""
    class CustomHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress logging for cleaner output
            return
    
    try:
        server = HTTPServer(('0.0.0.0', web_port), CustomHandler)
        print(f"[*] Web visualization running at http://localhost:{web_port}")
        print(f"[*] Open this URL in your browser to view the tracking visualization")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    except Exception as e:
        print(f"[-] Error starting web server: {e}")


class TrackingDataServer(DataServer):
    """Extended data server that updates the shared measurement dictionary"""
    def handle_client(self, client_socket, addr):
        """Handle communication with a connected client"""
        client_id = f"{addr[0]}_{addr[1]}"
        self.clients[client_id] = {
            "socket": client_socket,
            "address": addr,
            "connected_time": datetime.now(),
            "last_data_time": None
        }
        
        try:
            while running:
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
                        
                        # Process pixel data from detection client
                        if "station_id" in json_data and "x" in json_data and "y" in json_data:
                            camera_id = json_data["station_id"]
                            x = int(json_data["x"])
                            y = int(json_data["y"])
                            
                            # Update global measurements
                            with lock:
                                measurements_by_camera[camera_id] = (x, y)
                                
                            print(f"[*] Updated pixel for camera {camera_id}: ({x}, {y})")
                        
                        # Send acknowledgment back to client
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        response = {"status": "success", "timestamp": timestamp}
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        
                    except json.JSONDecodeError:
                        # Not JSON, treat as plain text
                        print(f"[*] Received from {addr[0]}: {decoded_data}")
                        response = {"status": "error", "message": "Invalid JSON"}
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        
                except UnicodeDecodeError:
                    # Handle binary data
                    print(f"[*] Received binary data from {addr[0]}, length: {len(data)} bytes")
                    response = {"status": "error", "message": "Binary data not supported"}
                    client_socket.send(json.dumps(response).encode('utf-8'))
        
        except Exception as e:
            print(f"[-] Error handling client {addr[0]}: {e}")
        finally:
            # Clean up when client disconnects
            print(f"[-] Client {addr[0]} disconnected")
            client_socket.close()
            if client_id in self.clients:
                del self.clients[client_id]


def main():
    global cameras_data, running, web_port
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="VISTRKR real-time drone tracking with web visualization")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on for data (default: 5000)")
    parser.add_argument("--web-port", type=int, default=8080, help="Port for web server (default: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--cameras", default=None, help="Path to cameras XML file (default: data/cameras_data.xml)")
    parser.add_argument("--no-browser", action="store_true", help="Don't automatically open browser")
    args = parser.parse_args()
    
    # Set web port
    web_port = args.web_port
    
    # Load camera configuration
    cameras_xml_path = args.cameras or os.path.join(os.getcwd(), 'data', 'cameras_data.xml')
    print(f"[*] Loading camera data from {cameras_xml_path}")
    
    try:
        cameras_data = load_cameras_from_xml(cameras_xml_path)
        print(f"[*] Loaded {len(cameras_data)} cameras")
    except Exception as e:
        print(f"[-] Error loading camera data: {e}")
        return
    
    # Create web files
    create_web_files()
    
    # Start data server in a separate thread
    server = TrackingDataServer(host=args.host, port=args.port)
    print(f"[*] Starting data server on {args.host}:{args.port}")
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    # Start position estimation in a separate thread
    estimation_thread = threading.Thread(target=position_estimation_loop)
    estimation_thread.daemon = True
    estimation_thread.start()
    
    # Open web browser if not disabled
    if not args.no_browser:
        webbrowser.open(f"http://localhost:{web_port}")
    
    # Start web server (this will block until interrupted)
    try:
        start_web_server()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        running = False
        time.sleep(1)  # Give threads time to clean up
    
    print("[*] VISTRKR real-time tracking stopped")


if __name__ == '__main__':
    main()