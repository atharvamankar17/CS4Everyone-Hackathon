import pyautogui
import screen_brightness_control as sbc
import pythoncom
import logging
import time
import os
import psutil
import subprocess
import numpy as np

class Actions:
    def adjust_brightness(self, direction):
        for _ in range(3):
            try:
                current_brightness = sbc.get_brightness()
                if isinstance(current_brightness, list):
                    current_brightness = current_brightness[0]
                if direction == "up":
                    new_brightness = min(100, current_brightness + self.brightness_step)
                    sbc.set_brightness(new_brightness, force=True)
                    self.status_message.set(f"Brightness Increased to {new_brightness}%")
                elif direction == "down":
                    new_brightness = max(0, current_brightness - self.brightness_step)
                    sbc.set_brightness(new_brightness, force=True)
                    self.status_message.set(f"Brightness Decreased to {new_brightness}%")
                break
            except Exception as e:
                time.sleep(0.1)
                if _ == 2:
                    self.status_message.set("Brightness Control Failed")
    
    def adjust_volume(self, direction):
        if not self.volume:
            self.status_message.set("Volume Control Not Initialized")
            return
        for _ in range(3):
            try:
                pythoncom.CoInitialize()
                current_volume = self.volume.GetMasterVolumeLevelScalar()
                if direction == "up":
                    new_volume = min(1.0, current_volume + self.volume_step)
                    self.volume.SetMasterVolumeLevelScalar(new_volume, None)
                    self.status_message.set(f"Volume Increased to {int(new_volume * 100)}%")
                elif direction == "down":
                    new_volume = max(0.0, current_volume - self.volume_step)
                    self.volume.SetMasterVolumeLevelScalar(new_volume, None)
                    self.status_message.set(f"Volume Decreased to {int(new_volume * 100)}%")
                break
            except Exception as e:
                time.sleep(0.1)
                if _ == 2:
                    self.status_message.set("Volume Control Failed")
            finally:
                pythoncom.CoUninitialize()

    def get_running_pids(self):
        return {p.pid for p in psutil.process_iter()}

    def find_new_process(self, before_pids, file_path, timeout=3):
        start_time = time.time()
        while time.time() - start_time < timeout:
            after_pids = self.get_running_pids()
            new_pids = after_pids - before_pids
            for pid in new_pids:
                try:
                    process = psutil.Process(pid)
                    cmdline = process.cmdline()
                    process_name = process.name().lower()
                    file_name = os.path.basename(file_path).lower()
                    file_ext = os.path.splitext(file_path)[1].lower()
                    app_indicators = {
                        '.pdf': ['acrobat', 'foxit', 'pdf'],
                        '.mp4': ['vlc', 'wmplayer', 'mpc-hc'],
                        '.avi': ['vlc', 'wmplayer', 'mpc-hc'],
                        '.mkv': ['vlc', 'wmplayer', 'mpc-hc'],
                        '.mp3': ['vlc', 'wmplayer', 'winamp'],
                        '.wav': ['vlc', 'wmplayer', 'winamp'],
                        '.ppt': ['powerpnt'],
                        '.pptx': ['powerpnt'],
                        '.doc': ['winword'],
                        '.docx': ['winword'],
                        '.txt': ['notepad']
                    }
                    indicators = app_indicators.get(file_ext, [])
                    if any(indicator in process_name for indicator in indicators):
                        if any(file_name in arg.lower() for arg in cmdline if isinstance(arg, str)):
                            return pid
                        return pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            time.sleep(0.1)
        return None

    def open_file(self, file_path, gesture, action):
        key = (gesture, action)
        try:
            if key in self.opened_processes:
                pid = self.opened_processes[key]
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
                    self.status_message.set("Failed to Close File: Process Still Running")
                except psutil.NoSuchProcess:
                    self.status_message.set("File Closed")
                finally:
                    del self.opened_processes[key]
            else:
                if not os.path.exists(file_path):
                    self.status_message.set("File Path Invalid")
                    return
                before_pids = self.get_running_pids()
                os.startfile(file_path)
                pid = self.find_new_process(before_pids, file_path)
                if pid:
                    self.opened_processes[key] = pid
                    self.status_message.set("File Opened/Played")
                else:
                    self.status_message.set("Failed to Track Process")
        except Exception as e:
            self.status_message.set(f"File Operation Failed: {str(e)}")
    
    def smooth_scroll(self, distance):
        steps = 10
        step_distance = distance // steps
        for _ in range(steps):
            pyautogui.scroll(step_distance)
            time.sleep(0.02)
    
    def smooth_swipe(self, direction, swipe_count):
        for _ in range(swipe_count):
            pyautogui.hotkey('alt', direction)
            time.sleep(0.02)
    
    def perform_action(self, gesture, handedness, landmark_data, depth):
        if not self.is_controlling_mouse:
            self.status_message.set("Mouse Control Disabled")
            return
        index_tip = landmark_data.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_tip_x, index_tip_y = index_tip.x, index_tip.y
        normalized_x = np.clip(index_tip_x, 0.15, 0.85)
        normalized_y = np.clip(index_tip_y, 0.15, 0.85)
        mapped_x = ((normalized_x - 0.15) / 0.7) * self.screen_width
        mapped_y = ((normalized_y - 0.15) / 0.7) * self.screen_height
        screen_x = mapped_x * (self.sensitivity ** 0.5)
        screen_y = mapped_y * (self.sensitivity ** 0.5)
        margin_x = self.screen_width * 0.05
        margin_y = self.screen_height * 0.05
        screen_x = np.clip(screen_x, margin_x, self.screen_width - margin_x)
        screen_y = np.clip(screen_y, margin_y, self.screen_height - margin_y)
        self.kf.predict()
        self.kf.update(np.array([screen_x, screen_y]))
        smooth_x, smooth_y = self.kf.x[:2]
        smooth_x = np.clip(smooth_x, 0, self.screen_width - 1)
        smooth_y = np.clip(smooth_y, 0, self.screen_height - 1)
        self.prev_x, self.prev_y = smooth_x, smooth_y
        duration = self.get_gesture_duration(handedness)
        action = self.gesture_actions[handedness].get(gesture, "None")
        confidence = self.gesture_confidence[handedness]
        if action == "None" or confidence < 70.0 or duration > 10.0:
            if self.drag_active:
                pyautogui.mouseUp()
                self.drag_active = False
                self.status_message.set("Drag End")
            return
        try:
            if action == "Move Pointer":
                pyautogui.moveTo(int(smooth_x), int(smooth_y), duration=0.01, tween=pyautogui.easeOutQuad)
                self.status_message.set("Pointer Moved")
            elif action == "Left Click" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    pyautogui.click(button='left')
                    self.status_message.set("Left Click")
                    self.last_click_time = time.time()
            elif action == "Right Click" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    pyautogui.click(button='right')
                    self.status_message.set("Right Click")
                    self.last_click_time = time.time()
            elif action == "Double Left Click" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    pyautogui.click(button='left')
                    time.sleep(0.1)
                    pyautogui.click(button='left')
                    self.status_message.set("Double Left Click")
                    self.last_click_time = time.time()
            elif action == "Double Right Click" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    pyautogui.click(button='right')
                    time.sleep(0.1)
                    pyautogui.click(button='right')
                    self.status_message.set("Double Right Click")
                    self.last_click_time = time.time()
            elif action == "Drag" and duration > 0.1:
                if not self.drag_active:
                    pyautogui.mouseDown(button='left')
                    self.drag_active = True
                    self.status_message.set("Drag Start")
                pyautogui.moveTo(int(smooth_x), int(smooth_y), duration=0.01, tween=pyautogui.easeOutQuad)
            elif action == "Scroll Up" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    scroll_distance = self.scroll_speed * 5
                    self.smooth_scroll(scroll_distance)
                    self.status_message.set("Scroll Up")
                    self.last_click_time = time.time()
            elif action == "Scroll Down" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    scroll_distance = -self.scroll_speed * 5
                    self.smooth_scroll(scroll_distance)
                    self.status_message.set("Scroll Down")
                    self.last_click_time = time.time()
            elif action in ["Swipe Left", "Swipe Right"] and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    swipe_count = max(1, int(self.scroll_speed // 5))
                    direction = 'left' if action == "Swipe Left" else 'right'
                    self.smooth_swipe(direction, swipe_count)
                    self.status_message.set(action)
                    self.last_click_time = time.time()
            elif action == "Brightness Up" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    self.adjust_brightness("up")
                    self.last_click_time = time.time()
            elif action == "Brightness Down" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    self.adjust_brightness("down")
                    self.last_click_time = time.time()
            elif action == "Volume Up" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    self.adjust_volume("up")
                    self.last_click_time = time.time()
            elif action == "Volume Down" and duration > 0.1:
                if time.time() - self.last_click_time > self.click_cooldown:
                    self.adjust_volume("down")
                    self.last_click_time = time.time()
            elif action in ["Open/Play File 1", "Open/Play File 2", "Open/Play File 3", "Open/Play File 4", "Open/Play File 5"] and duration > 0.3:
                if time.time() - self.last_click_time > self.click_cooldown:
                    file_path = self.file_paths.get((gesture, action))
                    if file_path:
                        self.open_file(file_path, gesture, action)
                    self.last_click_time = time.time()
            if self.drag_active and action != "Drag":
                pyautogui.mouseUp()
                self.drag_active = False
                self.status_message.set("Drag End")
        except Exception as e:
            self.status_message.set(f"Action Failed: {str(e)}")
