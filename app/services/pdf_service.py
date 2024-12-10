from flask import current_app
from werkzeug.utils import secure_filename
import os
import uuid
import io
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from typing import List, Tuple

class PDFService:
    def __init__(self):
        self.save_dir = current_app.config['IMG_TO_PDF_FOLDER']
        self.saved_files: List[str] = []
        
    def _allowed_file(self, filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    
    def _save_image(self, file, index: int) -> str:
        """保存上传的图片文件"""
        if not file or not self._allowed_file(file.filename):
            current_app.logger.warning(f"Invalid file: {file.filename if file else 'None'}")
            raise ValueError(f"Invalid file format for file {index + 1}")
            
        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{extension}"
        filepath = os.path.join(self.save_dir, unique_filename)
        
        file.save(filepath)
        return filepath
        
    def _calculate_image_dimensions(self, img: Image.Image) -> Tuple[float, float, float, float]:
        """计算图片在PDF页面中的尺寸和位置"""
        img_width, img_height = img.size
        aspect = img_height / float(img_width)
        
        # A4页面尺寸(单位：点）
        a4_width, a4_height = A4
        
        # 设置图片在页面上的最大宽度（留出边距）
        max_width = a4_width - 40  # 左右各留20点边距
        
        # 计算等比例缩放后的高度
        width = max_width
        height = width * aspect
        
        # 如果高度超出页面，则按高度进行缩放
        if height > (a4_height - 40):  # 上下各留20点边距
            height = a4_height - 40
            width = height / aspect
        
        # 计算居中位置
        x = (a4_width - width) / 2
        y = (a4_height - height) / 2
        
        return width, height, x, y
    
    def convert_images_to_pdf(self, files) -> io.BytesIO:
        """将图片文件转换为PDF"""
        try:
            # 确保保存目录存在
            os.makedirs(self.save_dir, exist_ok=True)
            
            # 保存所有图片
            for i, file in enumerate(files):
                try:
                    filepath = self._save_image(file, i)
                    self.saved_files.append(filepath)
                except Exception as e:
                    current_app.logger.error(f"Error saving file {i+1}: {str(e)}")
                    raise
            
            # 创建PDF
            output = io.BytesIO()
            c = canvas.Canvas(output, pagesize=A4)
            
            # 处理每个图片
            for i, filepath in enumerate(self.saved_files):
                try:
                    with Image.open(filepath) as img:
                        # 计算尺寸和位置
                        width, height, x, y = self._calculate_image_dimensions(img)
                        # 将图片绘制到PDF页面
                        c.drawImage(ImageReader(img), x, y, width, height)
                        c.showPage()
                except Exception as e:
                    current_app.logger.error(f"Error processing image {i+1}: {str(e)}")
                    raise
            
            c.save()
            output.seek(0)
            return output
            
        except Exception as e:
            self.cleanup()
            raise e
    
    def cleanup(self):
        """清理临时文件"""
        for filepath in self.saved_files:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as cleanup_error:
                current_app.logger.error(f"Error cleaning up {filepath}: {str(cleanup_error)}") 