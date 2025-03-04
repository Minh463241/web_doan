import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from bson import ObjectId

# Load biến môi trường từ .env (nếu có)
load_dotenv()

# Lấy URI và tên DB từ biến môi trường
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise Exception("MONGO_URI chưa được thiết lập trong biến môi trường")

client = MongoClient(MONGO_URI)
db_name = os.environ.get("DB_NAME", "qlksda")
db = client[db_name]

# ---------------------------
# Các collection
# ---------------------------
customers_collection        = db['customers']
room_images_collection      = db['room_images']
bookings_collection         = db['bookings']
services_collection         = db['services']
invoices_collection         = db['invoices']
invoice_services_collection = db['invoice_services']
room_types_collection       = db['room_types']
staff_collection            = db['staff']
rooms_collection            = db['rooms']

# ---------------------------
# Khách hàng
# ---------------------------
def get_customer_by_email(email):
    return customers_collection.find_one({'Email': email})

def create_customer(customer_data):
    result = customers_collection.insert_one(customer_data)
    return str(result.inserted_id)

def update_last_login(email):
    result = customers_collection.update_one(
        {'Email': email},
        {'$set': {'last_login': datetime.utcnow()}}
    )
    return result.modified_count

def update_user_avatar(email, avatar_filename):
    result = customers_collection.update_one(
        {'Email': email},
        {'$set': {'avatar': avatar_filename}}
    )
    return result.modified_count

# ---------------------------
# Ảnh phòng
# ---------------------------
def create_room_image(room_image_data):
    result = room_images_collection.insert_one(room_image_data)
    return str(result.inserted_id)

def get_room_images_by_room(ma_phong):
    return list(room_images_collection.find({'MaPhong': ma_phong}))

# ---------------------------
# Đặt phòng
# ---------------------------
def create_booking(booking_data):
    result = bookings_collection.insert_one(booking_data)
    return str(result.inserted_id)

def get_booking_by_id(ma_dat_phong):
    return bookings_collection.find_one({'MaDatPhong': ma_dat_phong})

def update_booking(ma_dat_phong, update_data):
    result = bookings_collection.update_one(
        {'MaDatPhong': ma_dat_phong},
        {'$set': update_data}
    )
    return result.modified_count

def is_room_booked(ma_phong, checkin_date, checkout_date):
    booking = bookings_collection.find_one({
        'MaPhong': ma_phong,
        'NgayNhan': {'$lt': checkout_date},
        'NgayTra': {'$gt': checkin_date}
    })
    return booking is not None

# ---------------------------
# Dịch vụ
# ---------------------------
def get_service_by_id(ma_dich_vu):
    return services_collection.find_one({'MaDichVu': ma_dich_vu})

def create_service(service_data):
    result = services_collection.insert_one(service_data)
    return str(result.inserted_id)

def get_all_services():
    return list(services_collection.find())

# ---------------------------
# Hóa đơn
# ---------------------------
def create_invoice(invoice_data):
    result = invoices_collection.insert_one(invoice_data)
    return str(result.inserted_id)

def get_invoice_by_id(ma_hoa_don):
    return invoices_collection.find_one({'MaHoaDon': ma_hoa_don})

def get_all_invoices():
    return list(invoices_collection.find())

# ---------------------------
# Hóa đơn dịch vụ
# ---------------------------
def create_invoice_service(invoice_service_data):
    result = invoice_services_collection.insert_one(invoice_service_data)
    return str(result.inserted_id)

def get_invoice_services_by_invoice(ma_hoa_don):
    return list(invoice_services_collection.find({'MaHoaDon': ma_hoa_don}))

# ---------------------------
# Loại phòng
# ---------------------------
def get_all_room_types():
    return list(room_types_collection.find())

def get_room_type_by_id(ma_loai_phong):
    return room_types_collection.find_one({'MaLoaiPhong': ma_loai_phong})

def create_room_type(room_type_data):
    result = room_types_collection.insert_one(room_type_data)
    return str(result.inserted_id)

# Alias để dùng trong app
add_room_type = create_room_type

def add_room_to_db(so_phong, ma_loai_phong, mo_ta, trang_thai):
    try:
        room_type = room_types_collection.find_one({'_id': ObjectId(ma_loai_phong)})
    except Exception as e:
        raise ValueError("ID loại phòng không hợp lệ: " + str(ma_loai_phong))
    if not room_type:
        raise ValueError("Không tìm thấy loại phòng với ID: " + str(ma_loai_phong))
    
    price = room_type.get('price', 0)
    room_data = {
        'MaPhong': None,  # Sẽ được cập nhật sau khi chèn
        'SoPhong': so_phong,
        'MaLoaiPhong': ma_loai_phong,  # Lưu ID loại phòng dưới dạng string
        'TrangThai': trang_thai,
        'MoTa': mo_ta,
        'price': price,
        'created_at': datetime.utcnow()
    }
    return create_room(room_data)

def add_room_with_image(file_path, filename, so_phong, ma_loai_phong, mo_ta, image_description, trang_thai):
    # Tạo phòng mới và lấy ID phòng
    room_id = add_room_to_db(so_phong, ma_loai_phong, mo_ta, trang_thai)
    
    # Sử dụng hàm upload từ file drive_upload.py
    from drive_upload import upload_file_to_drive
    image_url = upload_file_to_drive(file_path, filename)

    room_image_data = {
        'MaAnh': None,
        'MaPhong': room_id,         # Liên kết ảnh với phòng vừa tạo
        'DuongDanAnh': image_url,   # Đường dẫn ảnh từ Google Drive
        'MoTa': image_description,
        'uploaded_at': datetime.utcnow()
    }
    create_room_image(room_image_data)
    
    # Cập nhật document phòng với thông tin ảnh để hiển thị trong danh sách phòng
    update_room(room_id, {'image_url': image_url, 'image_url_hd': image_url})
    
    return room_id

# ---------------------------
# Nhân viên (Admin)
# ---------------------------
def get_staff_by_email(email):
    return staff_collection.find_one({'Email': email})

def create_staff(staff_data):
    result = staff_collection.insert_one(staff_data)
    return str(result.inserted_id)

def get_all_staff():
    return list(staff_collection.find())

def get_admin_by_email_and_password(email, password):
    admin = staff_collection.find_one({'Email': email})
    if admin and admin.get('password') == password:
        return admin
    return None

# ---------------------------
# Phòng
# ---------------------------
def get_all_rooms():
    return list(rooms_collection.find())

def get_room_by_id(ma_phong):
    return rooms_collection.find_one({'MaPhong': ma_phong})

def create_room(room_data):
    # Sao chép dữ liệu và loại bỏ 'MaPhong' nếu có
    doc = dict(room_data)
    doc.pop('MaPhong', None)
    
    # Chèn document vào MongoDB
    result = rooms_collection.insert_one(doc)
    inserted_id = result.inserted_id
    inserted_id_str = str(inserted_id)
    
    # Cập nhật lại trường 'MaPhong' với giá trị của inserted_id (dạng chuỗi)
    update_result = rooms_collection.update_one(
        {'_id': inserted_id},
        {'$set': {'MaPhong': inserted_id_str}}
    )
    if update_result.modified_count == 0:
        print("[Warning] Không thể cập nhật MaPhong cho document vừa chèn.")
    
    return inserted_id_str

def update_room(ma_phong, update_data):
    result = rooms_collection.update_one({'MaPhong': ma_phong}, {'$set': update_data})
    return result.modified_count
