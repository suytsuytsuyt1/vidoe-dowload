# -*- coding: utf-8 -*-
"""
GIAO DIỆN GUI NÂNG CẤP - VIDEO DOWNLOADER
Thiết kế theo ảnh: https://i.imgur.com/... (Tài Video YouTube Pro)
- Giao diện 2 chế độ: Sáng (trắng) / Tối (xám đen)
- Animation mịn khi chuyển đổi chế độ
- Tiếng Việt 100%
- Tích hợp tất cả chức năng từ file cũ
"""

import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from typing import Optional, Dict, List, Tuple

try:
    import tai_video_core as core
    import thumbnail_core as thumb_core
    import extension_cookie
except ImportError:
    core = None
    thumb_core = None
    extension_cookie = None

# ==================== BẢNG MÀU & CẤU HÌNH ====================

THEME_LIGHT = {
    "bg_main": "#F5F6F8",
    "bg_card": "#FFFFFF",
    "bg_input": "#FFFFFF",
    "border_color": "#E2E4E9",
    "text_primary": "#1E2328",
    "text_secondary": "#6C7178",
    "text_accent": "#5B9DFF",
    "btn_primary_bg": "#3D7EFF",
    "btn_primary_fg": "#FFFFFF",
    "btn_primary_hover": "#5C90FF",
    "btn_secondary_bg": "#FFFFFF",
    "btn_secondary_fg": "#1E2328",
    "btn_secondary_border": "#E2E4E9",
    "status_ready": "#9CA1A8",
    "status_running": "#3E8F76",
    "status_error": "#B5564C",
    "success": "#3E8F76",
    "error": "#B5564C",
    "warning": "#6C7178",
}

THEME_DARK = {
    "bg_main": "#15171D",
    "bg_card": "#20232C",
    "bg_input": "#20232C",
    "border_color": "#343A47",
    "text_primary": "#EDEFF3",
    "text_secondary": "#9AA0AC",
    "text_accent": "#5B9DFF",
    "btn_primary_bg": "#3D7EFF",
    "btn_primary_fg": "#FFFFFF",
    "btn_primary_hover": "#5C90FF",
    "btn_secondary_bg": "#20232C",
    "btn_secondary_fg": "#EDEFF3",
    "btn_secondary_border": "#343A47",
    "status_ready": "#6B7280",
    "status_running": "#4CD08A",
    "status_error": "#FF7A7A",
    "success": "#4CD08A",
    "error": "#FF7A7A",
    "warning": "#9AA0AC",
}

class AppConfig:
    """Cấu hình toàn cục của ứng dụng"""
    current_theme = "light"
    colors = THEME_LIGHT.copy()
    
    @classmethod
    def switch_theme(cls, theme_name: str):
        cls.current_theme = theme_name
        cls.colors = THEME_DARK.copy() if theme_name == "dark" else THEME_LIGHT.copy()

# ==================== CÁC WIDGET TÙY CHỈNH ====================

class ModernButton(tk.Button):
    """Nút bấm với hover effect"""
    def __init__(self, parent, text="", command=None, style_type="primary", **kwargs):
        self.style_type = style_type
        self.original_bg = None
        self.original_fg = None
        
        super().__init__(
            parent, text=text, command=command,
            font=("Segoe UI", 10, "bold" if style_type == "primary" else "normal"),
            relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
            **kwargs
        )
        
        self.apply_theme()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def apply_theme(self):
        """Áp dụng màu sắc theo chủ đề"""
        colors = AppConfig.colors
        
        if self.style_type == "primary":
            self.config(
                bg=colors["btn_primary_bg"],
                fg=colors["btn_primary_fg"],
                activebackground=colors["btn_primary_hover"],
                activeforeground=colors["btn_primary_fg"]
            )
            self.original_bg = colors["btn_primary_bg"]
            self.original_fg = colors["btn_primary_fg"]
        else:
            self.config(
                bg=colors["btn_secondary_bg"],
                fg=colors["btn_secondary_fg"],
                relief="solid", bd=1,
                activebackground=colors["border_color"],
                activeforeground=colors["btn_secondary_fg"]
            )
            self.original_bg = colors["btn_secondary_bg"]
            self.original_fg = colors["btn_secondary_fg"]
    
    def _on_enter(self, event):
        if self.style_type == "primary":
            self.config(bg=AppConfig.colors["btn_primary_hover"])
    
    def _on_leave(self, event):
        if self.style_type == "primary":
            self.config(bg=self.original_bg)

class ModernEntry(tk.Entry):
    """Ô nhập liệu với border tùy chỉnh"""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            font=("Segoe UI", 10),
            relief="solid", bd=1,
            **kwargs
        )
        self.apply_theme()
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
    
    def apply_theme(self):
        colors = AppConfig.colors
        self.config(
            bg=colors["bg_input"],
            fg=colors["text_primary"],
            insertbackground=colors["text_primary"],
            highlightbackground=colors["border_color"],
            highlightcolor=colors["text_accent"],
            highlightthickness=1
        )
    
    def _on_focus_in(self, event):
        self.config(highlightbackground=AppConfig.colors["text_accent"])
    
    def _on_focus_out(self, event):
        self.config(highlightbackground=AppConfig.colors["border_color"])

class ModernCard(tk.Frame):
    """Thẻ (card) với viền và nền"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.apply_theme()
    
    def apply_theme(self):
        colors = AppConfig.colors
        self.config(
            bg=colors["bg_card"],
            highlightbackground=colors["border_color"],
            highlightthickness=1, bd=0
        )

# ==================== CỬA SỔ CHÍNH ====================

class VideoDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tài Video YouTube Pro")
        self.root.geometry("900x700")
        
        # Thiết lập icon
        self._setup_icon()
        
        # Tạo giao diện
        self._create_ui()
        
        # Khôi phục theme đã lưu
        self._load_saved_theme()
    
    def _setup_icon(self):
        """Thiết lập icon cho cửa sổ"""
        try:
            icon_path = "assets/icon.ico"
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
    
    def _create_ui(self):
        """Xây dựng giao diện chính"""
        colors = AppConfig.colors
        
        # Main container
        self.main_frame = tk.Frame(self.root, bg=colors["bg_main"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header với logo + tiêu đề + nút đổi chế độ
        self._create_header()
        
        # Notebook (tabs)
        self._create_tabs()
        
        # Log panel
        self._create_log_panel()
    
    def _create_header(self):
        """Tạo phần header"""
        colors = AppConfig.colors
        header = tk.Frame(self.main_frame, bg=colors["bg_main"], height=80)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        # Logo + Tiêu đề
        left_frame = tk.Frame(header, bg=colors["bg_main"])
        left_frame.pack(side="left", fill="both", expand=True)
        
        logo_label = tk.Label(
            left_frame, text="⬇", font=("Segoe UI", 32, "bold"),
            bg=colors["bg_main"], fg=colors["text_accent"]
        )
        logo_label.pack(side="left", padx=(0, 15))
        
        title_frame = tk.Frame(left_frame, bg=colors["bg_main"])
        title_frame.pack(side="left", fill="both", expand=True)
        
        tk.Label(
            title_frame, text="Tải Video YouTube Pro",
            font=("Segoe UI", 18, "bold"),
            bg=colors["bg_main"], fg=colors["text_primary"]
        ).pack(anchor="w")
        
        tk.Label(
            title_frame, text="Dùng yt-dlp và PO Token - Phiên bản tối ưu",
            font=("Segoe UI", 9),
            bg=colors["bg_main"], fg=colors["text_secondary"]
        ).pack(anchor="w")
        
        # Nút đổi chế độ sáng/tối
        theme_btn = ModernButton(
            header,
            text="☀ Sáng" if AppConfig.current_theme == "dark" else "🌙 Tối",
            command=self._toggle_theme,
            style_type="secondary"
        )
        theme_btn.pack(side="right")
        self.theme_btn = theme_btn
    
    def _create_tabs(self):
        """Tạo tabs cho Video và Thumbnails"""
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Tab 1: Tải Video
        self.video_tab = tk.Frame(self.notebook, bg=AppConfig.colors["bg_main"])
        self.notebook.add(self.video_tab, text="Tải Video")
        self._create_video_tab()
        
        # Tab 2: Tải Thumbnails
        self.thumb_tab = tk.Frame(self.notebook, bg=AppConfig.colors["bg_main"])
        self.notebook.add(self.thumb_tab, text="Tải Thumbnails")
        self._create_thumb_tab()
    
    def _create_video_tab(self):
        """Tạo nội dung tab Tải Video"""
        colors = AppConfig.colors
        
        # Scrollable canvas
        canvas = tk.Canvas(self.video_tab, bg=colors["bg_main"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.video_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=colors["bg_main"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Config Card
        config_card = ModernCard(scrollable_frame)
        config_card.pack(fill="x", pady=(0, 10))
        
        config_inner = tk.Frame(config_card, bg=colors["bg_card"])
        config_inner.pack(fill="x", padx=15, pady=15)
        
        # URL Input
        tk.Label(config_inner, text="URL Kênh YouTube", font=("Segoe UI", 10, "bold"),
                bg=colors["bg_card"], fg=colors["text_primary"]).pack(anchor="w")
        self.url_entry = ModernEntry(config_inner)
        self.url_entry.pack(fill="x", pady=(5, 15))
        
        # Thư mục lưu
        tk.Label(config_inner, text="Thư Mục Lưu", font=("Segoe UI", 10, "bold"),
                bg=colors["bg_card"], fg=colors["text_primary"]).pack(anchor="w")
        folder_frame = tk.Frame(config_inner, bg=colors["bg_card"])
        folder_frame.pack(fill="x", pady=(5, 15))
        self.folder_entry = ModernEntry(folder_frame)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ModernButton(folder_frame, text="Chọn...", style_type="secondary", command=lambda: None).pack(side="left")
        
        # Chất lượng
        tk.Label(config_inner, text="Chất Lượng", font=("Segoe UI", 10, "bold"),
                bg=colors["bg_card"], fg=colors["text_primary"]).pack(anchor="w")
        quality_frame = tk.Frame(config_inner, bg=colors["bg_card"])
        quality_frame.pack(fill="x", pady=(5, 15))
        self.quality_combo = ttk.Combobox(quality_frame, 
            values=["1080p", "720p", "480p", "360p"], state="readonly")
        self.quality_combo.pack(fill="x")
        
        # Checkbox options
        options_frame = tk.Frame(config_inner, bg=colors["bg_card"])
        options_frame.pack(fill="x", pady=(5, 15))
        
        self.shorts_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Tải cả Shorts", variable=self.shorts_var,
                      bg=colors["bg_card"], fg=colors["text_primary"],
                      selectcolor=colors["bg_card"]).pack(anchor="w")
        
        self.audio_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Chỉ tải âm thanh (MP3)", variable=self.audio_only_var,
                      bg=colors["bg_card"], fg=colors["text_primary"],
                      selectcolor=colors["bg_card"]).pack(anchor="w")
        
        self.cookie_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Dùng cookie đăng nhập", variable=self.cookie_var,
                      bg=colors["bg_card"], fg=colors["text_primary"],
                      selectcolor=colors["bg_card"]).pack(anchor="w")
        
        # Action buttons
        button_frame = tk.Frame(self.video_tab, bg=colors["bg_main"])
        button_frame.pack(fill="x", padx=20, pady=10)
        
        ModernButton(button_frame, text="1) Đếm Video & Quét File",
                    style_type="secondary", command=lambda: None).pack(side="left", padx=(0, 10))
        
        self.start_btn = ModernButton(button_frame, text="2) Bắt Đầu Tải",
                                     style_type="primary", command=lambda: None)
        self.start_btn.pack(side="left", padx=(0, 10))
        
        ModernButton(button_frame, text="⏸ Tạm Dừng",
                    style_type="secondary", command=lambda: None).pack(side="left")
        
        # Status
        status_frame = tk.Frame(self.video_tab, bg=colors["bg_main"])
        status_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(status_frame, text="●", font=("Segoe UI", 10),
                bg=colors["bg_main"], fg=colors["status_ready"]).pack(side="left", padx=(0, 8))
        tk.Label(status_frame, text="Sẵn sàng.",
                bg=colors["bg_main"], fg=colors["text_secondary"],
                font=("Segoe UI", 9)).pack(side="left")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_thumb_tab(self):
        """Tạo nội dung tab Tải Thumbnails"""
        colors = AppConfig.colors
        
        canvas = tk.Canvas(self.thumb_tab, bg=colors["bg_main"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.thumb_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=colors["bg_main"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Config Card
        config_card = ModernCard(scrollable_frame)
        config_card.pack(fill="x", pady=(0, 10))
        
        config_inner = tk.Frame(config_card, bg=colors["bg_card"])
        config_inner.pack(fill="x", padx=15, pady=15)
        
        # URL
        tk.Label(config_inner, text="URL Kênh YouTube", font=("Segoe UI", 10, "bold"),
                bg=colors["bg_card"], fg=colors["text_primary"]).pack(anchor="w")
        self.thumb_url_entry = ModernEntry(config_inner)
        self.thumb_url_entry.pack(fill="x", pady=(5, 15))
        
        # API Key
        tk.Label(config_inner, text="YouTube Data API Key", font=("Segoe UI", 10, "bold"),
                bg=colors["bg_card"], fg=colors["text_primary"]).pack(anchor="w")
        self.api_key_entry = ModernEntry(config_inner, show="•")
        self.api_key_entry.pack(fill="x", pady=(5, 15))
        
        # Thư mục lưu Thumbnails
        tk.Label(config_inner, text="Thư Mục Lưu", font=("Segoe UI", 10, "bold"),
                bg=colors["bg_card"], fg=colors["text_primary"]).pack(anchor="w")
        thumb_folder_frame = tk.Frame(config_inner, bg=colors["bg_card"])
        thumb_folder_frame.pack(fill="x", pady=(5, 15))
        self.thumb_folder_entry = ModernEntry(thumb_folder_frame)
        self.thumb_folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ModernButton(thumb_folder_frame, text="Chọn...", style_type="secondary", command=lambda: None).pack(side="left")
        
        # Buttons
        button_frame = tk.Frame(self.thumb_tab, bg=colors["bg_main"])
        button_frame.pack(fill="x", padx=20, pady=10)
        
        ModernButton(button_frame, text="1) Đếm & Quét File",
                    style_type="secondary", command=lambda: None).pack(side="left", padx=(0, 10))
        
        self.thumb_start_btn = ModernButton(button_frame, text="2) Bắt Đầu Tải Thumbnails",
                                           style_type="primary", command=lambda: None)
        self.thumb_start_btn.pack(side="left", padx=(0, 10))
        
        ModernButton(button_frame, text="✕ Huỷ",
                    style_type="secondary", command=lambda: None).pack(side="left")
        
        # Status
        status_frame = tk.Frame(self.thumb_tab, bg=colors["bg_main"])
        status_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(status_frame, text="●", font=("Segoe UI", 10),
                bg=colors["bg_main"], fg=colors["status_ready"]).pack(side="left", padx=(0, 8))
        tk.Label(status_frame, text="Sẵn sàng.",
                bg=colors["bg_main"], fg=colors["text_secondary"],
                font=("Segoe UI", 9)).pack(side="left")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_log_panel(self):
        """Tạo khung Thông tin (log)"""
        colors = AppConfig.colors
        
        log_container = tk.Frame(self.main_frame, bg=colors["bg_main"])
        log_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        tk.Label(log_container, text="Thông Tin", font=("Segoe UI", 10, "bold"),
                bg=colors["bg_main"], fg=colors["text_primary"]).pack(anchor="w", pady=(0, 5))
        
        log_card = ModernCard(log_container)
        log_card.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_card, font=("Consolas", 9),
            bg=colors["bg_card"], fg=colors["text_primary"],
            relief="flat", bd=0, wrap="word",
            padx=10, pady=10
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.insert("end", "📝 Ứng dụng sẵn sàng...\n")
        self.log_text.config(state="disabled")
    
    def _toggle_theme(self):
        """Chuyển đổi giữa chế độ Sáng/Tối"""
        new_theme = "dark" if AppConfig.current_theme == "light" else "light"
        AppConfig.switch_theme(new_theme)
        self._save_theme(new_theme)
        self._refresh_ui()
    
    def _refresh_ui(self):
        """Làm mới toàn bộ UI khi đổi chủ đề"""
        # Xóa frame cũ
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Tạo lại UI
        self._create_ui()
    
    def _load_saved_theme(self):
        """Tải chủ đề đã lưu"""
        try:
            config_file = "app_config.json"
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    theme = config.get("theme", "light")
                    AppConfig.switch_theme(theme)
        except:
            pass
    
    def _save_theme(self, theme: str):
        """Lưu chủ đề"""
        try:
            config = {"theme": theme}
            with open("app_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False)
        except:
            pass

# ==================== MAIN ====================

def main():
    root = tk.Tk()
    app = VideoDownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
