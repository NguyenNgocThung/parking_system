import os
import sqlite3
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path='database/parking_system.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def normalize_license_plate(self, raw_text):
        if not raw_text or raw_text.strip() == "":
            return ""
        clean_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        match = re.match(r'^(\d{2})([A-Z]{1,2})(.+)$', clean_text)
        if match:
            area_code = match.group(1)      # 54, 29, 69
            letter_code = match.group(2)    # L, B, AL
            remaining = match.group(3)      # 19999, 125662, 01469
            if len(letter_code) == 1 and remaining and remaining[0] in '123456789':
                letter_code += remaining[0]  # L1, B1
                number_code = remaining[1:]  # 9999, 25662
            else:
                number_code = remaining      # 01469
            return f"{area_code}-{letter_code} {number_code}"
        return clean_text
        
    def get_connection(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
            return None
    
    def initialize_database(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                license_plate TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicle_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT NOT NULL,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                student_id TEXT,
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_spots (
                spot_id TEXT PRIMARY KEY,
                is_occupied BOOLEAN DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            logger.info("Đã khởi tạo cơ sở dữ liệu thành công")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khởi tạo cơ sở dữ liệu: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_student_by_license_plate(self, license_plate):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            normalized_plate = self.normalize_license_plate(license_plate)
            
            cursor.execute('''
            SELECT student_id, full_name, license_plate 
            FROM students 
            WHERE license_plate = ?
            ''', (normalized_plate,))
            
            result = cursor.fetchone()
            if result:
                logger.info(f"Tìm thấy sinh viên: {result['full_name']} ({result['student_id']}) cho biển số {normalized_plate}")
            
            return result
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn sinh viên: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def is_plate_in_database(self, license_plate):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            normalized_plate = self.normalize_license_plate(license_plate)
            
            cursor.execute('''
            SELECT * FROM vehicle_logs 
            WHERE license_plate = ? AND exit_time IS NULL
            ''', (normalized_plate,))
            
            result = cursor.fetchone()
            return result is not None
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn cơ sở dữ liệu: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def save_to_database(self, license_plate, exit=False):
        try:
            normalized_plate = self.normalize_license_plate(license_plate)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            student_info = self.get_student_by_license_plate(normalized_plate)
            student_id = student_info['student_id'] if student_info else None
            
            if exit:
                cursor.execute('''
                UPDATE vehicle_logs 
                SET exit_time = ? 
                WHERE license_plate = ? AND exit_time IS NULL
                ''', (current_time, normalized_plate))
            else:
                cursor.execute('''
                INSERT INTO vehicle_logs (license_plate, entry_time, student_id)
                VALUES (?, ?, ?)
                ''', (normalized_plate, current_time, student_id))
            
            conn.commit()
            
            if student_info:
                logger.info(f"{'Xe ra' if exit else 'Xe vào'} - {student_info['full_name']} ({student_info['student_id']}) - {normalized_plate}")
            else:
                logger.info(f"{'Xe ra' if exit else 'Xe vào'} - Biển số: {normalized_plate}")
            
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi lưu dữ liệu: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_vehicle_logs(self, filter_by=None, limit=100):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = '''
            SELECT vl.id, vl.license_plate, vl.entry_time, vl.exit_time,
                   COALESCE(vl.student_id, s.student_id) as student_id, 
                   s.full_name
            FROM vehicle_logs vl
            LEFT JOIN students s ON vl.license_plate = s.license_plate
            '''
            
            params = []
            if filter_by:
                if 'license_plate' in filter_by:
                    query += ' WHERE vl.license_plate LIKE ?'
                    params.append(f"%{filter_by['license_plate']}%")
                elif 'student_id' in filter_by:
                    query += ' WHERE (vl.student_id LIKE ? OR s.student_id LIKE ?)'
                    params.append(f"%{filter_by['student_id']}%")
                    params.append(f"%{filter_by['student_id']}%")
                elif 'date' in filter_by:
                    query += ' WHERE DATE(vl.entry_time) = ?'
                    params.append(filter_by['date'])
            
            query += ' ORDER BY vl.entry_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn cơ sở dữ liệu: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def add_student(self, student_id, full_name, license_plate=None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if license_plate:
                license_plate = self.normalize_license_plate(license_plate)
            
            cursor.execute('''
            INSERT INTO students (student_id, full_name, license_plate)
            VALUES (?, ?, ?)
            ''', (student_id, full_name, license_plate))
            
            conn.commit()
            logger.info(f"Đã thêm sinh viên: {full_name} ({student_id}) - Biển số: {license_plate}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi thêm sinh viên: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def update_student(self, student_id, full_name=None, license_plate=None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            update_fields = []
            params = []
            
            if full_name is not None:
                update_fields.append("full_name = ?")
                params.append(full_name)
            
            if license_plate is not None:
                update_fields.append("license_plate = ?")
                params.append(self.normalize_license_plate(license_plate))
            
            if not update_fields:
                return False
            
            params.append(student_id)
            
            query = f'''
            UPDATE students
            SET {', '.join(update_fields)}
            WHERE student_id = ?
            '''
            
            cursor.execute(query, params)
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Đã cập nhật sinh viên: {student_id}")
                return True
            else:
                logger.warning(f"Không tìm thấy sinh viên: {student_id}")
                return False
        except sqlite3.Error as e:
            logger.error(f"Lỗi cập nhật sinh viên: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def delete_student(self, student_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Đã xóa sinh viên: {student_id}")
                return True
            else:
                logger.warning(f"Không tìm thấy sinh viên: {student_id}")
                return False
        except sqlite3.Error as e:
            logger.error(f"Lỗi xóa sinh viên: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_available_spots(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT spot_id FROM parking_spots
            WHERE is_occupied = 0
            ORDER BY spot_id
            ''')
            
            result = cursor.fetchall()
            return [row['spot_id'] for row in result]
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_total_spots(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM parking_spots')
            result = cursor.fetchone()
            return result['count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_current_vehicles(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) as count FROM vehicle_logs
            WHERE exit_time IS NULL
            ''')
            
            result = cursor.fetchone()
            return result['count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_statistics(self, period='day'):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if period == 'day':
                query = '''
                SELECT 
                    strftime('%H', entry_time) as hour, 
                    COUNT(*) as entries,
                    COALESCE((
                        SELECT COUNT(*) 
                        FROM vehicle_logs vl2 
                        WHERE strftime('%H', vl2.exit_time) = strftime('%H', vehicle_logs.entry_time)
                        AND DATE(vl2.exit_time) = DATE('now', 'localtime')
                    ), 0) as exits
                FROM vehicle_logs
                WHERE DATE(entry_time) = DATE('now', 'localtime')
                GROUP BY strftime('%H', entry_time)
                ORDER BY hour
                '''
            elif period == 'week':
                query = '''
                SELECT 
                    strftime('%w', entry_time) as day_of_week, 
                    COUNT(*) as entries,
                    COALESCE((
                        SELECT COUNT(*) 
                        FROM vehicle_logs vl2 
                        WHERE strftime('%w', vl2.exit_time) = strftime('%w', vehicle_logs.entry_time)
                        AND vl2.entry_time >= date('now', '-6 days')
                    ), 0) as exits
                FROM vehicle_logs
                WHERE entry_time >= date('now', '-6 days')
                GROUP BY strftime('%w', entry_time)
                ORDER BY day_of_week
                '''
            elif period == 'month':
                query = '''
                SELECT 
                    strftime('%d', entry_time) as day, 
                    COUNT(*) as entries,
                    COALESCE((
                        SELECT COUNT(*) 
                        FROM vehicle_logs vl2 
                        WHERE strftime('%d', vl2.exit_time) = strftime('%d', vehicle_logs.entry_time)
                        AND strftime('%m-%Y', vl2.exit_time) = strftime('%m-%Y', 'now')
                    ), 0) as exits
                FROM vehicle_logs
                WHERE strftime('%m-%Y', entry_time) = strftime('%m-%Y', 'now')
                GROUP BY strftime('%d', entry_time)
                ORDER BY day
                '''
            else:
                return []
            
            cursor.execute(query)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Lỗi lấy thống kê: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def update_parking_spot(self, spot_id, is_occupied):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('SELECT * FROM parking_spots WHERE spot_id = ?', (spot_id,))
            spot = cursor.fetchone()
            
            if spot:
                cursor.execute('''
                UPDATE parking_spots
                SET is_occupied = ?, last_updated = ?
                WHERE spot_id = ?
                ''', (1 if is_occupied else 0, current_time, spot_id))
            else:
                cursor.execute('''
                INSERT INTO parking_spots (spot_id, is_occupied, last_updated)
                VALUES (?, ?, ?)
                ''', (spot_id, 1 if is_occupied else 0, current_time))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi cập nhật vị trí đỗ xe: {e}")
            return False    
        finally:
             if conn:
                conn.close()

    def get_vehicles_count_by_period(self, period='day'):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if period == 'day':
                query = '''
                SELECT COUNT(*) as count FROM vehicle_logs
                WHERE DATE(entry_time) = DATE('now', 'localtime')
                '''
            elif period == 'week':
                query = '''
                SELECT COUNT(*) as count FROM vehicle_logs
                WHERE entry_time >= date('now', '-6 days')
                '''
            elif period == 'month':
                query = '''
                SELECT COUNT(*) as count FROM vehicle_logs
                WHERE strftime('%m-%Y', entry_time) = strftime('%m-%Y', 'now')
                '''
            else:
                return 0
            
            cursor.execute(query)
            result = cursor.fetchone()
            return result['count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_vehicle_logs_by_period(self, period='day', limit=100):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            base_query = '''
            SELECT vl.id, vl.license_plate, vl.entry_time, vl.exit_time,
                   COALESCE(vl.student_id, s.student_id) as student_id, 
                   s.full_name
            FROM vehicle_logs vl
            LEFT JOIN students s ON vl.license_plate = s.license_plate
            '''
            
            if period == 'day':
                query = base_query + '''
                WHERE DATE(vl.entry_time) = DATE('now', 'localtime')
                ORDER BY vl.entry_time DESC LIMIT ?
                '''
            elif period == 'week':
                query = base_query + '''
                WHERE vl.entry_time >= date('now', '-6 days')
                ORDER BY vl.entry_time DESC LIMIT ?
                '''
            elif period == 'month':
                query = base_query + '''
                WHERE strftime('%m-%Y', vl.entry_time) = strftime('%m-%Y', 'now')
                ORDER BY vl.entry_time DESC LIMIT ?
                '''
            else:
                return []
            
            cursor.execute(query, (limit,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Lỗi truy vấn: {e}")
            return []
        finally:
            if conn:
                conn.close()