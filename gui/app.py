import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
import logging
from gui.sidebar import Sidebar
from gui.pages import HomePage, VehicleInOutPage, ParkingLotPage, VehicleInfoPage
from config import UI_CONFIG

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình CustomTkinter
ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue")  

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Cấu hình cửa sổ
        self.title(UI_CONFIG['title'])
        self.geometry(f"{UI_CONFIG['width']}x{UI_CONFIG['height']}")
        self.minsize(800, 600)
        self.grid_columnconfigure(1, weight=1)  # Cột nội dung chính mở rộng
        self.grid_rowconfigure(0, weight=1)  # Hàng duy nhất mở rộng
        self.sidebar = Sidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.pages = {}
        self.current_page = None
        self.initialize_pages()
        self.show_page("home")  # Hiển thị trang mặc định (trang chủ)
        self.sidebar.set_page_change_callback(self.show_page) # Thiết lập sự kiện chuyển trang từ sidebar
        logger.info("Đã khởi tạo ứng dụng GUI thành công")
    
    # Khởi tạo các trang
    def initialize_pages(self):
        self.pages["home"] = HomePage(self)
        self.pages["home"].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.pages["vehicle_inout"] = VehicleInOutPage(self)
        self.pages["vehicle_inout"].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.pages["parking_lot"] = ParkingLotPage(self)
        self.pages["parking_lot"].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.pages["vehicle_info"] = VehicleInfoPage(self)
        self.pages["vehicle_info"].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        for page in self.pages.values():
            page.grid_remove()
    
    # Hiển thị trang tương ứng
    def show_page(self, page_name):
        if page_name in self.pages:
            # Ẩn trang hiện tại
            if self.current_page:
                self.current_page.on_leave()
                self.current_page.grid_remove()
            
            # Hiển thị trang mới
            self.current_page = self.pages[page_name]
            self.current_page.grid()
            self.current_page.on_enter()
            
            # Cập nhật trạng thái nút trong sidebar
            self.sidebar.set_active_button(page_name)
            logger.info(f"Đã chuyển sang trang: {page_name}")
        else:
            logger.error(f"Không tìm thấy trang: {page_name}")