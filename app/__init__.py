from flask import Flask
from flask_bootstrap import Bootstrap5
from config import Config

bootstrap = Bootstrap5()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    bootstrap.init_app(app)
    
    # 注册蓝图
    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    return app 