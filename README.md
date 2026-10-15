# 办公助手

办公助手是一个基于 Flask 的图片与 PDF 处理工具，提供图片背景移除、图片编辑和文档转换等功能。项目使用 Python 3.12.9，依赖版本见 [`requirements.txt`](requirements.txt)。

## 功能

- 图片去背景：上传图片并下载去除背景后的结果。该功能使用阿里云图像分割服务，需要配置阿里云 AccessKey。
- 图片转 PDF：将图片转换为 PDF 文件。
- 图片水印：添加文字或图片水印，支持单个水印、平铺和批量处理。
- 图片压缩：压缩图片并下载处理结果。
- 模糊面部：检测并模糊图片中的人脸。
- 图片裁剪：裁剪图片并下载结果。
- PDF 转 Word：将 PDF 文档转换为 Word 文档。
- PDF 加密：为 PDF 设置打开密码。

## 功能演示
![demo](./app/static/demo/demo1.gif)

## 环境要求

- Python 3.12.9
- pip
- 如需使用图片去背景功能，需有可调用阿里云图像分割服务的 AccessKey

## 安装与运行

### Windows PowerShell

先确认 Python 版本为 3.12.9，再创建虚拟环境并安装依赖：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

如果要使用图片去背景功能，在启动应用前设置阿里云凭据。建议同时设置独立的 Flask `SECRET_KEY`：

```powershell
$env:SECRET_KEY = "请替换为随机生成的值"
$env:ALIBABA_CLOUD_ACCESS_KEY_ID = "你的阿里云 AccessKey ID"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET = "你的阿里云 AccessKey Secret"
```

启动应用：

```powershell
.\.venv\Scripts\python.exe run.py
```

### Linux / macOS

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

如需使用图片去背景功能，请在当前终端设置 `ALIBABA_CLOUD_ACCESS_KEY_ID` 和 `ALIBABA_CLOUD_ACCESS_KEY_SECRET`；建议设置随机的 `SECRET_KEY`，然后运行：

```bash
export SECRET_KEY="请替换为随机生成的值"
export ALIBABA_CLOUD_ACCESS_KEY_ID="你的阿里云 AccessKey ID"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="你的阿里云 AccessKey Secret"
python run.py
```

应用启动后访问 <http://127.0.0.1:5001/>。

## 配置与文件

- 应用监听 `0.0.0.0:5001`，图片上传和 PDF 上传的请求体上限为 16 MiB。
- 支持的图片扩展名为 PNG、JPG、JPEG、GIF、BMP 和 WEBP；PDF 功能接收 PDF 文件。
- 上传与处理文件保存在 `app/static/uploads/`。应用启动后会注册定时清理任务；请不要把该目录当作长期文件存储。
- 阿里云凭据通过环境变量读取。不要把真实凭据写进源代码、README 或 Git 历史。
- `run.py` 使用 Flask 开发服务器并启用调试模式，适合本地开发，不应直接暴露到公网。

## 项目结构

```text
app/
├── routes/       Flask 页面和处理路由
├── services/     图片及 PDF 处理逻辑
├── templates/    页面模板
├── static/       CSS、JavaScript、图片和上传目录
└── models/       OpenCV 级联模型等本地模型文件
config.py         应用配置
run.py            本地启动入口
requirements.txt  Python 依赖
.python-version   Python 版本标记
```

## 项目链接

- 技术博客：[qqphp.com](https://qqphp.com)
- 开源地址：[qqphp/office-toolkit](https://github.com/qqphp/office-toolkit)
