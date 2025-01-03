import os
import time
from datetime import datetime, timedelta
from flask import Flask, current_app
import logging

class CleanupService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 设置日志级别
        self.logger.setLevel(logging.INFO)
        # 添加控制台处理器
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        
    def cleanup_old_files(self, app: Flask):
        """清理所有文件，只保留.gitkeep"""
        self.logger.info("Starting cleanup task...")
        try:
            # 获取uploads目录的绝对路径
            uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
            self.logger.info(f"Scanning directory: {uploads_dir}")
            
            files_checked = 0
            files_removed = 0
            
            # 遍历所有子目录
            for subdir in ['remove_bg', 'img_to_pdf', 'watermark', 'compress', 'blur_face', 'crop']:
                dir_path = os.path.join(uploads_dir, subdir)
                if not os.path.exists(dir_path):
                    self.logger.info(f"Directory not found: {dir_path}")
                    continue
                    
                self.logger.info(f"Cleaning up directory: {dir_path}")
                
                # 遍历目录中的所有文件
                for filename in os.listdir(dir_path):
                    files_checked += 1
                    
                    # 跳过 .gitkeep 文件
                    if filename == '.gitkeep':
                        self.logger.info(f"Keeping file: {filename}")
                        continue
                        
                    file_path = os.path.join(dir_path, filename)
                    if not os.path.isfile(file_path):
                        continue
                        
                    try:
                        os.remove(file_path)
                        files_removed += 1
                        self.logger.info(f"Removed file: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Error removing file {file_path}: {str(e)}")
            
            self.logger.info(f"Cleanup completed. Checked {files_checked} files, removed {files_removed} files.")
                            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}") 