from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.services.image_service import remove_background
import os
import uuid
import zipfile
from io import BytesIO
from flask import send_file
import time

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/remove-background', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 生成唯一文件名避免冲突
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        # 确保上传目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        file.save(filepath)
        
        try:
            result_path = remove_background(filepath)
            return jsonify({
                'success': True,
                'image_url': result_path
            })
        except Exception as e:
            # 清理临时文件
            if os.path.exists(filepath):
                os.remove(filepath)
            current_app.logger.error(f"处理图片失败: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': '不支持的文件类型'}), 400

@main_bp.route('/download-all', methods=['POST'])
def download_all():
    try:
        files = request.json.get('files', [])
        if not files:
            return jsonify({'error': '没有可下载的文件'}), 400

        current_app.logger.debug(f"准备打包文件: {files}")

        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_url in files:
                relative_path = file_url.lstrip('/')
                file_path = os.path.join(current_app.root_path, relative_path)
                
                current_app.logger.debug(f"处理文件: {file_path}")
                
                if os.path.exists(file_path):
                    # 获取原始文件名（去掉UUID前缀）
                    filename = os.path.basename(file_path)
                    # UUID_原始文件名.png 格式
                    parts = filename.split('_', 1)  # 只在第一个下划线处分割
                    if len(parts) > 1:
                        original_filename = parts[1]  # 获取原始文件名部分
                    else:
                        original_filename = filename  # 如果没有下划线，使用完整文件名
                        
                    # 确保文件名以.png结尾
                    if not original_filename.lower().endswith('.png'):
                        original_filename = os.path.splitext(original_filename)[0] + '.png'
                    
                    zf.write(file_path, original_filename)
                    current_app.logger.debug(f"已添加文件: {original_filename}")
                else:
                    current_app.logger.error(f"文件不存在: {file_path}")

        memory_file.seek(0)
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'processed_images_{timestamp}.zip'
        )

    except Exception as e:
        current_app.logger.error(f"打包下载失败: {str(e)}")
        return jsonify({'error': '打包下载失败'}), 500

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS'] 