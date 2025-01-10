import os
import uuid
from pathlib import Path
from typing import Tuple
import pikepdf
from flask import current_app

class PDFEncryptService:
    def __init__(self):
        self.upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'pdf_encrypt')
        self.ensure_upload_dir()
        
    def ensure_upload_dir(self):
        """确保上传目录存在"""
        os.makedirs(self.upload_dir, exist_ok=True)
        gitkeep_path = os.path.join(self.upload_dir, '.gitkeep')
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, 'w') as f:
                f.write('')

    def encrypt_pdf(self, pdf_file, password: str) -> Tuple[str, str]:
        """
        为PDF文件添加密码保护
        
        Args:
            pdf_file: 上传的PDF文件对象
            password: 设置的密码
            
        Returns:
            Tuple[str, str]: (加密后的PDF路径, 生成的文件名)
            
        Raises:
            ValueError: 当文件格式或密码无效时
            RuntimeError: 当加密过程失败时
        """
        try:
            # 验证文件格式
            if not pdf_file or not pdf_file.filename.lower().endswith('.pdf'):
                raise ValueError('请上传有效的PDF文件')
                
            # 验证密码
            if not password or len(password) < 4:
                raise ValueError('请设置至少4位字符的密码')

            # 生成唯一的文件名
            original_filename = f"upload_{uuid.uuid4().hex}.pdf"
            encrypted_filename = f"encrypted_{uuid.uuid4().hex}.pdf"
            
            original_path = os.path.join(self.upload_dir, original_filename)
            encrypted_path = os.path.join(self.upload_dir, encrypted_filename)

            # 保存上传的PDF文件
            pdf_file.save(original_path)
            
            # 加密PDF
            with pikepdf.open(original_path) as pdf:
                # 设置加密参数
                encryption = pikepdf.Encryption(
                    owner=password,  # 所有者密码
                    user=password,   # 用户密码
                    R=4,            # 使用 R=4 加密方案
                    allow=pikepdf.Permissions(extract=False)  # 禁止提取内容
                )
                
                # 保存加密后的文件
                pdf.save(encrypted_path, encryption=encryption)
            
            # 验证生成的文件
            if not os.path.exists(encrypted_path):
                raise RuntimeError('加密文件生成失败')
                
            # 删除原始PDF文件
            os.remove(original_path)
            
            return encrypted_path, encrypted_filename
            
        except Exception as e:
            # 清理任何临时文件
            if 'original_path' in locals() and os.path.exists(original_path):
                os.remove(original_path)
            if 'encrypted_path' in locals() and os.path.exists(encrypted_path):
                os.remove(encrypted_path)
            
            current_app.logger.error(f"PDF加密失败: {str(e)}")
            raise RuntimeError(f"加密失败: {str(e)}") 