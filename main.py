import customtkinter as ctk
import string
import random
import os
import subprocess
from core.config_manager import load_config, save_config, DEFAULT_GROUP_CONFIG
import ctypes
import sys
from daemon import ADBLOCK_LISTS

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
    def __init__(self, master, config_key, placeholder, validation_fn=None, info_tooltip=None, browse_mode=None, **kwargs):
        super().__init__(master, fg_color="#2b2b2b", corner_radius=10, **kwargs)
        
        self.config_key = config_key
        self.validation_fn = validation_fn
        self.browse_mode = browse_mode
        self.app = master.app
        self.group_name = master.group_name
        
        group_data = self.app.config_data["groups"][self.group_name]
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
        
        if info_tooltip:
            self.info_desc = ctk.CTkLabel(self, text=info_tooltip, text_color="gray", font=ctk.CTkFont(size=11))
            self.info_desc.pack(fill="x", padx=15, pady=(2, 0))
            
        self.feedback_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.feedback_lbl.pack(fill="x", padx=10)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.item_frames = {}
        self.render_list()

    def browse_file(self):
        filetypes = []
        if self.browse_mode == "app":
            filetypes = [("Executables", "*.exe")] if os.name == 'nt' else [("All Files", "*.*")]
        elif self.browse_mode == "file":
            filetypes = [("All Files", "*.*")]
            
        filename = ctk.filedialog.askopenfilename(title="Select File", filetypes=filetypes)
        if filename:
            if self.browse_mode == "app" and os.name == 'nt':
                filename = os.path.basename(filename)
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
        
        self.app.config_data["groups"][self.group_name][self.config_key] = self.items
        self.app.trigger_save()
        self.add_item_ui(val)

    def remove_item(self, val):
        if val in self.items:
            self.items.remove(val)
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
        self.exceptions_list = InputListFrame(container, "exceptions", "Enter domain to exclude (e.g. google.com)", validation_fn=validate_domain)
        self.exceptions_list.pack(fill="both", expand=True, padx=20, pady=5)

        lbl_custom = ctk.CTkLabel(container, text="Custom Lists (URLs or local .txt paths):", font=ctk.CTkFont(weight="bold"))
        lbl_custom.pack(anchor="w", padx=20, pady=(15, 0))
        
        self.custom_lists = InputListFrame(container, "custom_lists", "Enter URL or absolute Path", browse_mode="file")
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
        self.app.config_data["groups"][self.group_name]["adblocker"] = ad_cfg
        self.app.trigger_save()


class ProductivityApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Simple Productivity Blocker")
        
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        w = int(ws * 0.65)
        h = int(hs * 0.75)
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.config_data = load_config()
        self.save_job = None
        self.current_screen = None
        self.group_name = None
        
        self.check_daemon()
        
        if self.config_data.get("security", {}).get("enabled", False):
            self.show_challenge_screen()
        else:
            self.show_dashboard()

    def check_daemon(self):
        try:
            if getattr(sys, 'frozen', False):
                daemon_name = "daemon.exe" if os.name == 'nt' else "daemon"
                cmd = f'tasklist /fi "imagename eq {daemon_name}" /v' if os.name == 'nt' else f'pgrep {daemon_name}'
            else:
                cmd = 'tasklist /fi "imagename eq python.exe" /v' if os.name == 'nt' else 'pgrep -f "python.*daemon.py"'
            
            output = subprocess.check_output(cmd, shell=True).decode()
            if "daemon" not in output.lower() and not getattr(sys, 'frozen', False) or (getattr(sys, 'frozen', False) and not output.strip()):
                self.launch_daemon()
        except:
            self.launch_daemon()

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
        self.hide_saving()
        
    def show_saving(self):
        if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
            self.status_lbl.configure(text="Saving... ⏳", text_color="#1f538d")
        
    def hide_saving(self):
        if hasattr(self, 'status_lbl') and self.status_lbl.winfo_exists():
            self.status_lbl.configure(text="All changes saved ✅", text_color="green")

    def clear_screen(self):
        if self.current_screen:
            self.current_screen.destroy()

    def show_challenge_screen(self):
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        
        length = self.config_data.get("security", {}).get("challenge_length", 32)
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:',.<>?/"
        self.challenge_string = ''.join(random.choice(chars) for _ in range(length))
        
        challenge_frame = ctk.CTkFrame(self.current_screen)
        challenge_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        label = ctk.CTkLabel(challenge_frame, text="Security Challenge", font=ctk.CTkFont(size=24, weight="bold"))
        label.pack(pady=20)
        
        instructions = ctk.CTkLabel(challenge_frame, text="Please type the following text exactly to access settings:")
        instructions.pack()
        
        mono_font = ctk.CTkFont(family="Consolas", size=16)
        
        self.text_display = ctk.CTkLabel(challenge_frame, text=self.challenge_string, font=mono_font, wraplength=800)
        self.text_display.pack(fill="x", padx=20, pady=20)
        
        self.input_entry = ctk.CTkTextbox(challenge_frame, height=80, wrap="word", font=mono_font)
        self.input_entry.pack(fill="x", padx=20, pady=10)
        
        def on_enter(event):
            self.verify_challenge()
            return "break"
            
        self.input_entry.bind("<Return>", on_enter)
        
        btn = ctk.CTkButton(challenge_frame, text="Verify", command=self.verify_challenge)
        btn.pack(pady=10)
        
    def verify_challenge(self):
        user_input = self.input_entry.get("1.0", "end-1c").strip()
        if user_input == self.challenge_string:
            self.show_dashboard()
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
        
        self.groups_scroll = ctk.CTkScrollableFrame(self.current_screen)
        self.groups_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        for name, data in self.config_data["groups"].items():
            self.create_group_card(name, data)
            
        add_btn = ctk.CTkButton(self.current_screen, text="+ Add New Group", command=self.add_new_group)
        add_btn.pack(pady=10)
        
        # --- Bottom Bar ---
        bottom_bar = ctk.CTkFrame(self.current_screen, fg_color="transparent")
        bottom_bar.pack(fill="x", side="bottom", padx=20, pady=10)
        
        self.status_lbl = ctk.CTkLabel(bottom_bar, text="Ready", text_color="gray")
        self.status_lbl.pack(side="left")
        
        sec_frame = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        sec_frame.pack(side="right")
        
        info_lbl = ctk.CTkLabel(sec_frame, text="(Higher lengths are more secure but harder to type)", text_color="gray", font=ctk.CTkFont(size=11))
        info_lbl.pack(side="bottom", anchor="e", pady=(0, 5))
        
        controls_frame = ctk.CTkFrame(sec_frame, fg_color="transparent")
        controls_frame.pack(side="top")

        ctk.CTkLabel(controls_frame, text="Challenge Length:").pack(side="left", padx=(0, 5))
        
        sec = self.config_data.get("security", {})
        self.length_var = ctk.StringVar(value=str(sec.get("challenge_length", 32)))
        length_combo = ctk.CTkComboBox(controls_frame, values=["32", "64", "128", "256"], variable=self.length_var, command=self.save_security, width=70)
        length_combo.pack(side="left", padx=(0, 15))
        
        self.sec_enabled = ctk.CTkSwitch(controls_frame, text="Enable Security Challenge", command=self.save_security)
        if sec.get("enabled", False):
            self.sec_enabled.select()
        self.sec_enabled.pack(side="left")

    def save_security(self, *args):
        self.config_data["security"] = {
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
        
        ctk.CTkButton(btn_frame, text="Rename", width=60, fg_color="#4a4a4a", hover_color="#3a3a3a", 
                      command=lambda n=name: self.rename_group(n)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Edit", width=60, command=lambda n=name: self.show_group_editor(n)).pack(side="left")
        
        stats = f"Websites: {len(data.get('websites', []))} | Apps: {len(data.get('apps', []))} | Files: {len(data.get('files', []))} | Content Filter: {'On' if data.get('adblocker', {}).get('enabled') else 'Off'}"
        ctk.CTkLabel(card, text=stats, text_color="gray").pack(anchor="w", padx=10, pady=(0, 5))

    def add_new_group(self):
        dialog = ctk.CTkInputDialog(text="Enter new group name:", title="New Group")
        name = dialog.get_input()
        if name and name not in self.config_data["groups"]:
            self.config_data["groups"][name] = DEFAULT_GROUP_CONFIG.copy()
            self.trigger_save()
            self.show_dashboard()

    def rename_group(self, old_name):
        dialog = ctk.CTkInputDialog(text=f"Enter new name for '{old_name}':", title="Rename Group")
        new_name = dialog.get_input()
        if new_name and new_name != old_name and new_name not in self.config_data["groups"]:
            self.config_data["groups"][new_name] = self.config_data["groups"].pop(old_name)
            self.trigger_save()
            self.show_dashboard()

    def show_group_editor(self, group_name):
        self.group_name = group_name
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        
        top_bar = ctk.CTkFrame(self.current_screen, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(top_bar, text="Back to Dashboard", command=self.show_dashboard, fg_color="transparent", width=120).pack(side="left")
        ctk.CTkLabel(top_bar, text=f"Editing: {group_name}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=20)
        
        self.tabview = ctk.CTkTabview(self.current_screen)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(5, 0))
        
        self.tab_websites = self.tabview.add("Websites")
        self.tab_apps = self.tabview.add("Apps")
        self.tab_files = self.tabview.add("Files")
        self.tab_content = self.tabview.add("Content Filter")
        self.tab_schedule = self.tabview.add("Schedule")
        
        self.status_frame = ctk.CTkFrame(self.current_screen, height=30, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=10, pady=5)
        self.status_lbl = ctk.CTkLabel(self.status_frame, text="Ready", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_lbl.pack(side="right", padx=10)
        
        def validate_website(val):
            if "http" in val: return False, "Do not include http:// or https://"
            return True, ""
            
        def validate_app(val):
            if not val.endswith(".exe"): return False, "App must end with .exe"
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
        self.list_web.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_apps.app = self
        self.tab_apps.group_name = group_name
        self.list_apps = InputListFrame(self.tab_apps, "apps", "Enter App Name (e.g. notepad.exe)", validation_fn=validate_app, browse_mode="app")
        self.list_apps.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_files.app = self
        self.tab_files.group_name = group_name
        self.list_files = InputListFrame(self.tab_files, "files", "Enter absolute file path (e.g. C:\\Docs\\secret.txt)", browse_mode="file")
        self.list_files.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.content_ui = ContentFilterTab(self.tab_content, self, group_name)
        self.content_ui.pack(fill="both", expand=True)

        self.build_schedule_ui()
        
    def build_schedule_ui(self):
        schedule = self.config_data["groups"][self.group_name].get("schedule", {})
        
        container = ctk.CTkFrame(self.tab_schedule, fg_color="#2b2b2b", corner_radius=10)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        top_frame = ctk.CTkFrame(container, fg_color="transparent")
        top_frame.pack(fill="x", pady=10)
        
        def toggle_schedule():
            if self.sch_enabled.get():
                self.sch_persist.deselect()
            self.save_schedule()

        def toggle_persist():
            if self.sch_persist.get():
                self.sch_enabled.deselect()
            self.save_schedule()

        self.sch_enabled = ctk.CTkSwitch(top_frame, text="Enable Schedule", command=toggle_schedule, font=ctk.CTkFont(weight="bold"))
        if schedule.get("enabled", False):
            self.sch_enabled.select()
        self.sch_enabled.pack(side="left", padx=20)
        
        self.sch_persist = ctk.CTkSwitch(top_frame, text="Enforce All Day", command=toggle_persist)
        if schedule.get("persist_all_day", False):
            self.sch_persist.select()
        self.sch_persist.pack(side="left", padx=20)
        
        start_frame = ctk.CTkFrame(container, fg_color="transparent")
        start_frame.pack(pady=5, anchor="w", padx=20)
        ctk.CTkLabel(start_frame, text="Start Time (HH:MM): ", width=130, anchor="w").pack(side="left")
        self.start_entry = ctk.CTkEntry(start_frame, width=100)
        self.start_entry.insert(0, schedule.get("start_time", "09:00"))
        self.start_entry.pack(side="left")
        self.start_entry.bind("<KeyRelease>", lambda e: self.save_schedule())
        
        end_frame = ctk.CTkFrame(container, fg_color="transparent")
        end_frame.pack(pady=5, anchor="w", padx=20)
        ctk.CTkLabel(end_frame, text="End Time (HH:MM): ", width=130, anchor="w").pack(side="left")
        self.end_entry = ctk.CTkEntry(end_frame, width=100)
        self.end_entry.insert(0, schedule.get("end_time", "17:00"))
        self.end_entry.pack(side="left")
        self.end_entry.bind("<KeyRelease>", lambda e: self.save_schedule())
        
        self.days_vars = {}
        days_frame = ctk.CTkFrame(container, fg_color="transparent")
        days_frame.pack(pady=10, anchor="w", padx=20)
        ctk.CTkLabel(days_frame, text="Active Days:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            var = ctk.BooleanVar(value=(day in schedule.get("days", [])))
            cb = ctk.CTkCheckBox(days_frame, text=day, variable=var, command=self.save_schedule)
            cb.pack(anchor="w", pady=2, padx=10)
            self.days_vars[day] = var
            
    def save_schedule(self, *args):
        self.config_data["groups"][self.group_name]["schedule"] = {
            "enabled": self.sch_enabled.get() == 1,
            "persist_all_day": self.sch_persist.get() == 1,
            "start_time": self.start_entry.get(),
            "end_time": self.end_entry.get(),
            "days": [day for day, var in self.days_vars.items() if var.get()]
        }
        self.trigger_save()

if __name__ == "__main__":
    app = ProductivityApp()
    app.mainloop()
