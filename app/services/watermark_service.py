from flask import current_app
from PIL import Image, ImageDraw, ImageFont
import os
import uuid
from typing import Optional, Tuple, Dict
import io
import math

class WatermarkService:
    def __init__(self):
        # 使用 current_app.root_path 获取应用根目录的绝对路径
        app_root = current_app.root_path
        self.upload_folder = os.path.join(app_root, 'static', 'uploads', 'watermark')
        self.fonts_folder = os.path.join(app_root, 'static', 'fonts')
        self.temp_files = []
        
        # 定义字体映射
        self.font_map = {
            'noto-sans': 'NotoSansSC-Regular.otf',      # 思源黑体
            'noto-serif': 'NotoSerifSC-Regular.otf',    # 思源宋体
            'harmony-sans': 'HarmonyOS_Sans_SC_Regular.ttf',  # 鸿蒙字体
            'lxgw': 'LXGWWenKai-Regular.ttf',           # 霞鹜文楷
            'source-han': 'SourceHanSansCN-Regular.otf'  # 思源黑体 CN
        }
        
        current_app.logger.debug(f"Upload folder path: {self.upload_folder}")
        current_app.logger.debug(f"Fonts folder path: {self.fonts_folder}")
        
        # 检查字体文件是否存在
        for font_name, font_file in self.font_map.items():
            font_path = os.path.join(self.fonts_folder, font_file)
            if not os.path.exists(font_path):
                current_app.logger.warning(f"Font file not found: {font_path}")
        
    def add_watermark(self, image_file, options: Dict) -> str:
        """添加水印到图片"""
        try:
            # 添加日志以跟踪参数
            current_app.logger.debug(f"Processing watermark with options: {options}")
            
            # 打开原图
            image = Image.open(image_file)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                
            # 创建水印层
            watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark)
            
            if options['type'] == 'text':
                self._add_text_watermark(
                    watermark,
                    draw, 
                    watermark.size, 
                    options['text'],
                    options['position'],
                    options['opacity'],
                    options['size'],
                    rotation=options['rotation'],
                    font_name=options['font_name'],
                    color=options['color']
                )
            else:
                watermark_image = options.get('image')
                if watermark_image:
                    self._add_image_watermark(
                        watermark,
                        watermark_image,
                        options['position'],
                        options['opacity'],
                        options['size'],
                        rotation=options['rotation']
                    )
            
            # 合并原图和水印
            result = Image.alpha_composite(image, watermark)
            
            # 保存结果
            return self._save_image(result)
            
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
        font_name: str = 'noto-sans',
        color: str = '#000000'
    ):
        """添加文字水印"""
        try:
            # 计算字体大小 - 使用更合理的计算方式
            base_size = min(size[0], size[1])  # 使用较小的边作为基准
            
            # text_size 现在是 1-50 的值，将其映射到合适的字体大小范围
            min_font_size = 12
            max_font_size = int(base_size * 0.2)  # 最大字体大小为图片较小边的 20%
            
            # 线性映射 text_size (1-50) 到字体大小范围
            font_size = min_font_size + (max_font_size - min_font_size) * (text_size / 50)
            font_size = int(font_size)
            
            current_app.logger.debug(f"Base size: {base_size}, Text size: {text_size}, Font size: {font_size}")
            
            # 根据文字长度调整字体大小
            if len(text) > 10:
                # 使用对数调整，避免文字过长时字体太小
                adjustment = 1 - math.log(len(text) - 9, 20)  # 使用对数函数使调整更平滑
                font_size = int(font_size * max(0.5, adjustment))  # 确保字体不会小于原大小的一半
                current_app.logger.debug(f"Adjusted font size for long text: {font_size}")
            
            # 加字体
            font_file = self.font_map.get(font_name.lower(), 'NotoSansSC-Regular.otf')
            font_path = os.path.join(self.fonts_folder, font_file)
            
            if not os.path.exists(font_path):
                current_app.logger.warning(f"Font file not found: {font_path}, trying fallback font")
                fallback_fonts = ['NotoSansSC-Regular.otf', 'SourceHanSansCN-Regular.otf']
                for fallback_font in fallback_fonts:
                    fallback_path = os.path.join(self.fonts_folder, fallback_font)
                    if os.path.exists(fallback_path):
                        font_path = fallback_path
                        break
            
            font = ImageFont.truetype(font_path, font_size)
            current_app.logger.debug(f"Using font: {font_path} with size {font_size}")
            
            # 创建一个临时画布来计算文字实际大小
            temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 创建一个足够大的画布来容纳旋转后的文字
            # 使用勾股定理计算旋转后的最大尺寸
            angle_rad = math.radians(abs(rotation))
            rotated_width = int(abs(text_width * math.cos(angle_rad)) + abs(text_height * math.sin(angle_rad)))
            rotated_height = int(abs(text_width * math.sin(angle_rad)) + abs(text_height * math.cos(angle_rad)))
            
            # 确保画布足够大
            canvas_width = max(rotated_width, text_width) + 100  # 添加一些额外的边距
            canvas_height = max(rotated_height, text_height) + 100
            
            # 创建新画布
            txt = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 0))
            d = ImageDraw.Draw(txt)

            # 转换颜色格式
            color = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            color = color + (int(255 * opacity / 100),)

            # 在画布正中心绘制文字
            center_x = canvas_width // 2
            center_y = canvas_height // 2
            d.text((center_x, center_y), text, font=font, fill=color, anchor="mm")

            # 如果需要旋转
            if rotation:
                txt = txt.rotate(float(rotation), expand=True, fillcolor=(255, 255, 255, 0))

            # 裁剪掉多余的透明部分
            bbox = txt.getbbox()
            if bbox:
                txt = txt.crop(bbox)

            # 计算在原图上的位置
            x, y = self._calculate_position(
                position,
                size[0],
                size[1],
                txt.width,
                txt.height
            )

            # 直接粘贴，不需要额外的偏移计算
            watermark.paste(txt, (x, y), txt)

        except Exception as e:
            current_app.logger.error(f"Failed to add text watermark: {str(e)}")
            raise
        
    def _add_image_watermark(
        self, 
        base_image: Image, 
        watermark_image,
        position: str,
        opacity: int,
        size: int,
        rotation: float = 0
    ):
        """添加图片水印"""
        try:
            mark = Image.open(watermark_image)
            if mark.mode != 'RGBA':
                mark = mark.convert('RGBA')
                
            # 调整水大小
            ratio = min(base_image.size) * size / 100 / max(mark.size)
            new_size = tuple(int(dim * ratio) for dim in mark.size)
            mark = mark.resize(new_size, Image.LANCZOS)
            
            # 调整透明度
            alpha = int(255 * opacity / 100)
            mark.putalpha(alpha)
            
            # 旋转图片（如果需要）
            if rotation:
                # 使用白色透明背景进行旋转
                mark = mark.rotate(float(rotation), expand=True, fillcolor=(255, 255, 255, 0))
            
            # 计算位置（考虑旋转后的新尺寸）
            x, y = self._calculate_position(
                position,
                base_image.size[0],
                base_image.size[1],
                mark.size[0],
                mark.size[1]
            )
            
            # 贴水印
            base_image.paste(mark, (x, y), mark)
            
        except Exception as e:
            current_app.logger.error(f"Failed to add image watermark: {str(e)}")
            raise
        
    def _calculate_position(
        self, 
        position: str, 
        width: int, 
        height: int,
        mark_width: int,
        mark_height: int
    ) -> Tuple[int, int]:
        """
        计算水印位置
        
        Args:
            position: 位置标识（'center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'）
            width: 原图宽度
            height: 原图高度
            mark_width: 水印宽度
            mark_height: 水印高度
            
        Returns:
            Tuple[int, int]: 水印的(x, y)坐标
        """
        try:
            # 设置边距（可以根据图片大小动态调整）
            padding_ratio = 0.05  # 边距比例为图片尺寸的 5%
            padding_x = int(width * padding_ratio)
            padding_y = int(height * padding_ratio)
            
            # 确保边距不会太大或太小
            padding_x = max(20, min(padding_x, 100))
            padding_y = max(20, min(padding_y, 100))
            
            # 计算各个位置的坐标
            positions = {
                # 居中：精确计算中心点位置
                'center': (
                    (width - mark_width) // 2,
                    (height - mark_height) // 2
                ),
                
                # 左上角：考虑边距
                'top-left': (
                    padding_x,
                    padding_y
                ),
                
                # 右上角：考虑边距和水印宽度
                'top-right': (
                    width - mark_width - padding_x,
                    padding_y
                ),
                
                # 左下角：考虑边距和水印高度
                'bottom-left': (
                    padding_x,
                    height - mark_height - padding_y
                ),
                
                # 右下角：考虑边距和水印尺寸
                'bottom-right': (
                    width - mark_width - padding_x,
                    height - mark_height - padding_y
                )
            }
            
            # 获取计算后的位置，如果位置不存在则使用居中位置
            x, y = positions.get(position, positions['center'])
            
            # 确保水印不会超出图片边界
            x = max(0, min(x, width - mark_width))
            y = max(0, min(y, height - mark_height))
            
            current_app.logger.debug(
                f"Position calculation: {position}, "
                f"Image size: ({width}, {height}), "
                f"Watermark size: ({mark_width}, {mark_height}), "
                f"Result: ({x}, {y})"
            )
            
            return x, y
            
        except Exception as e:
            current_app.logger.error(f"Error calculating position: {str(e)}")
            # 发生错误时返回居中位置
            return (width - mark_width) // 2, (height - mark_height) // 2
        
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