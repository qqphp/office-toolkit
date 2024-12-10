from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.services.image_service import remove_background
import os
import uuid
import zipfile
from io import BytesIO
from flask import send_file
import time
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

main_bp = Blueprint('main', __name__)

@main_bp.route('/home')
@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/remove-bg')
def index():
    return render_template('remove_bg.html')

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

@main_bp.route('/download-image', methods=['POST'])
def download_image():
    data = request.get_json()
    if not data or 'image_url' not in data:
        return jsonify({'error': '无效的请求'}), 400
        
    image_url = data['image_url']
    bg_color = data.get('background_color', 'transparent')
    
    try:
        # 修正图片路径处理
        # 从 URL 中提取相对路径
        relative_path = image_url.split('/static/')[-1] if '/static/' in image_url else image_url.lstrip('/')
        # 构建完整的文件系统路径
        image_path = os.path.join(current_app.root_path, 'static', relative_path)
        
        current_app.logger.debug(f"Attempting to access image at: {image_path}")  # 添加日志
        
        if not os.path.exists(image_path):
            current_app.logger.error(f"Image not found at path: {image_path}")  # 添加日志
            return jsonify({'error': '图片不存在'}), 404
            
        # 打开图片
        img = Image.open(image_path)
        
        # 如果指定了背景颜色且不是透明
        if bg_color != 'transparent':
            # 创建新的图片，使用指定的背景颜色
            background = Image.new('RGBA', img.size, bg_color)
            # 将原图复制到背景上
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
            
        # 将图片保存到内存中
        img_io = io.BytesIO()
        img.save(img_io, 'PNG', quality=95)
        img_io.seek(0)
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'processed_image_{timestamp}.png'
        )
        
    except Exception as e:
        current_app.logger.error(f"下载图片失败: {str(e)}")
        return jsonify({'error': '处理图片失败'}), 500

@main_bp.route('/download-all', methods=['POST'])
def download_all():
    data = request.get_json()
    if not data or 'files' not in data:
        return jsonify({'error': '无效的请求'}), 400
        
    files = data['files']
    bg_color = data.get('background_color', 'transparent')
    
    if not files:
        return jsonify({'error': '没有可下载的文件'}), 400
        
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, file_url in enumerate(files):
                # 修正图片路径处理
                relative_path = file_url.split('/static/')[-1] if '/static/' in file_url else file_url.lstrip('/')
                image_path = os.path.join(current_app.root_path, 'static', relative_path)
                
                if not os.path.exists(image_path):
                    current_app.logger.warning(f"Skipping non-existent file: {image_path}")
                    continue
                    
                # 打开图片
                img = Image.open(image_path)
                
                # 如果指定了背景颜色且不是透明
                if bg_color != 'transparent':
                    background = Image.new('RGBA', img.size, bg_color)
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img)
                    img = background
                
                # 将处理后的图片保存到内存中
                img_io = io.BytesIO()
                img.save(img_io, 'PNG', quality=95)
                img_io.seek(0)
                
                # 添加到zip文件
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                zf.writestr(f'processed_image_{i+1}_{timestamp}.png', img_io.getvalue())

        memory_file.seek(0)
        
        # 生成随机字符串
        random_str = uuid.uuid4().hex[:8]
        # 构造下载文件名
        download_filename = f'wuying_{random_str}.zip'
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=download_filename  # 使用新的文件名格式
        )
        
    except Exception as e:
        current_app.logger.error(f"打包下载失败: {str(e)}")
        return jsonify({'error': '打包文件失败'}), 500

@main_bp.route('/convert-pdf')
def convert_pdf():
    return render_template('convert_pdf.html')

@main_bp.route('/convert-to-pdf', methods=['POST'])
def convert_to_pdf():
    if 'images' not in request.files:
        current_app.logger.error("No files in request")
        return jsonify({'error': '没有上传文件'}), 400
        
    files = request.files.getlist('images')
    if not files:
        current_app.logger.error("Empty files list")
        return jsonify({'error': '没有选择文件'}), 400
        
    # 创建保存目录
    save_dir = os.path.join(current_app.root_path, current_app.config['IMG_TO_PDF_FOLDER'])
    os.makedirs(save_dir, exist_ok=True)
    
    # 保存的文件路径列表
    saved_files = []
    
    try:
        # 先保存所有图片
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                try:
                    # 生成唯一文件名
                    original_filename = secure_filename(file.filename)
                    extension = os.path.splitext(original_filename)[1]
                    unique_filename = f"{uuid.uuid4().hex}{extension}"
                    filepath = os.path.join(save_dir, unique_filename)
                    
                    # 保存文件
                    file.save(filepath)
                    saved_files.append(filepath)
                    
                except Exception as e:
                    current_app.logger.error(f"Error saving file {i+1}: {str(e)}")
                    raise
            else:
                current_app.logger.warning(f"Invalid file: {file.filename if file else 'None'}")
        
        # 创建PDF
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=A4)
        
        for i, filepath in enumerate(saved_files):
            try:
                # 读取图片
                img = Image.open(filepath)
                
                # 调整图片大小以适应A4页面
                img_width, img_height = img.size
                aspect = img_height / float(img_width)
                
                # A4页面尺寸(单位：点）
                a4_width, a4_height = A4
                
                # 设置图片在页面上的最大宽度（留出边距）
                max_width = a4_width - 40  # 左右各留20点边距
                
                # 计算等比例缩放后的高度
                width = max_width
                height = width * aspect
                
                # 如果高度超出页面，则按高度进行缩放
                if height > (a4_height - 40):  # 上下各留20点边距
                    height = a4_height - 40
                    width = height / aspect
                
                # 计算居中位置
                x = (a4_width - width) / 2
                y = (a4_height - height) / 2
                
                # 将图片绘制到PDF页面
                c.drawImage(ImageReader(img), x, y, width, height)
                c.showPage()
                
            except Exception as e:
                current_app.logger.error(f"Error processing image {i+1}: {str(e)}")
                raise
            finally:
                # 关闭图片
                if 'img' in locals():
                    img.close()
        
        c.save()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='converted.pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"PDF转换失败: {str(e)}", exc_info=True)
        # 发生错误时才清理文件
        for filepath in saved_files:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as cleanup_error:
                current_app.logger.error(f"Error cleaning up {filepath}: {str(cleanup_error)}")
        return jsonify({'error': f'转换失败: {str(e)}'}), 500

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS'] 