import os
import hashlib
import urllib.parse
from flask import Flask, flash, render_template, request, redirect, url_for, session, Blueprint, jsonify
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime

# Import các hàm từ db_mongo.py (MongoDB)
from db_mongo import (
    create_customer,
    get_customer_by_email,
    update_last_login,
    update_user_avatar,
    get_all_rooms,
    get_all_room_types,
    add_room_type,
    get_admin_by_email_and_password,
    get_room_by_id,
    is_room_booked,
    create_booking,
    add_room_with_image,
    add_room_to_db
)

# Giả sử bạn vẫn sử dụng hàm upload_file_to_drive từ drive_upload.py
from drive_upload import upload_file_to_drive

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=7)

# Cấu hình cho file upload avatar
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'avatars')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------
# ROUTE: Thay đổi ngôn ngữ
# -------------------------------
@app.route('/change_language/<lang>')
def change_language(lang):
    referrer = request.referrer or url_for('index')
    response = redirect(referrer)
    response.set_cookie('lang', lang)
    return response

# -------------------------------
# ROUTE: Trang chủ
# -------------------------------
@app.route('/')
def index():
    user_email = session.get('email')
    user_avatar = session.get('avatar', 'default.jpg')
    rooms = get_all_rooms()  # Lấy danh sách phòng từ MongoDB

    # Các bộ lọc nếu bạn có sử dụng
    popular = session.get('popular')
    tiennghi = session.get('tiennghi')
    xephang = session.get('xephang')
    rating = session.get('rating')

    return render_template(
        'index.html',
        user_email=user_email,
        user_avatar=user_avatar,
        rooms=rooms,
        filter_popular=popular,
        filter_tiennghi=tiennghi,
        filter_xephang=xephang,
        filter_rating=rating
    )

# -------------------------------
# ROUTE: Tìm kiếm
# -------------------------------
@app.route('/search', methods=['GET'])
def search():
    destination = request.args.get('destination')
    checkin = request.args.get('checkin')
    checkout = request.args.get('checkout')
    guests = request.args.get('guests')
    print("Search data:", destination, checkin, checkout, guests)
    return render_template('index.html')

# -------------------------------
# Blueprint AUTH (Đăng ký, đăng nhập, cập nhật avatar)
# -------------------------------
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
        
        user = get_customer_by_email(email)
        if user:
            if user.get('password') == password:
                session.permanent = True
                session['user_id'] = str(user.get('_id'))
                session['email'] = user.get('Email')
                update_last_login(user.get('Email'))
                if request.is_json:
                    return jsonify({"success": True, "message": "Đăng nhập thành công"})
                else:
                    return redirect(url_for('index'))
            else:
                if request.is_json:
                    return jsonify({"success": False, "message": "Mật khẩu không chính xác"})
                else:
                    flash("Mật khẩu không chính xác", "error")
                    return redirect(url_for('auth_bp.login'))
        else:
            if request.is_json:
                return jsonify({"success": False, "message": "Không tìm thấy tài khoản với email này"})
            else:
                flash("Không tìm thấy tài khoản với email này", "error")
                return redirect(url_for('auth_bp.login'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        ho_ten = request.form.get('ho_ten')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        dia_chi = request.form.get('dia_chi')
        cmnd = request.form.get('cmnd')
        
        if get_customer_by_email(email):
            flash("Email đã được sử dụng, vui lòng sử dụng email khác.", "error")
            return redirect(url_for('auth_bp.register'))
        
        customer_data = {
            'HoTen': ho_ten,
            'Email': email,
            'password': password,
            'DienThoai': phone,
            'DiaChi': dia_chi,
            'CMND': cmnd,
            'last_login': None,
            'avatar': None
        }
        user_id = create_customer(customer_data)
        if user_id:
            flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
            return redirect(url_for('auth_bp.login'))
        else:
            flash("Đăng ký thất bại.", "error")
            return redirect(url_for('auth_bp.register'))

@auth_bp.route('/update_avatar', methods=['GET', 'POST'])
def update_avatar():
    if 'user_id' not in session or 'email' not in session:
        flash("Bạn cần đăng nhập để thay đổi avatar.", "error")
        return redirect(url_for('auth_bp.login'))
    
    if request.method == 'GET':
        return render_template('update_avatar.html')
    else:
        if 'avatar' not in request.files:
            flash("Không tìm thấy file tải lên.", "error")
            return redirect(request.url)
        
        file = request.files['avatar']
        if file.filename == '':
            flash("Bạn chưa chọn file.", "error")
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"user_{session['user_id']}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file.save(file_path)
            update_user_avatar(session['email'], filename)
            session['avatar'] = filename
            flash("Avatar cập nhật thành công!", "success")
            return redirect(url_for('index'))
        else:
            flash("Loại file không được chấp nhận.", "error")
            return redirect(request.url)

app.register_blueprint(auth_bp)

# -------------------------------
# ROUTE: Quản trị Admin
# -------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin_login.html')
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        admin = get_admin_by_email_and_password(email, password)
        if admin:
            session['admin_id'] = str(admin.get('_id'))
            session['admin_email'] = admin.get('Email')
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Sai thông tin đăng nhập. Vui lòng kiểm tra lại."
            return render_template('admin_login.html', error=error)

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/add_room_type', methods=['GET', 'POST'])
def add_room_type_route():
    if request.method == 'GET':
        room_types = get_all_room_types()
        return render_template('add_room_type.html', room_types=room_types)
    else:
        ten_loai = request.form.get('ten_loai')
        gia_phong = request.form.get('gia_phong')
        mota = request.form.get('mota')
        try:
            gia_phong = float(gia_phong)
        except (ValueError, TypeError):
            flash("Giá phòng không hợp lệ.", "error")
            return redirect(url_for('add_room_type_route'))
        room_type_data = {
            'name': ten_loai,
            'price': gia_phong,
            'description': mota
        }
        result = add_room_type(room_type_data)
        if result:
            flash("Thêm loại phòng thành công!", "success")
            return redirect(url_for('add_room_type_route'))
        else:
            flash("Thêm loại phòng thất bại.", "error")
            return redirect(url_for('add_room_type_route'))

@app.route('/add_room', methods=['GET', 'POST'])
def add_room():
    if request.method == 'GET':
        room_types = get_all_room_types()
        return render_template('add_room.html', room_types=room_types)
    
    so_phong = request.form.get('room_number')
    ma_loai_phong = request.form.get('room_type')
    mo_ta = request.form.get('description')
    trang_thai = "Trống"
    
    if not ma_loai_phong or not ma_loai_phong.strip():
        flash("Chưa chọn loại phòng.", "error")
        return redirect(url_for('add_room'))
    
    file = request.files.get('room_image')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        temp_folder = os.path.join(app.root_path, 'temp')
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        temp_path = os.path.join(temp_folder, filename)
        file.save(temp_path)
        # Hàm add_room_with_image xử lý tạo phòng và upload ảnh
        add_room_with_image(temp_path, f"room_{filename}", so_phong, ma_loai_phong, mo_ta, "", trang_thai)
        os.remove(temp_path)
    else:
        add_room_to_db(so_phong, ma_loai_phong, mo_ta, trang_thai)
    
    flash("Thêm phòng thành công!", "success")
    return redirect(url_for('add_room'))

# -------------------------------
# ROUTE: Đặt phòng (Booking) & Thanh toán
# -------------------------------
# Sửa route nhận room_id dưới dạng string
@app.route('/booking/<room_id>', methods=['GET', 'POST'])
def booking(room_id):
    if request.method == 'GET':
        checkin_str = request.args.get('checkin')
        checkout_str = request.args.get('checkout')
        room = get_room_by_id(room_id)
        if not room:
            flash("Không tìm thấy phòng", "error")
            return redirect(url_for('index'))

        so_dem = 1
        tong_gia = room.get('price', 0)
        if checkin_str and checkout_str:
            try:
                checkin_date = datetime.strptime(checkin_str, "%Y-%m-%d").date()
                checkout_date = datetime.strptime(checkout_str, "%Y-%m-%d").date()
                so_dem = (checkout_date - checkin_date).days
                if so_dem < 1:
                    so_dem = 1
                tong_gia = so_dem * room.get('price', 0)
            except Exception as e:
                print("Error parsing dates:", e)
        
        return render_template(
            'booking.html',
            room=room,
            checkin=checkin_str,
            checkout=checkout_str,
            so_dem=so_dem,
            tong_gia=tong_gia
        )
    else:
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        country = request.form.get('country')
        address = request.form.get('address')
        city = request.form.get('city')
        postal_code = request.form.get('postalCode')
        region_code = request.form.get('regionCode')
        phone = request.form.get('phone')
        booking_data = {
            'customer_first_name': first_name,
            'customer_last_name': last_name,
            'email': email,
            'country': country,
            'address': address,
            'city': city,
            'postal_code': postal_code,
            'region_code': region_code,
            'phone': phone,
            # Các trường khác cần thêm theo logic của bạn
        }
        create_booking(booking_data)
        return redirect(url_for('create_payment', amount=tong_gia))

# -------------------------------
# ROUTE: Tích hợp Thanh toán VNPay
# -------------------------------
@app.route('/create_payment')
def create_payment():
    amount = request.args.get('amount', default=1000000, type=int)
    vnp_Version = "2.1.0"
    vnp_Command = "pay"
    vnp_TmnCode = "YOUR_TMN_CODE"  # Thay bằng TmnCode của bạn
    vnp_Amount = str(amount * 100)
    vnp_CurrCode = "VND"
    vnp_TxnRef = "ORDER" + datetime.now().strftime("%H%M%S")
    vnp_OrderInfo = "Thanh toán đặt phòng khách sạn"
    vnp_OrderType = "other"
    vnp_Locale = "vn"
    vnp_SecureHashType = "SHA256"
    vnp_ReturnUrl = url_for('vnpay_return', _external=True)
    vnp_CreateDate = datetime.now().strftime("%Y%m%d%H%M%S")
    vnp_IpAddr = request.remote_addr
    secret_key = "YOUR_SECRET_KEY"  # Thay bằng secret key của bạn

    vnp_params = {
        "vnp_Version": vnp_Version,
        "vnp_Command": vnp_Command,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Amount": vnp_Amount,
        "vnp_CurrCode": vnp_CurrCode,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_OrderType": vnp_OrderType,
        "vnp_Locale": vnp_Locale,
        "vnp_ReturnUrl": vnp_ReturnUrl,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_SecureHashType": vnp_SecureHashType
    }

    sorted_vnp_params = sorted(vnp_params.items())
    query_string = urllib.parse.urlencode(sorted_vnp_params)
    sign_data = '&'.join(["{}={}".format(k, v) for k, v in sorted_vnp_params])
    secure_hash = hashlib.sha256((secret_key + sign_data).encode('utf-8')).hexdigest()

    payment_url = (
        "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?"
        + query_string
        + "&vnp_SecureHash=" + secure_hash
    )

    print("Payment URL:", payment_url)
    return redirect(payment_url)

@app.route('/vnpay_return')
def vnpay_return():
    data = request.args.to_dict()
    print("VNPay callback data:", data)
    received_hash = data.pop('vnp_SecureHash', None)
    received_hash_type = data.pop('vnp_SecureHashType', None)

    sorted_data = sorted(data.items())
    sign_data = '&'.join(["{}={}".format(k, v) for k, v in sorted_data])

    # Secret key mẫu, thay bằng key thực tế của bạn
    secret_key = "*bzwzl9d&aq)rg2z9(@twit_)=5fp77et3i&l4-xp1h$r)^+gp"
    my_hash = hashlib.sha256((secret_key + sign_data).encode('utf-8')).hexdigest()

    if my_hash.upper() == (received_hash or "").upper():
        response_code = data.get('vnp_ResponseCode', '99')
        if response_code == '00':
            flash("Thanh toán thành công!", "success")
            return redirect(url_for('index'))
        else:
            flash(f"Thanh toán thất bại. Mã lỗi: {response_code}", "error")
            return redirect(url_for('index'))
    else:
        flash("Chữ ký không hợp lệ, giao dịch bị từ chối!", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
