import os
from PIL import Image
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
import re

class CropService:
    def __init__(self):
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        # 确保裁剪目录存在
        os.makedirs(current_app.config['CROP_FOLDER'], exist_ok=True)
        
    def allowed_file(self, filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
               
    def get_file_extension(self, filename):
        """获取文件扩展名，支持中文文件名"""
        # 使用正则表达式匹配文件扩展名
        match = re.search(r'\.(png|jpe?g|gif)$', filename.lower())
        if match:
            return match.group(1)
        return None
        
    def process_image(self, file, crop_data):
        """处理图片裁剪
        
        Args:
            file: 上传的文件对象
            crop_data: 裁剪参数字典，包含 x, y, width, height, rotate, scaleX, scaleY 等信息
            
        Returns:
            str: 处理后的图片URL路径
        """
        if not self.allowed_file(file.filename):
            raise ValueError('不支持的文件类型')
            
        try:
            # 读取原图
            image = Image.open(file)
            
            # 处理旋转
            rotate_angle = float(crop_data.get('rotate', 0))
            if rotate_angle != 0:
                # 使用BICUBIC重采样以获得更好的质量
                image = image.rotate(-rotate_angle, expand=True, resample=Image.BICUBIC)
            
            # 处理翻转
            if crop_data.get('scaleX', 1) == -1:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
            if crop_data.get('scaleY', 1) == -1:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                
            # 获取裁剪区域
            crop_box = (
                int(float(crop_data['x'])),
                int(float(crop_data['y'])),
                int(float(crop_data['x']) + float(crop_data['width'])),
                int(float(crop_data['y']) + float(crop_data['height']))
            )
            
            # 裁剪图片
            image = image.crop(crop_box)
            
            # 获取文件扩展名
            ext = self.get_file_extension(file.filename)
            if not ext:
                ext = 'jpg'  # 默认使用jpg格式
                
            # 生成保存路径，使用uuid避免文件名冲突
            save_name = f"crop_{uuid.uuid4().hex[:8]}.{ext}"
            save_path = os.path.join(current_app.config['CROP_FOLDER'], save_name)
            
            # 根据文件扩展名选择保存格式
            save_format = 'JPEG' if ext.lower() in ['jpg', 'jpeg'] else ext.upper()
            
            # 保存处理后的图片
            if save_format == 'JPEG':
                # JPEG格式特殊处理
                if image.mode in ['RGBA', 'P']:
                    image = image.convert('RGB')
                image.save(save_path, format=save_format, quality=95, optimize=True)
            else:
                # 其他格式
                image.save(save_path, format=save_format, optimize=True)
            
            # 返回可访问的URL路径
            return f'/static/uploads/crop/{save_name}'
            
        except Exception as e:
            current_app.logger.error(f"裁剪图片失败: {str(e)}")
            raise Exception('图片处理失败') 