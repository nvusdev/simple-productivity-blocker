import customtkinter as ctk
import string
import random
import datetime
import re
import os
import subprocess
import psutil
import webbrowser
import ctypes
import sys
import copy
from core.config_manager import load_config, save_config, DEFAULT_GROUP_CONFIG, get_config_dir, export_config, import_config
from core.platform_handler import get_platform_handler, detect_security_appliances
handler = get_platform_handler()

# Provide legacy helper that returns a simple conflict name for UI compatibility
try:
    def detect_conflicting_services():
        res = detect_security_appliances()
        if res and isinstance(res, dict):
            items = res.get("items") or []
            if items:
                return items[0].get("name")
        return None
except Exception:
    def detect_conflicting_services():
        return None

VERSION = "1.4.8"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

def is_admin():
    return handler.is_admin()

class InputListFrame(ctk.CTkFrame):
    def __init__(self, master, app, config_key, placeholder, validation_fn=None, info_tooltip=None, browse_mode=None, config_section=None, **kwargs):
        super().__init__(master, fg_color="#2b2b2b", corner_radius=10, **kwargs)
        self.app = app
        self.config_key = config_key
        self.validation_fn = validation_fn
        self.browse_mode = browse_mode
        self.config_section = config_section
        self.group_name = getattr(master, "group_name", None)
        if not self.group_name and hasattr(master, "master"):
             self.group_name = getattr(master.master, "group_name", None)
        
        group_data = self.app.config_data.get("groups", {}).get(self.group_name, {})
        if self.config_section:
            section = group_data.get(self.config_section, {})
            self.items = section.get(config_key, [])
        else:
            self.items = group_data.get(config_key, [])
        
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=20, pady=(15, 0)) # Reduced margins
        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text=placeholder, height=38, corner_radius=8, border_width=1)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add_item())
        
        if self.browse_mode:
            self.browse_btn = ctk.CTkButton(self.input_frame, text="Browse", width=80, height=38, corner_radius=8, command=self.browse_file)
            self.browse_btn.pack(side="left", padx=(10, 0))
        self.add_btn = ctk.CTkButton(self.input_frame, text="+", width=45, height=38, corner_radius=8, font=ctk.CTkFont(size=18, weight="bold"), command=self.add_item)
        self.add_btn.pack(side="left", padx=(10, 0))
        
        if info_tooltip:
            self.info_desc = ctk.CTkLabel(self, text=info_tooltip, text_color="gray", font=ctk.CTkFont(size=11), justify="left", wraplength=550)
            self.info_desc.pack(fill="x", padx=20, pady=(8, 2))
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(5, 5))
        
        self.feedback_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.feedback_lbl.pack(side="bottom", fill="x", padx=20, pady=(2, 10))
        
        self.item_frames = {}
        self.render_list()

    def browse_file(self):
        if self.browse_mode == "folder":
            filename = ctk.filedialog.askdirectory(title="Select Folder")
        else:
            filetypes = [("Executables", "*.exe")] if self.browse_mode == "app" else [("All Files", "*.*")]
            filename = ctk.filedialog.askopenfilename(title="Select File", filetypes=filetypes)
        if filename:
            self.entry.delete(0, "end")
            self.entry.insert(0, filename)
            self.add_item() # Auto-Submit UX

    def render_list(self):
        for frame in self.item_frames.values():
            frame.destroy()
        self.item_frames = {}
        for item in self.items:
            frame = ctk.CTkFrame(self.scroll_frame, fg_color="#333333", corner_radius=8)
            frame.pack(fill="x", padx=5, pady=4)
            lbl = ctk.CTkLabel(frame, text=item, font=ctk.CTkFont(size=14), anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=15, pady=8)
            btn = ctk.CTkButton(frame, text="Remove", width=70, height=32, fg_color="#8b0000", hover_color="#5a0000", command=lambda i=item: self.remove_item(i))
            btn.pack(side="right", padx=10)
            self.item_frames[item] = frame

    def add_item(self):
        val = self.entry.get().strip()
        if not val: return
        if self.validation_fn:
            valid, msg = self.validation_fn(val)
            if not valid:
                self.feedback_lbl.configure(text=msg, text_color="red")
                return
        if val in self.items:
            self.feedback_lbl.configure(text="Already in list", text_color="orange")
            return
        self.items.append(val)
        self.save_to_config()
        self.render_list()
        self.entry.delete(0, "end")
        self.feedback_lbl.configure(text="Added successfully", text_color="green")

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            self.save_to_config()
            self.render_list()

    def save_to_config(self):
        group_data = self.app.config_data["groups"][self.group_name]
        if self.config_section:
            group_data.setdefault(self.config_section, {})[self.config_key] = self.items
        else:
            group_data[self.config_key] = self.items
        self.app.trigger_save()

class ContentFilterTab(ctk.CTkFrame):
    def __init__(self, master: any, app: any, group_name: str):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.group_name = group_name
        self.config_data = app.config_data
        self.ad = self.config_data["groups"][self.group_name].setdefault("adblocker", {})
        
        self.container = ctk.CTkScrollableFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.container.pack(fill="both", expand=True, padx=20, pady=15)
        
        self.enabled_var = ctk.BooleanVar(value=self.ad.get("enabled", False))
        ctk.CTkSwitch(self.container, text="Enable Content Filter", variable=self.enabled_var, command=self.save, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=25, pady=(20, 8))
        
        ctk.CTkLabel(self.container, text="Advanced filtering supports keywords (word), wildcards (*.domain.com), prefixes (word*), and suffixes (*word.com). Applies to exceptions and custom lists.", text_color="gray", font=ctk.CTkFont(size=11), justify="left", wraplength=550).pack(anchor="w", padx=25, pady=(0, 10))
        
        self.persist_var = ctk.BooleanVar(value=self.ad.get("persist_all_day", False))
        ctk.CTkSwitch(self.container, text="Enforce All Day (Bypass Schedule)", variable=self.persist_var, command=self.save).pack(anchor="w", padx=25, pady=8)
        
        ctk.CTkLabel(self.container, text="Filter Categories:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25, pady=(20, 8))
        self.cat_vars = {}
        cats = [
            ("Ads & Trackers", "ads_trackers"), 
            ("Malware & Annoyances", "malware_annoyances"), 
            ("Social Media", "social_media"), 
            ("Gaming & Game Stores", "gaming"),
            ("Entertainment & Video", "entertainment"), 
            ("Shopping & E-commerce", "shopping"), 
            ("AI & Tech News", "ai_tech"), 
            ("Music & Podcasts", "music_podcasts"), 
            ("Adult Content", "adult_content"), 
            ("Gambling", "gambling"), 
            ("Piracy & Illegal", "piracy_illegal")
        ]
        for label, key in cats:
            var = ctk.BooleanVar(value=self.ad.get(key, False))
            ctk.CTkCheckBox(self.container, text=label, variable=var, command=self.save).pack(anchor="w", padx=35, pady=4)
            self.cat_vars[key] = var
            
        ctk.CTkLabel(self.container, text="Exceptions (Allowlist):", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25, pady=(20, 0))
        self.exc_list = self.app._inline_list(self.container, self.ad.get("exceptions", []), self.save, "e.g. google.com")

        ctk.CTkLabel(self.container, text="Custom Blocklists (URL or Local Path):", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25, pady=(20, 0))
        self.custom_list = self.app._inline_list(self.container, self.ad.get("custom_lists", []), self.save, "e.g. https://example.com/blocklist.txt")

    def save(self, *args: any) -> None:
        self.ad["enabled"] = self.enabled_var.get()
        self.ad["persist_all_day"] = self.persist_var.get()
        for key, var in self.cat_vars.items(): self.ad[key] = var.get()
        self.ad["exceptions"] = self.exc_list["items"]
        self.ad["custom_lists"] = self.custom_list["items"]
        self.app.trigger_save()

class ProductivityApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Anti-Flash: Hide window
        self.attributes('-alpha', 0.0) # Absolute stealth during construction
        
        self.title(f"Simple Productivity Blocker v{VERSION}")
        
        self.update_idletasks()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        w = int(ws * 0.65)
        h = int(hs * 0.85)
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        # Robust Icon Loading
        self.after(200, self._apply_app_icon)

        self.config_data = load_config()
        self._save_timer = None
        self._debounce_timer = None # 3s Batching timer
        self._countdown_timer = None # UI update timer
        self._countdown_val = 0
        
        self.show_dashboard()
        
        # Phase 2: DNS Health Indicator Polling
        self.dns_health_lbl = None
        self._update_dns_health_ui()

        # Anti-Flash: Show window once UI is ready
        self.after(250, lambda: [self.attributes('-alpha', 1.0), self.deiconify()])
        
        # Protocol handler for graceful/forced exit persistence
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _update_dns_health_ui(self):
        """Polls the daemon health signal and updates the UI status."""
        health_file = os.path.join(get_config_dir(), "dns_health.signal")
        status = "Unknown"
        color = "gray"
        
        if os.path.exists(health_file):
            try:
                with open(health_file, "r") as f:
                    status = f.read().strip()
                if status == "Active":
                    color = "#4CAF50" # Material Green
                elif status == "Fallback":
                    color = "#FF9800" # Material Orange
            except: pass
            
        if hasattr(self, "dns_health_lbl") and self.dns_health_lbl:
            try:
                self.dns_health_lbl.configure(text=f"DNS ENGINE: {status.upper()}", text_color=color)
            except: pass
            
        self.after(5000, self._update_dns_health_ui)

    def _apply_app_icon(self):
        try:
            import tkinter as tk
            from PIL import Image
            logo_path = resource_path("newlogo.png")
            if os.path.exists(logo_path):
                # Apply as window icon
                self.iconphoto(False, tk.PhotoImage(file=logo_path))
                # For Windows taskbar/titlebar specifically
                if os.name == 'nt':
                    ico_path = resource_path("newlogo.ico")
                    if os.path.exists(ico_path):
                        self.wm_iconbitmap(ico_path)
        except: pass

    def trigger_save(self):
        """Batches changes and triggers a system-wide reload after a 3s cooldown."""
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)
        if self._countdown_timer:
            self.after_cancel(self._countdown_timer)
        
        self._countdown_val = 3.0
        self._update_cooldown_ui()
        
        # Debounce for 3 seconds of inactivity
        self._debounce_timer = self.after(3000, self._finalize_save)

    def _update_cooldown_ui(self):
        if self._countdown_val > 0:
            self.cooldown_label.configure(text=f"SYNCING IN {self._countdown_val:.1f}s...", text_color="#888888")
            self._countdown_val -= 0.1
            self._countdown_timer = self.after(100, self._update_cooldown_ui)
        else:
            self.cooldown_label.configure(text="SHIELD SYNCHRONIZED", text_color="#4CAF50")
            self._countdown_timer = self.after(2000, lambda: self.cooldown_label.configure(text=""))

    def _finalize_save(self):
        save_config(self.config_data)
        self.status_lbl.configure(text="Changes Saved & Applied", text_color="green")
        self._debounce_timer = None

    def on_exit(self):
        """Force a save if a sync is pending before closing."""
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)
            self._finalize_save()
        self.destroy()

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        top_bar = ctk.CTkFrame(self.current_screen, fg_color="transparent")
        top_bar.pack(fill="x", padx=30, pady=20) # Tightened header
        ctk.CTkLabel(top_bar, text="Group Profiles", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="⚙  Settings", command=self.show_settings, fg_color="#3a3a3a", hover_color="#4a4a4a", width=120, height=35).pack(side="right")
        
        self.groups_scroll = ctk.CTkScrollableFrame(self.current_screen, fg_color="transparent")
        self.groups_scroll.pack(fill="both", expand=True, padx=30, pady=(0, 10))
        for name, data in self.config_data["groups"].items():
            self.create_group_card(name, data)
            
        self.status_frame = ctk.CTkFrame(self.current_screen, height=60, fg_color="transparent")
        self.status_frame.pack(fill="x", side="bottom", padx=30, pady=15)
        self.status_frame.pack_propagate(False)
        self.status_lbl = ctk.CTkLabel(self.status_frame, text="Ready", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_lbl.pack(side="left")
        
        # Cooldown/Countdown Label (Locked to right margin)
        self.cooldown_label = ctk.CTkLabel(self.status_frame, text="", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.cooldown_label.pack(side="right", padx=10)

        # DNS Health Label
        self.dns_health_lbl = ctk.CTkLabel(self.status_frame, text="DNS ENGINE: CHECKING...", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="gray")
        self.dns_health_lbl.pack(side="right", padx=10)

        # Create New Profile button - Locked to center of backdrop
        ctk.CTkButton(self.status_frame, text="+ Create New Profile", font=ctk.CTkFont(weight="bold"), width=200, height=40, command=self.add_new_group).place(relx=0.5, rely=0.5, anchor="center")

    def create_group_card(self, name, data):
        card = ctk.CTkFrame(self.groups_scroll, fg_color="#2b2b2b", corner_radius=12)
        card.pack(fill="x", pady=8, padx=2)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(header, text=name, font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        btn_f = ctk.CTkFrame(header, fg_color="transparent")
        btn_f.pack(side="right")
        ctk.CTkButton(btn_f, text="Delete", width=75, height=32, fg_color="#8b0000", hover_color="#5a0000", command=lambda n=name: self.delete_group(n)).pack(side="left", padx=6)
        ctk.CTkButton(btn_f, text="Rename", width=75, height=32, fg_color="#4a4a4a", hover_color="#5a5a5a", command=lambda n=name: self.rename_group(n)).pack(side="left", padx=6)
        ctk.CTkButton(btn_f, text="Edit", width=75, height=32, fg_color="#1f538d", hover_color="#14375e", command=lambda n=name: self.on_edit_click(n)).pack(side="left", padx=6)
        stats = f"Websites: {len(data.get('websites', []))}  |  Apps: {len(data.get('apps', []))}  |  Files: {len(data.get('files', []))}  |  Folders: {len(data.get('folders', []))}"
        ctk.CTkLabel(card, text=stats, text_color="gray", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(0, 15))

    def on_edit_click(self, group_name):
        self.group_name = group_name
        sec = self.config_data["groups"][group_name].get("security", {})
        if sec.get("enabled", False):
            self.show_challenge_screen(lambda: self.show_group_editor(group_name))
        else:
            self.show_group_editor(group_name)

    def show_group_editor(self, group_name):
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        top = ctk.CTkFrame(self.current_screen, fg_color="transparent", height=60)
        top.pack(fill="x", padx=30, pady=10) # Reduced pady
        top.pack_propagate(False)
        ctk.CTkButton(top, text="⇚ Dashboard", command=self.show_dashboard, fg_color="transparent", width=120, height=35, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkLabel(top, text=f"Editing: {group_name}", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=30)
        
        self.tabview = ctk.CTkTabview(self.current_screen, corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=30, pady=(5, 10)) # Tightened TabView
        t_web = self.tabview.add("Websites")
        t_apps = self.tabview.add("Apps")
        t_files = self.tabview.add("Files")
        t_folders = self.tabview.add("Folders")
        t_content = self.tabview.add("Content Filter")
        t_schedule = self.tabview.add("Schedule")
        
        t_web.group_name = group_name; t_apps.group_name = group_name; t_files.group_name = group_name; t_folders.group_name = group_name
        def validate_web(val):
            if "http" in val: return False, "Do not include http:// or https://"
            return True, ""
        dns_msg = "Supports keywords (word), wildcards (*.domain.com), prefixes (word*), and suffixes (*word.com). Path-level blocking (site.com/path) is not supported at the DNS level.\n\nNote: If the DNS proxy is bypassed by another app (e.g. Portmaster), a fallback to the Windows hosts file occurs. In fallback mode, entering a domain like x.com will block both x.com and www.x.com on IPv4 (0.0.0.0) and IPv6 (::1). Wildcards/keywords will be expanded to common extensions."
        self.list_web = InputListFrame(t_web, self, "websites", "Enter URL or Pattern", validation_fn=validate_web, info_tooltip=dns_msg)
        self.list_web.pack(fill="both", expand=True, padx=10, pady=10)
        self.list_apps = InputListFrame(t_apps, self, "apps", "Enter App Name (e.g. notepad.exe)", browse_mode="app")
        self.list_apps.pack(fill="both", expand=True, padx=10, pady=10)
        self.list_files = InputListFrame(t_files, self, "files", "Enter File Path", browse_mode="file")
        self.list_files.pack(fill="both", expand=True, padx=10, pady=10)
        self.list_folders = InputListFrame(t_folders, self, "folders", "Enter Folder Path", browse_mode="folder")
        self.list_folders.pack(fill="both", expand=True, padx=10, pady=10)
        ContentFilterTab(t_content, self, group_name).pack(fill="both", expand=True)
        self.build_schedule_ui(t_schedule)

        # Security Challenge at Bottom (Anchored within margin)
        sec_f = ctk.CTkFrame(self.current_screen, fg_color="transparent")
        sec_f.pack(fill="x", padx=30, pady=(5, 15))
        sec = self.config_data["groups"][group_name].get("security", {})
        ctk.CTkLabel(sec_f, text="Challenge Length:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(10, 5))
        self.length_var = ctk.StringVar(value=str(sec.get("challenge_length", 32)))
        length_cb = ctk.CTkComboBox(sec_f, values=["32", "64", "128", "256"], variable=self.length_var, command=self.save_security, width=80)
        length_cb.pack(side="left", padx=(0, 15))
        self.sec_enabled = ctk.CTkSwitch(sec_f, text="Enable Security Challenge", command=self.save_security)
        if sec.get("enabled"): self.sec_enabled.select()
        self.sec_enabled.pack(side="left")

        # Cooldown/Countdown Label in margin (consistent across screens)
        self.cooldown_label = ctk.CTkLabel(sec_f, text="", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.cooldown_label.pack(side="right", padx=10)
        self.status_lbl = ctk.CTkLabel(sec_f, text="Editor Active", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_lbl.pack(side="right", padx=10)

    def save_security(self, *args):
        self.config_data["groups"][self.group_name]["security"] = {
            "enabled": self.sec_enabled.get() == 1,
            "challenge_length": int(self.length_var.get())
        }
        self.trigger_save()

    def build_schedule_ui(self, parent):
        schedule = self.config_data["groups"][self.group_name].get("schedule", {})
        container = ctk.CTkScrollableFrame(parent, fg_color="#2b2b2b", corner_radius=12)
        container.pack(fill="both", expand=True, padx=20, pady=15)
        self.sch_enabled = ctk.CTkSwitch(container, text="Enable Schedule", command=self.save_schedule, font=ctk.CTkFont(size=15, weight="bold"))
        if schedule.get("enabled"): self.sch_enabled.select()
        self.sch_enabled.pack(pady=(20, 8), anchor="w", padx=25)
        self.sch_persist = ctk.CTkSwitch(container, text="Enforce All Day (Bypass start/end times)", command=self.save_schedule)
        if schedule.get("persist_all_day"): self.sch_persist.select()
        self.sch_persist.pack(pady=6, anchor="w", padx=25)
        ctk.CTkLabel(container, text="Time Window (HH:MM):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=25, pady=(20, 5))
        f_time = ctk.CTkFrame(container, fg_color="transparent")
        f_time.pack(pady=5, anchor="w", padx=35)
        self.start_entry = ctk.CTkEntry(f_time, width=100, height=35)
        start_initial = self._normalize_schedule_time(schedule.get("start_time", "09:00")) or "09:00"
        self.start_entry.insert(0, start_initial)
        self.start_entry.pack(side="left")
        ctk.CTkLabel(f_time, text="to", font=ctk.CTkFont(size=14)).pack(side="left", padx=15)
        self.end_entry = ctk.CTkEntry(f_time, width=100, height=35)
        end_initial = self._normalize_schedule_time(schedule.get("end_time", "17:00")) or "17:00"
        self.end_entry.insert(0, end_initial)
        self.end_entry.pack(side="left")
        self.start_entry.bind("<KeyRelease>", lambda e: self.save_schedule())
        self.end_entry.bind("<KeyRelease>", lambda e: self.save_schedule())
        self.schedule_feedback_lbl = ctk.CTkLabel(container, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self.schedule_feedback_lbl.pack(anchor="w", padx=35, pady=(4, 0))
        ctk.CTkLabel(container, text="Active Days:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=25, pady=(20, 5))
        self.days_vars = {}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            var = ctk.BooleanVar(value=(day in schedule.get("days", [])))
            ctk.CTkCheckBox(container, text=day, variable=var, command=self.save_schedule).pack(anchor="w", pady=4, padx=40)
            self.days_vars[day] = var

    def _normalize_schedule_time(self, value):
        txt = str(value or "").strip()
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", txt)
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
        return None

    def save_schedule(self):
        existing = self.config_data["groups"][self.group_name].get("schedule", {})
        prev_start = self._normalize_schedule_time(existing.get("start_time", "09:00")) or "09:00"
        prev_end = self._normalize_schedule_time(existing.get("end_time", "17:00")) or "17:00"
        start_input = self.start_entry.get().strip()
        end_input = self.end_entry.get().strip()
        start_time = self._normalize_schedule_time(start_input)
        end_time = self._normalize_schedule_time(end_input)

        if start_time is None or end_time is None:
            start_time = start_time or prev_start
            end_time = end_time or prev_end
            self.schedule_feedback_lbl.configure(
                text="Invalid time format. Use H:MM or HH:MM (e.g., 16:00). Invalid value ignored.",
                text_color="orange"
            )
        else:
            self.schedule_feedback_lbl.configure(text="", text_color="gray")

        self.config_data["groups"][self.group_name]["schedule"] = {
            "enabled": self.sch_enabled.get() == 1,
            "persist_all_day": self.sch_persist.get() == 1,
            "start_time": start_time,
            "end_time": end_time,
            "days": [day for day, var in self.days_vars.items() if var.get()]
        }
        self.trigger_save()

    def show_settings(self):
        self.clear_screen()
        self.current_screen = ctk.CTkFrame(self)
        self.current_screen.pack(fill="both", expand=True)
        top = ctk.CTkFrame(self.current_screen, fg_color="transparent", height=60)
        top.pack(fill="x", padx=30, pady=10)
        top.pack_propagate(False)
        ctk.CTkButton(top, text="⇚ Dashboard", command=self.show_dashboard, fg_color="transparent", width=120, height=35, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkLabel(top, text="Global Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=30)
        tabs = ctk.CTkTabview(self.current_screen, corner_radius=12)
        tabs.pack(fill="both", expand=True, padx=30, pady=(5, 30))
        t_perf = tabs.add("Performance")
        t_cloud = tabs.add("Cloud Allowlist")
        t_notif = tabs.add("Notifications")
        t_about = tabs.add("About")
        self._build_performance_tab(t_perf)
        self._build_cloud_tab(t_cloud)
        self._build_notifications_tab(t_notif)
        self._build_about_tab(t_about)

    def _build_performance_tab(self, parent):
        c = self._settings_container(parent)
        s = self.config_data.get("settings", {})
        
        # System Shield Intensity (Renamed from Daemon for modern context)
        ctk.CTkLabel(c, text="System Shield Intensity", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(20, 4))
        desc_map = {
            "Passive": "Checks rules every 5s. Minimum resource usage.",
            "Balanced": "Checks rules every 2s. Optimized for standard PCs.",
            "Strict": "Checks rules every 0.5s. Maximum security enforcement."
        }
        self._perf_desc = ctk.CTkLabel(c, text=desc_map.get(s.get("performance_mode", "Balanced"), ""), text_color="gray")
        self._perf_desc.pack(anchor="w", padx=25, pady=(0, 10))
        
        def on_perf(val):
            self.config_data["settings"]["performance_mode"] = val
            self._perf_desc.configure(text=desc_map.get(val, ""))
            self.trigger_save()
            
        seg = ctk.CTkSegmentedButton(c, values=["Passive", "Balanced", "Strict"], command=on_perf, height=38)
        seg.set(s.get("performance_mode", "Balanced"))
        seg.pack(fill="x", padx=25, pady=10)

        # Interface Responsiveness
        ctk.CTkLabel(c, text="Interface Responsiveness", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(30, 4))
        ctk.CTkLabel(c, text="Adjust UI refresh rates and animation quality.", text_color="gray").pack(anchor="w", padx=25, pady=(0, 10))
        
        def on_ui(val):
            self.config_data["settings"]["ui_mode"] = val
            self.trigger_save()
            
        ui_seg = ctk.CTkSegmentedButton(c, values=["Fast", "Smooth", "Ultra"], command=on_ui, height=38)
        ui_seg.set(s.get("ui_mode", "Smooth"))
        ui_seg.pack(fill="x", padx=25, pady=10)

        # Hosts File Line Cap
        ctk.CTkLabel(c, text="Hosts File Line Cap", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(30, 4))
        ctk.CTkLabel(c, text="Limit the total lines written to the hosts file to prevent resolution latency.", text_color="gray").pack(anchor="w", padx=25, pady=(0, 10))
        def on_cap(val):
            self.config_data["settings"]["max_domains_cap"] = int(val)
            self.trigger_save()
        cap_seg = ctk.CTkSegmentedButton(c, values=["1000", "2000", "3000", "4000", "5000"], command=on_cap, height=38)
        cap_seg.set(str(s.get("max_domains_cap", 1000)))
        cap_seg.pack(fill="x", padx=25, pady=10)

        # Persistence
        ctk.CTkLabel(c, text="Persistence", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(30, 4))
        self.startup_var = ctk.BooleanVar(value=handler.is_startup_enabled())
        ctk.CTkSwitch(c, text="Run Protection Engine on System Startup", variable=self.startup_var, command=self._on_startup_toggle).pack(anchor="w", padx=30, pady=10)

    def _on_startup_toggle(self):
        e = self.startup_var.get()
        if handler.set_startup(e):
            self.config_data["settings"]["startup_enabled"] = e
            self.trigger_save()

    def _build_about_tab(self, parent):
        c = self._settings_container(parent)
        ctk.CTkLabel(c, text="Simple Productivity Blocker", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(30, 8))
        ctk.CTkLabel(c, text=f"Release Version {VERSION}", text_color="gray", font=ctk.CTkFont(size=14)).pack(pady=(0, 30))
        f = ctk.CTkFrame(c, fg_color="transparent")
        f.pack(pady=10)
        ctk.CTkButton(f, text="GitHub Repository", width=180, height=40, command=lambda: webbrowser.open("https://github.com/nvusdev/simple-productivity-blocker")).pack(side="left", padx=10)
        ctk.CTkButton(f, text="Open Config Folder", width=180, height=40, command=self._open_config_folder).pack(side="left", padx=10)
        ctk.CTkLabel(c, text="Maintenance & Recovery", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(40, 10))
        f_b = ctk.CTkFrame(c, fg_color="transparent")
        f_b.pack(pady=10)
        ctk.CTkButton(f_b, text="Backup Configuration", width=180, height=38, command=self._backup_settings).pack(side="left", padx=10)
        ctk.CTkButton(f_b, text="Restore Configuration", width=180, height=38, command=self._restore_settings).pack(side="left", padx=10)
        
        # Add Emergency Recovery button in Maintenance & Recovery
        f_recovery = ctk.CTkFrame(c, fg_color="transparent")
        f_recovery.pack(pady=(15, 10))
        ctk.CTkButton(
            f_recovery, 
            text="🚨 Emergency Recovery", 
            width=380, 
            height=42, 
            fg_color="#D32F2F", 
            hover_color="#B71C1C",
            font=ctk.CTkFont(weight="bold"),
            command=self._run_emergency_recovery
        ).pack(padx=10)

        # Compatibility warning: if a security appliance (e.g., Portmaster) is detected, show a prominent notice
        try:
            conflict_name = detect_conflicting_services()
        except Exception:
            conflict_name = None
        if conflict_name:
            ctk.CTkLabel(
                c,
                text=f"Compatibility mode active: yielding DNS to {conflict_name}. SPB is using hosts-file fallback to avoid breaking network access.",
                text_color="#FF9800",
                font=ctk.CTkFont(size=12, weight="bold"),
                wraplength=700,
                justify="left"
            ).pack(pady=(12, 10))

            ctk.CTkLabel(
                c,
                text="If you are an advanced user and understand the risks, you can enable 'Force DNS Proxy' in the configuration file (not recommended).",
                text_color="gray",
                font=ctk.CTkFont(size=11)
            ).pack(pady=(0, 8))

            def _open_conflict_help():
                webbrowser.open("https://github.com/nvusdev/simple-productivity-blocker#compatibility-with-security-appliances")
            ctk.CTkButton(c, text="Learn More", width=140, height=34, command=_open_conflict_help).pack(pady=(0, 12))

    def _run_emergency_recovery(self):
        # Find recovery_uplift.exe in production or fallback to recovery_uplift.py in development
        exe_path = resource_path("recovery_uplift.exe")
        if not os.path.exists(exe_path):
            # Development fallback
            py_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "recovery_uplift.py"))
            if os.path.exists(py_path):
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{py_path}"', None, 1)
                    self.status_lbl.configure(text="Emergency Recovery launched", text_color="green")
                except Exception as e:
                    self.status_lbl.configure(text=f"Failed to launch: {e}", text_color="red")
            else:
                self.status_lbl.configure(text="Recovery tool not found", text_color="red")
        else:
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, "", None, 1)
                self.status_lbl.configure(text="Emergency Recovery launched", text_color="green")
            except Exception as e:
                self.status_lbl.configure(text=f"Failed to launch: {e}", text_color="red")

    def _backup_settings(self):
        p = ctk.filedialog.asksaveasfilename(defaultextension=".spb", filetypes=[("SPB Backup", "*.spb")])
        if p and export_config(self.config_data, p):
            self.status_lbl.configure(text="Backup saved", text_color="green")

    def _restore_settings(self):
        p = ctk.filedialog.askopenfilename(filetypes=[("SPB Backup", "*.spb")])
        if p:
            n = import_config(p, self.config_data)
            if n:
                self.config_data = n
                save_config(n)
                self.show_dashboard()
                self.status_lbl.configure(text="Restored", text_color="green")

    def _settings_container(self, parent):
        c = ctk.CTkScrollableFrame(parent, fg_color="#2b2b2b", corner_radius=12)
        c.pack(fill="both", expand=True, padx=20, pady=15)
        return c

    def _inline_list(self, parent, items, on_change, placeholder=""):
        state = {"items": list(items)}
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=25, pady=5)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, height=36, corner_radius=8)
        entry.pack(side="left", fill="x", expand=True)
        list_f = ctk.CTkFrame(frame, fg_color="transparent")
        list_f.pack(fill="x", pady=(8, 0))
        ws = {}
        def render(v):
            r = ctk.CTkFrame(list_f, fg_color="#333333", corner_radius=6)
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=v, anchor="w", font=ctk.CTkFont(size=13)).pack(side="left", fill="x", expand=True, padx=12, pady=6)
            ctk.CTkButton(r, text="Remove", width=65, height=28, fg_color="#8b0000", hover_color="#5a0000", command=lambda x=v: remove(x)).pack(side="right", padx=8)
            ws[v] = r
        def remove(v):
            if v in state["items"]:
                state["items"].remove(v)
                ws.pop(v).destroy()
                on_change()
        def add():
            val = entry.get().strip()
            if val and val not in state["items"]:
                state["items"].append(val)
                render(val)
                entry.delete(0, "end")
                on_change()
        ctk.CTkButton(row, text="+", width=40, height=36, command=add).pack(side="left", padx=(10, 0))
        entry.bind("<Return>", lambda e: add())
        for v in state["items"]:
            render(v)
        return state

    def _open_config_folder(self):
        p = get_config_dir()
        if os.name == 'nt': os.startfile(p)
        else: subprocess.Popen(["xdg-open", p])

    def _build_cloud_tab(self, parent):
        c = self._settings_container(parent)
        s = self.config_data.get("settings", {})
        v = ctk.BooleanVar(value=s.get("cloud_allowlist_enabled", True))
        ctk.CTkSwitch(c, text="Protect Cloud Sync & System Processes", variable=v, command=self._save_settings, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=25, pady=(20, 8))
        self._cloud_enabled = v
        ctk.CTkLabel(c, text="Allowed Executables:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25, pady=(15, 0))
        ctk.CTkLabel(c, text="Processes matching these exact names will never be blocked.", text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=25, pady=(0, 5))
        self._cloud_exe_list = self._inline_list(c, s.get("cloud_allowlist", []), self._save_settings, "e.g. OneDrive.exe")
        ctk.CTkLabel(c, text="Allowed Path Keywords:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25, pady=(25, 0))
        ctk.CTkLabel(c, text="Processes running from paths containing these words will be exempted.", text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=25, pady=(0, 5))
        self._cloud_kw_list = self._inline_list(c, s.get("cloud_path_keywords", []), self._save_settings, "e.g. onedrive")

    def _save_settings(self, *args):
        s = self.config_data.setdefault("settings", {})
        if hasattr(self, '_cloud_enabled'): s["cloud_allowlist_enabled"] = self._cloud_enabled.get()
        if hasattr(self, '_cloud_exe_list'): s["cloud_allowlist"] = self._cloud_exe_list["items"]
        if hasattr(self, '_cloud_kw_list'): s["cloud_path_keywords"] = self._cloud_kw_list["items"]
        if hasattr(self, '_notif_vars'): s["notifications"] = {k: var.get() for k, var in self._notif_vars.items()}
        self.trigger_save()

    def _build_notifications_tab(self, parent):
        c = self._settings_container(parent)
        s = self.config_data.get("settings", {})
        n = s.get("notifications", {})
        self._notif_vars = {}
        def sec(t, d, opts):
            ctk.CTkLabel(c, text=t, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=25, pady=(20, 2))
            ctk.CTkLabel(c, text=d, text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=25, pady=(0, 8))
            for k, l, dft in opts:
                v = ctk.BooleanVar(value=n.get(k, dft))
                ctk.CTkSwitch(c, text=l, variable=v, command=self._save_settings).pack(anchor="w", padx=40, pady=5)
                self._notif_vars[k] = v
        sec("Block Events", "Fired when the daemon actively enforces a blocking rule.", [("on_block", "Notify on block rule applied", True), ("on_block_attempt", "Notify on blocked app kill", True), ("on_exception_bypass", "Notify on allowlist bypass", False)])
        sec("Schedule Events", "Notifications for profile schedule activation.", [("on_schedule_start", "Notify on profile start", True), ("on_schedule_end", "Notify on profile end", True), ("on_day_change", "Notify on day recalculation", False)])
        sec("Daemon Events", "General protection engine activity.", [("on_daemon_start", "Notify on engine start", True), ("on_config_reload", "Notify on sync/reload", False), ("on_hosts_write", "Notify on DNS/hosts update", False)])

    def add_new_group(self):
        name = self._prompt_text_dialog("New Profile", "Enter name for the new profile:")
        if name:
            if name in self.config_data["groups"]:
                self._info_dialog("Error", "Profile name exists.")
                return
            self.config_data["groups"][name] = copy.deepcopy(DEFAULT_GROUP_CONFIG)
            self.trigger_save()
            self.show_dashboard()

    def delete_group(self, name):
        if len(self.config_data["groups"]) <= 1: return
        if self._confirm_dialog("Delete Profile", f"Delete '{name}'?"):
            del self.config_data["groups"][name]
            self.trigger_save()
            self.show_dashboard()

    def rename_group(self, old):
        new = self._prompt_text_dialog("Rename Profile", f"New name for '{old}':", initial=old)
        if new and new != old and new not in self.config_data["groups"]:
            self.config_data["groups"][new] = self.config_data["groups"].pop(old)
            self.trigger_save()
            self.show_dashboard()

    def _center_dialog(self, d, w, h):
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()-w)//2
        y = self.winfo_y() + (self.winfo_height()-h)//2
        d.geometry(f"{w}x{h}+{x}+{y}")

    def _prompt_text_dialog(self, t, m, initial=""):
        d = ctk.CTkToplevel(self)
        d.attributes("-alpha", 0.0) # Stealth initialization
        d.title(t)
        d.resizable(False, False)
        d.transient(self)
        d.grab_set()
        self._center_dialog(d, 450, 240)
        d.attributes("-alpha", 1.0) # Reveal when centered
        ctk.CTkLabel(d, text=m, font=ctk.CTkFont(size=15)).pack(pady=(35, 12))
        e = ctk.CTkEntry(d, width=380, height=40)
        e.pack(padx=30)
        e.insert(0, initial)
        e.focus_set()
        res = {"v": None}
        def ok():
            res["v"] = e.get().strip()
            d.destroy()
        
        e.bind("<Return>", lambda event: ok()) # UX: Enter to save
        ctk.CTkButton(d, text="Save", width=140, height=40, command=ok).pack(pady=30)
        d.wait_window()
        return res["v"]

    def _confirm_dialog(self, t, m):
        d = ctk.CTkToplevel(self)
        d.attributes("-alpha", 0.0) # Stealth initialization
        d.title(t)
        d.resizable(False, False)
        d.transient(self)
        d.grab_set()
        self._center_dialog(d, 460, 220)
        d.attributes("-alpha", 1.0) # Reveal when centered
        ctk.CTkLabel(d, text=m, font=ctk.CTkFont(size=15)).pack(pady=40)
        res = {"v": False}
        def yes():
            res["v"] = True
            d.destroy()
        f = ctk.CTkFrame(d, fg_color="transparent")
        f.pack()
        ctk.CTkButton(f, text="Yes, Delete", width=140, height=40, fg_color="#8b0000", hover_color="#5a0000", command=yes).pack(side="left", padx=15)
        ctk.CTkButton(f, text="Cancel", width=140, height=40, fg_color="#4a4a4a", command=d.destroy).pack(side="left", padx=15)
        d.wait_window()
        return res["v"]

    def _info_dialog(self, t, m):
        d = ctk.CTkToplevel(self)
        d.attributes("-alpha", 0.0) # Stealth initialization
        d.title(t)
        d.resizable(False, False)
        d.transient(self)
        d.grab_set()
        self._center_dialog(d, 420, 180)
        d.attributes("-alpha", 1.0) # Reveal when centered
        ctk.CTkLabel(d, text=m, font=ctk.CTkFont(size=15)).pack(pady=40)
        ctk.CTkButton(d, text="OK", width=120, height=38, command=d.destroy).pack()
        d.wait_window()

    def show_challenge_screen(self, n):
        self.clear_screen()
        f = ctk.CTkFrame(self)
        f.pack(fill="both", expand=True)
        
        # Use a diverse set of common keyboard characters (excluding alt-code combinations)
        chars = string.ascii_letters + string.digits + "|+[{;':\",.<>?/!@#$%^&*()-_="
        challenge_len = self.config_data["groups"][self.group_name]["security"]["challenge_length"]
        self.challenge_string = "".join(random.choices(chars, k=challenge_len))
        
        ctk.CTkLabel(f, text="Enter Security Challenge", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(30, 5))
        ctk.CTkLabel(f, text="For security, long challenges are segmented into 32-character scrollable chunks.", font=ctk.CTkFont(size=13), text_color="#aaaaaa").pack(pady=(0, 15))
        
        # Break down the challenge string into 32-character chunks
        chunks = [self.challenge_string[i:i+32] for i in range(0, len(self.challenge_string), 32)]
        
        # Scrollable container for segment cards
        scroll_frame = ctk.CTkScrollableFrame(f, width=560, height=320, fg_color="transparent")
        scroll_frame.pack(pady=10, fill="both", expand=True, padx=20)
        
        entries = []
        cards = []
        
        def check_segment(idx):
            entry = entries[idx]
            card = cards[idx]
            target = chunks[idx]
            val = entry.get()
            
            if val == target:
                card.configure(border_color="#2ecc71", border_width=2)
                # Auto-focus the next entry if it exists
                if idx + 1 < len(chunks):
                    entries[idx + 1].focus_set()
                else:
                    # Check if ALL entries match
                    all_ok = True
                    for i, ent in enumerate(entries):
                        if ent.get() != chunks[i]:
                            all_ok = False
                            break
                    if all_ok:
                        n()
            elif val and not target.startswith(val):
                card.configure(border_color="#e74c3c", border_width=2)
            else:
                card.configure(border_color="#555555", border_width=1)
                
        for i, chunk in enumerate(chunks):
            # Segment card container
            card = ctk.CTkFrame(scroll_frame, border_color="#555555", border_width=1, corner_radius=8, fg_color="#2b2b2b")
            card.pack(pady=10, fill="x", padx=10)
            cards.append(card)
            
            # Header with Segment index and progress
            header_text = f"Segment {i+1} of {len(chunks)} ({len(chunk)} characters)"
            ctk.CTkLabel(card, text=header_text, font=ctk.CTkFont(size=12, weight="bold"), text_color="#10b981").pack(anchor="w", padx=15, pady=(8, 2))
            
            # Display target chunk
            ctk.CTkLabel(card, text=chunk, font=ctk.CTkFont(family="Consolas", size=18, weight="bold"), text_color="#ffffff", justify="left")
            card.winfo_children()[-1].pack(anchor="w", padx=15, pady=(2, 6))
            
            # Entry Container
            entry_container = ctk.CTkFrame(card, fg_color="#1e1e1e", height=45, corner_radius=6)
            entry_container.pack(fill="x", padx=15, pady=(0, 10))
            entry_container.pack_propagate(False)
            
            # Typing Entry
            entry = ctk.CTkEntry(entry_container, font=ctk.CTkFont(family="Consolas", size=16), fg_color="transparent", border_width=0, placeholder_text="Type segment here...")
            entry.pack(fill="both", expand=True, padx=10, pady=5)
            entries.append(entry)
            
            # Bind key release for real-time validation and autofocus
            entry.bind("<KeyRelease>", lambda e, idx=i: check_segment(idx))
            
        # Focus the first entry
        if entries:
            entries[0].focus_set()
            
        def manual_unlock():
            # Check all
            all_ok = True
            for i, entry in enumerate(entries):
                if entry.get() == chunks[i]:
                    cards[i].configure(border_color="#2ecc71", border_width=2)
                else:
                    cards[i].configure(border_color="#e74c3c", border_width=2)
                    all_ok = False
            if all_ok:
                n()
                
        # Action Buttons
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x")
        
        ctk.CTkButton(btn_frame, text="Unlock Settings", width=200, height=40, command=manual_unlock, fg_color="#10b981", hover_color="#059669").pack(side="left", expand=True, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=200, height=40, fg_color="transparent", border_color="#555555", border_width=1, hover_color="#333333", command=self.show_dashboard).pack(side="right", expand=True, padx=10)

if __name__ == "__main__":
    from core.win32_utils import is_safe_mode
    if is_safe_mode():
        try:
            from recovery_uplift import run_auto_recovery
            run_auto_recovery()
        except Exception as e:
            print(f"[!] Safe Mode automated recovery failed: {e}")
        sys.exit(0)

    app = ProductivityApp()
    app.mainloop()
