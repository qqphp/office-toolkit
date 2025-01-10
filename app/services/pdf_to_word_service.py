import os
import uuid
from pathlib import Path
from pdf2docx import Converter
from flask import current_app
import logging
from typing import Tuple

class PDFToWordService:
    def __init__(self):
        self.upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'pdf_to_word')
        self.ensure_upload_dir()
        
    def ensure_upload_dir(self):
        """确保上传目录存在"""
        os.makedirs(self.upload_dir, exist_ok=True)
        # 确保.gitkeep文件存在
        gitkeep_path = os.path.join(self.upload_dir, '.gitkeep')
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, 'w') as f:
                f.write('')

    def convert_pdf_to_word(self, pdf_file) -> Tuple[str, str]:
        """
        将PDF文件转换为Word文档
        
        Args:
            pdf_file: 上传的PDF文件对象
            
        Returns:
            Tuple[str, str]: (word文件路径, 生成的文件名)
            
        Raises:
            ValueError: 当文件格式无效时
            RuntimeError: 当转换过程失败时
        """
        try:
            # 验证文件格式
            if not pdf_file or not pdf_file.filename.lower().endswith('.pdf'):
                raise ValueError('请上传有效的PDF文件')

            # 生成唯一的文件名
            pdf_filename = f"upload_{uuid.uuid4().hex}.pdf"
            word_filename = f"converted_{uuid.uuid4().hex}.docx"
            
            pdf_path = os.path.join(self.upload_dir, pdf_filename)
            word_path = os.path.join(self.upload_dir, word_filename)

            # 保存上传的PDF文件
            pdf_file.save(pdf_path)
            
            # 转换PDF到Word
            cv = Converter(pdf_path)
            cv.convert(word_path)
            cv.close()
            
            # 验证生成的文件
            if not os.path.exists(word_path):
                raise RuntimeError('Word文件生成失败')
                
            # 删除临时PDF文件
            os.remove(pdf_path)
            
            return word_path, word_filename
            
        except Exception as e:
            # 清理任何临时文件
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)
            if 'word_path' in locals() and os.path.exists(word_path):
                os.remove(word_path)
            
            current_app.logger.error(f"PDF转Word失败: {str(e)}")
            raise RuntimeError(f"转换失败: {str(e)}") 