import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import logging
import threading
import time
import openpyxl as px
from datetime import datetime
import pandas as pd  

from database.database_manager import DatabaseManager
from my_parking.statistics import ParkingStatistics

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HomePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # Khởi tạo database manager
        self.db_manager = DatabaseManager()
        
        # Khởi tạo thống kê
        self.stats = ParkingStatistics(self.db_manager)
        
        # Trạng thái chạy
        self.running = False
        self.update_thread = None
        self.stop_flag = threading.Event()
        
        # Store current data for export
        self.current_export_data = []
        
        # Khởi tạo UI
        self.setup_ui()
        
        logger.info("Đã khởi tạo trang chủ")
    
    def setup_ui(self):
        """
        Thiết lập giao diện trang chủ theo layout mới
        """
        # Cấu hình grid chính
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Phần trên
        self.grid_rowconfigure(2, weight=1)  # Phần dưới
        
        # Tiêu đề
        self.title_label = ctk.CTkLabel(
            self, 
            text="Trang chủ",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # PHẦN TRÊN - Chia 2 cột
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.top_frame.grid_columnconfigure(0, weight=1)  # Cột trái
        self.top_frame.grid_columnconfigure(1, weight=2)  # Cột phải rộng hơn
        self.top_frame.grid_rowconfigure(0, weight=1)
        
        # CỘT TRÁI - 2 thẻ thống kê
        self.left_stats_frame = ctk.CTkFrame(self.top_frame)
        self.left_stats_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.left_stats_frame.grid_columnconfigure(0, weight=1)
        self.left_stats_frame.grid_rowconfigure(0, weight=1)
        self.left_stats_frame.grid_rowconfigure(1, weight=1)
        
        # Thẻ 1: Tổng số xe hiện tại
        self.current_vehicles_frame = ctk.CTkFrame(self.left_stats_frame)
        self.current_vehicles_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        
        self.current_vehicles_title = ctk.CTkLabel(
            self.current_vehicles_frame,
            text="Tổng số xe hiện tại",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.current_vehicles_title.pack(pady=(15, 5))
        
        self.current_vehicles_count = ctk.CTkLabel(
            self.current_vehicles_frame,
            text="0",
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color="#4CAF50"
        )
        self.current_vehicles_count.pack(expand=True)
        
        # Thẻ 2: Tổng vị trí trống
        self.free_spots_frame = ctk.CTkFrame(self.left_stats_frame)
        self.free_spots_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        
        self.free_spots_title = ctk.CTkLabel(
            self.free_spots_frame,
            text="Tổng vị trí trống",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.free_spots_title.pack(pady=(15, 5))
        
        self.free_spots_count = ctk.CTkLabel(
            self.free_spots_frame,
            text="0 / 0",
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color="#2196F3"
        )
        self.free_spots_count.pack(expand=True)
        
        # CỘT PHẢI - Biểu đồ thống kê
        self.chart_section = ctk.CTkFrame(self.top_frame)
        self.chart_section.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        self.chart_section.grid_columnconfigure(0, weight=1)
        self.chart_section.grid_rowconfigure(1, weight=1)  # Khu vực biểu đồ mở rộng
        
        # Header biểu đồ với tiêu đề và radio buttons
        self.chart_header = ctk.CTkFrame(self.chart_section, fg_color="transparent")
        self.chart_header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        self.chart_header.grid_columnconfigure(0, weight=1)
        
        self.chart_title = ctk.CTkLabel(
            self.chart_header,
            text="Biểu đồ thống kê",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.chart_title.grid(row=0, column=0, sticky="w")
        
        # Radio buttons cho lựa chọn thời gian - ĐÃ SỬA: Thêm callback để cập nhật tất cả
        self.stats_period_var = tk.StringVar(value="day")
        self.period_frame = ctk.CTkFrame(self.chart_header, fg_color="transparent")
        self.period_frame.grid(row=0, column=1, sticky="e")
        
        self.day_radio = ctk.CTkRadioButton(
            self.period_frame,
            text="Ngày",
            variable=self.stats_period_var,
            value="day",
            command=self.update_all_content  # Thay đổi callback
        )
        self.day_radio.pack(side="left", padx=5)
        
        self.week_radio = ctk.CTkRadioButton(
            self.period_frame,
            text="Tuần",
            variable=self.stats_period_var,
            value="week",
            command=self.update_all_content  # Thay đổi callback
        )
        self.week_radio.pack(side="left", padx=5)
        
        self.month_radio = ctk.CTkRadioButton(
            self.period_frame,
            text="Tháng",
            variable=self.stats_period_var,
            value="month",
            command=self.update_all_content  # Thay đổi callback
        )
        self.month_radio.pack(side="left", padx=5)
        
        # Khu vực hiển thị biểu đồ - mở rộng toàn bộ không gian còn lại
        self.chart_frame = ctk.CTkFrame(self.chart_section)
        self.chart_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.chart_frame.configure(height=320, width=650)
        
        self.chart_label = ctk.CTkLabel(
            self.chart_frame,
            text="Đang tải biểu đồ...",
            font=ctk.CTkFont(size=14)
        )
        self.chart_label.pack(expand=True)
        
        # PHẦN DƯỚI - Danh sách thống kê (mở rộng toàn bộ không gian còn lại)
        self.table_section = ctk.CTkFrame(self)
        self.table_section.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.table_section.grid_columnconfigure(0, weight=1)
        self.table_section.grid_rowconfigure(1, weight=1)
        
        # Header cho bảng với tiêu đề và nút Export Excel
        self.table_header = ctk.CTkFrame(self.table_section, fg_color="transparent")
        self.table_header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        self.table_header.grid_columnconfigure(0, weight=1)
        
        # Tiêu đề bảng
        self.table_title = ctk.CTkLabel(
            self.table_header,
            text="Danh sách thống kê",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.table_title.grid(row=0, column=0, sticky="w")
        
        # Nút Export Excel
        self.export_button = ctk.CTkButton(
            self.table_header,
            text="📊 Xuất Excel",
            font=ctk.CTkFont(size=14),
            width=120,
            height=32,
            fg_color="#28a745",
            hover_color="#218838",
            command=self.export_to_excel
        )
        self.export_button.grid(row=0, column=1, sticky="e", padx=10)
        
        # Styling cho Treeview
        self.style = ttk.Style()
        self.style.configure("Treeview", 
                            background="#2b2b2b",
                            foreground="white",
                            rowheight=25,
                            fieldbackground="#2b2b2b")
        self.style.map('Treeview', background=[('selected', '#347ab3')])
        self.style.configure("Treeview.Heading", 
                            background="#2a6496", 
                            foreground="white", 
                            relief="flat")
        
        # Frame chứa bảng với scrollbars đầy đủ
        self.tree_frame = ctk.CTkFrame(self.table_section, fg_color="transparent")
        self.tree_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)
        
        # Tạo Treeview
        self.tree = ttk.Treeview(self.tree_frame, style="Treeview")
        
        # Định nghĩa các cột - bỏ cột parking_spot
        self.tree["columns"] = ("license_plate", "student_name", "student_id", "entry_time", "exit_time")
        self.tree.column("#0", width=50, minwidth=50, anchor="center")
        self.tree.column("license_plate", width=120, minwidth=120, anchor="center")
        self.tree.column("student_name", width=180, minwidth=180, anchor="center")
        self.tree.column("student_id", width=120, minwidth=120, anchor="center")
        self.tree.column("entry_time", width=150, minwidth=150, anchor="center")
        self.tree.column("exit_time", width=150, minwidth=150, anchor="center")
        
        # Định nghĩa tiêu đề cột - bỏ cột parking_spot
        self.tree.heading("#0", text="STT")
        self.tree.heading("license_plate", text="Biển số")
        self.tree.heading("student_name", text="Họ tên sinh viên")
        self.tree.heading("student_id", text="MSSV")
        self.tree.heading("entry_time", text="Thời gian vào")
        self.tree.heading("exit_time", text="Thời gian ra")
        
        # Scrollbars đầy đủ
        self.scrollbar_y = ctk.CTkScrollbar(self.tree_frame, orientation="vertical", command=self.tree.yview)
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        
        self.scrollbar_x = ctk.CTkScrollbar(self.tree_frame, orientation="horizontal", command=self.tree.xview)
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        self.tree.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
    
    def export_to_excel(self):
        """
        Xuất dữ liệu bảng hiện tại ra file Excel
        """
        try:
            # Kiểm tra xem có dữ liệu để xuất không
            if not self.current_export_data:
                messagebox.showwarning("Cảnh báo", "Không có dữ liệu để xuất!")
                return
            
            # Mở dialog chọn nơi lưu file
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            period = self.stats_period_var.get()
            period_text = {"day": "Ngay", "week": "Tuan", "month": "Thang"}[period]
            
            default_filename = f"BaoCao_BaiXe_{period_text}_{current_time}.xlsx"
            
            file_path = filedialog.asksaveasfilename(
                title="Lưu file Excel",
                defaultextension=".xlsx",
                initialfile=default_filename,
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            if not file_path:
                return  # Người dùng hủy
            
            # Tạo DataFrame từ dữ liệu hiện tại
            df = pd.DataFrame(self.current_export_data)
            
            # Đổi tên cột sang tiếng Việt
            df.columns = ["STT", "Biển số", "Họ tên sinh viên", "MSSV", "Thời gian vào", "Thời gian ra"]
            
            # Thêm thông tin metadata
            period_name = {"day": "Theo ngày", "week": "Theo tuần", "month": "Theo tháng"}[period]
            export_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            # Tạo Excel writer với nhiều sheet
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Sheet chính với dữ liệu
                df.to_excel(writer, sheet_name='Dữ liệu', index=False)
                
                # Sheet thống kê tổng hợp
                summary_data = {
                    'Thông tin': [
                        'Thời gian xuất báo cáo',
                        'Loại báo cáo',
                        'Tổng số bản ghi',
                        'Số xe vào',
                        'Số xe ra',
                        'Số xe hiện tại trong bãi'
                    ],
                    'Giá trị': [
                        export_time,
                        period_name,
                        len(df),
                        len(df[df['Thời gian ra'].notna()]),
                        len(df[df['Thời gian ra'].isna()]),
                        len(df[df['Thời gian ra'].isna()])
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Thống kê', index=False)
                
                # Định dạng Excel
                workbook = writer.book
                
                # Định dạng sheet dữ liệu
                worksheet = workbook['Dữ liệu']
                worksheet.auto_filter.ref = worksheet.dimensions
                
                # Định dạng header
                for cell in worksheet[1]:
                    cell.font = cell.font.copy(bold=True)
                    cell.fill = cell.fill.copy(fgColor="366092")
                
                # Định dạng sheet thống kê
                summary_worksheet = workbook['Thống kê']
                for cell in summary_worksheet[1]:
                    cell.font = cell.font.copy(bold=True)
                    cell.fill = cell.fill.copy(fgColor="28a745")
            
            # Thông báo thành công
            messagebox.showinfo(
                "Thành công", 
                f"Đã xuất {len(df)} bản ghi ra file Excel thành công!\n\nFile được lưu tại:\n{file_path}"
            )
            
            logger.info(f"Đã xuất {len(df)} bản ghi ra file Excel: {file_path}")
            
        except ImportError:
            messagebox.showerror(
                "Lỗi", 
                "Không tìm thấy thư viện pandas hoặc openpyxl!\n\nVui lòng cài đặt:\npip install pandas openpyxl"
            )
        except Exception as e:
            logger.error(f"Lỗi khi xuất Excel: {e}")
            messagebox.showerror("Lỗi", f"Có lỗi xảy ra khi xuất file Excel:\n{str(e)}")
    
    def on_enter(self):
        """
        Được gọi khi trang được hiển thị
        """
        self.running = True
        self.stop_flag.clear()
        
        # Khởi động thread cập nhật
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        
        # Cập nhật ngay lập tức tất cả nội dung
        self.update_all_content()
        
        logger.info("Đã vào trang chủ")
    
    def on_leave(self):
        """
        Được gọi khi rời khỏi trang
        """
        self.running = False
        self.stop_flag.set()
        
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
            self.update_thread = None
        
        logger.info("Đã rời khỏi trang chủ")
    
    def update_loop(self):
        """
        Vòng lặp cập nhật dữ liệu
        """
        while self.running and not self.stop_flag.is_set():
            try:
                # Cập nhật nội dung trang (chỉ cập nhật "Tổng vị trí trống", không cập nhật theo period)
                self.update_static_content()
                
                # Đợi 5 giây hoặc cho đến khi stop_flag được đặt
                self.stop_flag.wait(timeout=5.0)
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp cập nhật: {e}")
    
    def update_static_content(self):
        """
        Cập nhật nội dung tĩnh (chỉ tổng vị trí trống)
        """
        try:
            # Lấy thống kê tổng hợp
            summary = self.stats.get_summary_statistics()
            
            # Chỉ cập nhật "Tổng vị trí trống" (không phụ thuộc vào period)
            self.free_spots_count.configure(
                text=f"{summary['free_spots']} / {summary['total_spots']}"
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật nội dung tĩnh: {e}")
    
    def update_all_content(self):
        """
        Cập nhật tất cả nội dung theo period được chọn
        """
        try:
            period = self.stats_period_var.get()
            
            # Cập nhật "Tổng số xe hiện tại" theo period
            current_vehicles = self.get_current_vehicles_by_period(period)
            self.current_vehicles_count.configure(text=str(current_vehicles))
            
            # Cập nhật "Tổng vị trí trống" (không thay đổi theo period)
            summary = self.stats.get_summary_statistics()
            self.free_spots_count.configure(
                text=f"{summary['free_spots']} / {summary['total_spots']}"
            )
            
            # Cập nhật bảng dữ liệu theo period
            self.update_table_by_period(period)
            
            # Cập nhật biểu đồ theo period
            self.update_chart()
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật tất cả nội dung: {e}")
    
    def get_current_vehicles_by_period(self, period):
        """
        Lấy số lượng xe theo period được chọn
        """
        try:
            if period == "day":
                # Số xe vào trong ngày hôm nay
                return self.db_manager.get_vehicles_count_by_period("day")
            elif period == "week":
                # Số xe vào trong tuần này
                return self.db_manager.get_vehicles_count_by_period("week")
            elif period == "month":
                # Số xe vào trong tháng này
                return self.db_manager.get_vehicles_count_by_period("month")
            else:
                return 0
        except Exception as e:
            logger.error(f"Lỗi khi lấy số xe theo period: {e}")
            return 0
    
    def update_chart(self):
        """
        Cập nhật biểu đồ thống kê
        """
        try:
            # Lấy khoảng thời gian được chọn
            period = self.stats_period_var.get()
            
            # Hiển thị thông báo đang tải
            self.chart_label.configure(text="Đang tải biểu đồ...")
            
            # Xóa widget hình ảnh cũ nếu có
            for widget in self.chart_frame.winfo_children():
                if widget != self.chart_label:
                    widget.destroy()
            
            # Tạo biểu đồ trong thread riêng để không làm đứng UI
            def generate_chart():
                try:
                    # Tạo biểu đồ tương ứng
                    if period == "day":
                        chart_data = self.stats.generate_daily_chart()
                    elif period == "week":
                        chart_data = self.stats.generate_weekly_chart()
                    else:  # month
                        chart_data = self.stats.generate_monthly_chart()
                    
                    if chart_data:
                        # Chuyển đổi base64 thành hình ảnh
                        import base64
                        from io import BytesIO
                        
                        image_data = base64.b64decode(chart_data)
                        image = Image.open(BytesIO(image_data))
                        
                        # Điều chỉnh kích thước
                        # max_width = self.chart_frame.winfo_width() - 20
                        # max_height = self.chart_frame.winfo_height() - 20
                        
                        # if max_width > 0 and max_height > 0:
                        #     image = self.resize_image(image, max_width, max_height)
                        
                        fixed_width = 600   # Chiều rộng cố định
                        fixed_height = 300  # Chiều cao cố định
                        image = image.resize((fixed_width, fixed_height), Image.LANCZOS)

                        # Hiển thị trên UI
                        photo = ImageTk.PhotoImage(image)
                        
                        # Cập nhật UI trong main thread
                        self.after(0, lambda: self.display_chart(photo))
                    else:
                        # Hiển thị thông báo lỗi
                        self.after(0, lambda: self.chart_label.configure(
                            text="Không thể tạo biểu đồ. Vui lòng thử lại sau."
                        ))
                except Exception as e:
                    logger.error(f"Lỗi khi tạo biểu đồ: {e}")
                    self.after(0, lambda: self.chart_label.configure(
                        text=f"Lỗi khi tạo biểu đồ: {e}"
                    ))
            
            # Khởi động thread tạo biểu đồ
            chart_thread = threading.Thread(target=generate_chart, daemon=True)
            chart_thread.start()
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật biểu đồ: {e}")
            self.chart_label.configure(text=f"Lỗi khi cập nhật biểu đồ: {e}")
    
    def display_chart(self, photo):
        """
        Hiển thị biểu đồ lên UI
        """
        # Xóa thông báo đang tải
        self.chart_label.configure(text="")
        
        # Tạo và hiển thị label chứa hình ảnh
        image_label = tk.Label(self.chart_frame, image=photo, bg="#2b2b2b")
        image_label.image = photo  # Giữ tham chiếu để tránh bị thu gom rác
        # image_label.pack(expand=True, fill="both", padx=10, pady=10)
        image_label.place(relx=0.5, rely=0.5, anchor="center")

    # def resize_image(self, image, max_width, max_height):
    #     """
    #     Điều chỉnh kích thước hình ảnh
    #     """
    #     width, height = image.size
        
    #     # Tính tỷ lệ để giữ tỷ lệ khung hình
    #     width_ratio = max_width / width
    #     height_ratio = max_height / height
    #     ratio = min(width_ratio, height_ratio)
        
    #     new_width = int(width * ratio)
    #     new_height = int(height * ratio)
        
    #     return image.resize((new_width, new_height), Image.LANCZOS)
    
    def update_table_by_period(self, period):
        """
        Cập nhật bảng dữ liệu theo period được chọn
        """
        try:
            # Xóa dữ liệu cũ
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Reset export data
            self.current_export_data = []
            
            # Lấy dữ liệu theo period
            if period == "day":
                filter_by = {'date': datetime.now().strftime('%Y-%m-%d')}
            elif period == "week":
                # Lấy dữ liệu 7 ngày gần nhất
                logs = self.db_manager.get_vehicle_logs_by_period("week", limit=50)
            elif period == "month":
                # Lấy dữ liệu tháng hiện tại
                logs = self.db_manager.get_vehicle_logs_by_period("month", limit=50)
            else:
                logs = []
            
            # Nếu là "day", sử dụng filter_by
            if period == "day":
                logs = self.db_manager.get_vehicle_logs(filter_by=filter_by, limit=50)
            
            # Thêm dữ liệu mới vào bảng và chuẩn bị cho export
            for i, log in enumerate(logs, 1):
                license_plate = log['license_plate']
                student_name = log['full_name'] if log['full_name'] else "N/A"
                student_id = log['student_id'] if log['student_id'] else "N/A"
                entry_time = log['entry_time'] if log['entry_time'] else "N/A"
                exit_time = log['exit_time'] if log['exit_time'] else ""
                
                # Thêm vào table
                self.tree.insert("", "end", text=str(i), values=(
                    license_plate, student_name, student_id, entry_time, exit_time
                ))
                
                # Lưu dữ liệu cho export
                self.current_export_data.append([
                    i, license_plate, student_name, student_id, entry_time, exit_time
                ])
            
        except Exception as e:  
            logger.error(f"Lỗi khi cập nhật bảng theo period: {e}")
    
    def update_table(self):
        """
        Cập nhật bảng dữ liệu (sử dụng period hiện tại)
        """
        period = self.stats_period_var.get()
        self.update_table_by_period(period)