# 图片处理工具

## 功能

1. 图片去背景
2. 图片转pdf
3. 图片加水印
4. 图片压缩
5. 模糊面部
6. 图片裁剪

## 使用

1. 安装 Python 3.12.9 版本（`.python-version` 已固定版本）
2. 创建独立虚拟环境并安装依赖（Windows PowerShell）：

   ```powershell
   python --version  # 确认输出 Python 3.12.9
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m pip check
   ```

3. 运行 `.\.venv\Scripts\python.exe run.py`
4. 访问 `http://127.0.0.1:5001/`

Linux/macOS 使用 `.venv/bin/python` 替换上述虚拟环境解释器路径。

## 注意事项

1. 文件上传目录为 `app/static/uploads`，请确保有足够的空间
2. 文件清理任务每30分钟执行一次，请确保有足够的空间
3. 使用阿里云图片处理功能前，请设置环境变量 `ALIBABA_CLOUD_ACCESS_KEY_ID` 和 `ALIBABA_CLOUD_ACCESS_KEY_SECRET`，不要将凭据写入代码或提交到 Git
