import customtkinter as ctk
import string
import random
import datetime
import os
import subprocess
import psutil
import webbrowser
from core.config_manager import load_config, save_config, DEFAULT_GROUP_CONFIG, get_config_dir
import ctypes
import sys
from daemon import ADBLOCK_LISTS

VERSION = "1.1.1"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

def is_admin():
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        return os.geteuid() == 0

class InputListFrame(ctk.CTkFrame):
    def __init__(self, master, config_key, placeholder, validation_fn=None, info_tooltip=None, browse_mode=None, config_section=None, **kwargs):
        super().__init__(master, fg_color="#2b2b2b", corner_radius=10, **kwargs)
        
        self.config_key = config_key
        self.validation_fn = validation_fn
        self.browse_mode = browse_mode
        self.config_section = config_section
        self.app = master.app
        self.group_name = master.group_name
        
        group_data = self.app.config_data["groups"][self.group_name]
        if self.config_section:
            section = group_data.get(self.config_section, {})
            self.items = section.get(config_key, [])
        else:
            self.items = group_data.get(config_key, [])
        
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text=placeholder, height=35, corner_radius=8, border_width=1)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add_item())
        
        if self.browse_mode:
            self.browse_btn = ctk.CTkButton(self.input_frame, text="Browse", width=70, height=35, corner_radius=8, command=self.browse_file)
            self.browse_btn.pack(side="left", padx=(8, 0))
            
        self.add_btn = ctk.CTkButton(self.input_frame, text="+", width=40, height=35, corner_radius=8, command=self.add_item)
        self.add_btn.pack(side="left", padx=(8, 0))
        
        self.feedback_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.feedback_lbl.pack(fill="x", padx=10, pady=(0, 2))
        
        # Fixed height spacer to prevent layout jumps when info_tooltip is present/absent
        if not info_tooltip:
            ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), height=1).pack(pady=(0, 15))
        else:
            self.info_desc = ctk.CTkLabel(self, text=info_tooltip, text_color="gray", font=ctk.CTkFont(size=11))
            self.info_desc.pack(fill="x", padx=15, pady=(2, 5))

        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.item_frames = {}
        self.render_list()

    def browse_file(self):
        if self.browse_mode == "folder":
            filename = ctk.filedialog.askdirectory(title="Select Folder")
        else:
            filetypes = []
            if self.browse_mode == "app":
                filetypes = [("Executables", "*.exe")] if os.name == 'nt' else [("All Files", "*.*")]
            elif self.browse_mode == "file":
                filetypes = [("All Files", "*.*")]
                
            filename = ctk.filedialog.askopenfilename(title="Select File", filetypes=filetypes)
        if filename:
            self.entry.delete(0, "end")
            self.entry.insert(0, filename)
            self.add_item()
            
    def add_item(self):
        val = self.entry.get().strip()
        if not val:
            return
            
        if self.validation_fn:
            is_valid, err_msg = self.validation_fn(val)
            if not is_valid:
                self.feedback_lbl.configure(text=f"❌ {err_msg}", text_color="red")
                return
                
        if val in self.items:
            self.feedback_lbl.configure(text="❌ Item already exists", text_color="red")
            return
            
        self.items.append(val)
        self.entry.delete(0, "end")
        self.feedback_lbl.configure(text="✅ Added successfully", text_color="green")
        self.after(2000, lambda: self.feedback_lbl.configure(text=""))
        
        if self.config_section:
            section = self.app.config_data["groups"][self.group_name].setdefault(self.config_section, {})
            section[self.config_key] = self.items
        else:
            self.app.config_data["groups"][self.group_name][self.config_key] = self.items
        self.app.trigger_save()
        self.add_item_ui(val)

    def remove_item(self, val):
        if val in self.items:
            self.items.remove(val)
            if self.config_section:
                section = self.app.config_data["groups"][self.group_name].setdefault(self.config_section, {})
                section[self.config_key] = self.items
            else:
                self.app.config_data["groups"][self.group_name][self.config_key] = self.items
            self.app.trigger_save()
            frame = self.item_frames.pop(val)
            frame.destroy()

    def render_list(self):
        for val in self.items:
            self.add_item_ui(val)
            
    def add_item_ui(self, val):
        frame = ctk.CTkFrame(self.scroll_frame)
        frame.pack(fill="x", pady=2)
        lbl = ctk.CTkLabel(frame, text=val, anchor="w")
        lbl.pack(side="left", fill="x", expand=True, padx=5)
        del_btn = ctk.CTkButton(frame, text="Remove", width=60, fg_color="#8b0000", hover_color="#5a0000",
                                command=lambda v=val: self.remove_item(v))
        del_btn.pack(side="right", padx=5)
        self.item_frames[val] = frame


class ContentFilterTab(ctk.CTkFrame):
    def __init__(self, master, app, group_name, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.group_name = group_name
        
        ad_cfg = self.app.config_data["groups"][self.group_name].get("adblocker", {})
        
        container = ctk.CTkScrollableFrame(self, fg_color="#2b2b2b", corner_radius=10)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        container.app = self.app
        container.group_name = self.group_name
        
        self.enabled_var = ctk.BooleanVar(value=ad_cfg.get("enabled", False))
        self.enabled_switch = ctk.CTkSwitch(container, text="Enable Content Filter", variable=self.enabled_var, font=ctk.CTkFont(weight="bold"), command=self.on_change)
        self.enabled_switch.pack(pady=10, anchor="w", padx=20)
        
        self.persist_var = ctk.BooleanVar(value=ad_cfg.get("persist_all_day", False))
        self.persist_switch = ctk.CTkSwitch(container, text="Enforce All Day (Ignores Schedule)", variable=self.persist_var, command=self.on_change)
        self.persist_switch.pack(pady=5, anchor="w", padx=20)
        
        lbl = ctk.CTkLabel(container, text="Block Categories:", font=ctk.CTkFont(weight="bold"))
        lbl.pack(anchor="w", padx=20, pady=(10, 0))
        
        self.ads_var = ctk.BooleanVar(value=ad_cfg.get("ads_trackers", False))
        ctk.CTkCheckBox(container, text="Ads, Trackers & Telemetry", variable=self.ads_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)
        
        self.malware_var = ctk.BooleanVar(value=ad_cfg.get("malware_annoyances", False))
        ctk.CTkCheckBox(container, text="Malware & Annoyances", variable=self.malware_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)
        
        self.social_var = ctk.BooleanVar(value=ad_cfg.get("social_media", False))
        ctk.CTkCheckBox(container, text="Social Media & Chat (Twitter, Discord)", variable=self.social_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)

        self.adult_var = ctk.BooleanVar(value=ad_cfg.get("adult_content", False))
        ctk.CTkCheckBox(container, text="Adult Content (18+)", variable=self.adult_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)

        self.gambling_var = ctk.BooleanVar(value=ad_cfg.get("gambling", False))
        ctk.CTkCheckBox(container, text="Gambling & Betting", variable=self.gambling_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)
        
        self.piracy_var = ctk.BooleanVar(value=ad_cfg.get("piracy_illegal", False))
        ctk.CTkCheckBox(container, text="Piracy & Illegal Sites", variable=self.piracy_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)
        
        self.entertainment_var = ctk.BooleanVar(value=ad_cfg.get("entertainment", False))
        ctk.CTkCheckBox(container, text="Entertainment & Anime (Netflix, Crunchyroll)", variable=self.entertainment_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)
        
        self.shopping_var = ctk.BooleanVar(value=ad_cfg.get("shopping", False))
        ctk.CTkCheckBox(container, text="Shopping (Amazon, Temu)", variable=self.shopping_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)
        
        self.ai_var = ctk.BooleanVar(value=ad_cfg.get("ai_tech", False))
        ctk.CTkCheckBox(container, text="AI & Tech Newsletters", variable=self.ai_var, command=self.on_change).pack(anchor="w", padx=30, pady=2)

        lbl = ctk.CTkLabel(container, text="Exceptions (Allowlist):", font=ctk.CTkFont(weight="bold"))
        lbl.pack(anchor="w", padx=20, pady=(15, 0))
        
        def validate_domain(domain):
            if "http" in domain: return False, "Exclude http/https"
            return True, ""
            
        self.app.group_name = self.group_name
        self.exceptions_list = InputListFrame(container, "exceptions", "Enter domain to exclude (e.g. google.com)", validation_fn=validate_domain, config_section="adblocker")
        self.exceptions_list.pack(fill="both", expand=True, padx=20, pady=5)

        lbl_custom = ctk.CTkLabel(container, text="Custom Lists (URLs or local .txt paths):", font=ctk.CTkFont(weight="bold"))
        lbl_custom.pack(anchor="w", padx=20, pady=(15, 0))
        
        self.custom_lists = InputListFrame(container, "custom_lists", "Enter URL or absolute Path", browse_mode="file", config_section="adblocker")
        self.custom_lists.pack(fill="both", expand=True, padx=20, pady=5)
        
    def on_change(self, *args):
        ad_cfg = self.app.config_data["groups"][self.group_name].get("adblocker", {})
        ad_cfg["enabled"] = self.enabled_var.get()
        ad_cfg["persist_all_day"] = self.persist_var.get()
        ad_cfg["ads_trackers"] = self.ads_var.get()
        ad_cfg["malware_annoyances"] = self.malware_var.get()
        ad_cfg["social_media"] = self.social_var.get()
        ad_cfg["adult_content"] = self.adult_var.get()
        ad_cfg["gambling"] = self.gambling_var.get()
        ad_cfg["piracy_illegal"] = self.piracy_var.get()
        ad_cfg["entertainment"] = self.entertainment_var.get()
        ad_cfg["shopping"] = self.shopping_var.get()
        ad_cfg["ai_tech"] = self.ai_var.get()
        ad_cfg["exceptions"] = self.exceptions_list.items
        # Persist custom_lists into the adblocker block (daemon reads from here)
        ad_cfg["custom_lists"] = self.custom_lists.items
        self.app.config_data["groups"][self.group_name]["adblocker"] = ad_cfg
        self.app.trigger_save()


class ProductivityApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Simple Productivity Blocker")
        
        self.update_idletasks()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        w = int(ws * 0.65)
        h = int(hs * 0.75)
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.config_data = load_config()
        self.save_job = None
        self.countdown_job = None
        self.current_screen = None
        self.group_name = None
        
        self.check_daemon()
        self.show_dashboard()

    def check_daemon(self):
        try:
            if not self._daemon_running():
                self.launch_daemon()
        except:
            self.launch_daemon()

    def _daemon_running(self):
        daemon_name = "daemon.exe" if os.name == 'nt' else "daemon"
        daemon_name_lower = daemon_name.lower()
        for proc in psutil.process_iter(['name', 'cmdline', 'exe']):
            try:
                name = (proc.info.get('name') or '').lower()
                cmdline = proc.info.get('cmdline') or []
                if getattr(sys, 'frozen', False):
                    if name == daemon_name_lower:
                        return True
                    exe = (proc.info.get('exe') or '').lower()
                    if exe.endswith(daemon_name_lower):
                        return True
                else:
                    for arg in cmdline:
                        if "daemon.py" in str(arg).lower():
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def launch_daemon(self):
        if getattr(sys, 'frozen', False):
            daemon_path = os.path.join(os.path.dirname(sys.executable), "daemon.exe" if os.name == 'nt' else "daemon")
            exe_to_run = daemon_path
        else:
            daemon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon.py")
            exe_to_run = sys.executable

        args = [exe_to_run] if getattr(sys, 'frozen', False) else [sys.executable, daemon_path]

        if not is_admin():
            if os.name == 'nt':
                ctypes.windll.shell32.ShellExecuteW(None, "runas", args[0], daemon_path if not getattr(sys, 'frozen', False) else "", None, 0)
            else:
                try:
                    subprocess.Popen(["pkexec"] + args)
                except FileNotFoundError:
                    pass
        else:
            if os.name == 'nt':
                subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def trigger_save(self):
        self.show_saving()
        if self.save_job:
            self.after_cancel(self.save_job)
        self.save_job = self.after(1000, self._do_save)
        
    def _do_save(self):
        save_config(self.config_data)
        self.start_countdown(3.00)
        
    def start_countdown(self, remaining):
        if self.countdown_job:
            self.after_cancel(self.countdown_job)
        if remaining <= 0:
            self.hide_saving()
        else:
            if hasattr(self, 'timer_lbl') and self.timer_lbl.winfo_exists():
                self.timer_lbl.configure(text=f"{remaining:.2f}s left until applied...", text_color="orange")
            self.countdown_job = self.after(50, self.start_countdown, remaining - 0.05)
        
    def show_saving(self):
        if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
            self.status_lbl.configure(text="Saving... ⏳", text_color="#1f538d")
        if hasattr(self, 'timer_lbl') and self.timer_lbl.winfo_exists():
            self.timer_lbl.configure(text="")
        
    def hide_saving(self):
        if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
            self.status_lbl.configure(text="All changes saved ✅", text_color="green")
        if hasattr(self, 'timer_lbl') and self.timer_lbl.winfo_exists():
            self.timer_lbl.configure(text="")

    def clear_screen(self):
        if self.current_screen:
            self.current_screen.destroy()

    def show_challenge_screen(self, next_action):
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        
        # Access security config for the current group
        sec_cfg = self.config_data["groups"][self.group_name].get("security", {})
        length = sec_cfg.get("challenge_length", 32)
        
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:',.<>?/"
        self.challenge_string = ''.join(random.choice(chars) for _ in range(length))
        
        challenge_frame = ctk.CTkFrame(self.current_screen)
        challenge_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        label = ctk.CTkLabel(challenge_frame, text=f"Security Challenge: {self.group_name}", font=ctk.CTkFont(size=24, weight="bold"))
        label.pack(pady=20)
        
        instructions = ctk.CTkLabel(challenge_frame, text="Please type the following text exactly to edit this group:")
        instructions.pack()
        
        mono_font = ctk.CTkFont(family="Consolas", size=16)
        
        self.text_display = ctk.CTkLabel(challenge_frame, text=self.challenge_string, font=mono_font, wraplength=800)
        self.text_display.pack(fill="x", padx=20, pady=20)
        
        self.input_entry = ctk.CTkTextbox(challenge_frame, height=80, wrap="word", font=mono_font)
        self.input_entry.pack(fill="x", padx=20, pady=10)
        
        def on_enter(event):
            self.verify_challenge(next_action)
            return "break"
            
        self.input_entry.bind("<Return>", on_enter)
        
        btn_frame = ctk.CTkFrame(challenge_frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Back to Dashboard", fg_color="transparent", width=140, command=self.show_dashboard).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Verify", command=lambda: self.verify_challenge(next_action)).pack(side="left", padx=6)
        
    def verify_challenge(self, next_action):
        user_input = self.input_entry.get("1.0", "end-1c").strip()
        if user_input == self.challenge_string:
            next_action()
        else:
            self.input_entry.configure(fg_color="#3a1c1c")
            self.after(500, lambda: self.input_entry.configure(fg_color=["#F9F9FA", "#1D1E1E"]))

    def show_dashboard(self):
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        
        top_bar = ctk.CTkFrame(self.current_screen, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(top_bar, text="Groups (Profiles)", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="⚙  Options", command=self.show_settings,
                      fg_color="transparent", hover_color="#3a3a3a", width=100).pack(side="right")
        
        self.groups_scroll = ctk.CTkScrollableFrame(self.current_screen)
        self.groups_scroll.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        
        for name, data in self.config_data["groups"].items():
            self.create_group_card(name, data)

        # --- Bottom Status Bar ---
        self.status_frame = ctk.CTkFrame(self.current_screen, height=44, fg_color="transparent")
        self.status_frame.pack(fill="x", side="bottom", padx=20, pady=10)
        self.status_frame.pack_propagate(False)
        
        self.status_lbl = ctk.CTkLabel(self.status_frame, text="Ready", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_lbl.pack(side="left", anchor="center")
        
        self.timer_lbl = ctk.CTkLabel(self.status_frame, text="", text_color="green", font=ctk.CTkFont(size=12))
        self.timer_lbl.pack(side="left", padx=10, anchor="center")

        # Center frame absorbs remaining space so the button sits at true center
        center_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        center_frame.pack(side="left", fill="both", expand=True)
        ctk.CTkButton(center_frame, text="+ Add New Group", command=self.add_new_group
                      ).place(relx=0.5, rely=0.5, anchor="center")

    def _center_dialog(self, dialog, width, height):
        self.update_idletasks()
        x = self.winfo_x() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_y() + max(0, (self.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _prompt_text_dialog(self, title, message, initial=""):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        self._center_dialog(dialog, 420, 180)

        ctk.CTkLabel(dialog, text=message).pack(padx=20, pady=(20, 10))
        entry = ctk.CTkEntry(dialog)
        entry.pack(fill="x", padx=20)
        if initial:
            entry.insert(0, initial)
        entry.focus_set()

        result = {"value": None}

        def on_ok():
            value = entry.get().strip()
            result["value"] = value if value else None
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        entry.bind("<Return>", lambda event: (on_ok(), "break"))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", command=on_cancel).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="OK", command=on_ok).pack(side="left", padx=6)

        dialog.wait_window()
        return result["value"]

    def _confirm_dialog(self, title, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        self._center_dialog(dialog, 420, 170)

        ctk.CTkLabel(dialog, text=message).pack(padx=20, pady=(25, 10))

        result = {"value": False}

        def on_yes():
            result["value"] = True
            dialog.destroy()

        def on_no():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_no)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", command=on_no).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Delete", fg_color="#8b0000", hover_color="#5a0000", command=on_yes).pack(side="left", padx=6)

        dialog.wait_window()
        return result["value"]

    def _info_dialog(self, title, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        self._center_dialog(dialog, 420, 160)

        ctk.CTkLabel(dialog, text=message).pack(padx=20, pady=(25, 10))

        def on_ok():
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_ok)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="OK", command=on_ok).pack(side="left", padx=6)

        dialog.wait_window()

    def save_security(self, *args):
        self.config_data["groups"][self.group_name]["security"] = {
            "enabled": self.sec_enabled.get() == 1,
            "challenge_length": int(self.length_var.get())
        }
        self.trigger_save()

    def create_group_card(self, name, data):
        card = ctk.CTkFrame(self.groups_scroll)
        card.pack(fill="x", pady=5)
        
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(header, text=name, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(btn_frame, text="Delete", width=60, fg_color="#8b0000", hover_color="#5a0000",
                  command=lambda n=name: self.delete_group(n)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Rename", width=60, fg_color="#4a4a4a", hover_color="#3a3a3a",
                  command=lambda n=name: self.rename_group(n)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Edit", width=60, command=lambda n=name: self.on_edit_click(n)).pack(side="left", padx=5)
        
        stats = f"Websites: {len(data.get('websites', []))} | Apps: {len(data.get('apps', []))} | Files: {len(data.get('files', []))} | Content Filter: {'On' if data.get('adblocker', {}).get('enabled') else 'Off'}"
        ctk.CTkLabel(card, text=stats, text_color="gray").pack(anchor="w", padx=10, pady=(0, 5))

    def add_new_group(self):
        name = self._prompt_text_dialog("New Group", "Enter new group name:")
        if name and name not in self.config_data["groups"]:
            import copy
            self.config_data["groups"][name] = copy.deepcopy(DEFAULT_GROUP_CONFIG)
            self.trigger_save()
            self.show_dashboard()

    def rename_group(self, old_name):
        new_name = self._prompt_text_dialog("Rename Group", f"Enter new name for '{old_name}':", initial=old_name)
        if new_name and new_name != old_name and new_name not in self.config_data["groups"]:
            self.config_data["groups"][new_name] = self.config_data["groups"].pop(old_name)
            self.trigger_save()
            self.show_dashboard()

    def delete_group(self, group_name):
        if len(self.config_data["groups"]) <= 1:
            self._info_dialog("Cannot Delete", "At least one group must remain.")
            return
        if not self._confirm_dialog("Delete Group", f"Delete '{group_name}'? This cannot be undone."):
            return
        if group_name in self.config_data["groups"]:
            del self.config_data["groups"][group_name]
            self.trigger_save()
            self.show_dashboard()

    def _run_schtasks(self, args):
        kwargs = {"capture_output": True, "text": True}
        if os.name == 'nt':
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        return subprocess.run(args, **kwargs)

    def _startup_task_exists(self):
        if os.name != 'nt':
            return False
        result = self._run_schtasks(["schtasks", "/query", "/tn", "SPB_Daemon"])
        return result.returncode == 0

    def _startup_task_command(self):
        if getattr(sys, 'frozen', False):
            daemon_path = os.path.join(os.path.dirname(sys.executable), "daemon.exe" if os.name == 'nt' else "daemon")
            return f'"{daemon_path}"'
        daemon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon.py")
        return f'"{sys.executable}" "{daemon_path}"'

    def _on_startup_toggle(self):
        if os.name != 'nt':
            return
        enabled = self.startup_var.get()
        if enabled:
            cmd = self._startup_task_command()
            result = self._run_schtasks(["schtasks", "/create", "/tn", "SPB_Daemon", "/tr", cmd,
                                         "/sc", "onlogon", "/rl", "highest", "/f"])
            if result.returncode == 0:
                if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
                    self.status_lbl.configure(text="Startup enabled", text_color="green")
            else:
                if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
                    self.status_lbl.configure(text="Failed to enable startup", text_color="red")
        else:
            result = self._run_schtasks(["schtasks", "/delete", "/tn", "SPB_Daemon", "/f"])
            if result.returncode == 0:
                if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
                    self.status_lbl.configure(text="Startup disabled", text_color="gray")
            else:
                if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
                    self.status_lbl.configure(text="Failed to disable startup", text_color="red")

        self.startup_var.set(self._startup_task_exists())

    def on_edit_click(self, group_name):
        self.group_name = group_name
        sec_cfg = self.config_data["groups"][group_name].get("security", {})
        if sec_cfg.get("enabled", False):
            self.show_challenge_screen(lambda: self.show_group_editor(group_name))
        else:
            self.show_group_editor(group_name)

    def show_group_editor(self, group_name):
        self.group_name = group_name
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        
        top_bar = ctk.CTkFrame(self.current_screen, fg_color="transparent", height=45)
        top_bar.pack(fill="x", padx=20, pady=10)
        top_bar.pack_propagate(False)
        ctk.CTkButton(top_bar, text="Back to Dashboard", command=self.show_dashboard, fg_color="transparent", width=120, height=32).pack(side="left", anchor="center")
        ctk.CTkLabel(top_bar, text=f"Editing: {group_name}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=20, anchor="center")
        
        self.tabview = ctk.CTkTabview(self.current_screen)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(5, 0))
        
        self.tab_websites = self.tabview.add("Websites")
        self.tab_apps = self.tabview.add("Apps")
        self.tab_files = self.tabview.add("Files")
        self.tab_folders = self.tabview.add("Folders")
        self.tab_content = self.tabview.add("Content Filter")
        self.tab_schedule = self.tabview.add("Schedule")
        
        self.status_frame = ctk.CTkFrame(self.current_screen, height=60, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20, pady=10)
        self.status_frame.pack_propagate(False)
        
        self.status_lbl = ctk.CTkLabel(self.status_frame, text="Ready", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_lbl.pack(side="left", anchor="center")
        
        self.timer_lbl = ctk.CTkLabel(self.status_frame, text="", text_color="green", font=ctk.CTkFont(size=12))
        self.timer_lbl.pack(side="left", padx=10, anchor="center")
        
        # Security controls: right-aligned, vertically centered within the bar
        sec_wrapper = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        sec_wrapper.pack(side="right", anchor="center", padx=(0, 10))
        
        sec = self.config_data["groups"][self.group_name].get("security", {})
        
        controls_frame = ctk.CTkFrame(sec_wrapper, fg_color="transparent")
        controls_frame.pack(anchor="e")
        
        ctk.CTkLabel(controls_frame, text="Challenge Length:").pack(side="left", padx=(0, 5))
        
        self.length_var = ctk.StringVar(value=str(sec.get("challenge_length", 32)))
        length_combo = ctk.CTkComboBox(controls_frame, values=["32", "64", "128", "256"], 
                                      variable=self.length_var, command=self.save_security, width=75)
        length_combo.pack(side="left", padx=(0, 15))
        
        self.sec_enabled = ctk.CTkSwitch(controls_frame, text="Enable Security Challenge", command=self.save_security)
        if sec.get("enabled", False):
            self.sec_enabled.select()
        self.sec_enabled.pack(side="left")
        
        ctk.CTkLabel(sec_wrapper, text="(Longer lengths are more secure but harder to type.)",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="e", pady=(2, 0))

        
        def validate_website(val):
            if "http" in val: return False, "Do not include http:// or https://"
            return True, ""
            
        def validate_app(val):
            if not val.lower().endswith(".exe"): return False, "App must end with .exe"
            return True, ""
            
        def check_proxy_installed():
            # In the future, this could check for mitmproxy or a similar local proxy service.
            return False
            
        proxy_msg = "Blocking specific subdirectories requires an Advanced Web Proxy (Installed ✅)" if check_proxy_installed() else "Note: Blocking specific subdirectories requires an Advanced Web Proxy (Not Installed ❌)."
            
        self.tab_websites.app = self
        self.tab_websites.group_name = group_name
        self.list_web = InputListFrame(self.tab_websites, "websites", "Enter URL (e.g. facebook.com)", 
                                       validation_fn=validate_website,
                                       info_tooltip=proxy_msg)
        self.list_web.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_apps.app = self
        self.tab_apps.group_name = group_name
        self.list_apps = InputListFrame(self.tab_apps, "apps", "Enter App Name (e.g. notepad.exe)", validation_fn=validate_app, browse_mode="app")
        self.list_apps.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_files.app = self
        self.tab_files.group_name = group_name
        self.list_files = InputListFrame(self.tab_files, "files", "Enter absolute file path (e.g. C:\\Docs\\secret.txt)", browse_mode="file")
        self.list_files.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tab_folders.app = self
        self.tab_folders.group_name = group_name
        self.list_folders = InputListFrame(self.tab_folders, "folders", "Enter absolute folder path (e.g. C:\\Games)", browse_mode="folder")
        self.list_folders.pack(fill="both", expand=True, padx=20, pady=10)

        
        self.content_ui = ContentFilterTab(self.tab_content, self, group_name)
        self.content_ui.pack(fill="both", expand=True)

        self.build_schedule_ui()

    def _is_valid_time(self, value):
        try:
            datetime.datetime.strptime(value, "%H:%M")
            return True
        except ValueError:
            return False
        
    def build_schedule_ui(self):
        schedule = self.config_data["groups"][self.group_name].get("schedule", {})

        # Match Content Filter: scrollable container with same style
        container = ctk.CTkScrollableFrame(self.tab_schedule, fg_color="#2b2b2b", corner_radius=10)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        def toggle_schedule():
            if self.sch_enabled.get():
                self.sch_persist.deselect()
            self.save_schedule()

        def toggle_persist():
            if self.sch_persist.get():
                self.sch_enabled.deselect()
            self.save_schedule()

        # Switches — vertical stack matching Content Filter switch layout
        self.sch_enabled = ctk.CTkSwitch(container, text="Enable Schedule",
                                          command=toggle_schedule,
                                          font=ctk.CTkFont(weight="bold"))
        if schedule.get("enabled", False):
            self.sch_enabled.select()
        self.sch_enabled.pack(pady=10, anchor="w", padx=20)

        self.sch_persist = ctk.CTkSwitch(container, text="Enforce All Day",
                                          command=toggle_persist)
        if schedule.get("persist_all_day", False):
            self.sch_persist.select()
        self.sch_persist.pack(pady=5, anchor="w", padx=20)

        # Time window section header
        ctk.CTkLabel(container, text="Time Window:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(15, 0))

        start_frame = ctk.CTkFrame(container, fg_color="transparent")
        start_frame.pack(pady=5, anchor="w", padx=30)
        ctk.CTkLabel(start_frame, text="Start Time (HH:MM):", width=160, anchor="w").pack(side="left")
        self.start_entry = ctk.CTkEntry(start_frame, width=100)
        self.start_entry.insert(0, schedule.get("start_time", "09:00"))
        self.start_entry.pack(side="left")
        self.start_entry.bind("<KeyRelease>", lambda e: self.save_schedule())

        end_frame = ctk.CTkFrame(container, fg_color="transparent")
        end_frame.pack(pady=5, anchor="w", padx=30)
        ctk.CTkLabel(end_frame, text="End Time (HH:MM):", width=160, anchor="w").pack(side="left")
        self.end_entry = ctk.CTkEntry(end_frame, width=100)
        self.end_entry.insert(0, schedule.get("end_time", "17:00"))
        self.end_entry.pack(side="left")
        self.end_entry.bind("<KeyRelease>", lambda e: self.save_schedule())

        # Active days — matching Content Filter checkbox indentation (padx=30)
        ctk.CTkLabel(container, text="Active Days:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(15, 0))

        self.days_vars = {}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            var = ctk.BooleanVar(value=(day in schedule.get("days", [])))
            cb = ctk.CTkCheckBox(container, text=day, variable=var, command=self.save_schedule)
            cb.pack(anchor="w", pady=2, padx=30)
            self.days_vars[day] = var

    def save_schedule(self, *args):
        start_val = self.start_entry.get().strip()
        end_val = self.end_entry.get().strip()
        if not self._is_valid_time(start_val) or not self._is_valid_time(end_val):
            if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
                self.status_lbl.configure(text="Invalid time format. Use HH:MM", text_color="red")
            return

        self.config_data["groups"][self.group_name]["schedule"] = {
            "enabled": self.sch_enabled.get() == 1,
            "persist_all_day": self.sch_persist.get() == 1,
            "start_time": start_val,
            "end_time": end_val,
            "days": [day for day, var in self.days_vars.items() if var.get()]
        }
        self.trigger_save()

    # -----------------------------------------------------------------------
    # Settings Screen
    # -----------------------------------------------------------------------

    def show_settings(self):
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)

        top_bar = ctk.CTkFrame(self.current_screen, fg_color="transparent", height=45)
        top_bar.pack(fill="x", padx=20, pady=10)
        top_bar.pack_propagate(False)
        ctk.CTkButton(top_bar, text="Back to Dashboard", command=self.show_dashboard,
                      fg_color="transparent", width=120, height=32).pack(side="left", anchor="center")
        ctk.CTkLabel(top_bar, text="Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=20, anchor="center")

        tabview = ctk.CTkTabview(self.current_screen)
        tabview.pack(fill="both", expand=True, padx=20, pady=(5, 0))

        tab_perf    = tabview.add("Performance")
        tab_cloud   = tabview.add("Cloud Allowlist")
        tab_notif   = tabview.add("Notifications")
        tab_about   = tabview.add("About")

        self._build_performance_tab(tab_perf)
        self._build_cloud_tab(tab_cloud)
        self._build_notifications_tab(tab_notif)
        self._build_about_tab(tab_about)

        # Status bar
        self.status_frame = ctk.CTkFrame(self.current_screen, height=30, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20, pady=10)
        self.status_lbl = ctk.CTkLabel(self.status_frame, text="Ready", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_lbl.pack(side="left")
        self.timer_lbl = ctk.CTkLabel(self.status_frame, text="", text_color="green", font=ctk.CTkFont(size=12))
        self.timer_lbl.pack(side="left", padx=10)

    def _settings_container(self, parent):
        """Shared scrollable container matching Content Filter / Schedule style."""
        c = ctk.CTkScrollableFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        c.pack(fill="both", expand=True, padx=10, pady=10)
        return c

    # --- Performance tab ---
    def _build_performance_tab(self, parent):
        c = self._settings_container(parent)
        s = self.config_data.get("settings", {})

        ctk.CTkLabel(c, text="Daemon Poll Rate", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 0))

        desc_map = {
            "Passive":  "Checks every 5 seconds. Lightest on CPU — ideal for laptops on battery.",
            "Balanced": "Checks every 2 seconds. Recommended for most users.",
            "Strict":   "Checks every second. Near-instant enforcement — slightly higher CPU usage.",
        }
        self._perf_desc = ctk.CTkLabel(c, text=desc_map.get(s.get("performance_mode", "Balanced"), ""),
                                       text_color="gray", wraplength=480, justify="left")

        def on_perf(val):
            self.config_data["settings"]["performance_mode"] = val
            self._perf_desc.configure(text=desc_map.get(val, ""))
            self.trigger_save()

        seg = ctk.CTkSegmentedButton(c, values=["Passive", "Balanced", "Strict"], command=on_perf)
        seg.set(s.get("performance_mode", "Balanced"))
        seg.pack(padx=20, pady=(8, 4))
        self._perf_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Startup on boot
        ctk.CTkLabel(c, text="System", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 0))
        self.startup_var = ctk.BooleanVar(value=self._startup_task_exists())
        startup_sw = ctk.CTkSwitch(c, text="Start daemon on PC boot (Windows only)",
                                   variable=self.startup_var, command=self._on_startup_toggle)
        if os.name != 'nt':
            startup_sw.configure(state="disabled")
        startup_sw.pack(anchor="w", padx=20, pady=8)

    # --- Cloud Allowlist tab ---
    def _build_cloud_tab(self, parent):
        c = self._settings_container(parent)
        s = self.config_data.get("settings", {})

        self._cloud_enabled = ctk.BooleanVar(value=s.get("cloud_allowlist_enabled", True))
        ctk.CTkSwitch(c, text="Protect Cloud Sync Processes",
                      variable=self._cloud_enabled,
                      font=ctk.CTkFont(weight="bold"),
                      command=self._save_settings).pack(anchor="w", padx=20, pady=(15, 4))
        ctk.CTkLabel(c, text="Listed processes and paths are never terminated by the App Blocker,\neven if they match a blocked entry.",
                     text_color="gray", justify="left").pack(anchor="w", padx=20, pady=(0, 10))

        # --- Process names ---
        ctk.CTkLabel(c, text="Protected Process Names (.exe):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(8, 0))
        self._cloud_exe_list = self._inline_list(c, s.get("cloud_allowlist", []), self._save_settings,
                                                  placeholder="e.g. OneDrive.exe")

        # --- Path keywords ---
        ctk.CTkLabel(c, text="Protected Path Keywords:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(12, 0))
        self._cloud_kw_list = self._inline_list(c, s.get("cloud_path_keywords", []), self._save_settings,
                                                 placeholder="e.g. onedrive")

    def _inline_list(self, parent, items, on_change, placeholder=""):
        """Simple add/remove list widget for use inside settings tabs."""
        state = {"items": list(items)}
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=4)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, height=32, corner_radius=8)
        entry.pack(side="left", fill="x", expand=True)

        list_frame = ctk.CTkFrame(frame, fg_color="transparent")
        list_frame.pack(fill="x", pady=(4, 0))
        item_widgets = {}

        def render_item(val):
            r = ctk.CTkFrame(list_frame)
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=val, anchor="w").pack(side="left", fill="x", expand=True, padx=5)
            ctk.CTkButton(r, text="Remove", width=60, height=26,
                          fg_color="#8b0000", hover_color="#5a0000",
                          command=lambda v=val: remove_item(v)).pack(side="right", padx=4)
            item_widgets[val] = r

        def remove_item(val):
            if val in state["items"]:
                state["items"].remove(val)
                item_widgets.pop(val).destroy()
                on_change()

        def add_item():
            val = entry.get().strip()
            if val and val not in state["items"]:
                state["items"].append(val)
                render_item(val)
                entry.delete(0, "end")
                on_change()

        ctk.CTkButton(row, text="+", width=36, height=32, corner_radius=8,
                      command=add_item).pack(side="left", padx=(6, 0))
        entry.bind("<Return>", lambda e: add_item())

        for v in state["items"]:
            render_item(v)

        return state

    def _save_settings(self, *args):
        s = self.config_data.setdefault("settings", {})
        if hasattr(self, '_cloud_enabled'):
            s["cloud_allowlist_enabled"] = self._cloud_enabled.get()
        if hasattr(self, '_cloud_exe_list'):
            s["cloud_allowlist"] = self._cloud_exe_list["items"]
        if hasattr(self, '_cloud_kw_list'):
            s["cloud_path_keywords"] = self._cloud_kw_list["items"]
        if hasattr(self, '_notif_vars'):
            s["notifications"] = {k: var.get() for k, var in self._notif_vars.items()}
        self.trigger_save()

    # --- Notifications tab ---
    def _build_notifications_tab(self, parent):
        c = self._settings_container(parent)
        s = self.config_data.get("settings", {})
        notif = s.get("notifications", {})

        self._notif_vars = {}

        def section(title, desc, options):
            ctk.CTkLabel(c, text=title, font=ctk.CTkFont(weight="bold")).pack(
                anchor="w", padx=20, pady=(15, 2))
            if desc:
                ctk.CTkLabel(c, text=desc, text_color="gray", justify="left").pack(
                    anchor="w", padx=20, pady=(0, 6))
            for key, label, default in options:
                var = ctk.BooleanVar(value=notif.get(key, default))
                ctk.CTkSwitch(c, text=label, variable=var, command=self._save_settings).pack(
                    anchor="w", padx=30, pady=4)
                self._notif_vars[key] = var

        section(
            "Block Events",
            "Fired when the daemon actively enforces a blocking rule.",
            [
                ("on_block",           "Notify when a block rule is applied",          True),
                ("on_block_attempt",   "Notify when a blocked app is detected and killed", True),
                ("on_exception_bypass","Notify when an exception allowlist bypasses a block", False),
            ]
        )

        section(
            "Schedule Events",
            "Fired when scheduled rules change state.",
            [
                ("on_schedule",              "Notify when a schedule activates or deactivates", True),
                ("on_schedule_window_miss",  "Notify if a schedule's time window is invalid",   True),
            ]
        )

        section(
            "Daemon Events",
            "Low-level daemon lifecycle and config events.",
            [
                ("on_daemon_start",  "Notify on daemon startup",                     True),
                ("on_config_reload", "Notify whenever the config is reloaded from disk", False),
                ("on_hosts_write",   "Notify whenever the hosts file is written or cleared", False),
            ]
        )

        section(
            "Security Events",
            "Fired when a security challenge is attempted.",
            [
                ("on_challenge_fail", "Notify on failed security challenge attempt", True),
                ("on_challenge_pass", "Notify on successful challenge completion",   False),
            ]
        )

    # --- About tab ---
    def _build_about_tab(self, parent):
        c = self._settings_container(parent)

        ctk.CTkLabel(c, text="Simple Productivity Blocker",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(c, text=f"Version {VERSION}", text_color="gray").pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(c, fg_color="transparent")
        btn_frame.pack(pady=4)

        ctk.CTkButton(btn_frame, text="View on GitHub", width=160,
                      command=lambda: webbrowser.open("https://github.com/nvusdev/simple-productivity-blocker")
                      ).pack(side="left", padx=6)

        ctk.CTkButton(btn_frame, text="Open Config Folder", width=160,
                      command=self._open_config_folder).pack(side="left", padx=6)

        ctk.CTkButton(c, text="Reset All Settings to Defaults",
                      fg_color="#8b0000", hover_color="#5a0000", width=200,
                      command=self._reset_settings).pack(pady=(20, 4))

    def _open_config_folder(self):
        path = get_config_dir()
        if os.name == 'nt':
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])

    def _reset_settings(self):
        from core.config_manager import DEFAULT_SETTINGS
        import copy
        if self._confirm_dialog("Reset Settings", "Reset all Settings to defaults? This cannot be undone."):
            self.config_data["settings"] = copy.deepcopy(DEFAULT_SETTINGS)
            self.trigger_save()
            self.show_settings()

if __name__ == "__main__":
    app = ProductivityApp()
    app.mainloop()
