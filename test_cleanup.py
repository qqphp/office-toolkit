from app import create_app
from app.services.cleanup_service import CleanupService
import os
import time
from pathlib import Path

def test_cleanup():
    # 创建应用实例
    app = create_app()
    uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
    
    # 创建测试文件的函数
    def create_test_files(directory):
        try:
            # 确保目录存在
            os.makedirs(directory, exist_ok=True)
            
            # 创建.gitkeep文件（如果不存在）
            gitkeep_path = os.path.join(directory, '.gitkeep')
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, 'w') as f:
                    f.write('')
            
            # 创建3个测试文件
            created_files = []
            for i in range(3):
                filepath = os.path.join(directory, f'test_file_{i+1}.txt')
                with open(filepath, 'w') as f:
                    f.write(f'test content {i+1}')
                created_files.append(filepath)
            
            return created_files
                
        except Exception as e:
            print(f"Error creating test files in {directory}: {str(e)}")
            return []

    # 创建测试文件
    test_files = []
    directories = ['remove_bg', 'img_to_pdf', 'watermark', 'compress', 'blur_face', 'crop']
    
    print("Creating test files...")
    for subdir in directories:
        dir_path = os.path.join(uploads_dir, subdir)
        files = create_test_files(dir_path)
        test_files.extend(files)
    
    if not test_files:
        print("No test files were created!")
        return
    
    print(f"Created {len(test_files)} test files")
    
    # 运行清理服务
    print("\nRunning cleanup service...")
    cleanup_service = CleanupService()
    cleanup_service.cleanup_old_files(app)
    
    # 验证结果
    print("\nVerifying results...")
    all_correct = True
    for subdir in directories:
        dir_path = os.path.join(uploads_dir, subdir)
        remaining_files = os.listdir(dir_path)
        
        # 验证是否只剩下.gitkeep
        if not (len(remaining_files) == 1 and remaining_files[0] == '.gitkeep'):
            all_correct = False
            print(f"Directory {subdir}: Unexpected files remain: {remaining_files}")
    
    if all_correct:
        print("✓ All directories cleaned successfully - only .gitkeep files remain")

if __name__ == "__main__":
    test_cleanup()
