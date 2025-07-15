import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from io import BytesIO
import base64

# Cấu hình Matplotlib để sử dụng với Tkinter
matplotlib.use('Agg')  # Use Agg backend

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParkingStatistics:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def generate_daily_chart(self):
        """
        Tạo biểu đồ thống kê theo giờ trong ngày
        """
        try:
            # Lấy dữ liệu thống kê từ cơ sở dữ liệu
            stats = self.db_manager.get_statistics(period='day')
            
            # Chuyển đổi dữ liệu sang định dạng phù hợp
            hours = []
            entries = []
            exits = []
            
            for row in stats:
                hours.append(f"{row['hour']}h")
                entries.append(row['entries'])
                exits.append(row['exits'])
            
            # Nếu không có dữ liệu, tạo dữ liệu mẫu
            if not hours:
                hours = [f"{i}h" for i in range(24)]
                entries = [0] * 24
                exits = [0] * 24
            
            # Vẽ biểu đồ
            fig, ax = plt.subplots(figsize=(10, 6))
            
            x = np.arange(len(hours))
            width = 0.35
            
            ax.bar(x - width/2, entries, width, label='Xe vào', color='#4CAF50')
            ax.bar(x + width/2, exits, width, label='Xe ra', color='#F44336')
            
            ax.set_title('Thống kê xe ra vào theo giờ trong ngày')
            ax.set_xlabel('Giờ')
            ax.set_ylabel('Số lượng xe')
            ax.set_xticks(x)
            ax.set_xticklabels(hours, rotation=45)
            ax.legend()
            
            # ĐÃ SỬA: Force trục Y hiển thị số nguyên
            max_value = max(max(entries) if entries else 0, max(exits) if exits else 0)
            if max_value == 0:
                ax.set_ylim(0, 5)  # Nếu không có dữ liệu, set range 0-5
            else:
                ax.set_ylim(0, max_value + 1)  # Thêm 1 để có khoảng trống trên top
            
            # Force ticks là số nguyên
            ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
            
            plt.tight_layout()
            
            # Chuyển biểu đồ thành hình ảnh
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            image_data = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            return image_data
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ thống kê theo ngày: {e}")
            return None
    
    def generate_weekly_chart(self):
        """
        Tạo biểu đồ thống kê theo ngày trong tuần
        """
        try:
            # Lấy dữ liệu thống kê từ cơ sở dữ liệu
            stats = self.db_manager.get_statistics(period='week')
            
            # Chuyển đổi dữ liệu sang định dạng phù hợp
            days = []
            entries = []
            exits = []
            
            # Tên các ngày trong tuần
            day_names = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']
            
            # Khởi tạo dữ liệu mặc định
            default_entries = [0] * 7
            default_exits = [0] * 7
            
            # Điền dữ liệu từ cơ sở dữ liệu
            for row in stats:
                day_idx = int(row['day_of_week'])
                default_entries[day_idx] = row['entries']
                default_exits[day_idx] = row['exits']
            
            # Vẽ biểu đồ
            fig, ax = plt.subplots(figsize=(10, 6))
            
            x = np.arange(len(day_names))
            width = 0.35
            
            ax.bar(x - width/2, default_entries, width, label='Xe vào', color='#4CAF50')
            ax.bar(x + width/2, default_exits, width, label='Xe ra', color='#F44336')
            
            ax.set_title('Thống kê xe ra vào theo ngày trong tuần')
            ax.set_xlabel('Ngày')
            ax.set_ylabel('Số lượng xe')
            ax.set_xticks(x)
            ax.set_xticklabels(day_names)
            ax.legend()
            
            # ĐÃ SỬA: Force trục Y hiển thị số nguyên
            max_value = max(max(default_entries), max(default_exits))
            if max_value == 0:
                ax.set_ylim(0, 5)  # Nếu không có dữ liệu, set range 0-5
            else:
                ax.set_ylim(0, max_value + 1)  # Thêm 1 để có khoảng trống trên top
            
            # Force ticks là số nguyên
            ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
            
            plt.tight_layout()
            
            # Chuyển biểu đồ thành hình ảnh
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            image_data = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            return image_data
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ thống kê theo tuần: {e}")
            return None
    
    def generate_monthly_chart(self):
        """
        Tạo biểu đồ thống kê theo ngày trong tháng
        """
        try:
            # Lấy dữ liệu thống kê từ cơ sở dữ liệu
            stats = self.db_manager.get_statistics(period='month')
            
            # Chuyển đổi dữ liệu sang định dạng phù hợp
            days = []
            entries = []
            exits = []
            
            # Xác định số ngày trong tháng hiện tại
            now = datetime.now()
            _, days_in_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1).month, now.day
            
            # Khởi tạo dữ liệu mặc định
            days = [str(i) for i in range(1, days_in_month + 1)]
            default_entries = [0] * days_in_month
            default_exits = [0] * days_in_month
            
            # Điền dữ liệu từ cơ sở dữ liệu
            for row in stats:
                day_idx = int(row['day']) - 1  # Chuyển từ 1-31 sang 0-30
                if 0 <= day_idx < days_in_month:
                    default_entries[day_idx] = row['entries']
                    default_exits[day_idx] = row['exits']
            
            # Vẽ biểu đồ
            fig, ax = plt.subplots(figsize=(12, 6))
            
            x = np.arange(len(days))
            width = 0.35
            
            ax.bar(x - width/2, default_entries, width, label='Xe vào', color='#4CAF50')
            ax.bar(x + width/2, default_exits, width, label='Xe ra', color='#F44336')
            
            ax.set_title(f'Thống kê xe ra vào theo ngày trong tháng {now.month}/{now.year}')
            ax.set_xlabel('Ngày')
            ax.set_ylabel('Số lượng xe')
            ax.set_xticks(x[::2])  # Chỉ hiển thị mỗi ngày thứ 2 để tránh quá đông
            ax.set_xticklabels(days[::2])
            ax.legend()
            
            # ĐÃ SỬA: Force trục Y hiển thị số nguyên
            max_value = max(max(default_entries), max(default_exits))
            if max_value == 0:
                ax.set_ylim(0, 5)  # Nếu không có dữ liệu, set range 0-5
            else:
                ax.set_ylim(0, max_value + 1)  # Thêm 1 để có khoảng trống trên top
            
            # Force ticks là số nguyên
            ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
            
            plt.tight_layout()
            
            # Chuyển biểu đồ thành hình ảnh
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            image_data = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            return image_data
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ thống kê theo tháng: {e}")
            return None
    
    def get_summary_statistics(self):
        """
        Lấy thống kê tổng hợp
        """
        try:
            # Tổng số xe hiện tại
            current_vehicles = self.db_manager.get_current_vehicles()
            
            # Tổng số vị trí đỗ xe
            total_spots = self.db_manager.get_total_spots()
            
            # Số vị trí trống
            free_spots = len(self.db_manager.get_available_spots())
            
            # Tỷ lệ lấp đầy
            occupancy_rate = ((total_spots - free_spots) / total_spots) * 100 if total_spots > 0 else 0
            
            # Trả về tổng hợp thống kê
            return {
                'current_vehicles': current_vehicles,
                'total_spots': total_spots,
                'free_spots': free_spots,
                'occupancy_rate': occupancy_rate
            }
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy thống kê tổng hợp: {e}")
            return {
                'current_vehicles': 0,
                'total_spots': 0,
                'free_spots': 0,
                'occupancy_rate': 0
            }