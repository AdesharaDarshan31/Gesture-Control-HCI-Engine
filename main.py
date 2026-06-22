import cv2
import time
import math
import os
import threading
import webbrowser
import ctypes
from collections import deque
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = "hand_landmarker.task"

NUM_HANDS_TO_TRACK = 2          
DUAL_HAND_ACTIVATION_FRAMES = 5 
SINGLE_HAND_COOLDOWN = 0.8       

SWIPE_THRESHOLD = 0.14        
VERTICAL_THRESHOLD = 0.14     
DEPTH_PUSH_THRESHOLD = 1.45   
DEPTH_PULL_THRESHOLD = 0.65   
REQUIRED_FRAMES = 5        

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000

user32 = ctypes.windll.user32
screen_width = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)

app_is_open = False        
swipe_start_x = None       
swipe_start_y = None          
base_palm_size = None         
current_gesture_streak = 0
last_stable_gesture = "UNKNOWN"

dual_hand_mode_active = False
hands_visible_streak = 0
last_second_hand_time = 0.0
base_dual_distance = None  

canvas_points = []          
prev_canvas_x = None
prev_canvas_y = None
canvas_clear_cooldown = 0.0

is_clicking = False
virtual_object_radius = 100 

class SimplePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def dist(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def count_four_fingers(hand):
    fingers = 0
    pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
    for tip, pip in pairs:
        if hand[tip].y < hand[pip].y:
            fingers += 1
    return fingers

def is_thumb_open(hand):
    THUMB_MCP = 2
    THUMB_TIP = 4
    PINKY_MCP = 17
    d_tip_to_pinky = dist(hand[THUMB_TIP], hand[PINKY_MCP])
    d_mcp_to_pinky = dist(hand[THUMB_MCP], hand[PINKY_MCP])
    return d_tip_to_pinky > d_mcp_to_pinky

def gesture_from_hand(hand):
    four_count = count_four_fingers(hand)
    thumb_open = is_thumb_open(hand)
    total_fingers = four_count + (1 if thumb_open else 0)

    if total_fingers == 0: return "FIST", 0
    if total_fingers == 1: return "THUMB" if thumb_open else "ONE", 1
    if total_fingers == 2: return "TWO", 2
    if total_fingers == 3: return "THREE", 3
    if total_fingers == 4: return "FOUR", 4
    if total_fingers == 5: return "PALM", 5
    return "UNKNOWN", total_fingers

def launch_chrome(): os.system("start chrome")
def launch_youtube(): webbrowser.open("https://www.youtube.com", new=2)
def launch_brave():
    brave_path = r'"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"'
    os.system(f'start "" {brave_path} || start chrome')
def shift_window_next():
    user32.keybd_event(0x12, 0, 0, 0); user32.keybd_event(0x09, 0, 0, 0)
    user32.keybd_event(0x09, 0, 2, 0); user32.keybd_event(0x12, 0, 2, 0)
def shift_window_prev():
    user32.keybd_event(0x12, 0, 0, 0); user32.keybd_event(0x10, 0, 0, 0); user32.keybd_event(0x09, 0, 0, 0)
    user32.keybd_event(0x09, 0, 2, 0); user32.keybd_event(0x10, 0, 2, 0); user32.keybd_event(0x12, 0, 2, 0)
def minimize_active_window():
    user32.keybd_event(0x5B, 0, 0, 0); user32.keybd_event(0x28, 0, 0, 0)
    user32.keybd_event(0x28, 0, 2, 0); user32.keybd_event(0x5B, 0, 2, 0)
def clear_desktop():
    user32.keybd_event(0x5B, 0, 0, 0); user32.keybd_event(0x44, 0, 0, 0)
    user32.keybd_event(0x44, 0, 2, 0); user32.keybd_event(0x5B, 0, 2, 0)
def maximize_active_window():
    user32.keybd_event(0x5B, 0, 0, 0); user32.keybd_event(0x26, 0, 0, 0)
    user32.keybd_event(0x26, 0, 2, 0); user32.keybd_event(0x5B, 0, 2, 0)
def launch_system_app(command): os.system(command)

def main():
    global app_is_open, swipe_start_x, swipe_start_y, base_palm_size, current_gesture_streak, last_stable_gesture
    global dual_hand_mode_active, hands_visible_streak, last_second_hand_time, base_dual_distance
    global is_clicking, virtual_object_radius
    global canvas_points, prev_canvas_x, prev_canvas_y, canvas_clear_cooldown

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options, running_mode=vision.RunningMode.VIDEO, num_hands=NUM_HANDS_TO_TRACK
    )
    
    try: landmarker = vision.HandLandmarker.create_from_options(options)
    except Exception as e: print(f"ERROR: {e}"); return

    cap = cv2.VideoCapture(0)
    prev_time = time.time()

    print("\n>>> ADVANCED DOUBLE-TWO CANVAS CONFIGURATION ACTIVE <<<")

    while True:
        ok, frame = cap.read()
        if not ok: break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        current_time = time.time()
        result = landmarker.detect_for_video(mp_image, int(current_time * 1000))

        if app_is_open: status, ui_color = "LOCKED - Spacebar", (0, 0, 255)
        else: status, ui_color = "ENGINE READY", (0, 255, 0)

        num_hands_detected = max(0, len(result.hand_landmarks)) if result.hand_landmarks else 0

        for i in range(1, len(canvas_points)):
            if canvas_points[i - 1] is not None and canvas_points[i] is not None:
                cv2.line(frame, canvas_points[i - 1], canvas_points[i], (0, 255, 255), 5) 

        if num_hands_detected == 2:
            hands_visible_streak += 1
            if hands_visible_streak >= DUAL_HAND_ACTIVATION_FRAMES:
                dual_hand_mode_active = True
                app_is_open = False 
        else:
            if dual_hand_mode_active:
                last_second_hand_time = current_time 
                if is_clicking: 
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    is_clicking = False
                prev_canvas_x, prev_canvas_y = None, None
            dual_hand_mode_active = False
            hands_visible_streak = 0
            base_dual_distance = None


        if dual_hand_mode_active:
            lms1, lms2 = result.hand_landmarks[0], result.hand_landmarks[1]
            if lms1[0].x < lms2[0].x: left_hand_lms, right_hand_lms = lms1, lms2
            else: left_hand_lms, right_hand_lms = lms2, lms1

            left_gesture, _ = gesture_from_hand(left_hand_lms)
            right_gesture, _ = gesture_from_hand(right_hand_lms)

            if left_gesture == "TWO":
                ui_color = (255, 0, 255) 
                status = "[CANVAS MODE] Left 2-Fingers Active"
                base_dual_distance = None 
                
                cx = int(right_hand_lms[8].x * w)
                cy = int(right_hand_lms[8].y * h)

                normalized_x = int(right_hand_lms[8].x * 65535)
                normalized_y = int(right_hand_lms[8].y * 65535)
                user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, normalized_x, normalized_y, 0, 0)

                if right_gesture == "TWO":
                    if not is_clicking:
                        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        is_clicking = True
                    status = "[DRAWING] Double 2-Fingers Engaged"
                    canvas_points.append((cx, cy))
                    cv2.circle(frame, (cx, cy), 10, (0, 0, 255), -1)
                else:
                    if is_clicking:
                        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        is_clicking = False
                    status = "[HOVERING] Move Right Index to Aim"
                    canvas_points.append(None) # Break segment path safely
                    cv2.circle(frame, (cx, cy), 12, (255, 255, 0), 2)

            else:
                ui_color = (255, 128, 0) 
                canvas_points.append(None) 
                if is_clicking:
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    is_clicking = False

                if right_gesture == "PALM" and (current_time - canvas_clear_cooldown > 1.5):
                    if prev_canvas_y is not None and (right_hand_lms[0].y - prev_canvas_y > 0.12):
                        print("\n[CANVAS CLEANED] Swiped Down -> Flushing Ink Memory")
                        canvas_points.clear()
                        canvas_clear_cooldown = current_time
                    prev_canvas_y = right_hand_lms[0].y
                else:
                    prev_canvas_y = right_hand_lms[0].y

                p1 = SimplePoint(left_hand_lms[0].x, left_hand_lms[0].y)
                p2 = SimplePoint(right_hand_lms[0].x, right_hand_lms[0].y)
                current_dual_dist = dist(p1, p2)

                if base_dual_distance is None: base_dual_distance = current_dual_dist
                
                zoom_factor = (current_dual_dist / base_dual_distance) if base_dual_distance > 0 else 1.0
                virtual_object_radius = max(20, min(int(100 * zoom_factor), 250))
                status = f"[STRETCHING] Zoom Factor: {zoom_factor:.2f}x"

                hud_center = (w - 120, h - 120)
                overlay = frame.copy()
                cv2.circle(overlay, hud_center, virtual_object_radius, (0, 165, 255), -1)
                cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
                cv2.circle(frame, hud_center, virtual_object_radius, (0, 255, 255), 2)

                px1, px2 = (int(p1.x * w), int(p1.y * h)), (int(p2.x * w), int(p2.y * h))
                cv2.line(frame, px1, px2, (255, 255, 0), 2)

            for lm in left_hand_lms: cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (0, 255, 255), -1)
            for lm in right_hand_lms: cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (0, 255, 0), -1)

        elif num_hands_detected == 1 and (current_time - last_second_hand_time > SINGLE_HAND_COOLDOWN):
            if app_is_open: current_gesture_streak = 0 
            else:
                hand = result.hand_landmarks[0]
                raw_gesture, _ = gesture_from_hand(hand)
                
                if raw_gesture == last_stable_gesture: current_gesture_streak += 1
                else: last_stable_gesture = raw_gesture; current_gesture_streak = 1
                
                if current_gesture_streak >= REQUIRED_FRAMES:
                    status = f"Tracking: {last_stable_gesture}"

                    if last_stable_gesture in ["ONE", "TWO"]:
                        current_x, current_y = hand[8].x, hand[8].y
                        if swipe_start_x is None: swipe_start_x, swipe_start_y = current_x, current_y
                        
                        delta_x = current_x - swipe_start_x
                        delta_y = current_y - swipe_start_y

                        sx, curx = int(swipe_start_x * w), int(current_x * w)
                        line_c = (0, 255, 255) if last_stable_gesture == "ONE" else (255, 0, 255)
                        cv2.line(frame, (sx, h // 2), (curx, h // 2), line_c, 4)

                        if last_stable_gesture == "TWO" and delta_y > VERTICAL_THRESHOLD:
                            minimize_active_window(); swipe_start_x = None; current_gesture_streak = 0
                        elif delta_x > SWIPE_THRESHOLD:
                            if last_stable_gesture == "ONE": app_is_open = True; threading.Thread(target=launch_brave).start()
                            else: threading.Thread(target=shift_window_prev).start()
                            swipe_start_x = None; current_gesture_streak = 0
                        elif delta_x < -SWIPE_THRESHOLD:
                            if last_stable_gesture == "ONE": app_is_open = True; threading.Thread(target=launch_youtube).start()
                            else: threading.Thread(target=shift_window_next).start()
                            swipe_start_x = None; current_gesture_streak = 0
                        elif last_stable_gesture == "TWO" and current_gesture_streak > 25:
                            app_is_open = True; threading.Thread(target=launch_chrome).start()
                            swipe_start_x = None; current_gesture_streak = 0

                    elif last_stable_gesture == "PALM":
                        swipe_start_x = None
                        current_palm_size = dist(hand[0], hand[17])
                        if base_palm_size is None: base_palm_size = current_palm_size
                        
                        depth_ratio = current_palm_size / base_palm_size
                        status = f"Palm Depth Ratio: {depth_ratio:.2f}"

                        if depth_ratio > DEPTH_PUSH_THRESHOLD:
                            app_is_open = True; threading.Thread(target=clear_desktop).start()
                            base_palm_size = None; current_gesture_streak = 0
                        elif depth_ratio < DEPTH_PULL_THRESHOLD:
                            app_is_open = True; threading.Thread(target=maximize_active_window).start()
                            base_palm_size = None; current_gesture_streak = 0

                    else:
                        swipe_start_x = None; base_palm_size = None
                        if last_stable_gesture == "THREE":
                            app_is_open = True; threading.Thread(target=launch_system_app, args=("start notepad",)).start()
                            current_gesture_streak = 0
                        elif last_stable_gesture == "FOUR":
                            app_is_open = True; threading.Thread(target=launch_system_app, args=("start msedge",)).start()
                            current_gesture_streak = 0
                else: status = f"Validating Posture: ({current_gesture_streak})"
            
                for lm in hand: cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (0, 255, 0), -1)


        else:
            swipe_start_x = None; swipe_start_y = None; base_palm_size = None; base_dual_distance = None
            current_gesture_streak = 0; last_stable_gesture = "UNKNOWN"; virtual_object_radius = 100

        now = time.time()
        fps = int(1 / (now - prev_time)) if now != prev_time else 0
        prev_time = now

        # HUD Overlay Rendering
        cv2.rectangle(frame, (0, 0), (w, 60), (30, 30, 30), -1)
        cv2.putText(frame, status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, ui_color, 2)
        cv2.putText(frame, f"FPS: {fps}", (w - 140, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.imshow("Gesture Control HCI Engine", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"): break
        elif key == ord(" "): 
            print("\n[RESET] System unlocked.")
            app_is_open = False; swipe_start_x = None; current_gesture_streak = 0

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()

if __name__ == "__main__":
    main()