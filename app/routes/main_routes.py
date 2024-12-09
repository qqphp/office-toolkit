from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.services.image_service import remove_background
import os
import uuid

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS'] 