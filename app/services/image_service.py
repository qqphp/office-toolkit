from rembg import remove, new_session
from PIL import Image
import os
from flask import current_app
import uuid
import numpy as np
import cv2
from typing import Tuple, Optional

def detect_skin_tone(img_array: np.ndarray) -> float:
    """
    检测图片中的肤色比例
    
    Args:
        img_array: numpy格式的图片数组
    
    Returns:
        float: 肤色像素占比 (0-1)
    """
    # 转换到YCrCb颜色空间
    img_ycrcb = cv2.cvtColor(img_array, cv2.COLOR_RGB2YCR_CB)
    
    # 定义肤色范围
    lower_skin = np.array([0, 133, 77])
    upper_skin = np.array([255, 173, 127])
    
    # 创建肤色蒙版
    skin_mask = cv2.inRange(img_ycrcb, lower_skin, upper_skin)
    
    # 计算肤色像素占比
    total_pixels = skin_mask.size
    skin_pixels = np.sum(skin_mask > 0)
    
    return skin_pixels / total_pixels

def detect_face(img_array: np.ndarray) -> bool:
    """
    使用OpenCV的人脸检测器检测是否存在人脸
    """
    # 强制使用CPU
    cv2.ocl.setUseOpenCL(False)
    
    # 加载人脸检测器
    face_cascade_path = os.path.join(current_app.config['CASCADE_PATH'], 'haarcascade_frontalface_default.xml')
    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    
    # 转换为灰度图并进行直方图均衡化以提高检测效果
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    
    # 使用更保守的参数进行人脸检测
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.05,  # 更小的缩放因子
        minNeighbors=6,    # 更多的邻居要求
        minSize=(35, 35),  # 稍大的最小人脸尺寸
        maxSize=(300, 300) # 限制最大人脸尺寸
    )
    
    return len(faces) > 0

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
    
    # 特征1: 检查图像比例
    height, width = img_array.shape[:2]
    aspect_ratio = height / width
    is_portrait_ratio = 0.75 < aspect_ratio < 2.5  # 更宽松的比例范围
    
    # 特征2: 检测肤色比例
    skin_ratio = detect_skin_tone(img_array)
    has_skin = skin_ratio > 0.05  # 至少5%的肤色像素
    
    # 特征3: 人脸检测
    has_face = detect_face(img_array)
    
    # 综合���断
    # 1. 如果检测到人脸，直接判定为人像
    if has_face:
        return True
    
    # 2. 如果比例合适且有足够的肤色像素，判定为人像
    if is_portrait_ratio and has_skin:
        return True
    
    # 3. 如果肤色比例特别高，也判定为人像
    if skin_ratio > 0.15:  # 超过15%的肤色像素
        return True
    
    return False

def detect_image_type(image: Image.Image) -> str:
    """
    检测图片类型，选择合适的模型
    
    Args:
        image: PIL Image对象
    
    Returns:
        str: 模型名称
    """
    try:
        if is_portrait_image(image):
            return "u2net_human_seg"
    except Exception as e:
        current_app.logger.warning(f"人像检测失败: {str(e)}, 使用默认模型")
    
    return "u2net"  # 默认使用通用模型

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
    # 强制使用CPU
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    os.environ['U2NET_HOME'] = current_app.config['U2NET_HOME']
    # 禁用所有GPU相关提供程序
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['ONNXRUNTIME_PROVIDER'] = 'CPUExecutionProvider'
    os.environ['ONNXRUNTIME_PROVIDERS'] = '["CPUExecutionProvider"]'
    
    output_filename = f"{uuid.uuid4()}.png"
    output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], output_filename)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        input_image = Image.open(input_path)
        input_image = optimize_image(input_image)
        
        model_name = detect_image_type(input_image)
        # 指定仅使用CPU的会话
        session = new_session(
            model_name=model_name,
            providers=['CPUExecutionProvider']
        )
        
        # 优化移除背景的参数
        remove_params = {
            'session': session,
            'alpha_matting': True,
            'alpha_matting_foreground_threshold': 250,  # 更严格的前景阈值
            'alpha_matting_background_threshold': 5,    # 更严格的背景阈值
            'alpha_matting_erode_size': 10,            # 减小腐蚀尺寸以保留更多细节
            'post_process_mask': True,
            'only_mask': False,
            'bgcolor': None,
        }
        
        # 为人像模型进一步优化参数
        if model_name == "u2net_human_seg":
            remove_params.update({
                'alpha_matting_foreground_threshold': 240,  # 稍微放宽人像前景阈值
                'alpha_matting_erode_size': 5,             # 更小的腐蚀尺寸保留发丝等细节
            })
        
        # 移除背景
        output_image = remove(input_image, **remove_params)
        
        # 后处理优化
        if output_image.mode == 'RGBA':
            # 提高透明度的精确度
            alpha = output_image.split()[3]
            # 根据模型类型调整透明度阈值
            threshold = 80 if model_name == "u2net_human_seg" else 100
            # 使用更平滑的透���度过渡
            alpha = alpha.point(lambda x: max(0, min(255, int(1.5 * x))) if x > threshold else 0)
            r, g, b, _ = output_image.split()
            output_image = Image.merge('RGBA', (r, g, b, alpha))
        
        # 保存处理后的图片,使用最高质量设置
        output_image.save(
            output_path, 
            'PNG',
            optimize=True,
            quality=100,  # 最高质量
            compress_level=1  # 最小压缩以保持质量
        )
        
        os.remove(input_path)
        return f"/static/uploads/{output_filename}"
        
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e