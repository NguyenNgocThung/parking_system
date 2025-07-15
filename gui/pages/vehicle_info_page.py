import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import logging
import threading
from datetime import datetime
from database.database_manager import DatabaseManager

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VehicleInfoPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.db_manager = DatabaseManager()
        self.running = False
        self.update_thread = None
        self.stop_flag = threading.Event()
        self.setup_ui()
        logger.info("Đã khởi tạo trang quản lý thông tin xe")
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.title_label = ctk.CTkLabel(self, text="Quản lý thông tin xe", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Khung tìm kiếm và điều khiển
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Tìm kiếm
        self.search_frame = ctk.CTkFrame(self.control_frame)
        self.search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.search_label = ctk.CTkLabel(self.search_frame, text="Tìm kiếm:", font=ctk.CTkFont(size=14))
        self.search_label.pack(side="left", padx=10)
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Nhập biển số hoặc MSSV", width=200)
        self.search_entry.pack(side="left", padx=10)
        self.search_button = ctk.CTkButton(self.search_frame, text="Tìm", width=80, command=self.search_records)
        self.search_button.pack(side="left", padx=10)

        # Thêm sinh viên mới
        self.add_button = ctk.CTkButton(self.control_frame, text="Thêm sinh viên", width=120, command=self.show_add_dialog)
        self.add_button.grid(row=0, column=1, padx=10, pady=10)
        
        # Xóa sinh viên
        self.delete_button = ctk.CTkButton(self.control_frame, text="Xóa sinh viên", width=120, fg_color="#F44336", hover_color="#D32F2F", command=self.delete_student)
        self.delete_button.grid(row=0, column=2, padx=10, pady=10)
        
        # Bảng thông tin
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
        
        self.style = ttk.Style()
        self.style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=25, fieldbackground="#2b2b2b")
        self.style.map('Treeview', background=[('selected', '#347ab3')])
        self.style.configure("Treeview.Heading", 
                            background="#1f6aa5",
                            foreground="black",
                            relief="flat",
                            font=('Arial Black', 11, 'bold'))
        self.style.map("Treeview.Heading",
                      background=[('active', '#2a7dbf')],
                      foreground=[('active', 'white')])
        
        # Tạo frame cho bảng với thanh cuộn
        self.tree_container = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.tree_container.grid(row=0, column=0, sticky="nsew")
        self.tree_container.grid_columnconfigure(0, weight=1)
        self.tree_container.grid_rowconfigure(0, weight=1)
        
        # Tạo bảng
        self.tree = ttk.Treeview(self.tree_container, style="Treeview")
        
        # Thanh cuộn
        self.scrollbar_y = ctk.CTkScrollbar(self.tree_container, orientation="vertical", command=self.tree.yview)
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.scrollbar_x = ctk.CTkScrollbar(self.tree_container, orientation="horizontal", command=self.tree.xview)
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Định nghĩa các cột
        self.tree["columns"] = ("student_id", "full_name", "license_plate", "entry_time", "exit_time")
        self.tree.column("#0", width=50, minwidth=50, anchor="center")
        self.tree.column("student_id", width=120, minwidth=120, anchor="center")
        self.tree.column("full_name", width=180, minwidth=180, anchor="center")
        self.tree.column("license_plate", width=120, minwidth=120, anchor="center")
        self.tree.column("entry_time", width=150, minwidth=150, anchor="center")
        self.tree.column("exit_time", width=150, minwidth=150, anchor="center")
        
        # Định nghĩa tiêu đề cột
        self.tree.heading("#0", text="STT")
        self.tree.heading("student_id", text="MSSV")
        self.tree.heading("full_name", text="Họ tên sinh viên")
        self.tree.heading("license_plate", text="Biển số")
        self.tree.heading("entry_time", text="Thời gian vào")
        self.tree.heading("exit_time", text="Thời gian ra")
        
        # Bind sự kiện double-click
        self.tree.bind("<Double-1>", self.on_tree_double_click)
    
    def on_enter(self):
        self.stop_flag.clear()
        self.running = True
        self.update_table()
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Đã vào trang quản lý thông tin xe")
    
    def on_leave(self):
        self.running = False
        self.stop_flag.set()
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
            self.update_thread = None
        logger.info("Đã rời khỏi trang quản lý thông tin xe")
    
    def update_loop(self):
        while self.running and not self.stop_flag.is_set():
            try:
                self.stop_flag.wait(timeout=5.0)
                if not self.stop_flag.is_set():
                    self.after(0, self.update_table)
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp cập nhật: {e}")
    
    def update_table(self, filter_by=None):
        try:
            # Xóa dữ liệu cũ
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Lấy dữ liệu mới
            logs = self.db_manager.get_vehicle_logs(filter_by=filter_by, limit=100)
            for i, log in enumerate(logs, 1):
                student_id = log['student_id'] if log['student_id'] else "N/A"
                full_name = log['full_name'] if log['full_name'] else "N/A"
                license_plate = log['license_plate']
                entry_time = log['entry_time'] if log['entry_time'] else "N/A"
                exit_time = log['exit_time'] if log['exit_time'] else ""
                
                self.tree.insert("", "end", text=str(i), values=(
                    student_id, full_name, license_plate, entry_time, exit_time
                ))
            
            if not logs:
                if filter_by:
                    logger.info("Không tìm thấy kết quả phù hợp với điều kiện lọc")
                else:
                    logger.info("Không có dữ liệu")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật bảng: {e}")
    
    def search_records(self):
        search_text = self.search_entry.get().strip()
        if not search_text:
            self.update_table()
            return
        
        if search_text.isdigit():
            filter_by = {'student_id': search_text}
        else:
            filter_by = {'license_plate': search_text}
        self.update_table(filter_by)
    
    def show_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Thêm sinh viên mới")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Thông tin sinh viên mới", font=ctk.CTkFont(size=18, weight="bold")).pack(padx=20, pady=(20, 10))
        
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        form_frame.pack(fill="both", padx=20, pady=10, expand=True)
        
        ctk.CTkLabel(form_frame, text="MSSV:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        student_id_entry = ctk.CTkEntry(form_frame, width=300)
        student_id_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(form_frame, text="Họ tên:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        full_name_entry = ctk.CTkEntry(form_frame, width=300)
        full_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(form_frame, text="Biển số xe:", font=ctk.CTkFont(size=14)).grid(row=2, column=0, padx=10, pady=5, sticky="e")
        license_plate_entry = ctk.CTkEntry(form_frame, width=300)
        license_plate_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(padx=20, pady=10, fill="x")
        
        def add_student():
            student_id = student_id_entry.get().strip()
            full_name = full_name_entry.get().strip()
            license_plate = license_plate_entry.get().strip().upper()
            
            if not student_id or not full_name:
                self.show_error("MSSV và họ tên không được để trống!")
                return
            
            if self.db_manager.add_student(student_id, full_name, license_plate):
                self.show_info("Đã thêm sinh viên thành công!")
                dialog.destroy()
                self.update_table()
            else:
                self.show_error("Không thể thêm sinh viên. Vui lòng kiểm tra lại thông tin!")
        
        ctk.CTkButton(button_frame, text="Thêm", width=100, command=add_student).pack(side="left", padx=10, pady=10, expand=True)
        ctk.CTkButton(button_frame, text="Hủy", width=100, fg_color="#F44336", hover_color="#D32F2F", command=dialog.destroy).pack(side="left", padx=10, pady=10, expand=True)
    
    def on_tree_double_click(self, event):
        # Kiểm tra xem có item nào được chọn không
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, "values")
        student_id = values[0]
        
        if student_id != "N/A":
            self.show_edit_dialog(student_id, values)
        else:
            self.show_error("Không thể chỉnh sửa thông tin xe không có MSSV!")
    
    def show_edit_dialog(self, student_id, values):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Chỉnh sửa thông tin sinh viên")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        full_name = values[1] if values[1] != "N/A" else ""
        license_plate = values[2] if values[2] != "N/A" else ""
        
        ctk.CTkLabel(dialog, text=f"Chỉnh sửa thông tin sinh viên: {student_id}", font=ctk.CTkFont(size=18, weight="bold")).pack(padx=20, pady=(20, 10))
        
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        form_frame.pack(fill="both", padx=20, pady=10, expand=True)

        ctk.CTkLabel(form_frame, text="Họ tên:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        full_name_entry = ctk.CTkEntry(form_frame, width=300)
        full_name_entry.insert(0, full_name)
        full_name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(form_frame, text="Biển số xe:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        license_plate_entry = ctk.CTkEntry(form_frame, width=300)
        license_plate_entry.insert(0, license_plate)
        license_plate_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(padx=20, pady=10, fill="x")
        
        def update_student():
            new_full_name = full_name_entry.get().strip()
            new_license_plate = license_plate_entry.get().strip().upper()
            
            if not new_full_name:
                self.show_error("Họ tên không được để trống!")
                return
            
            if self.db_manager.update_student(student_id, full_name=new_full_name, license_plate=new_license_plate):
                self.show_info("Đã cập nhật thông tin sinh viên thành công!")
                dialog.destroy()
                self.update_table()
            else:
                self.show_error("Không thể cập nhật thông tin sinh viên!")

        ctk.CTkButton(button_frame, text="Cập nhật", width=100, command=update_student).pack(side="left", padx=10, pady=10, expand=True)
        ctk.CTkButton(button_frame, text="Hủy", width=100, fg_color="#F44336", hover_color="#D32F2F", command=dialog.destroy).pack(side="left", padx=10, pady=10, expand=True)
    
    def delete_student(self):
        selection = self.tree.selection()
        if not selection:
            self.show_error("Vui lòng chọn một sinh viên để xóa!")
            return
        
        item = selection[0]
        values = self.tree.item(item, "values")
        student_id = values[0]
        
        if student_id != "N/A":
            if self.show_confirm(f"Bạn có chắc chắn muốn xóa sinh viên {student_id}?"):
                if self.db_manager.delete_student(student_id):
                    self.show_info(f"Đã xóa sinh viên {student_id}!")
                    self.update_table()
                else:
                    self.show_error("Không thể xóa sinh viên!")
        else:
            self.show_error("Không thể xóa sinh viên không có MSSV!")
    
    def show_error(self, message):
        from tkinter import messagebox
        messagebox.showerror("Lỗi", message)
    
    def show_info(self, message):
        from tkinter import messagebox
        messagebox.showinfo("Thông báo", message)
    
    def show_confirm(self, message):
        from tkinter import messagebox
        return messagebox.askyesno("Xác nhận", message)