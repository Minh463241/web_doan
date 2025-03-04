import mysql.connector
import os

db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    
}

def get_connection():
    return mysql.connector.connect(**db_config)

# --- Các hàm liên quan đến KHÁCH_HÀNG (Customer) ---

def get_customer_by_email(email):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM khach_hang WHERE Email = %s"
    cursor.execute(query, (email,))
    customer = cursor.fetchone()
    cursor.close()
    conn.close()
    return customer

def create_customer(ho_ten, email, password, phone, dia_chi=None, cmnd=None):
    """
    Tạo mới khách hàng với các trường:
    - HoTen, Email, MatKhau, DienThoai, DiaChi, CMND.
    Lưu ý: Nên mã hóa mật khẩu trong môi trường sản xuất.
    """
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO khach_hang (HoTen, Email, MatKhau, DienThoai, DiaChi, CMND)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (ho_ten, email, password, phone, dia_chi, cmnd))
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        print("Error in create_customer:", err)
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def update_last_login(ma_kh):
    conn = get_connection()
    cursor = conn.cursor()
    query = "UPDATE khach_hang SET last_login = NOW() WHERE MaKH = %s"
    try:
        cursor.execute(query, (ma_kh,))
        conn.commit()
    except mysql.connector.Error as err:
        print("Error in update_last_login:", err)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def update_user_avatar(ma_kh, avatar_filename):
    conn = get_connection()
    cursor = conn.cursor()
    query = "UPDATE khach_hang SET avatar = %s WHERE MaKH = %s"
    try:
        cursor.execute(query, (avatar_filename, ma_kh))
        conn.commit()
    except mysql.connector.Error as err:
        print("Error in update_user_avatar:", err)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# --- Các hàm liên quan đến LOẠI_PHÒNG (Room Type) ---

def get_all_room_types():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM loai_phong"
    cursor.execute(query)
    types = cursor.fetchall()
    cursor.close()
    conn.close()
    return types

def add_room_type(ten_loai, gia_phong, mota):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO loai_phong (TenLoaiPhong, GiaPhong, MoTa)
        VALUES (%s, %s, %s)
    """
    try:
        cursor.execute(query, (ten_loai, gia_phong, mota))
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        print("Error in add_room_type:", err)
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

# --- Các hàm liên quan đến PHÒNG và ANH_PHÒNG (Room and Room Image) ---

def add_room_to_db(so_phong, ma_loai_phong, mo_ta, trang_thai="Trống"):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO phong (SoPhong, MaLoaiPhong, TrangThai, MoTa)
        VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (so_phong, ma_loai_phong, trang_thai, mo_ta))
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        print("Error in add_room_to_db:", err)
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def add_room_image_to_db(ma_phong, duong_dan_anh, mo_ta_anh=""):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO anh_phong (MaPhong, DuongDanAnh, MoTa)
        VALUES (%s, %s, %s)
    """
    try:
        cursor.execute(query, (ma_phong, duong_dan_anh, mo_ta_anh))
        conn.commit()
    except mysql.connector.Error as err:
        print("Error in add_room_image_to_db:", err)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def add_room_with_image(file_path, filename, so_phong, ma_loai_phong, mo_ta, mo_ta_anh="", trang_thai="Trống"):
    room_id = add_room_to_db(so_phong, ma_loai_phong, mo_ta, trang_thai)
    from drive_upload import upload_file_to_drive  # Hàm này trả về URL ảnh
    image_url = upload_file_to_drive(file_path, filename)
    add_room_image_to_db(room_id, image_url, mo_ta_anh)

def get_all_rooms():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT p.MaPhong, p.SoPhong, p.MaLoaiPhong, p.TrangThai, p.MoTa AS MoTaPhong,
               a.DuongDanAnh AS image_url, lp.GiaPhong
        FROM phong p
        LEFT JOIN anh_phong a ON p.MaPhong = a.MaPhong
        LEFT JOIN loai_phong lp ON p.MaLoaiPhong = lp.MaLoaiPhong
    """
    cursor.execute(query)
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    return rooms

def get_room_by_id(room_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT p.MaPhong, p.SoPhong, p.TrangThai, p.MoTa AS MoTaPhong, 
               a.DuongDanAnh AS image_url, lp.TenLoaiPhong AS name, lp.GiaPhong, lp.MoTa AS LoaiPhongMoTa
        FROM phong p 
        LEFT JOIN anh_phong a ON p.MaPhong = a.MaPhong 
        LEFT JOIN loai_phong lp ON p.MaLoaiPhong = lp.MaLoaiPhong 
        WHERE p.MaPhong = %s
    """
    cursor.execute(query, (room_id,))
    room = cursor.fetchone()
    cursor.close()
    conn.close()
    return room

# --- Các hàm liên quan đến ĐẶT PHÒNG (Booking) ---
def is_room_booked(room_id, checkin_date, checkout_date):
    """
    Kiểm tra xem phòng (room_id) có bị đặt trong khoảng thời gian [checkin_date, checkout_date)
    không, dựa trên bảng dat_phong.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT * FROM dat_phong
        WHERE MaPhong = %s AND (NgayNhan < %s AND NgayTra > %s)
    """
    cursor.execute(query, (room_id, checkout_date, checkin_date))
    booking = cursor.fetchone()
    cursor.close()
    conn.close()
    return booking is not None

def create_booking(ma_kh, ma_phong, ngay_dat, ngay_nhan, ngay_tra, so_luong_khach, tinh_trang="Chờ xác nhận"):
    """
    Tạo mới đặt phòng trong bảng dat_phong.
    """
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO dat_phong (MaKH, MaPhong, NgayDat, NgayNhan, NgayTra, SoLuongKhach, TinhTrang)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (ma_kh, ma_phong, ngay_dat, ngay_nhan, ngay_tra, so_luong_khach, tinh_trang))
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        print("Error in create_booking:", err)
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

# --- Các hàm liên quan đến NHÂN VIÊN (Admin) ---
def get_admin_by_email_and_password(email, password):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM nhan_vien WHERE Email = %s AND password = %s"
    cursor.execute(query, (email, password))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()
    return admin
