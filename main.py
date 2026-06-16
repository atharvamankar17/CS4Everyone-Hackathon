import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '2'

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf.symbol_database')

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime
from collections import deque
import queue
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import pythoncom
import logging
from filterpy.kalman import KalmanFilter
import psutil
import subprocess

from ui import UI
from gesture import Gesture
from actions import Actions

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
pyautogui.FAILSAFE = False

class GestureMouseController(UI, Gesture, Actions):
    def __init__(self, root):
        self.root = root
        self.root.title("Gesture Mouse Controller")
        self.root.geometry("1024x768")
        self.root.configure(bg="#C0C0C0")
        self.style = ttk.Style()
        self.configure_styles()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            model_complexity=0
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.screen_width, self.screen_height = pyautogui.size()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open camera.")
            self.root.destroy()
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.camera_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_queue = queue.Queue(maxsize=2)
        self.smoothing = 5
        self.prev_x, self.prev_y = self.screen_width // 2, self.screen_height // 2
        self.prev_hand_positions = deque(maxlen=15)
        self.sensitivity = 1.0
        self.prev_gestures = {"Left": deque(maxlen=20), "Right": deque(maxlen=20)}
        self.gesture_confidence = {"Left": 0.0, "Right": 0.0}
        self.gesture_validation_window = {"Left": deque(maxlen=6), "Right": deque(maxlen=6)}
        self.left_hand_gesture = "None"
        self.right_hand_gesture = "None"
        self.is_running = True
        self.is_controlling_mouse = True
        self.show_landmarks = True
        self.last_click_time = 0
        self.click_cooldown = 0.5
        self.drag_active = False
        self.scroll_speed = 6
        self.brightness_step = 5
        self.volume_step = 0.05
        self.finger_extension_threshold = 0.04
        self.opened_processes = {}
        self.initialize_kalman_filter()
        self.prev_landmarks = {"Left": None, "Right": None}
        self.depth_estimates = {"Left": deque(maxlen=8), "Right": deque(maxlen=8)}
        self.gesture_timers = {
            "Left": {"gesture": None, "time": 0, "duration": 0},
            "Right": {"gesture": None, "time": 0, "duration": 0}
        }
        self.left_hand_color = (0, 255, 0)
        self.right_hand_color = (0, 0, 255)
        self.available_actions = [
            "Move Pointer", "Left Click", "Right Click", "Double Left Click",
            "Double Right Click", "Drag", "Scroll Up", "Scroll Down", "Swipe Left",
            "Swipe Right", "Brightness Up", "Brightness Down", "Volume Up",
            "Volume Down", "Open/Play File 1", "Open/Play File 2", "Open/Play File 3",
            "Open/Play File 4", "Open/Play File 5"
        ]
        self.gesture_definitions = {
            "index_pointing": {"index": True, "middle": False, "ring": False, "pinky": False, "thumb": False},
            "victory": {"index": True, "middle": True, "ring": False, "pinky": False, "thumb": False},
            "three_fingers": {"index": True, "middle": True, "ring": True, "pinky": False, "thumb": False},
            "four_fingers": {"index": True, "middle": True, "ring": True, "pinky": True, "thumb": False},
            "open_hand": {"index": True, "middle": True, "ring": True, "pinky": True, "thumb": True},
            "fist": {"index": False, "middle": False, "ring": False, "pinky": False, "thumb": False}
        }
        self.gesture_actions = {
            "Left": {
                "Index pointing": "Move Pointer", "Victory sign": "Scroll Up",
                "Three fingers": "Swipe Left", "Four fingers": "None",
                "Open hand": "Brightness Up", "Fist": "None"
            },
            "Right": {
                "Index pointing": "Move Pointer", "Victory sign": "Scroll Down",
                "Three fingers": "Swipe Right", "Four fingers": "None",
                "Open hand": "Brightness Down", "Fist": "None"
            }
        }
        self.custom_gestures = {}
        self.file_paths = {}
        self.volume = None
        self.initialize_volume_control()
        self.fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.create_ui()
        self.video_thread = threading.Thread(target=self.video_stream)
        self.video_thread.daemon = True
        self.video_thread.start()
        self.update_video_display()
    
    def initialize_kalman_filter(self):
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self.kf.x = np.array([self.screen_width / 2, self.screen_height / 2, 0, 0])
        self.kf.F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]])
        self.kf.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        self.kf.P *= 1000.
        self.kf.R = np.array([[5, 0], [0, 5]])
        self.kf.Q = np.eye(4) * 0.1
    
    def initialize_volume_control(self):
        pythoncom.CoInitialize()
        for _ in range(3):
            try:
                devices = AudioUtilities.GetSpeakers()
                try:
                    self.volume = devices.EndpointVolume
                except AttributeError:
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self.volume = interface.QueryInterface(IAudioEndpointVolume)
                break
            except Exception:
                time.sleep(0.1)
        if not self.volume:
            messagebox.showwarning("Warning", "Volume control could not be initialized. Volume actions will be disabled.")
    
    def update_smoothing(self, event):
        self.smoothing = int(self.smoothing_scale.get())
        self.prev_hand_positions = deque(maxlen=max(5, self.smoothing))
        self.kf.R = np.array([[self.smoothing, 0], [0, self.smoothing]])
        self.status_message.set(f"Smoothing: {self.smoothing}")
        time.sleep(0.05)
    
    def update_scroll_speed(self, event):
        self.scroll_speed = int(self.scroll_scale.get())
        self.status_message.set(f"Scroll Speed: {self.scroll_speed}")
        time.sleep(0.05)
    
    def update_click_cooldown(self, event):
        self.click_cooldown = float(self.click_cooldown_scale.get())
        self.status_message.set(f"Click Cooldown: {self.click_cooldown:.2f}")
        time.sleep(0.05)
    
    def update_sensitivity(self, event):
        self.sensitivity = float(self.sensitivity_scale.get())
        self.status_message.set(f"Sensitivity: {self.sensitivity:.2f}")
        time.sleep(0.05)
    
    def toggle_mouse_control(self):
        self.is_controlling_mouse = self.mouse_control_var.get()
        self.reset_gesture_state()
        status = "On" if self.is_controlling_mouse else "Off"
        self.status_message.set(f"Mouse Control: {status}")
    
    def toggle_landmarks(self):
        self.show_landmarks = self.show_landmarks_var.get()
        status = "On" if self.show_landmarks else "Off"
        self.status_message.set(f"Landmarks: {status}")
    
    def reset_settings(self):
        self.smoothing = 5
        self.smoothing_scale.set(5)
        self.scroll_speed = 6
        self.scroll_scale.set(6)
        self.click_cooldown = 0.5
        self.click_cooldown_scale.set(0.5)
        self.sensitivity = 1.0
        self.sensitivity_scale.set(1.0)
        self.prev_hand_positions = deque(maxlen=15)
        self.status_message.set("Settings Reset")
    
    def calculate_fps(self):
        self.frame_count += 1
        elapsed_time = time.time() - self.fps_start_time
        if elapsed_time > 1:
            self.fps = self.frame_count / elapsed_time
            self.fps_start_time = time.time()
            self.frame_count = 0
            self.fps_var.set(f"FPS: {self.fps:.1f}")
    
    def get_display_dimensions(self):
        self.video_display_frame.update_idletasks()
        display_width = self.video_display_frame.winfo_width()
        display_height = self.video_display_frame.winfo_height()
        if display_width <= 1 or display_height <= 1:
            display_width = 640
            display_height = 480
        return display_width, display_height
    
    def on_frame_resize(self, event):
        self.get_display_dimensions()
    
    def update_video_display(self):
        try:
            if not self.frame_queue.empty():
                img = self.frame_queue.get_nowait()
                self.video_label.configure(image=img)
                self.video_label.image = img
        except queue.Empty:
            pass
        self.root.after(33, self.update_video_display)
    
    def video_stream(self):
        reinitialize_attempts = 0
        max_attempts = 5
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    reinitialize_attempts += 1
                    if reinitialize_attempts > max_attempts:
                        self.status_message.set("Camera Failure")
                        self.is_running = False
                        break
                    self.status_message.set("Camera Error")
                    self.cap.release()
                    self.cap = cv2.VideoCapture(0)
                    if not self.cap.isOpened():
                        self.status_message.set("Camera Reinitialization Failed")
                        time.sleep(1)
                        continue
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    reinitialize_attempts = 0
                    time.sleep(0.5)
                    continue
                self.calculate_fps()
                frame = cv2.flip(frame, 1)
                process_frame = frame.copy()
                rgb_frame = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)
                try:
                    self.hands_results = self.hands.process(rgb_frame)
                except Exception:
                    self.status_message.set("Reinitializing Hand Tracking")
                    self.hands.close()
                    self.hands = self.mp_hands.Hands(
                        static_image_mode=False,
                        max_num_hands=2,
                        min_detection_confidence=0.7,
                        min_tracking_confidence=0.7,
                        model_complexity=0
                    )
                    time.sleep(0.1)
                    continue
                if self.hands_results.multi_hand_landmarks:
                    left_hand_detected = False
                    right_hand_detected = False
                    for idx, hand_landmarks in enumerate(self.hands_results.multi_hand_landmarks):
                        handedness = self.hands_results.multi_handedness[idx].classification[0].label
                        if self.show_landmarks:
                            self.mp_draw.draw_landmarks(
                                frame, 
                                hand_landmarks, 
                                self.mp_hands.HAND_CONNECTIONS,
                                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                                self.mp_drawing_styles.get_default_hand_connections_style())
                        fingers_extended = self.check_fingers_extended(hand_landmarks, handedness)
                        depth = self.estimate_depth(hand_landmarks, handedness)
                        gesture = self.detect_gesture(fingers_extended, handedness)
                        self.update_gesture_timers(handedness, gesture)
                        if handedness == "Left":
                            self.left_hand_gesture = gesture
                            self.left_status_var.set(f"Left: {gesture} ({self.gesture_confidence['Left']:.1f}%)")
                            left_hand_detected = True
                        else:
                            self.right_hand_gesture = gesture
                            self.right_status_var.set(f"Right: {gesture} ({self.gesture_confidence['Right']:.1f}%)")
                            right_hand_detected = True
                        self.update_gesture_status(handedness, gesture)
                        self.perform_action(gesture, handedness, hand_landmarks, depth)
                        cv2.putText(frame, f"{handedness}: {gesture} ({self.gesture_confidence[handedness]:.1f}%)", (20 if handedness == "Left" else int(self.camera_width/2) + 20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.left_hand_color if handedness == "Left" else self.right_hand_color, 1)
                    if not left_hand_detected:
                        self.left_hand_gesture = "None"
                        self.left_status_var.set("Left: None (0%)")
                        self.gesture_timers["Left"]["gesture"] = None
                        self.gesture_confidence["Left"] = 0.0
                        self.prev_landmarks["Left"] = None
                    if not right_hand_detected:
                        self.right_hand_gesture = "None"
                        self.right_status_var.set("Right: None (0%)")
                        self.gesture_timers["Right"]["gesture"] = None
                        self.gesture_confidence["Right"] = 0.0
                        self.prev_landmarks["Right"] = None
                        if self.drag_active:
                            pyautogui.mouseUp()
                            self.drag_active = False
                            self.status_message.set("Drag End")
                else:
                    self.left_status_var.set("Left: None (0%)")
                    self.right_status_var.set("Right: None (0%)")
                    self.left_hand_gesture = "None"
                    self.right_hand_gesture = "None"
                    self.gesture_timers["Left"]["gesture"] = None
                    self.gesture_timers["Right"]["gesture"] = None
                    self.gesture_confidence["Left"] = 0.0
                    self.gesture_confidence["Right"] = 0.0
                    self.prev_landmarks["Left"] = None
                    self.prev_landmarks["Right"] = None
                    if self.drag_active:
                        pyautogui.mouseUp()
                        self.drag_active = False
                        self.status_message.set("Drag End")
                current_time = datetime.now().strftime("%H:%M:%S")
                cv2.putText(frame, current_time, (self.camera_width - 80, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                display_width, display_height = self.get_display_dimensions()
                camera_aspect = self.camera_width / self.camera_height
                display_aspect = display_width / display_height
                if camera_aspect > display_aspect:
                    new_height = display_height
                    new_width = int(new_height * camera_aspect)
                else:
                    new_width = display_width
                    new_height = int(new_width / camera_aspect)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                if new_width > display_width or new_height > display_height:
                    left = (new_width - display_width) // 2
                    top = (new_height - display_height) // 2
                    right = left + display_width
                    bottom = top + display_height
                    img = img.crop((left, top, right, bottom))
                img = ImageTk.PhotoImage(image=img)
                try:
                    self.frame_queue.put_nowait(img)
                except queue.Full:
                    pass
                time.sleep(0.01)
            except Exception:
                self.status_message.set("Video Stream Error")
                time.sleep(0.1)
                continue
        if self.cap is not None:
            self.cap.release()
        self.hands.close()
        cv2.destroyAllWindows()
        self.status_message.set("Video Stream Stopped")
    
    def cleanup(self):
        self.is_running = False
        for key, pid in list(self.opened_processes.items()):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    process.wait(timeout=3)
                    break
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    if attempt == max_retries - 1:
                        subprocess.run(['taskkill', '/PID', str(pid), '/F', '/T'], check=False)
                except Exception:
                    if attempt == max_retries - 1:
                        subprocess.run(['taskkill', '/PID', str(pid), '/F', '/T'], check=False)
                if attempt < max_retries - 1:
                    try:
                        psutil.Process(pid)
                        time.sleep(0.5)
                    except psutil.NoSuchProcess:
                        break
            try:
                psutil.Process(pid)
            except psutil.NoSuchProcess:
                pass
            finally:
                del self.opened_processes[key]
        if self.cap is not None:
            self.cap.release()
        self.hands.close()
        cv2.destroyAllWindows()
        self.root.destroy() 
    
    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.cleanup)
            self.root.mainloop()
        except Exception:
            self.status_message.set("Application Error")
            self.cleanup()

if __name__ == "__main__":
    root = tk.Tk()
    app = GestureMouseController(root)
    app.run()
