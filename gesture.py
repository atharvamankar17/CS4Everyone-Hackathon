import numpy as np
import time

class Gesture:
    def estimate_depth(self, hand_landmarks, handedness):
        wrist_z = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST].z
        depth_estimate = max(-0.5, min(0.5, wrist_z))
        self.depth_estimates[handedness].append(depth_estimate)
        smoothed_depth = np.mean(self.depth_estimates[handedness]) if self.depth_estimates[handedness] else depth_estimate
        return smoothed_depth
    
    def check_fingers_extended(self, hand_landmarks, handedness):
        landmarks = {i: lm for i, lm in enumerate(hand_landmarks.landmark)}
        wrist = landmarks[self.mp_hands.HandLandmark.WRIST]
        middle_mcp = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        hand_size = np.linalg.norm(np.array([wrist.x, wrist.y]) - np.array([middle_mcp.x, middle_mcp.y]))
        dynamic_threshold = self.finger_extension_threshold * hand_size
        thumb_tip = landmarks[self.mp_hands.HandLandmark.THUMB_TIP]
        thumb_ip = landmarks[self.mp_hands.HandLandmark.THUMB_IP]
        thumb_mcp = landmarks[self.mp_hands.HandLandmark.THUMB_MCP]
        index_mcp = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
        thumb_length = np.linalg.norm(np.array([thumb_tip.x, thumb_tip.y]) - np.array([thumb_mcp.x, thumb_mcp.y]))
        min_thumb_length = hand_size * 0.2
        thumb_extended = thumb_length > min_thumb_length
        thumb_up = thumb_tip.y < thumb_ip.y - dynamic_threshold
        if handedness == "Right":
            thumb_extended = thumb_extended and thumb_up and (thumb_tip.x < index_mcp.x)
        else:
            thumb_extended = thumb_extended and thumb_up and (thumb_tip.x > index_mcp.x)
        thumb_confidence = min(1.0, thumb_length / (min_thumb_length * 1.5))
        index_extended = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y < (landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y - dynamic_threshold)
        middle_extended = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < (landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y - dynamic_threshold)
        ring_extended = landmarks[self.mp_hands.HandLandmark.RING_FINGER_TIP].y < (landmarks[self.mp_hands.HandLandmark.RING_FINGER_PIP].y - dynamic_threshold)
        pinky_extended = landmarks[self.mp_hands.HandLandmark.PINKY_TIP].y < (landmarks[self.mp_hands.HandLandmark.PINKY_PIP].y - dynamic_threshold)
        if index_extended and middle_extended:
            index_tip_pos = np.array([landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].x, landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y])
            middle_tip_pos = np.array([landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].x, landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y])
            index_pip_pos = np.array([landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].x, landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y])
            middle_pip_pos = np.array([landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].x, landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y])
            index_vec = index_tip_pos - index_pip_pos
            middle_vec = middle_tip_pos - middle_pip_pos
            cos_angle = np.dot(index_vec, middle_vec) / (np.linalg.norm(index_vec) * np.linalg.norm(middle_vec))
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0)) * 180 / np.pi
            victory_valid = angle > 10
        else:
            victory_valid = True
        return {"thumb": thumb_extended, "index": index_extended, "middle": middle_extended, "ring": ring_extended, "pinky": pinky_extended, "victory_valid": victory_valid, "thumb_confidence": thumb_confidence}
    
    def detect_gesture(self, fingers_extended, handedness):
        gesture_scores = {}
        finger_weights = {"thumb": 2.0, "index": 1.5, "middle": 1.0, "ring": 0.8, "pinky": 0.8}
        for gesture_name, pattern in self.gesture_definitions.items():
            score = 0
            max_score = 0
            for finger, should_be_extended in pattern.items():
                weight = finger_weights.get(finger, 1.0)
                max_score += weight
                if finger == "thumb":
                    if fingers_extended.get(finger, False) == should_be_extended:
                        score += weight * fingers_extended.get("thumb_confidence", 0.5)
                    else:
                        score -= weight * 0.1
                else:
                    if fingers_extended.get(finger, False) == should_be_extended:
                        score += weight
                    else:
                        score -= weight * 0.2
            if gesture_name == "victory" and not fingers_extended.get("victory_valid", True):
                score -= 0.3
            if gesture_name in ["victory", "three_fingers"]:
                score += 0.2
            if gesture_name in self.custom_gestures:
                score += 0.2
            gesture_scores[gesture_name] = score / max_score if max_score > 0 else 0
        detected_gesture = max(gesture_scores, key=gesture_scores.get)
        confidence = gesture_scores[detected_gesture]
        self.gesture_confidence[handedness] = confidence * 100
        self.prev_gestures[handedness].append(detected_gesture)
        if len(self.prev_gestures[handedness]) >= 4:
            recent_gestures = list(self.prev_gestures[handedness])[-4:]
            gesture_counts = {}
            for g in recent_gestures:
                gesture_counts[g] = gesture_counts.get(g, 0) + 1
            most_common = max(gesture_counts, key=gesture_counts.get)
            if gesture_counts[most_common] >= 3:
                detected_gesture = most_common
                self.gesture_confidence[handedness] = min(100.0, self.gesture_confidence[handedness] * 1.2)
        gesture_name = {"index_pointing": "Index pointing", "victory": "Victory sign", "three_fingers": "Three fingers", "four_fingers": "Four fingers", "open_hand": "Open hand", "fist": "Fist"}.get(detected_gesture, detected_gesture)
        return gesture_name
    
    def update_gesture_timers(self, hand, gesture):
        current_time = time.time()
        if self.gesture_timers[hand]["gesture"] != gesture or self.gesture_timers[hand]["duration"] > 10:
            self.gesture_timers[hand]["gesture"] = gesture
            self.gesture_timers[hand]["time"] = current_time
            self.gesture_timers[hand]["duration"] = 0
        else:
            self.gesture_timers[hand]["duration"] = current_time - self.gesture_timers[hand]["time"]
    
    def get_gesture_duration(self, hand):
        return self.gesture_timers[hand]["duration"]
    
    def update_gesture_status(self, handedness, gesture):
        tree = self.left_tree if handedness == "Left" else self.right_tree
        items = self.left_tree_items if handedness == "Left" else self.right_tree_items
        for item_id in items.values():
            tree.set(item_id, "Status", "Not detected")
        if gesture in items:
            duration = self.get_gesture_duration(handedness)
            status = f"Active ({duration:.1f}s)"
            tree.set(items[gesture], "Status", status)

    def reset_gesture_state(self):
        from collections import deque
        self.prev_gestures = {"Left": deque(maxlen=20), "Right": deque(maxlen=20)}
        self.gesture_confidence = {"Left": 0.0, "Right": 0.0}
        self.gesture_validation_window = {"Left": deque(maxlen=6), "Right": deque(maxlen=6)}
        self.gesture_timers = {
            "Left": {"gesture": None, "time": 0, "duration": 0},
            "Right": {"gesture": None, "time": 0, "duration": 0}
        }
        if self.drag_active:
            import pyautogui
            pyautogui.mouseUp()
            self.drag_active = False
            self.status_message.set("Drag End")
