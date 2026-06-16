import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import psutil
import subprocess

class UI:
    def configure_styles(self):
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#C0C0C0", relief="raised")
        self.style.configure("TLabel", background="#C0C0C0", foreground="black", font=('MS Sans Serif', 8))
        self.style.configure("TButton", background="#C0C0C0", foreground="black", font=('MS Sans Serif', 8), relief="raised", borderwidth=2)
        self.style.configure("TCheckbutton", background="#C0C0C0", foreground="black", font=('MS Sans Serif', 8))
        self.style.configure("TScale", background="#C0C0C0", troughcolor="#D4D4D4", sliderrelief="raised")
        self.style.configure("TLabelframe", background="#C0C0C0", relief="groove", borderwidth=2)
        self.style.configure("TLabelframe.Label", background="#C0C0C0", foreground="black", font=('MS Sans Serif', 8, 'bold'))
        self.style.configure("Treeview", background="#FFFFFF", foreground="black", fieldbackground="#FFFFFF", font=('MS Sans Serif', 8))
        self.style.map("Treeview", background=[('selected', '#000080')])
        self.style.configure("Treeview.Heading", background="#C0C0C0", foreground="black", font=('MS Sans Serif', 8, 'bold'), relief="raised")
        self.style.configure("Status.TLabel", font=('MS Sans Serif', 8, 'bold'))
        self.style.configure("Title.TLabel", font=('MS Sans Serif', 10, 'bold'))

    def create_ui(self):
        main_frame = ttk.Frame(self.root, padding=4, relief="raised")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        title_frame = ttk.Frame(main_frame, relief="flat")
        title_frame.pack(fill=tk.X, pady=2)
        ttk.Label(title_frame, text="Gesture Mouse Controller", style="Title.TLabel").pack(side=tk.LEFT, padx=4)
        panel_frame = ttk.Frame(main_frame, relief="sunken", borderwidth=2)
        panel_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        left_panel = ttk.Frame(panel_frame, relief="flat")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        camera_frame = ttk.LabelFrame(left_panel, text=" Camera Feed ")
        camera_frame.pack(fill=tk.BOTH, expand=True, pady=4)
        self.video_display_frame = ttk.Frame(camera_frame, relief="sunken", borderwidth=2)
        self.video_display_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.video_display_frame.pack_propagate(False)
        self.video_display_frame.bind("<Configure>", self.on_frame_resize)
        self.video_label = ttk.Label(self.video_display_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        status_frame = ttk.Frame(camera_frame, relief="flat")
        status_frame.pack(fill=tk.X, padx=4, pady=2)
        self.left_status_var = tk.StringVar(value="Left: None (0%)")
        self.right_status_var = tk.StringVar(value="Right: None (0%)")
        self.fps_var = tk.StringVar(value="FPS: 0")
        ttk.Label(status_frame, textvariable=self.left_status_var, style="Status.TLabel", foreground="darkgreen").pack(side=tk.LEFT, padx=4)
        ttk.Label(status_frame, textvariable=self.right_status_var, style="Status.TLabel", foreground="darkred").pack(side=tk.LEFT, padx=16)
        ttk.Label(status_frame, textvariable=self.fps_var).pack(side=tk.RIGHT, padx=4)
        control_frame = ttk.LabelFrame(left_panel, text=" Control Panel ")
        control_frame.pack(fill=tk.X, pady=4)
        control_grid = ttk.Frame(control_frame, relief="flat")
        control_grid.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(control_grid, text="Mouse Control").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.mouse_control_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_grid, variable=self.mouse_control_var, command=self.toggle_mouse_control).grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(control_grid, text="Show Landmarks").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        self.show_landmarks_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_grid, variable=self.show_landmarks_var, command=self.toggle_landmarks).grid(row=0, column=3, sticky="w", padx=4, pady=2)
        ttk.Label(control_grid, text="Smoothing").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.smoothing_scale = ttk.Scale(control_grid, from_=1, to=20, orient=tk.HORIZONTAL, value=self.smoothing)
        self.smoothing_scale.bind("<B1-Motion>", self.update_smoothing)
        self.smoothing_scale.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(control_grid, text="Scroll Speed").grid(row=1, column=2, sticky="w", padx=4, pady=2)
        self.scroll_scale = ttk.Scale(control_grid, from_=1, to=50, orient=tk.HORIZONTAL, value=self.scroll_speed)
        self.scroll_scale.bind("<B1-Motion>", self.update_scroll_speed)
        self.scroll_scale.grid(row=1, column=3, sticky="w", padx=4, pady=2)
        ttk.Label(control_grid, text="Click Cooldown").grid(row=1, column=4, sticky="w", padx=4, pady=2)
        self.click_cooldown_scale = ttk.Scale(control_grid, from_=0.1, to=2.0, orient=tk.HORIZONTAL, value=self.click_cooldown)
        self.click_cooldown_scale.bind("<B1-Motion>", self.update_click_cooldown)
        self.click_cooldown_scale.grid(row=1, column=5, sticky="w", padx=4, pady=2)
        ttk.Label(control_grid, text="Sensitivity").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.sensitivity_scale = ttk.Scale(control_grid, from_=0.5, to=2.5, orient=tk.HORIZONTAL, value=self.sensitivity)
        self.sensitivity_scale.bind("<B1-Motion>", self.update_sensitivity)
        self.sensitivity_scale.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        reset_button = ttk.Button(control_grid, text="Reset", command=self.reset_settings)
        reset_button.grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        right_panel = ttk.Frame(panel_frame, width=320, relief="flat")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=4)
        self.create_gesture_tables(right_panel)
        custom_gesture_button = ttk.Button(right_panel, text="Add Custom Gesture", command=self.add_custom_gesture)
        custom_gesture_button.pack(fill=tk.X, padx=4, pady=4)
        help_frame = ttk.LabelFrame(right_panel, text=" Help ")
        help_frame.pack(fill=tk.X, pady=4)
        help_text = ("- Position hands in camera view\n- Keep hands visible\n- Use deliberate gestures\n- Click gestures to assign actions\n- Add custom gestures\n- Right-click custom gestures to rename or delete")
        ttk.Label(help_frame, text=help_text, justify=tk.LEFT, wraplength=300, font=('MS Sans Serif', 8)).pack(padx=4, pady=4, fill=tk.X)
        bottom_status = ttk.Frame(main_frame, relief="flat")
        bottom_status.pack(fill=tk.X, pady=2)
        self.status_message = tk.StringVar(value="Ready")
        ttk.Label(bottom_status, textvariable=self.status_message, font=('MS Sans Serif', 8)).pack(side=tk.LEFT, padx=4)
        ttk.Label(bottom_status, text="By ASEP grp-3").pack(side=tk.RIGHT, padx=4)

    def create_gesture_tables(self, parent):
        left_hand_frame = ttk.LabelFrame(parent, text=" Left Hand Gestures ")
        left_hand_frame.pack(fill=tk.BOTH, expand=True, pady=4)
        left_tree = ttk.Treeview(left_hand_frame, columns=("Gesture", "Action", "Status"), show="headings", height=8)
        left_tree.heading("Gesture", text="Gesture")
        left_tree.heading("Action", text="Action")
        left_tree.heading("Status", text="Status")
        left_tree.column("Gesture", width=100)
        left_tree.column("Action", width=120)
        left_tree.column("Status", width=100)
        left_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        left_tree.bind("<Double-1>", lambda e: self.open_action_selector("Left", left_tree))
        left_tree.bind("<Button-3>", lambda e: self.show_context_menu(e, "Left", left_tree))
        left_gestures = [("Index pointing", self.gesture_actions["Left"]["Index pointing"], "Not detected"), ("Victory sign", self.gesture_actions["Left"]["Victory sign"], "Not detected"), ("Three fingers", self.gesture_actions["Left"]["Three fingers"], "Not detected"), ("Four fingers", self.gesture_actions["Left"]["Four fingers"], "Not detected"), ("Open hand", self.gesture_actions["Left"]["Open hand"], "Not detected"), ("Fist", self.gesture_actions["Left"]["Fist"], "Not detected")]
        self.left_tree_items = {}
        for gesture, action, status in left_gestures:
            item_id = left_tree.insert("", "end", values=(gesture, action, status))
            self.left_tree_items[gesture] = item_id
        right_hand_frame = ttk.LabelFrame(parent, text=" Right Hand Gestures ")
        right_hand_frame.pack(fill=tk.BOTH, expand=True, pady=4)
        right_tree = ttk.Treeview(right_hand_frame, columns=("Gesture", "Action", "Status"), show="headings", height=8)
        right_tree.heading("Gesture", text="Gesture")
        right_tree.heading("Action", text="Action")
        right_tree.heading("Status", text="Status")
        right_tree.column("Gesture", width=100)
        right_tree.column("Action", width=120)
        right_tree.column("Status", width=100)
        right_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        right_tree.bind("<Double-1>", lambda e: self.open_action_selector("Right", right_tree))
        right_tree.bind("<Button-3>", lambda e: self.show_context_menu(e, "Right", right_tree))
        right_gestures = [("Index pointing", self.gesture_actions["Right"]["Index pointing"], "Not detected"), ("Victory sign", self.gesture_actions["Right"]["Victory sign"], "Not detected"), ("Three fingers", self.gesture_actions["Right"]["Three fingers"], "Not detected"), ("Four fingers", self.gesture_actions["Right"]["Four fingers"], "Not detected"), ("Open hand", self.gesture_actions["Right"]["Open hand"], "Not detected"), ("Fist", self.gesture_actions["Right"]["Fist"], "Not detected")]
        self.right_tree_items = {}
        for gesture, action, status in right_gestures:
            item_id = right_tree.insert("", "end", values=(gesture, action, status))
            self.right_tree_items[gesture] = item_id
        self.left_tree = left_tree
        self.right_tree = right_tree

    def show_context_menu(self, event, handedness, tree):
        selected = tree.identify_row(event.y)
        if not selected:
            return
        tree.selection_set(selected)
        item = tree.item(selected)
        gesture = item["values"][0]
        if gesture not in self.custom_gestures:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Rename", command=lambda: self.rename_gesture(handedness, gesture))
        menu.add_command(label="Delete", command=lambda: self.delete_gesture(handedness, gesture, tree))
        menu.post(event.x_root, event.y_root)

    def delete_gesture(self, handedness, gesture, tree):
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the gesture '{gesture}'?"):
            return
        keys_to_remove = [key for key in self.opened_processes if key[0] == gesture]
        for key in keys_to_remove:
            pid = self.opened_processes.get(key)
            if pid:
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
        if gesture in self.gesture_definitions:
            del self.gesture_definitions[gesture]
        if gesture in self.custom_gestures:
            del self.custom_gestures[gesture]
        for hand in ["Left", "Right"]:
            if gesture in self.gesture_actions[hand]:
                del self.gesture_actions[hand][gesture]
        for hand, tree_widget, items in [("Left", self.left_tree, self.left_tree_items), ("Right", self.right_tree, self.right_tree_items)]:
            if gesture in items:
                tree_widget.delete(items[gesture])
                del items[gesture]
        keys_to_remove = [key for key in self.file_paths if key[0] == gesture]
        for key in keys_to_remove:
            del self.file_paths[key]
        self.status_message.set(f"Gesture '{gesture}' deleted")

    def open_action_selector(self, handedness, tree):
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])
        gesture = item["values"][0]
        selector_window = tk.Toplevel(self.root)
        selector_window.title(f"Select Action for {gesture}")
        selector_window.geometry("300x650")
        selector_window.configure(bg="#C0C0C0")
        main_frame = ttk.Frame(selector_window, padding=4)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        action_frame = ttk.LabelFrame(main_frame, text=" Available Actions ")
        action_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        action_var = tk.StringVar(value=self.gesture_actions[handedness][gesture])
        def update_action():
            self.gesture_actions[handedness][gesture] = action_var.get()
            tree.set(selected[0], "Action", action_var.get())
            if action_var.get().startswith("Open/Play File"):
                file_path = filedialog.askopenfilename(title=f"Select File for {action_var.get()}", filetypes=[("All files", "*.*"), ("Video files", "*.mp4 *.avi *.mkv"), ("Audio files", "*.mp3 *.wav"), ("Image files", "*.jpg *.png *.gif"), ("Document files", "*.pdf *.doc *.docx *.txt")])
                if file_path:
                    self.file_paths[(gesture, action_var.get())] = file_path
                    self.status_message.set(f"File selected for {gesture} ({action_var.get()})")
                else:
                    action_var.set("None")
                    self.gesture_actions[handedness][gesture] = "None"
                    tree.set(selected[0], "Action", "None")
        for action in self.available_actions:
            ttk.Radiobutton(action_frame, text=action, value=action, variable=action_var, command=update_action).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(action_frame, text="None", value="None", variable=action_var, command=update_action).pack(anchor="w", padx=8, pady=2)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=4)
        ttk.Button(button_frame, text="OK", command=selector_window.destroy).pack(side=tk.RIGHT, padx=4)

    def add_custom_gesture(self):
        custom_window = tk.Toplevel(self.root)
        custom_window.title("Add Custom Gesture")
        custom_window.geometry("400x300")
        custom_window.configure(bg="#C0C0C0")
        main_frame = ttk.Frame(custom_window, padding=4)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(name_frame, text="Gesture Name:").pack(side=tk.LEFT)
        name_entry = ttk.Entry(name_frame)
        name_entry.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        finger_frame = ttk.LabelFrame(main_frame, text=" Finger States ")
        finger_frame.pack(fill=tk.X, padx=4, pady=4)
        finger_vars = {"thumb": tk.BooleanVar(), "index": tk.BooleanVar(), "middle": tk.BooleanVar(), "ring": tk.BooleanVar(), "pinky": tk.BooleanVar()}
        for i, (finger, var) in enumerate(finger_vars.items()):
            ttk.Checkbutton(finger_frame, text=finger.capitalize(), variable=var).grid(row=i//2, column=i%2, sticky="w", padx=4, pady=2)
        def save_gesture():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Gesture name is required.")
                return
            if name in self.gesture_definitions:
                messagebox.showerror("Error", "Gesture name already exists.")
                return
            definition = {finger: var.get() for finger, var in finger_vars.items()}
            self.gesture_definitions[name] = definition
            self.custom_gestures[name] = {"definition": definition}
            for handedness, tree, items in [("Left", self.left_tree, self.left_tree_items), ("Right", self.right_tree, self.right_tree_items)]:
                self.gesture_actions[handedness][name] = "None"
                item_id = tree.insert("", "end", values=(name, "None", "Not detected"))
                items[name] = item_id
            self.status_message.set(f"Custom gesture '{name}' added")
            custom_window.destroy()
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=4)
        ttk.Button(button_frame, text="Save", command=save_gesture).pack(side=tk.RIGHT, padx=4)
        ttk.Button(button_frame, text="Cancel", command=custom_window.destroy).pack(side=tk.RIGHT, padx=4)

    def rename_gesture(self, handedness, gesture):
        rename_window = tk.Toplevel(self.root)
        rename_window.geometry("300x150")
        rename_window.configure(bg="#C0C0C0")
        main_frame = ttk.Frame(rename_window, padding=4)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        ttk.Label(main_frame, text="New Name:").pack(anchor="w", padx=4)
        new_name_entry = ttk.Entry(main_frame)
        new_name_entry.pack(fill=tk.X, padx=4, pady=4)
        def save_new_name():
            new_name = new_name_entry.get().strip()
            if not new_name:
                messagebox.showerror("Error", "New name is required.")
                return
            if new_name in self.gesture_definitions:
                messagebox.showerror("Error", "Name already exists.")
                return
            self.gesture_definitions[new_name] = self.gesture_definitions.pop(gesture)
            if gesture in self.custom_gestures:
                self.custom_gestures[new_name] = self.custom_gestures.pop(gesture)
            for hand in ["Left", "Right"]:
                self.gesture_actions[hand][new_name] = self.gesture_actions[hand].pop(gesture)
            for hand, tree, items in [("Left", self.left_tree, self.left_tree_items), ("Right", self.right_tree, self.right_tree_items)]:
                item_id = items.pop(gesture)
                tree.set(item_id, "Gesture", new_name)
                items[new_name] = item_id
            keys_to_update = [key for key in self.file_paths if key[0] == gesture]
            for key in keys_to_update:
                self.file_paths[(new_name, key[1])] = self.file_paths.pop(key)
            keys_to_update = [key for key in self.opened_processes if key[0] == gesture]
            for key in keys_to_update:
                self.opened_processes[(new_name, key[1])] = self.opened_processes.pop(key)
            self.status_message.set(f"Gesture renamed to '{new_name}'")
            rename_window.destroy()
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=4)
        ttk.Button(button_frame, text="Save", command=save_new_name).pack(side=tk.RIGHT, padx=4)
        ttk.Button(button_frame, text="Cancel", command=rename_window.destroy).pack(side=tk.RIGHT, padx=4)
