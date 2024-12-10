from rembg import remove, new_session
from PIL import Image
import os
from flask import current_app
import uuid
import numpy as np
from .face_detection import FaceDetector
from typing import Tuple

def is_portrait_image(image: Image.Image) -> bool:
    """
    综合判断图片是否为人像
    
    Args:
        image: PIL Image对象
    
    Returns:
        bool: 是否为人像
    """
    # 转换为numpy数组
    img_array = np.array(image)
    
    # 初始化人脸检测器
    face_detector = FaceDetector(current_app.config['CASCADE_PATH'])
    
    # 特征1: 检查图像比例
    height, width = img_array.shape[:2]
    aspect_ratio = height / width
    is_portrait_ratio = 0.75 < aspect_ratio < 2.5  # 更宽松的比例范围
    
    # 特征2: 检测肤色比例
    skin_ratio = face_detector.detect_skin_tone(img_array)
    has_skin = skin_ratio > 0.05  # 至少5%的肤色像素
    
    # 特征3: 人脸检测
    has_face = face_detector.detect_faces(img_array)
    
    # 综合判断
    # 1. 如果检测到人脸，直接判定为人像
    if has_face:
        return True
    
    # 2. 比例合适且有足够的肤色像素，判定为人像
    if is_portrait_ratio and has_skin:
        return True
    
    # 3. 如果肤色比例特别高，也判定为人像
    if skin_ratio > 0.15:  # 超过15%的肤色像素
        return True
    
    return False

def detect_image_type(image: Image.Image) -> Tuple[str, dict]:
    """
    检测图片类型，选择合适的模型和参数
    
    Args:
        image: PIL Image对象
    
    Returns:
        Tuple[str, dict]: (模型名称, 模型特定参数)
    """
    try:
        # 转换为numpy数组进行分析
        img_array = np.array(image)
        face_detector = FaceDetector(current_app.config['CASCADE_PATH'])
        
        # 检测是否为人像
        if is_portrait_image(image):
            return "u2net_human_seg", {
                'alpha_matting_foreground_threshold': 240,
                'alpha_matting_background_threshold': 10,
                'alpha_matting_erode_size': 5,
                'post_process_mask': True
            }
        
        # 检测图像尺寸和比例
        height, width = img_array.shape[:2]
        aspect_ratio = height / width
        
        # 对于细长的图像（如全身照或长条形物体），使用silueta模型
        if aspect_ratio > 2.0 or aspect_ratio < 0.5:
            return "silueta", {
                'alpha_matting_foreground_threshold': 250,
                'alpha_matting_background_threshold': 5,
                'alpha_matting_erode_size': 15,
                'post_process_mask': True
            }
        
        # 对于大尺寸复杂图像，使用isnet-general-use模型
        if max(width, height) > 2000:
            return "isnet-general-use", {
                'alpha_matting_foreground_threshold': 240,
                'alpha_matting_background_threshold': 15,
                'alpha_matting_erode_size': 10,
                'post_process_mask': True
            }
        
        # 对于小尺寸图像，使用轻量级的u2netp模型
        if max(width, height) < 512:
            return "u2netp", {
                'alpha_matting_foreground_threshold': 230,
                'alpha_matting_background_threshold': 20,
                'alpha_matting_erode_size': 3,
                'post_process_mask': True
            }
        
        # 默认使用u2net通用模型
        return "u2net", {
            'alpha_matting_foreground_threshold': 250,
            'alpha_matting_background_threshold': 5,
            'alpha_matting_erode_size': 10,
            'post_process_mask': True
        }
        
    except Exception as e:
        current_app.logger.warning(f"像型检测失败: {str(e)}, 使用默认模型")
        return "u2net", {
            'alpha_matting_foreground_threshold': 250,
            'alpha_matting_background_threshold': 5,
            'alpha_matting_erode_size': 10,
            'post_process_mask': True
        }

def optimize_image(image: Image.Image, max_size: int = 3072) -> Image.Image:
    """
    优化图像大小和格式,保持更高质量
    """
    # 增加最大尺寸以保持更多细节
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # 确保图像模式正确,保持原始颜色空间
    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGBA' if 'A' in image.mode else 'RGB')
    
    return image

def remove_background(input_path: str) -> str:
    """
    移除图片背景并保存处理后的图片
    """
    # 设置环境变量
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    
    # 使用绝对路径并指向u2net子目录
    # 获取项目根目录的绝对路径
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    u2net_path = os.path.join(root_dir, current_app.config['U2NET_HOME'])
    os.environ['U2NET_HOME'] = u2net_path
    
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['ONNXRUNTIME_PROVIDER'] = 'CPUExecutionProvider'
    os.environ['ONNXRUNTIME_PROVIDERS'] = '["CPUExecutionProvider"]'
    
    # 确保模型目录存在
    os.makedirs(u2net_path, exist_ok=True)
    
    # 检查并修正模型文件名
    model_map = {
        'u2net': 'u2net.onnx',
        'u2netp': 'u2netp.onnx',
        'u2net_human_seg': 'u2net_human_seg.onnx',
        'silueta': 'silueta.onnx',
        'isnet-general-use': 'isnet-general-use.onnx'
    }
    
    # 预先检查所需模型是否存在
    model_name, _ = detect_image_type(Image.open(input_path))
    model_file = os.path.join(u2net_path, model_map[model_name])
    
    if not os.path.exists(model_file):
        raise FileNotFoundError(f"模型文件不存在: {model_file}")
    
    output_filename = f"{uuid.uuid4()}.png"
    output_path = os.path.join(current_app.config['REMOVE_BG_FOLDER'], output_filename)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        input_image = Image.open(input_path)
        input_image = optimize_image(input_image)
        
        # 获取模型名称和特定参数
        model_name, model_params = detect_image_type(input_image)
        
        # 指定仅使用CPU的会话
        session = new_session(
            model_name=model_name,
            providers=['CPUExecutionProvider']
        )
        
        # 基础参数
        remove_params = {
            'session': session,
            'alpha_matting': True,
            'post_process_mask': True,
            'only_mask': False,
            'bgcolor': None,
        }
        
        # 合并模型特定参数
        remove_params.update(model_params)
        
        # 移除背景
        output_image = remove(input_image, **remove_params)
        
        # 后处理优化
        if output_image.mode == 'RGBA':
            # 提高透明度的精确度
            alpha = output_image.split()[3]
            # 根据模型类型调整透明度阈值
            threshold = model_params.get('alpha_matting_background_threshold', 5)
            # 使用更平滑的透明度过渡
            alpha = alpha.point(lambda x: max(0, min(255, int(1.5 * x))) if x > threshold else 0)
            r, g, b, _ = output_image.split()
            output_image = Image.merge('RGBA', (r, g, b, alpha))
        
        # 保存处理后的图片
        output_image.save(
            output_path, 
            'PNG',
            optimize=True,
            quality=100,
            compress_level=1
        )
        
        os.remove(input_path)
        return f"/static/uploads/remove_bg/{output_filename}"
        
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e