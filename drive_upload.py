import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'up2.json')
FOLDER_ID = '120x9O34Cbn8LyjOmo0sBuczbLh_fHIWm'

def upload_file_to_drive(file_path, filename):
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)
    
    file_metadata = {'name': filename}
    if FOLDER_ID:
        file_metadata['parents'] = [FOLDER_ID]
    
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    # Lấy ID file từ phản hồi của API
    file_id = uploaded_file.get('id')
    if not file_id:
        raise Exception("Không lấy được file_id từ response")
    
    # Tạo quyền truy cập công khai cho file
    permission = {'type': 'anyone', 'role': 'reader'}
    drive_service.permissions().create(
        fileId=file_id,
        body=permission
    ).execute()
    
    # Tạo URL nhúng trực tiếp từ file_id với định dạng https://lh3.googleusercontent.com/d/ID-ANH=w1000
    direct_url = f"https://lh3.googleusercontent.com/d/{file_id}=w1000"
    return direct_url
