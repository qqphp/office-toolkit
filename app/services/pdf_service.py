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
        self.save_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'img_to_pdf')
        self.pdf_path = None
        
    def _allowed_file(self, filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    
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
    
    def convert_images_to_pdf(self, files) -> str:
        """将图片文件转换为PDF，不保存原始图片，返回生成的PDF文件路径"""
        try:
            # 创建PDF
            output = io.BytesIO()
            c = canvas.Canvas(output, pagesize=A4)
            
            # 直接处理每个图片
            for i, file in enumerate(files):
                try:
                    if not file or not self._allowed_file(file.filename):
                        raise ValueError(f"Invalid file format for file {i + 1}")
                    
                    # 直接从内存中读取图片
                    img_data = file.read()
                    img = Image.open(io.BytesIO(img_data))
                    
                    # 计算尺寸和位置
                    width, height, x, y = self._calculate_image_dimensions(img)
                    
                    # 将图片转换为可用于PDF的格式
                    img_buffer = io.BytesIO()
                    if img.mode == 'RGBA':
                        # 转换RGBA为RGB
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[3])
                        bg.save(img_buffer, format='JPEG')
                    else:
                        img.convert('RGB').save(img_buffer, format='JPEG')
                    
                    img_buffer.seek(0)
                    
                    # 将图片绘制到PDF页面
                    c.drawImage(ImageReader(img_buffer), x, y, width, height)
                    c.showPage()
                    
                except Exception as e:
                    current_app.logger.error(f"Error processing image {i+1}: {str(e)}")
                    raise
                
            c.save()
            output.seek(0)
            
            # 确保目录存在
            os.makedirs(self.save_dir, exist_ok=True)
            
            # 生成唯一文件名并保存PDF
            filename = f"converted_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join(self.save_dir, filename)
            
            # 记录日志
            current_app.logger.debug(f"Saving PDF to: {pdf_path}")
            
            with open(pdf_path, 'wb') as f:
                f.write(output.getvalue())
            
            # 验证文件是否成功创建
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"Failed to create PDF file at {pdf_path}")
            
            return pdf_path
            
        except Exception as e:
            current_app.logger.error(f"PDF conversion failed: {str(e)}")
            raise e
    
    def cleanup(self):
        """清理方法保留为空，不再自动删除文件"""
        pass