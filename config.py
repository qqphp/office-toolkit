import os

class Config:
    # Debug and port configuration
    DEBUG = True  # 直接设置为 False，不使用环境变量
    HOST = '0.0.0.0'  # 直接设置固定主机
    PORT = 5001   # 直接设置固定端口
    
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

    # 图片转pdf目录配置
    IMG_TO_PDF_FOLDER = os.path.join(UPLOAD_FOLDER, 'img_to_pdf')

    # 图片压缩目录配置
    IMG_COMPRESS_FOLDER = os.path.join(UPLOAD_FOLDER, 'compress')

    # 模糊面部目录配置
    BLUR_FACE_FOLDER = os.path.join(UPLOAD_FOLDER, 'blur_face')

    # 图片裁剪目录配置
    CROP_FOLDER = os.path.join(UPLOAD_FOLDER, 'crop')

    # APScheduler配置
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "Asia/Shanghai"

    # 添加阿里云配置
    ALIBABA_CLOUD_ACCESS_KEY_ID = 'REDACTED'  # 替换为实际的 Access Key ID
    ALIBABA_CLOUD_ACCESS_KEY_SECRET = 'REDACTED'  # 替换为实际的 Access Key Secret
    ALIBABA_CLOUD_ENDPOINT = 'imageseg.cn-shanghai.aliyuncs.com'
