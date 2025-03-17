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
import xml.etree.ElementTree as ET
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
from collections import deque
from datetime import datetime
import argparse

# Import project modules
from calibration import calib_functions
from estimation import estim_functions

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
        relevant_weights = relevant_weights / np.linalg.norm(relevant_weights)
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
            try:
                local_ip = socket.gethostbyname(hostname)
                print(f"[*] Local IP address: {local_ip}")
            except:
                print("[*] Could not determine local IP address")
            
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
                        
                        # Update the web data
                        update_web_data()
                except Exception as e:
                    print(f"[-] Error estimating position: {e}")
            
            last_estimation_time = current_time
            
        # Sleep a bit to avoid hogging CPU
        time.sleep(0.05)


def create_web_files():
    """Create the necessary web files for visualization"""
    # Create initial data.json
    with open('data.json', 'w') as f:
        f.write('{"positions":[], "cameras":[]}')
    
    # Create index.html
    with open('index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>VISTRKR 3D Drone Tracking</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            display: flex;
            flex-direction: column;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .status-bar {
            background-color: #e8e8e8;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .charts-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
        }
        .chart-container {
            flex: 1;
            min-width: 400px;
            height: 400px;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 15px;
            overflow: hidden;
        }
        .data-container {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 15px;
            margin-top: 20px;
        }
        #dataTable {
            width: 100%;
            border-collapse: collapse;
        }
        #dataTable th, #dataTable td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        #dataTable th {
            background-color: #f2f2f2;
        }
        
        /* Controls */
        .controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .controls button {
            padding: 8px 16px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .controls button:hover {
            background-color: #45a049;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>VISTRKR Real-time Drone Tracking</h1>
        
        <div class="status-bar">
            <div>Status: <span id="status">Waiting for data...</span></div>
            <div>Last update: <span id="lastUpdate">Never</span></div>
            <div>Active cameras: <span id="activeCameras">0</span></div>
        </div>
        
        <div class="charts-container">
            <div class="chart-container">
                <h3>3D Position</h3>
                <div id="3dContainer" style="width: 100%; height: 100%;"></div>
            </div>
            
            <div class="chart-container">
                <h3>Position Over Time</h3>
                <canvas id="positionChart"></canvas>
            </div>
        </div>
        
        <div class="controls">
            <button id="resetViewBtn">Reset View</button>
            <button id="toggleTrajBtn">Toggle Trajectory</button>
        </div>
        
        <div class="data-container">
            <h3>Latest Position Data</h3>
            <table id="dataTable">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>X</th>
                        <th>Y</th>
                        <th>Z</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Data will be populated here -->
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // 3D visualization with Three.js
        let scene, camera, renderer, drone, cameraObjects = [], trajectory = [];
        let showTrajectory = true;
        
        function init3D() {
            // Create scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0xf0f0f0);
            
            // Create camera
            camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
            camera.position.set(20, 20, 20);
            camera.lookAt(10, 10, 5);
            
            // Create renderer
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(document.getElementById('3dContainer').offsetWidth, 
                             document.getElementById('3dContainer').offsetHeight);
            document.getElementById('3dContainer').appendChild(renderer.domElement);
            
            // Add grid
            const gridHelper = new THREE.GridHelper(50, 50);
            scene.add(gridHelper);
            
            // Add axes
            const axesHelper = new THREE.AxesHelper(10);
            scene.add(axesHelper);
            
            // Create drone object
            const geometry = new THREE.SphereGeometry(0.5, 32, 32);
            const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
            drone = new THREE.Mesh(geometry, material);
            scene.add(drone);
            
            // Create trajectory line
            updateTrajectory([]);
            
            // Add event listener for window resize
            window.addEventListener('resize', onWindowResize, false);
            
            // Add orbit controls
            // Note: In production, you'd add OrbitControls.js separately
            // For simplicity in this example, we'll add basic rotation
            setInterval(() => {
                camera.position.x = 20 * Math.cos(Date.now() * 0.0001);
                camera.position.z = 20 * Math.sin(Date.now() * 0.0001);
                camera.lookAt(10, 10, 5);
            }, 50);
            
            // Animate
            animate();
        }
        
        function animate() {
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }
        
        function onWindowResize() {
            camera.aspect = document.getElementById('3dContainer').offsetWidth / 
                            document.getElementById('3dContainer').offsetHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(document.getElementById('3dContainer').offsetWidth, 
                             document.getElementById('3dContainer').offsetHeight);
        }
        
        function updateDronePosition(x, y, z) {
            drone.position.set(x, y, z);
        }
        
        function addCameras(camerasData) {
            // Clear existing camera objects
            cameraObjects.forEach(obj => scene.remove(obj));
            cameraObjects = [];
            
            // Add new camera objects
            camerasData.forEach(cam => {
                const camGeometry = new THREE.ConeGeometry(0.5, 1, 8);
                const camMaterial = new THREE.MeshBasicMaterial({ color: 0xff0000 });
                const camObject = new THREE.Mesh(camGeometry, camMaterial);
                
                // Position the camera
                camObject.position.set(cam.position[0], cam.position[1], cam.position[2]);
                
                // Rotate to point in the azimuth and elevation direction
                // This is a simplified rotation - in a real implementation, you'd need proper Euler angles
                const azimuthRad = cam.azimuth * Math.PI / 180;
                const elevationRad = cam.elevation * Math.PI / 180;
                camObject.rotation.y = -azimuthRad;
                camObject.rotation.x = elevationRad;
                
                scene.add(camObject);
                cameraObjects.push(camObject);
                
                // Add label for camera
                // In a more complex implementation, you would add text labels
            });
        }
        
        function updateTrajectory(positions) {
            // Remove old trajectory
            if (trajectory.length > 0) {
                scene.remove(trajectory[0]);
                trajectory = [];
            }
            
            if (!showTrajectory || positions.length < 2) return;
            
            // Create new trajectory
            const points = positions.map(p => new THREE.Vector3(p[0], p[1], p[2]));
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const material = new THREE.LineBasicMaterial({ color: 0x0000ff });
            const line = new THREE.Line(geometry, material);
            scene.add(line);
            trajectory.push(line);
        }
        
        // Initialize 2D charts
        let positionChart;
        
        function initCharts() {
            const ctx = document.getElementById('positionChart').getContext('2d');
            positionChart = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [
                        {
                            label: 'X Position',
                            borderColor: 'rgb(255, 99, 132)',
                            data: []
                        },
                        {
                            label: 'Y Position',
                            borderColor: 'rgb(75, 192, 192)',
                            data: []
                        },
                        {
                            label: 'Z Position',
                            borderColor: 'rgb(153, 102, 255)',
                            data: []
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'second',
                                tooltipFormat: 'HH:mm:ss',
                                displayFormats: {
                                    second: 'HH:mm:ss'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Position (m)'
                            }
                        }
                    }
                }
            });
        }
        
        function updatePositionChart(data) {
            // Extract data for chart
            const times = data.map(d => new Date(d.time * 1000));
            const xValues = data.map(d => d.x);
            const yValues = data.map(d => d.y);
            const zValues = data.map(d => d.z);
            
            // Update chart datasets
            positionChart.data.datasets[0].data = times.map((t, i) => ({ x: t, y: xValues[i] }));
            positionChart.data.datasets[1].data = times.map((t, i) => ({ x: t, y: yValues[i] }));
            positionChart.data.datasets[2].data = times.map((t, i) => ({ x: t, y: zValues[i] }));
            
            // Update chart
            positionChart.update();
        }
        
        function updateDataTable(data) {
            const tbody = document.getElementById('dataTable').getElementsByTagName('tbody')[0];
            tbody.innerHTML = '';
            
            // Display the most recent 10 data points (or fewer if there are less than 10)
            const recentData = data.slice(-10);
            
            recentData.forEach(d => {
                const row = tbody.insertRow();
                const timeCell = row.insertCell(0);
                const xCell = row.insertCell(1);
                const yCell = row.insertCell(2);
                const zCell = row.insertCell(3);
                
                const time = new Date(d.time * 1000).toLocaleTimeString();
                timeCell.textContent = time;
                xCell.textContent = d.x.toFixed(2);
                yCell.textContent = d.y.toFixed(2);
                zCell.textContent = d.z.toFixed(2);
            });
        }
        
        // Fetch and update data
        function fetchData() {
            fetch('data.json?' + new Date().getTime())
                .then(response => response.json())
                .then(data => {
                    // Update status
                    document.getElementById('status').textContent = 'Receiving data';
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                    document.getElementById('activeCameras').textContent = Object.keys(data.cameras).length;
                    
                    // Update 3D visualization
                    if (data.positions.length > 0) {
                        const latest = data.positions[data.positions.length - 1];
                        updateDronePosition(latest.x, latest.y, latest.z);
                        
                        // Update trajectory
                        updateTrajectory(data.positions.map(p => [p.x, p.y, p.z]));
                    }
                    
                    // Update cameras
                    if (data.cameras.length > 0 && cameraObjects.length === 0) {
                        addCameras(data.cameras);
                    }
                    
                    // Update charts
                    updatePositionChart(data.positions);
                    
                    // Update data table
                    updateDataTable(data.positions);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                    document.getElementById('status').textContent = 'Error: ' + error.message;
                });
        }
        
        // Initialize everything when the page loads
        document.addEventListener('DOMContentLoaded', () => {
            init3D();
            initCharts();
            
            // Add event listeners for buttons
            document.getElementById('resetViewBtn').addEventListener('click', () => {
                camera.position.set(20, 20, 20);
                camera.lookAt(10, 10, 5);
            });
            
            document.getElementById('toggleTrajBtn').addEventListener('click', () => {
                showTrajectory = !showTrajectory;
                // Re-fetch data to update
                fetchData();
            });
            
            // Start fetching data
            setInterval(fetchData, 500);
            fetchData();
        });
    </script>
</body>
</html>
''')
    
    print("[*] Created web files")


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


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="VISTRKR real-time drone tracking system with web visualization")
    parser.add_argument("--data-port", type=int, default=5000, help="Port for data server (default: 5000)")
    parser.add_argument("--web-port", type=int, default=8080, help="Port for web server (default: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--cameras", default=None, help="Path to cameras XML file (default: data/cameras_data.xml)")
    parser.add_argument("--no-browser", action="store_true", help="Don't automatically open browser")
    args = parser.parse_args()
    
    # Set global variables
    global web_port, data_port
    web_port = args.web_port
    data_port = args.data_port
    
    # Load camera configuration
    cameras_xml_path = args.cameras or os.path.join(os.getcwd(), 'data', 'cameras_data.xml')
    print(f"[*] Loading camera data from {cameras_xml_path}")
    
    try:
        cameras_data = load_cameras_from_xml(cameras_xml_path)
        print(f"[*] Loaded {len(cameras_data)} cameras")
    except Exception as e:
        print(f"[-] Error loading camera data: {e}")
        import sys
        sys.exit(1)
    
    # Create web files
    create_web_files()
    
    # Start data server in a separate thread
    server = DataServer(host=args.host, port=data_port)
    print(f"[*] Starting data server on {args.host}:{data_port}")
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