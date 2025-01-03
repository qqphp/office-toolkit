from flask import current_app
from werkzeug.utils import secure_filename
import os
import uuid
from typing import Optional
from app.services.image_service import remove_background

class BackgroundService:
    def __init__(self):
        self.upload_folder = current_app.config['UPLOAD_FOLDER']
        self.temp_file: Optional[str] = None
        
    def _allowed_file(self, filename: str) -> bool:
        """检查文件类型是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    
    def _save_upload(self, file) -> str:
        """保存上传的文件"""
        if not file or not self._allowed_file(file.filename):
            raise ValueError('不支持的文件类型')
            
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(self.upload_folder, unique_filename)
        
        # 确保上传目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        file.save(filepath)
        self.temp_file = filepath
        return filepath
    
    def process_image(self, file) -> str:
        """处理图片并返回结果路径"""
        try:
            filepath = self._save_upload(file)
            result_path = remove_background(filepath)
            return result_path
            
        except Exception as e:
            self.cleanup()
            current_app.logger.error(f"处理图片失败: {str(e)}")
            raise Exception("图片处理失败，请确保图片格式正确且大小适中")
    
    def cleanup(self):
        """清理临时文件"""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception as e:
                current_app.logger.error(f"清理临时文件失败: {str(e)}") 