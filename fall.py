import cv2
import time
import requests
from ultralytics import YOLO

# --- CONFIGURATION ---
# Replace these with your actual details
TOKEN = "token"
CHAT_ID = "chatid"
# Use your working RTSP URL here
CAMERA_URL = "rtsp://user:password@192.168.x.y:554/stream2" 

# Detection Tweaks
CONFIDENCE_THRESHOLD = 0.25  # Lower = more sensitive to "weird" body shapes
COOLDOWN_SECONDS = 60        # Don't spam phone; wait 1 min between alerts
# ---------------------

# Load the pose model
print("Loading Model...")
model = YOLO('yolov8n-pose.pt')

def send_telegram(frame):
    
    """Sends a photo alert to Telegram."""
    try:
        img_name = "fall_detected.jpg"
        cv2.imwrite(img_name, frame)
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        with open(img_name, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": CHAT_ID, "caption": "⚠️ ALERT: Fall detected! Please check the camera."}
            response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            print("✅ Telegram alert sent!")
        else:
            print(f"❌ Telegram failed: {response.text}")
    except Exception as e:
        print(f"❌ Error sending notification: {e}")

def monitor():
    cap = cv2.VideoCapture(CAMERA_URL)
    last_alert_time = 0
    
    if not cap.isOpened():
        print("❌ Error: Could not connect to camera.")
        return

    print("🚀 Monitoring active. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Dropped frame... reconnecting.")
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # Run AI Inference
        # imgsz=320 makes it much faster on CPUs
        results = model(frame, stream=True, conf=CONFIDENCE_THRESHOLD, imgsz=320, verbose=False)

        for r in results:
            boxes = r.boxes.xywh.cpu().numpy()  # [x_center, y_center, width, height]
            
            if len(boxes) > 0:
                # We found someone!
                for box in boxes:
                    x, y, w, h = box
                    
                    # --- DETECTION LOGIC ---
                    # 1. Aspect Ratio: If width > height, they are horizontal.
                    is_horizontal = w > (h * 1.1)
                    
                    # 2. Vertical Position: If the person's center is in the bottom 40% of screen
                    # (Adjust 0.6 if your camera is mounted very high)
                    is_low = y > (frame.shape[0] * 0.6)

                    if is_horizontal or is_low:
                        current_time = time.time()
                        if current_time - last_alert_time > COOLDOWN_SECONDS:
                            print("!!! FALL DETECTED !!!")
                            send_telegram(frame)
                            last_alert_time = current_time

        # Optional: Show the video feed (Comment out if running over SSH)
        cv2.imshow("Fall Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    monitor()
