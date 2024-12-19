from flask import Flask, request
from flask_bootstrap import Bootstrap5
from config import Config
from app.config.page_meta import PAGE_META
import os
from datetime import datetime

bootstrap = Bootstrap5()

def get_page_meta(key):
    """获取当前页面的元数据"""
    endpoint = request.endpoint
    meta = PAGE_META.get(endpoint, PAGE_META['default'])
    return meta.get(key, '')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    bootstrap.init_app(app)
    
    # 注册全局函数
    app.jinja_env.globals.update(get_page_meta=get_page_meta)
    
    # 注册蓝图
    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    @app.context_processor
    def utility_processor():
        return {'now': datetime.now()}
    
    return app 