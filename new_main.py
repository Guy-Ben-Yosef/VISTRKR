#!/usr/bin/env python3
"""
Real-time drone tracking system - Main execution script
"""

import os
import json
import time
import socket
import threading
import numpy as np
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation
from collections import deque
from datetime import datetime
import matplotlib

# Import project modules
from calibration import calib_functions
from estimation import estim_functions
from simulation import sim_functions

# Global variables
cameras_data = []
measurements_by_camera = {}
position_history = deque(maxlen=100)  # Keep last 100 positions
lock = threading.Lock()  # Synchronize data access
running = True  # Control server and plotting threads


def load_cameras_from_xml(filename):
    """
    Reads camera data from an XML file and returns a list of camera dictionaries.
    @param filename: (string) Name of the XML file to be read
    @return: (list) List of camera dictionaries
    """
    tree = ET.parse(filename)
    root = tree.getroot()

    cameras_data_list = []

    for camera_elem in root.findall('camera'):
        camera_dict = {}

        camera_dict['name'] = camera_elem.find('ID').text

        position_text = camera_elem.find('position').text
        camera_dict['position'] = tuple([float(coord) for coord in position_text.split(',')])

        camera_dict['azimuth'] = float(camera_elem.find('azimuth').text)
        camera_dict['elevation'] = float(camera_elem.find('elevation').text)
        camera_dict['angle_of_view'] = float(camera_elem.find('angle_of_view').text)

        resolution_text = camera_elem.find('resolution').text
        camera_dict['resolution'] = tuple([int(res) for res in resolution_text.split(',')])

        # Read calibration parameters only if they exist
        if camera_elem.find('calibration') is not None:
            calibration_dict = {}
            calibration_elem = camera_elem.find('calibration')

            azimuth_calib_text = calibration_elem.find('azimuth').text
            calibration_dict['azimuth'] = tuple([float(val) for val in azimuth_calib_text.split(',')])

            elevation_calib_text = calibration_elem.find('elevation').text
            calibration_dict['elevation'] = tuple([float(val) for val in elevation_calib_text.split(',')])

            camera_dict['calibration'] = calibration_dict

        cameras_data_list.append(camera_dict)

    return cameras_data_list


def estimate_position(cameras_list, pixels_by_camera):
    """
    Estimate the position using triangulation based on camera pixels.

    Args:
        @param: cameras_list (list): A list of dictionaries representing cameras.
                Each camera dictionary should have keys: 'name', 'calibration'.
        @param: pixels_by_camera (dict): A dictionary mapping camera names to pixel values.
                The pixel values can be either a single pixel or a list of pixels.

    Returns:
        @return: numpy.ndarray: A 2D array representing the estimated positions.
                 Each row corresponds to a measurement, and the columns represent the X, Y, and Z coordinates.
    """
    # Check if we have enough camera data
    if len(pixels_by_camera) < 2:
        print(f"Not enough cameras reporting data: {len(pixels_by_camera)}")
        return None

    # Get only the cameras that have measurements
    active_cameras = [cam for cam in cameras_list if cam['name'] in pixels_by_camera]
    
    if len(active_cameras) < 2:
        print(f"Not enough calibrated cameras with data: {len(active_cameras)}")
        return None

    # Determine the number of measurements
    if not isinstance(pixels_by_camera[active_cameras[0]['name']], list):
        number_of_measurements = 1
    else:
        number_of_measurements = len(pixels_by_camera[active_cameras[0]['name']])

    expected_angles = {}

    # Calculate the expected angles for each camera
    for camera in active_cameras:
        expected_angles_for_camera = []

        # Validate that the pixel is iterable
        if not isinstance(pixels_by_camera[camera['name']], list):
            pixels_by_camera[camera['name']] = [pixels_by_camera[camera['name']]]

        for pixel in pixels_by_camera[camera['name']]:
            expected_angles_for_camera.append(calib_functions.pixel2phi(camera['calibration'], pixel))

        expected_angles[camera['name']] = expected_angles_for_camera

    pixel_dim = len(pixels_by_camera[active_cameras[0]['name']][0])
    dimensions = pixel_dim + 1  # Recall that a 2D image represents 3D space

    # Initialize the array to store points and weights for each pair of cameras
    import math
    points_weights_by_pairs = np.zeros([math.comb(len(active_cameras), 2), dimensions + 1, number_of_measurements])

    # Perform triangulation for each measurement
    for k in range(number_of_measurements):
        angle_by_camera = {}
        for m in range(len(active_cameras)):
            camera_name = active_cameras[m]['name']
            angle_by_camera[camera_name] = expected_angles[camera_name][k]

        points_weights_by_pairs[:, :, k] = estim_functions.triangulation_by_pairs(active_cameras, angle_by_camera)

    # Perform weighted estimation for each measurement
    results = np.zeros([number_of_measurements, dimensions])
    for k in range(number_of_measurements):
        relevant_points = points_weights_by_pairs[:, :dimensions, k]
        relevant_weights = points_weights_by_pairs[:, dimensions, k]
        relevant_weights = 1 / relevant_weights
        relevant_weights = relevant_weights / sum(relevant_weights)
        results[k, :] = estim_functions.weighted_estimation(relevant_points, relevant_weights)

    return results


class DataServer:
    def __init__(self, host='0.0.0.0', port=5000):
        """Initialize the server with host and port"""
        self.host = host
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
                    return
                else:
                    raise
                    
            self.server_socket.listen(10)  # Allow up to 10 queued connections
            print(f"[*] Server started on {self.host}:{self.port}")
            
            # Get the local IP address to share with clients
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            print(f"[*] Local IP address: {local_ip}")
            print("[*] Share this IP address with your detection clients")
            
            # Accept connections in a loop
            while running:
                # Set a timeout to check the running flag periodically
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"[+] Accepted connection from {addr[0]}:{addr[1]}")
                    
                    # Start a new thread to handle the client
                    client_handler = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    client_handler.daemon = True
                    client_handler.start()
                except socket.timeout:
                    continue
                
        except Exception as e:
            print(f"[-] Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
                print("[*] Server shutdown complete")
    
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
                except Exception as e:
                    print(f"[-] Error estimating position: {e}")
            
            last_estimation_time = current_time
            
        # Sleep a bit to avoid hogging CPU
        time.sleep(0.05)


def setup_3d_plot():
    """Create and configure the 3D plot"""
    # Use plt.figure instead of directly enabling interactive mode
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Set labels and title
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Real-time Drone Tracking')
    
    # Plot camera positions
    for cam in cameras_data:
        pos = cam['position']
        ax.scatter(pos[0], pos[1], pos[2], color='red', marker='^', s=100, label=f"Camera {cam['name']}")
    
    # Create empty line for the trajectory
    line, = ax.plot([], [], [], 'b-', linewidth=2, label='Drone trajectory')
    
    # Create a scatter plot for the current position
    current_point = ax.scatter([], [], [], color='green', s=100, label='Current position')
    
    # Set axis limits - adjust as needed based on your environment
    ax.set_xlim(-5, 25)
    ax.set_ylim(-5, 25)
    ax.set_zlim(0, 15)
    
    # Show legend
    ax.legend()
    
    return fig, ax, line, current_point


def update_plot(ax, line, current_point):
    """Update the 3D plot with new position data"""
    with lock:
        history = list(position_history)
    
    if history:
        # Extract position data
        times = [h[0] for h in history]
        x_vals = [h[1][0] for h in history]
        y_vals = [h[1][1] for h in history]
        z_vals = [h[1][2] for h in history]
        
        # Update trajectory line
        line.set_data(x_vals, y_vals)
        line.set_3d_properties(z_vals)
        
        # Update current position
        current_point._offsets3d = ([x_vals[-1]], [y_vals[-1]], [z_vals[-1]])
        
        # Adjust plot limits if needed
        ax.set_xlim(min(min(x_vals) - 5, ax.get_xlim()[0]), max(max(x_vals) + 5, ax.get_xlim()[1]))
        ax.set_ylim(min(min(y_vals) - 5, ax.get_ylim()[0]), max(max(y_vals) + 5, ax.get_ylim()[1]))
        ax.set_zlim(min(min(z_vals), 0), max(max(z_vals) + 5, ax.get_zlim()[1]))
        
    return line, current_point


def main():
    global cameras_data, running
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="VISTRKR real-time drone tracking system")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--cameras", default=None, help="Path to cameras XML file (default: data/cameras_data.xml)")
    parser.add_argument("--backend", default=None, help="Matplotlib backend to use")
    args = parser.parse_args()
    
    # Set matplotlib backend if specified
    if args.backend:
        matplotlib.use(args.backend)
    else:
        # Use TkAgg backend by default which works well across platforms
        matplotlib.use('TkAgg')
    
    # Load camera configuration
    cameras_xml_path = args.cameras or os.path.join(os.getcwd(), 'data', 'cameras_data.xml')
    print(f"[*] Loading camera data from {cameras_xml_path}")
    
    try:
        cameras_data = load_cameras_from_xml(cameras_xml_path)
        print(f"[*] Loaded {len(cameras_data)} cameras")
    except Exception as e:
        print(f"[-] Error loading camera data: {e}")
        return
    
    # Set up the 3D plot
    fig, ax, line, current_point = setup_3d_plot()
    
    # Start server in a separate thread
    server = DataServer(host=args.host, port=args.port)
    print(f"[*] Starting server on {args.host}:{args.port}")
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    # Start position estimation in a separate thread
    estimation_thread = threading.Thread(target=position_estimation_loop)
    estimation_thread.daemon = True
    estimation_thread.start()
    
    # Use animation instead of a separate thread for plotting (safer on macOS)
    ani = FuncAnimation(fig, lambda i: update_plot(ax, line, current_point), 
                       interval=100, blit=False)
    
    # Show plot in interactive mode
    plt.show()
    
    try:
        print("[*] Press Ctrl+C to exit")
        while plt.fignum_exists(fig.number):
            plt.pause(0.1)  # Keep the plot responsive
            
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[*] Shutting down...")
        running = False
        time.sleep(1)  # Give threads time to clean up
        plt.close(fig)
    
    print("[*] VISTRKR real-time tracking stopped")


if __name__ == '__main__':
    main()