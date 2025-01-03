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
from app.services.crop_service import CropService
import json
import base64
from zipfile import ZipFile

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
        data = request.get_json()
        if not data or 'images' not in data:
            return jsonify({'error': '没有接收到图片数据'}), 400
            
        # 创建ZIP文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, img_data in enumerate(data['images']):
                # 从 base64 数据中提取图片内容
                img_base64 = img_data['data'].split(',')[1]
                img_bytes = base64.b64decode(img_base64)
                
                # 生成唯一文件名并保存图片
                filename = f'watermark_{uuid.uuid4().hex}.png'
                # 使用配置的水印文件夹路径
                save_path = os.path.join(current_app.config['WATERMARK_FOLDER'], filename)
                
                # 确保目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # 保存图片
                with open(save_path, 'wb') as f:
                    f.write(img_bytes)
                
                # 添加到zip文件
                arcname = f'watermark_{i+1}_{img_data["name"]}'
                zf.write(save_path, arcname)
        
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
        current_app.logger.error(f"Error in download_all_watermark: {str(e)}")
        return jsonify({'error': '处理失败'}), 500

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
    """接收前端处理好的水印图片并保存"""
    try:
        data = request.get_json()
        if not data or 'imageData' not in data:
            return jsonify({'error': '没有接收到图片数据'}), 400
            
        # 从 base64 数据中提取图片内容
        img_data = data['imageData'].split(',')[1]  # 移除 "data:image/png;base64," 前缀
        img_bytes = base64.b64decode(img_data)
        
        # 生成唯一文件名
        filename = f'watermark_{uuid.uuid4().hex}.png'
        # 使用配置的水印文件夹路径
        save_path = os.path.join(current_app.config['WATERMARK_FOLDER'], filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 保存图片
        with open(save_path, 'wb') as f:
            f.write(img_bytes)
        
        # 构建用于返回的URL路径（相对于static目录）
        url_path = os.path.join('uploads', 'watermark', filename)
        
        # 记录使用统计
        current_app.logger.info("Watermark image saved: %s", save_path)
        
        return jsonify({
            'success': True,
            'image_url': f'/static/{url_path}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in add_watermark: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@main_bp.route('/crop')
def crop():
    """图片裁剪页面"""
    return render_template('crop.html')

@main_bp.route('/crop-image', methods=['POST'])
def crop_image():
    """处理图片裁剪请求"""
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    try:
        # 获取裁剪参数
        crop_data = request.form.get('cropData')
        if not crop_data:
            return jsonify({'error': '未提供裁剪参数'}), 400
            
        crop_service = CropService()
        result_path = crop_service.process_image(file, json.loads(crop_data))
        
        # 确保返回完整的URL路径
        if not result_path.startswith('/'):
            result_path = '/' + result_path
            
        return jsonify({
            'success': True,
            'image_url': result_path
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"处理图片失败: {str(e)}")
        return jsonify({'error': '处理失败'}), 500

@main_bp.route('/download-cropped', methods=['POST'])
def download_cropped():
    """处理单张裁剪图片的下载"""
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
        
    try:
        # 生成唯一文件名，使用完整的 uuid
        original_ext = os.path.splitext(file.filename)[1].lower()
        filename = f"crop_{uuid.uuid4().hex}{original_ext}"
        
        # 保存裁剪后的图片
        save_path = os.path.join(current_app.static_folder, 'uploads', 'crop', filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)
        
        return send_file(
            save_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=f"cropped_{os.path.basename(file.filename)}"  # 下载时使用原文件名
        )
    except Exception as e:
        current_app.logger.error(f"下载裁剪图片失败: {str(e)}")
        return jsonify({'error': '下载失败'}), 500

@main_bp.route('/download-all-cropped', methods=['POST'])
def download_all_cropped():
    """处理多张裁剪图片的打包下载"""
    if 'images' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    files = request.files.getlist('images')
    if not files:
        return jsonify({'error': '没有选择文件'}), 400
        
    try:
        # 创建ZIP文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, file in enumerate(files):
                if file.filename:
                    # 生成唯一文件名，使用完整的 uuid
                    original_ext = os.path.splitext(file.filename)[1].lower()
                    filename = f"crop_{uuid.uuid4().hex}{original_ext}"
                    
                    # 保存裁剪后的图片
                    save_path = os.path.join(current_app.static_folder, 'uploads', 'crop', filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    file.save(save_path)
                    
                    # 添加到zip文件，使用原始文件名
                    zf.write(save_path, f"cropped_{os.path.basename(file.filename)}")
        
        memory_file.seek(0)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        response = send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'cropped_images_{timestamp}.zip'
        )
        
        # 添加响应头，防止缓存
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        current_app.logger.error(f"打包下载裁剪图片失败: {str(e)}")
        return jsonify({'error': '打包下载失败'}), 500

@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404