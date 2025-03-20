from ultralytics import YOLO
import cv2
from picamera2 import Picamera2

# Load the YOLOv8 model (make sure to use a model trained for drone detection)
model = YOLO("yolov8n.pt")  # Replace with a custom model if available

# Initialize Pi Camera
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

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
            
    # Display the frame
    cv2.imshow("Drone Detection", frame)
    
    # Break the loop with 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
picam2.close()
cv2.destroyAllWindows()
