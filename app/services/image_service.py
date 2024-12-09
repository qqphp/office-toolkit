from rembg import remove, new_session
from PIL import Image
import os
from flask import current_app
import uuid

def remove_background(input_path: str) -> str:
    """
    移除图片背景并保存处理后的图片
    
    Args:
        input_path: 输入图片路径
    
    Returns:
        str: 处理后图片的URL路径
    """
    # 设置模型路径环境变量
    os.environ['U2NET_HOME'] = current_app.config['U2NET_HOME']
    
    # 生成唯一的输出文件名
    output_filename = f"{uuid.uuid4()}.png"
    output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], output_filename)
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # 读取输入图片
        input_image = Image.open(input_path)
        
        # 创建一个新的会话，使用本地模型
        session = new_session(model_name="isnet-general-use")
        
        # 移除背景，添加额外参数提高精度
        output_image = remove(
            input_image,
            session=session,
            alpha_matting=True,              # 启用 alpha matting
            alpha_matting_foreground_threshold=240,  # 前景阈值
            alpha_matting_background_threshold=10,   # 背景阈值
            alpha_matting_erode_size=10,     # 腐蚀大小
            post_process_mask=True,          # 启用后处理
        )
        
        # 保存处理后的图片，使用最高质量设置
        output_image.save(
            output_path, 
            'PNG',
            optimize=True,
            quality=95
        )
        
        # 删除原始上传文件
        os.remove(input_path)
        
        # 返回相对于static目录的URL路径
        return f"/static/uploads/{output_filename}"
        
    except Exception as e:
        # 清理任何临时文件
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e 