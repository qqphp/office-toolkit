from app import create_app
import os

# 设置OpenCV在headless环境中的配置
os.environ['OPENCV_IO_ENABLE_JASPER'] = '1'  # 启用JPEG2000支持
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'  # 禁用视频IO后端

app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 