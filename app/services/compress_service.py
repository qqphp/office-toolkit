import os
from PIL import Image
import uuid
from flask import current_app
import shutil

class CompressService:
    def __init__(self):
        # 确保使用绝对路径
        self.upload_folder = os.path.join(
            current_app.root_path,
            'static',
            'uploads',
            'compress'
        )
        current_app.logger.debug(f"Compress folder path: {self.upload_folder}")
        os.makedirs(self.upload_folder, exist_ok=True)
        self.temp_files = []

    def process_image(self, file, quality=80, max_width=1920, max_height=1080):
        """
        处理图片压缩
        :param file: 上传的文件对象
        :param quality: 压缩质量 (1-100)
        :param max_width: 最大宽度
        :param max_height: 最大高度
        :return: 处理后的图片URL
        """
        try:
            # 生成唯一文件名
            filename = str(uuid.uuid4()) + '.jpg'
            # 构建完整的文件保存路径
            filepath = os.path.join(self.upload_folder, filename)
            current_app.logger.debug(f"Saving compressed image to: {filepath}")
            
            # 打开图片
            img = Image.open(file)
            
            # 转换为RGB模式(如果是RGBA)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # 调整图片大小
            if img.width > max_width or img.height > max_height:
                ratio = min(max_width/img.width, max_height/img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 保存压缩后的图片
            img.save(filepath, 'JPEG', quality=quality, optimize=True)
            
            # 返回相对URL路径
            return f'/static/uploads/compress/{filename}'
            
        except Exception as e:
            if 'filepath' in locals():
                self.temp_files.append(filepath)
            current_app.logger.error(f"图片压缩失败: {str(e)}")
            raise ValueError('图片处理失败')

    def cleanup(self):
        """只清理处理失败时产生的临时文件"""
        try:
            for file in self.temp_files:
                if os.path.exists(file):
                    os.remove(file)
            self.temp_files.clear()
        except Exception as e:
            current_app.logger.error(f"清理临时文件失败: {str(e)}") 