import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Sidebar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, width=200)
        
        # Cấu hình grid
        self.grid_rowconfigure(5, weight=1)  
        
        # Callback cho việc thay đổi trang
        self.page_change_callback = None
        
        # Thiết lập giao diện
        self.setup_ui()
        
        logger.info("Đã khởi tạo sidebar thành công")
    
    # Thiết lập giao diện sidebar
    def setup_ui(self):
        # Tiêu đề
        self.title_label = ctk.CTkLabel(
            self, 
            text="Hệ thống bãi giữ xe",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Đường kẻ phân cách
        self.separator = ctk.CTkFrame(self, height=2, fg_color="gray50")
        self.separator.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        
        # Các nút menu
        self.buttons = {}
        
        # Nút trang chủ
        self.buttons["home"] = ctk.CTkButton(
            self,
            text="Trang chủ",
            font=ctk.CTkFont(size=14),
            height=40,
            anchor="w",
            command=lambda: self.change_page("home")
        )
        self.buttons["home"].grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        # Nút quản lý xe vào/ra
        self.buttons["vehicle_inout"] = ctk.CTkButton(
            self,
            text="Quản lý xe vào/ra",
            font=ctk.CTkFont(size=14),
            height=40,
            anchor="w",
            command=lambda: self.change_page("vehicle_inout")
        )
        self.buttons["vehicle_inout"].grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        # Nút quản lý bãi đỗ xe
        self.buttons["parking_lot"] = ctk.CTkButton(
            self,
            text="Quản lý bãi đỗ xe",
            font=ctk.CTkFont(size=14),
            height=40,
            anchor="w",
            command=lambda: self.change_page("parking_lot")
        )
        self.buttons["parking_lot"].grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        
        # Nút quản lý thông tin xe
        self.buttons["vehicle_info"] = ctk.CTkButton(
            self,
            text="Quản lý thông tin xe",
            font=ctk.CTkFont(size=14),
            height=40,
            anchor="w",
            command=lambda: self.change_page("vehicle_info")
        )
        self.buttons["vehicle_info"].grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        # Khoảng trống
        self.spacer = ctk.CTkFrame(self, fg_color="transparent")
        self.spacer.grid(row=6, column=0, sticky="ew", padx=20, pady=5)
        
        # # Thông tin phiên bản
        # self.version_label = ctk.CTkLabel(
        #     self, 
        #     text="Phiên bản 1.0.0",
        #     font=ctk.CTkFont(size=12),
        #     text_color="gray70"
        # )
       # self.version_label.grid(row=7, column=0, padx=20, pady=(5, 20))
    
    # Thiết lập callback cho việc thay đổi trang
    def set_page_change_callback(self, callback):
        self.page_change_callback = callback
    
    # Thay đổi trang khi nhấn nút
    def change_page(self, page_name):
        if self.page_change_callback:
            self.page_change_callback(page_name)
    
    # Đặt trạng thái active cho nút được chọn
    def set_active_button(self, page_name):
        # Đặt lại màu cho tất cả các nút
        for name, button in self.buttons.items():
            if name == page_name:
                # Nút được chọn
                button.configure(
                    fg_color="#1f6aa5",  # Màu đậm hơn cho nút active
                    hover_color="#2a7dbf"
                )
            else:
                # Các nút khác
                button.configure(
                    fg_color="#3a7ebf",  # Màu mặc định
                    hover_color="#325882"
                )