from flask import Blueprint, render_template, request, send_file, jsonify
from app.services.pdf_encrypt_service import PDFEncryptService
import os

pdf_encrypt = Blueprint('pdf_encrypt', __name__)

@pdf_encrypt.route('/pdf-encrypt')
def pdf_encrypt_page():
    return render_template('pdf_encrypt.html')

@pdf_encrypt.route('/encrypt-pdf', methods=['POST'])
def encrypt_pdf():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
            
        pdf_file = request.files['pdf']
        if not pdf_file or not pdf_file.filename:
            return jsonify({'error': '没有选择文件'}), 400
            
        password = request.form.get('password')
        if not password:
            return jsonify({'error': '请输入密码'}), 400
            
        service = PDFEncryptService()
        pdf_path, filename = service.encrypt_pdf(pdf_file, password)
        
        # 确保文件存在
        if not os.path.exists(pdf_path):
            raise RuntimeError('加密文件生成失败')
            
        response = send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
        # 添加自定义响应头标识成功
        response.headers['X-Encrypt-Status'] = 'success'
        return response
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"PDF加密失败: {str(e)}")
        return jsonify({'error': str(e)}), 500 