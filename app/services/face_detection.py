import cv2
import numpy as np
import os
from typing import Tuple

class FaceDetector:
    """人脸检测器类"""
    
    def __init__(self, cascade_path: str):
        """
        初始化人脸检测器
        
        Args:
            cascade_path: 级联分类器文件所在目录
        """
        # 加载级联分类器
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(cascade_path, 'haarcascade_frontalface_default.xml')
        )
        self.profile_cascade = cv2.CascadeClassifier(
            os.path.join(cascade_path, 'haarcascade_profileface.xml')
        )
        self.eye_cascade = cv2.CascadeClassifier(
            os.path.join(cascade_path, 'haarcascade_eye.xml')
        )
        
        # 禁用OpenCL以确保CPU处理
        cv2.ocl.setUseOpenCL(False)

    def detect_faces(self, img_array: np.ndarray) -> bool:
        """
        使用多个级联分类器检测图像中的人脸
        
        Args:
            img_array: numpy格式的图片数组
            
        Returns:
            bool: 是否检测到人脸
        """
        # 转换为灰度图并进行直方图均衡化
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        gray = cv2.equalizeHist(gray)
        
        # 检测正面人脸
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            maxSize=(300, 300)
        )
        
        if len(faces) > 0:
            # 在检测到的人脸区域中寻找眼睛以确认
            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
                eyes = self.eye_cascade.detectMultiScale(roi_gray)
                if len(eyes) > 0:
                    return True
        
        # 如果没有检测到正面人脸，尝试检测侧面人脸
        profile_faces = self.profile_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            maxSize=(300, 300)
        )
        
        if len(profile_faces) > 0:
            return True
            
        # 检查镜像图像中的侧面人脸
        flipped = cv2.flip(gray, 1)
        profile_faces = self.profile_cascade.detectMultiScale(
            flipped,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            maxSize=(300, 300)
        )
        
        return len(profile_faces) > 0

    def detect_skin_tone(self, img_array: np.ndarray) -> float:
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