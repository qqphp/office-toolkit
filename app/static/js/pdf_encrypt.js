document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('pdfDropZone');
    const fileInput = document.getElementById('pdfFileInput');
    const passwordContainer = document.getElementById('passwordContainer');
    const passwordInput = document.getElementById('passwordInput');
    const encryptBtn = document.getElementById('encryptBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    let selectedFile = null;
    
    // 拖放相关事件处理
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight(e) {
        dropZone.classList.add('dragover');
    }
    
    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }
    
    // 处理拖放的文件
    dropZone.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
    
    // 处理文件选择
    fileInput.addEventListener('change', function(e) {
        handleFiles(this.files);
    });
    
    // 显示调试信息
    function showDebug(message, type = 'info') {
        const debugInfo = document.getElementById('debugInfo');
        if (!debugInfo) {
            console.warn('Debug info element not found');
            return;
        }
        
        const messageSpan = debugInfo.querySelector('.message');
        if (!messageSpan) {
            console.warn('Message span not found');
            return;
        }
        
        messageSpan.textContent = message;
        debugInfo.className = `alert alert-${type} alert-dismissible fade show`;
        
        try {
            const bsAlert = new bootstrap.Alert(debugInfo);
            setTimeout(() => {
                bsAlert.close();
            }, 2000);
        } catch (error) {
            console.warn('Bootstrap alert initialization failed:', error);
            // 降级处理：如果 Bootstrap alert 初始化失败，使用基本的隐藏方法
            setTimeout(() => {
                debugInfo.classList.remove('show');
            }, 2000);
        }
    }
    
    // 处理文件选择
    function handleFiles(files) {
        if (files.length === 0) return;
        
        const file = files[0];
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showDebug('请选择PDF文件', 'danger');
            return;
        }
        
        selectedFile = file;
        passwordContainer.classList.remove('d-none');
        showDebug('请设置PDF密码', 'info');
    }
    
    // 添加密码输入验证
    passwordInput.addEventListener('input', function() {
        const password = this.value.trim();
        const isValid = password.length >= 4 && password.length <= 32;
        
        // 更新按钮状态
        encryptBtn.disabled = !isValid;
        
        // 更新输入框验证状态
        if (password.length > 0) {
            if (isValid) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
            }
        } else {
            this.classList.remove('is-valid', 'is-invalid');
        }
    });
    
    // 处理加密按钮点击
    encryptBtn.addEventListener('click', function() {
        if (!selectedFile) {
            showDebug('请先选择PDF文件', 'danger');
            return;
        }
        
        const password = passwordInput.value.trim();
        if (!password || password.length < 4 || password.length > 32) {
            showDebug('密码长度必须在4-32个字符之间', 'danger');
            return;
        }
        
        // 显示进度条
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '50%';
        progressText.innerHTML = '<span class="badge bg-primary">正在加密...</span>';
        
        const formData = new FormData();
        formData.append('pdf', selectedFile);
        formData.append('password', password);
        
        fetch('/encrypt-pdf', {
            method: 'POST',
            body: formData
        })
        .then(async response => {
            // 检查是否是成功响应
            const isSuccess = response.headers.get('X-Encrypt-Status') === 'success';
            
            if (!response.ok || !isSuccess) {
                // 如果响应不成功，尝试解析错误信息
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || '加密失败');
                }
                throw new Error('加密失败');
            }
            
            // 更新进度条为成功状态（在获取文件之前）
            progressBar.style.width = '100%';
            progressText.innerHTML = '<span class="badge bg-success">加密成功</span>';
            
            // 获取文件名
            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'encrypted.pdf';
            if (contentDisposition) {
                const matches = /filename=(.+)/.exec(contentDisposition);
                if (matches && matches[1]) {
                    filename = decodeURIComponent(matches[1].replace(/["']/g, ''));
                }
            }
            
            // 获取文件数据并下载
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            
            showDebug('加密成功，开始下载', 'success');
            
            // 重置表单
            setTimeout(() => {
                progressContainer.classList.add('d-none');
                progressBar.style.width = '0%';
                progressBar.classList.remove('bg-danger');
                passwordContainer.classList.add('d-none');
                passwordInput.value = '';
                selectedFile = null;
            }, 2000);
        })
        .catch(error => {
            console.error('加密失败:', error);
            progressBar.style.width = '100%';
            progressBar.classList.add('bg-danger');
            progressText.innerHTML = '<span class="badge bg-danger">加密失败</span>';
            showDebug(error.message || '加密失败', 'danger');
            
            // 3秒后重置进度条
            setTimeout(() => {
                progressContainer.classList.add('d-none');
                progressBar.style.width = '0%';
                progressBar.classList.remove('bg-danger');
            }, 3000);
        });
    });
}); 