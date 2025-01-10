from flask import Blueprint, render_template, request, send_file, jsonify
from app.services.pdf_to_word_service import PDFToWordService
import os

pdf_to_word = Blueprint('pdf_to_word', __name__)

@pdf_to_word.route('/pdf-to-word')
def pdf_to_word_page():
    return render_template('pdf_to_word.html')

@pdf_to_word.route('/convert-to-word', methods=['POST'])
def convert_to_word():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
            
        pdf_file = request.files['pdf']
        if not pdf_file or not pdf_file.filename:
            return jsonify({'error': '没有选择文件'}), 400
            
        service = PDFToWordService()
        word_path, filename = service.convert_pdf_to_word(pdf_file)
        
        return send_file(
            word_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500 