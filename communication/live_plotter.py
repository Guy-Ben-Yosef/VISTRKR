import socket
import threading
import json
import time
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
from collections import deque

# Configuration
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5001        # Socket server port
WEB_PORT = 8080    # Web server port
MAX_POINTS = 100   # Max points to store per station

# Global variables
stations_data = {}  # Store data for each station
data_lock = threading.Lock()

def handle_client(client_socket, address):
    """Handle client connection and data"""
    print(f"[+] New connection from {address[0]}:{address[1]}")
    
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            
            try:
                json_data = json.loads(data.decode('utf-8'))
                station_id = json_data.get('station_id', 'unknown')
                x = json_data.get('x', 0)
                y = json_data.get('y', 0)
                timestamp = json_data.get('timestamp', time.time())
                
                # Store data
                with data_lock:
                    if station_id not in stations_data:
                        stations_data[station_id] = deque(maxlen=MAX_POINTS)
                    
                    stations_data[station_id].append({
                        'timestamp': timestamp,
                        'x': x,
                        'y': y
                    })
                
                # Print data
                print(f"[+] From {station_id}: x={x}, y={y}")
                
                # Send acknowledgment
                client_socket.send(b'{"status":"ok"}')
                
                # Update the web data file
                update_web_data()
                
            except json.JSONDecodeError:
                print("[-] Invalid JSON received")
                client_socket.send(b'{"status":"error","message":"Invalid JSON"}')
    
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        client_socket.close()
        print(f"[-] Connection from {address[0]}:{address[1]} closed")

def update_web_data():
    """Update the data.json file for the web interface"""
    try:
        with data_lock:
            # Convert data to a format suitable for JSON
            web_data = {}
            for station, points in stations_data.items():
                web_data[station] = list(points)
        
        # Write to file
        with open('data.json', 'w') as f:
            json.dump(web_data, f)
    
    except Exception as e:
        print(f"[-] Error updating web data: {e}")

def start_socket_server():
    """Start the socket server"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"[*] Socket server listening on {HOST}:{PORT}")
        
        while True:
            client, address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client, address))
            client_thread.daemon = True
            client_thread.start()
    
    except KeyboardInterrupt:
        print("\n[*] Server shutting down...")
    except Exception as e:
        print(f"[-] Server error: {e}")
    finally:
        server_socket.close()

def create_web_files():
    """Create the necessary web files"""
    # Create initial data.json
    with open('data.json', 'w') as f:
        f.write('{}')
    
    # Create index.html
    with open('index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Live Data Plot</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        h1 {
            color: #333;
        }
        .chart-container {
            width: 100%;
            max-width: 800px;
            height: 400px;
            margin-bottom: 30px;
            border: 1px solid #ddd;
            padding: 10px;
        }
        #dataTable {
            border-collapse: collapse;
            width: 100%;
            max-width: 800px;
        }
        #dataTable th, #dataTable td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        #dataTable th {
            background-color: #f2f2f2;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>Live Station Data</h1>
    <p>Status: <span id="status">Waiting for data...</span></p>
    
    <div class="chart-container">
        <canvas id="xyPlot"></canvas>
    </div>
    
    <h2>Latest Data</h2>
    <table id="dataTable">
        <thead>
            <tr>
                <th>Station</th>
                <th>X</th>
                <th>Y</th>
                <th>Time</th>
            </tr>
        </thead>
        <tbody>
            <!-- Data will be added here -->
        </tbody>
    </table>
    
    <script>
        // Initialize chart
        const ctx = document.getElementById('xyPlot').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: []
            },
            options: {
                animation: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'X Coordinate'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Y Coordinate'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'XY Position'
                    }
                }
            }
        });
        
        // Colors for different stations
        const colors = [
            'rgb(255, 99, 132)',
            'rgb(54, 162, 235)',
            'rgb(255, 206, 86)',
            'rgb(75, 192, 192)',
            'rgb(153, 102, 255)',
            'rgb(255, 159, 64)'
        ];
        
        // Update the chart and table with new data
        function updateDisplay(data) {
            // Clear existing datasets
            chart.data.datasets = [];
            
            // Add a dataset for each station
            let colorIndex = 0;
            let tableHTML = '';
            
            for (const station in data) {
                const points = data[station];
                const color = colors[colorIndex % colors.length];
                
                // Add to chart
                chart.data.datasets.push({
                    label: `Station ${station}`,
                    data: points.map(p => ({ x: p.x, y: p.y })),
                    backgroundColor: color,
                    pointRadius: 5
                });
                
                // Add most recent point to table
                if (points.length > 0) {
                    const latest = points[points.length - 1];
                    const time = new Date(latest.timestamp).toLocaleTimeString();
                    
                    tableHTML += `
                        <tr>
                            <td>${station}</td>
                            <td>${latest.x}</td>
                            <td>${latest.y}</td>
                            <td>${time}</td>
                        </tr>
                    `;
                }
                
                colorIndex++;
            }
            
            // Update the table
            document.querySelector('#dataTable tbody').innerHTML = tableHTML;
            
            // Update the chart
            chart.update();
            
            // Update status
            document.getElementById('status').textContent = 'Data updating in real-time';
        }
        
        // Fetch data periodically
        function fetchData() {
            fetch('data.json?' + new Date().getTime())
                .then(response => response.json())
                .then(data => {
                    updateDisplay(data);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                    document.getElementById('status').textContent = 'Error fetching data';
                });
        }
        
        // Start fetching data
        setInterval(fetchData, 1000);
        fetchData();
    </script>
</body>
</html>
        ''')
    
    print("[*] Created web files")

def start_web_server():
    """Start a simple HTTP server"""
    class CustomHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress logging for cleaner output
            return
    
    server = HTTPServer((HOST, WEB_PORT), CustomHandler)
    print(f"[*] Web server running at http://localhost:{WEB_PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

def main():
    """Main entry point"""
    # Create web files
    create_web_files()
    
    # Start the socket server in a thread
    socket_thread = threading.Thread(target=start_socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    
    # Open the web browser
    webbrowser.open(f"http://localhost:{WEB_PORT}")
    
    # Start the web server (blocking)
    start_web_server()

if __name__ == "__main__":
    main()