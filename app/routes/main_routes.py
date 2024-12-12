from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
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
from app.services.pdf_service import PDFService
from app.services.background_service import BackgroundService
from app.services.watermark_service import WatermarkService
from app.services.compress_service import CompressService
from app.services.blur_face_service import BlurFaceService

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
    
    bg_service = BackgroundService()
    try:
        result_path = bg_service.process_image(file)
        return jsonify({
            'success': True,
            'image_url': result_path
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"处理图片失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        bg_service.cleanup()

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

@main_bp.route('/download-all-watermark', methods=['POST'])
def download_all_watermark():
    try:
        # 获取所有处理后的图片路径
        image_paths = request.json.get('paths', [])
        if not image_paths:
            return jsonify({'error': '没有可下载的图片'}), 400
            
        # 创建ZIP文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, path in enumerate(image_paths):
                # 构建完整的文件系统路径
                full_path = os.path.join(current_app.root_path, 'static', path)
                
                # 检查文件是否存在并记录日志
                current_app.logger.debug(f"Processing file: {full_path}")
                
                if os.path.exists(full_path):
                    # 获取原始文件名
                    original_filename = os.path.basename(full_path)
                    # 添加到zip文件，使用序号和原始文件名
                    arcname = f'watermark_{i+1}_{original_filename}'
                    
                    current_app.logger.debug(f"Adding to zip: {arcname}")
                    zf.write(full_path, arcname)
                else:
                    current_app.logger.warning(f"File not found: {full_path}")
        
        memory_file.seek(0)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        response = send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'watermarks_{timestamp}.zip'
        )
        
        # 添加响应头，防止缓存
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"批量下载失败: {str(e)}", exc_info=True)
        return jsonify({'error': '打包下载失败'}), 500

@main_bp.route('/download-all-bg', methods=['POST'])
def download_all_bg():
    try:
        # 获取所有处理后的图片路径和背景颜色
        data = request.json
        image_paths = data.get('files', [])
        bg_color = data.get('background_color', 'transparent')
        
        if not image_paths:
            return jsonify({'error': '没有可下载的图片'}), 400
            
        # 创建ZIP文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, path in enumerate(image_paths):
                try:
                    # 从URL中提取相对路径
                    relative_path = path.split('/static/')[-1] if '/static/' in path else path.lstrip('/')
                    # 构建完整的文件系统路径
                    full_path = os.path.join(current_app.root_path, 'static', relative_path)
                    
                    # 检查文件是否存在并记录日志
                    current_app.logger.debug(f"Processing file: {full_path}")
                    
                    if not os.path.exists(full_path):
                        current_app.logger.warning(f"File not found: {full_path}")
                        continue
                        
                    # 打开图片并处理背景颜色
                    img = Image.open(full_path)
                    
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
                    
                    # 将处理后的图片保存到内存中
                    img_buffer = BytesIO()
                    img.save(img_buffer, format='PNG', quality=95)
                    img_buffer.seek(0)
                    
                    # 获取原始文件名并添加到zip
                    original_filename = os.path.basename(path)
                    arcname = f'processed_{i+1}_{original_filename}'
                    
                    current_app.logger.debug(f"Adding to zip: {arcname}")
                    zf.writestr(arcname, img_buffer.getvalue())
                    
                except Exception as e:
                    current_app.logger.error(f"处理图片失败: {str(e)}")
                    continue
        
        # 检查是否有文件被添加到zip中
        if zf.filelist:
            memory_file.seek(0)
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            
            response = send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'processed_images_{timestamp}.zip'
            )
            
            # 添加响应头，防止缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
        else:
            return jsonify({'error': '没有成功处理任何图片'}), 400
        
    except Exception as e:
        current_app.logger.error(f"批量下载失败: {str(e)}", exc_info=True)
        return jsonify({'error': '打包下载失败'}), 500

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
    
    pdf_service = PDFService()
    try:
        pdf_path = pdf_service.convert_images_to_pdf(files)
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='converted.pdf'
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"PDF转换失败: {str(e)}", exc_info=True)
        return jsonify({'error': f'转换失败: {str(e)}'}), 500

@main_bp.route('/watermark')
def watermark():
    return render_template('watermark.html')

@main_bp.route('/add-watermark', methods=['POST'])
def add_watermark():
    current_app.logger.debug("Processing watermark request")
    
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型'}), 400
    
    current_app.logger.debug(f"Received file: {file.filename}")
    
    try:
        # 获取并转换参数
        options = {
            'type': request.form.get('type', 'text'),
            'text': request.form.get('text', '图优助手'),
            'position': request.form.get('position', 'center'),
            'opacity': int(request.form.get('opacity', 50)),
            'size': int(request.form.get('size', 20)),
            'font_name': request.form.get('font_name', 'noto-sans'),
            'color': request.form.get('color', '#000000'),
            'rotation': float(request.form.get('rotation', 0))
        }
        
        current_app.logger.debug(f"Processing watermark with options: {options}")
        
        # 记录接收到的参��
        current_app.logger.debug(f"Received parameters: {options}")
        
        # 如果是图片水印，添加水印图片
        if options['type'] == 'image' and 'watermark' in request.files:
            options['image'] = request.files['watermark']
        
        watermark_service = WatermarkService()
        result_path = watermark_service.add_watermark(file, options)
        
        return jsonify({
            'success': True,
            'image_url': f'/static/{result_path}'
        })
        
    except ValueError as e:
        current_app.logger.error(f"Invalid parameter: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"添加水印失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'watermark_service' in locals():
            watermark_service.cleanup()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS'] 

@main_bp.route('/compress')
def compress():
    return render_template('compress.html')

@main_bp.route('/compress-image', methods=['POST'])
def process_compress():
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    compress_service = CompressService()
    try:
        # 获取压缩参数
        quality = request.form.get('quality', type=int, default=80)
        max_width = request.form.get('max_width', type=int, default=1920)
        max_height = request.form.get('max_height', type=int, default=1080)
        
        result_path = compress_service.process_image(file, quality, max_width, max_height)
        return jsonify({
            'success': True,
            'image_url': result_path
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"压缩图片失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        compress_service.cleanup()

@main_bp.route('/download-compressed', methods=['POST'])
def download_compressed():
    data = request.get_json()
    if not data or 'image_url' not in data:
        return jsonify({'error': '无效的请求'}), 400
        
    try:
        # 从 URL 中提取相对路径
        relative_path = data['image_url'].split('/static/')[-1] if '/static/' in data['image_url'] else data['image_url'].lstrip('/')
        # 构建完整的文件系统路径
        image_path = os.path.join(current_app.root_path, 'static', relative_path)
        
        if not os.path.exists(image_path):
            return jsonify({'error': '图片不存在'}), 404
            
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        return send_file(
            image_path,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=f'compressed_image_{timestamp}.jpg'
        )
        
    except Exception as e:
        current_app.logger.error(f"下载压缩图片失败: {str(e)}")
        return jsonify({'error': '下载失败'}), 500

@main_bp.route('/download-all-compressed', methods=['POST'])
def download_all_compressed():
    try:
        # 获取所有处理后的图片路径
        data = request.json
        image_paths = data.get('files', [])
        
        if not image_paths:
            return jsonify({'error': '没有可下载的图片'}), 400
            
        # 创建ZIP文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, path in enumerate(image_paths):
                try:
                    # 从URL中提取相对路径
                    relative_path = path.split('/static/')[-1] if '/static/' in path else path.lstrip('/')
                    # 构建完整的文件系统路径
                    full_path = os.path.join(current_app.root_path, 'static', relative_path)
                    
                    # 检查文件是否存在并记录日志
                    current_app.logger.debug(f"Processing file: {full_path}")
                    
                    if not os.path.exists(full_path):
                        current_app.logger.warning(f"File not found: {full_path}")
                        continue
                    
                    # 获取原始文件名并添加到zip
                    original_filename = os.path.basename(path)
                    arcname = f'compressed_{i+1}_{original_filename}'
                    
                    current_app.logger.debug(f"Adding to zip: {arcname}")
                    zf.write(full_path, arcname)
                    
                except Exception as e:
                    current_app.logger.error(f"处理图片失败: {str(e)}")
                    continue
        
        # 检查是否有文件被添加到zip中
        if zf.filelist:
            memory_file.seek(0)
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            
            response = send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'compressed_images_{timestamp}.zip'
            )
            
            # 添加响应头，防止缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
        else:
            return jsonify({'error': '没有成功处理任何图片'}), 400
            
    except Exception as e:
        current_app.logger.error(f"批量下载失败: {str(e)}", exc_info=True)
        return jsonify({'error': '打包下载失败'}), 500

@main_bp.route('/blur-face')
def blur_face():
    return render_template('blur_face.html')

@main_bp.route('/api/blur-face', methods=['POST'])
def process_blur_face():
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    blur_service = BlurFaceService()
    try:
        result_path = blur_service.process_image(file)
        return jsonify({
            'success': True,
            'image_url': result_path
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"处理图片失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        blur_service.cleanup()