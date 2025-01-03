from flask import Flask, request
from flask_bootstrap import Bootstrap5
from flask_apscheduler import APScheduler
from config import Config
from app.config.page_meta import PAGE_META
import os
from datetime import datetime
from app.services.cleanup_service import CleanupService
from functools import partial

bootstrap = Bootstrap5()
scheduler = APScheduler()

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
    
    # 配置APScheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    
    # 注册定时任务
    cleanup_service = CleanupService()
    
    # 创建一个偏函数，将app作为参数传递给cleanup_old_files
    cleanup_job = partial(cleanup_service.cleanup_old_files, app)
    
    scheduler.add_job(
        id='cleanup_old_files',
        func=cleanup_job,
        trigger='interval',
        minutes=30  # 每30分钟执行一次清理
    )
    
    # 启动调度器
    scheduler.start()
    
    # 注册全局函数
    app.jinja_env.globals.update(get_page_meta=get_page_meta)
    
    # 注册蓝图
    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    @app.context_processor
    def utility_processor():
        return {'now': datetime.now()}
    
    return app 