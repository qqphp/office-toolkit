import cv2
import numpy as np
import os
from PIL import Image
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

class BlurFaceService:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(current_app.config['CASCADE_PATH'], 'haarcascade_frontalface_default.xml')
        )
        self.temp_files = []  # 只用于存储临时的上传文件路径

    def process_image(self, file):
        """处理图片，检测并模糊面部"""
        # 保存上传的文件
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        self.temp_files.append(temp_path)  # 只添加临时上传文件

        try:
            # 读取图片
            image = cv2.imread(temp_path)
            if image is None:
                raise ValueError('无法读取图片')

            # 转换为灰度图进行人脸检测
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            # 对检测到的每个人脸进行模糊处理
            for (x, y, w, h) in faces:
                # 提取人脸区域
                face_roi = image[y:y+h, x:x+w]
                # 应用高斯模糊
                blurred_face = cv2.GaussianBlur(face_roi, (99, 99), 30)
                # 将模糊后的人脸放回原图
                image[y:y+h, x:x+w] = blurred_face

            # 如果没有检测到人脸
            if len(faces) == 0:
                raise ValueError('未检测到人脸')

            # 保存处理后的图片
            output_filename = f"blurred_{uuid.uuid4().hex[:8]}_{filename}"
            output_path = os.path.join(current_app.config['BLUR_FACE_FOLDER'], output_filename)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存图片（这个不添加到 temp_files，因为需要保留）
            cv2.imwrite(output_path, image)

            # 返回相对URL路径
            return os.path.join('static', 'uploads', 'blur_face', output_filename)

        except Exception as e:
            raise e

    def cleanup(self):
        """只清理临时的上传文件"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                current_app.logger.error(f"清理临时文件失败 {file_path}: {str(e)}") 