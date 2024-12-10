import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    
    # 添加模型路径配置
    U2NET_HOME = 'models'
    CASCADE_PATH = os.path.join('models', 'cascades')
    IMG_TO_PDF_FOLDER = os.path.join(UPLOAD_FOLDER, 'img_to_pdf')