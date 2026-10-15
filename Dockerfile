# 使用 Python 3.12.9 作为基础镜像
FROM python:3.12.9-slim-bookworm

# 设置工作目录
WORKDIR /app

# 安装系统依赖（Bookworm 使用 libgl1）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
COPY app/ ./app/
COPY config.py .
COPY run.py .

# 创建必要的目录
RUN mkdir -p app/static/uploads/remove_bg \
    app/static/uploads/img_to_pdf \
    app/static/uploads/watermark \
    app/static/uploads/compress \
    app/static/uploads/blur_face \
    app/static/uploads/crop \
    app/models

# 使用清华源安装Python依赖
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip/*

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV OPENCV_IO_ENABLE_JASPER=1
ENV OPENCV_VIDEOIO_PRIORITY_MSMF=0

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "run.py"] 