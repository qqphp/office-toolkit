from flask import Flask
from app.routes.main_routes import main_bp
from app.routes.pdf_to_word import pdf_to_word
from app.routes.pdf_encrypt import pdf_encrypt

def register_blueprints(app: Flask):
    """注册所有蓝图"""
    app.register_blueprint(main_bp)
    app.register_blueprint(pdf_to_word)
    app.register_blueprint(pdf_encrypt) 