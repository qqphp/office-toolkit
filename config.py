import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    REMOVE_BG_FOLDER = os.path.join(UPLOAD_FOLDER, 'remove_bg')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    
    # 添加水印目录配置
    WATERMARK_FOLDER = os.path.join(UPLOAD_FOLDER, 'watermark')
    
    # 更新模型路径配置
    U2NET_HOME = os.path.join('app', 'models', 'u2net')
    CASCADE_PATH = os.path.join('app', 'models', 'cascades')
    IMG_TO_PDF_FOLDER = os.path.join(UPLOAD_FOLDER, 'img_to_pdf')