from ultralytics import YOLO
import cv2
from picamera2 import Picamera2
import socket
import json
import datetime

# Configuration
SERVER_HOST = "192.168.1.149"  # Replace with actual server IP
SERVER_PORT = 5001  # Replace with actual server port
STATION_ID = "1"  # Replace with actual station ID

# Load the YOLOv8 model (make sure to use a model trained for drone detection)
model = YOLO("yolov8n.pt")  # Replace with a custom model if available

# Initialize Pi Camera
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

# Create a socket connection to the server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    print(f"Connecting to {SERVER_HOST}:{SERVER_PORT}...")
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    print("Connected to server.")
except Exception as e:
    print(f"Failed to connect to server: {e}")
    exit(1)

while True:
    # Capture image
    frame = picam2.capture_array()
    
    # Run YOLOv8 inference
    results = model(frame)
    
    # Process detections
    for result in results:
        for box in result.boxes:
            x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
            centroid_x = (x_min + x_max) // 2
            centroid_y = (y_min + y_max) // 2
            print(f"Drone detected at: ({centroid_x}, {centroid_y})")
            
            # Draw rectangle around the detected drone
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            
            # Prepare data packet
            data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "x": centroid_x,
                "y": centroid_y,
                "station_id": STATION_ID
            }
            
            # Convert data to JSON and send to server
            json_data = json.dumps(data)
            client_socket.sendall(json_data.encode('utf-8'))
            print(f"Sent data: {json_data}")
    
    # Display the frame
    cv2.imshow("Drone Detection", frame)
    
    # Break the loop with 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
client_socket.close()
picam2.close()
cv2.destroyAllWindows()
