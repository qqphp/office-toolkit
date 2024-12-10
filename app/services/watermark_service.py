from flask import current_app
from PIL import Image, ImageDraw, ImageFont
import os
import uuid
from typing import Optional, Tuple, Dict
import io

class WatermarkService:
    def __init__(self):
        # 使用 current_app.root_path 获取应用根目录的绝对路径
        app_root = current_app.root_path
        self.upload_folder = os.path.join(app_root, 'static', 'uploads', 'watermark')
        current_app.logger.debug(f"Upload folder path: {self.upload_folder}")
        self.temp_files = []
        
    def add_watermark(self, image_file, options: Dict) -> str:
        """添加水印到图片"""
        try:
            # 添加日志以跟踪文件处理
            current_app.logger.info(f"Opening image file: {image_file.filename}")
            
            # 打开原图
            image = Image.open(image_file)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                
            # 创建水印层
            watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark)
            
            # 获取水印设置
            watermark_type = options.get('type', 'text')
            position = options.get('position', 'center')
            opacity = int(options.get('opacity', 50))
            size = int(options.get('size', 30))
            
            current_app.logger.info(f"Adding {watermark_type} watermark")
            
            if watermark_type == 'text':
                self._add_text_watermark(
                    watermark,
                    draw, 
                    watermark.size, 
                    options.get('text', '无影抠图'),
                    position,
                    opacity,
                    size
                )
            else:
                watermark_image = options.get('image')
                if watermark_image:
                    self._add_image_watermark(
                        watermark,
                        watermark_image,
                        position,
                        opacity,
                        size
                    )
            
            # 合并原图和水印
            result = Image.alpha_composite(image, watermark)
            
            # 保存结果
            output_path = self._save_image(result)
            current_app.logger.info(f"Image saved to: {output_path}")
            return output_path
            
        except Exception as e:
            current_app.logger.error(f"添加水印失败: {str(e)}")
            raise
            
    def _add_text_watermark(
        self, 
        watermark: Image,
        draw: ImageDraw, 
        size: Tuple[int, int], 
        text: str,
        position: str,
        opacity: int,
        text_size: int,
        rotation: float = 0,
        font_name: str = 'arial',
        color: str = '#000000'
    ):
        """添加文字水印"""
        # 计算字体大小 - 基于图片宽度而不是最小边
        base_size = size[0]  # 使用图片宽度作为基准
        # 调整基准系数，增大默认字体大小
        font_size = int(base_size * text_size / 50)  # 调整除数使默认大小更大
        
        # 确保字体大小不会太小
        min_font_size = 24  # 增大最小字体大小
        font_size = max(font_size, min_font_size)
        
        # 根据文字长度调整字体大小
        if len(text) > 10:
            # 调整文字长度对大小的影响
            font_size = int(font_size * (1 - (len(text) - 10) / 100))  # 减小文字长度对大小的影响
        
        # 字体映射
        font_map = {
            'arial': 'arial.ttf',
            'times': 'times.ttf',
            'microsoft-yahei': 'msyh.ttc',
            'simhei': 'simhei.ttf'
        }
        
        try:
            font = ImageFont.truetype(font_map.get(font_name, 'arial.ttf'), font_size)
        except:
            font = ImageFont.load_default()
            
        # 计算文字大小和位置
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top
        
        # 计算基础位置
        x, y = self._calculate_position(
            position, 
            size[0], 
            size[1], 
            text_width, 
            text_height
        )
        
        # 创建新的图片用于旋转
        txt = Image.new('RGBA', (text_width * 2, text_height * 2), (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        
        # 转换颜色格式
        color = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        color = color + (int(255 * opacity / 100),)  # 添加透明度
        
        # 在中心点绘制文字
        d.text((text_width // 2, text_height // 2), text, font=font, fill=color, anchor="mm")
        
        # 旋转文字
        if rotation:
            txt = txt.rotate(float(rotation), expand=True, fillcolor=(255, 255, 255, 0))
        
        # 粘贴到原图
        watermark.paste(txt, (x - text_width // 2, y - text_height // 2), txt)
        
    def _add_image_watermark(
        self, 
        base_image: Image, 
        watermark_image,
        position: str,
        opacity: int,
        size: int
    ):
        """添加图片水印"""
        mark = Image.open(watermark_image)
        if mark.mode != 'RGBA':
            mark = mark.convert('RGBA')
            
        # 调整水印大小
        ratio = min(base_image.size) * size / 100 / max(mark.size)
        new_size = tuple(int(dim * ratio) for dim in mark.size)
        mark = mark.resize(new_size, Image.LANCZOS)
        
        # 调整透明度
        alpha = int(255 * opacity / 100)
        mark.putalpha(alpha)
        
        # 计算位置
        x, y = self._calculate_position(
            position,
            base_image.size[0],
            base_image.size[1],
            mark.size[0],
            mark.size[1]
        )
        
        # 粘贴水印
        base_image.paste(mark, (x, y), mark)
        
    def _calculate_position(
        self, 
        position: str, 
        width: int, 
        height: int,
        mark_width: int,
        mark_height: int
    ) -> Tuple[int, int]:
        """计算水印位置"""
        padding = 20  # 边距
        
        positions = {
            'center': ((width - mark_width) // 2, (height - mark_height) // 2),
            'top-left': (padding, padding),
            'top-right': (width - mark_width - padding, padding),
            'bottom-left': (padding, height - mark_height - padding),
            'bottom-right': (width - mark_width - padding, height - mark_height - padding)
        }
        
        return positions.get(position, positions['center'])
        
    def _save_image(self, image: Image) -> str:
        """保存处理后的图片"""
        try:
            filename = f"{uuid.uuid4()}.png"
            # 构建完整的文件系统路径
            filepath = os.path.join(self.upload_folder, filename)
            
            # 确保目录存在并有写入权限
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            current_app.logger.debug(f"Attempting to save file to: {filepath}")
            
            # 保存前检查目录权限
            if not os.access(os.path.dirname(filepath), os.W_OK):
                raise Exception(f"No write permission for directory: {os.path.dirname(filepath)}")
            
            # 保存图片
            image.save(filepath, 'PNG')
            
            # 验证文件是否已保存
            if not os.path.exists(filepath):
                raise Exception(f"Failed to save file to {filepath}")
            
            current_app.logger.info(f"File saved successfully at {filepath}")
            file_size = os.path.getsize(filepath)
            current_app.logger.debug(f"Saved file size: {file_size} bytes")
            
            # 返回相对路径，不要包含开头的斜杠
            return os.path.join('uploads', 'watermark', filename)
            
        except Exception as e:
            current_app.logger.error(f"保存图片失败: {str(e)}")
            raise
        
    def cleanup(self):
        """清理临时文件"""
        for file in self.temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                current_app.logger.error(f"清理临时文件失败: {str(e)}")