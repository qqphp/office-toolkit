document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('pdfDropZone');
    const fileInput = document.getElementById('pdfFileInput');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
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
        debugInfo.querySelector('.message').textContent = message;
        debugInfo.className = `alert alert-${type} alert-dismissible fade show`;
        
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(debugInfo);
            bsAlert.close();
        }, 2000);
    }
    
    // 处理文件上传和转换
    function handleFiles(files) {
        if (files.length === 0) return;
        
        const file = files[0];
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showDebug('请选择PDF文件', 'danger');
            return;
        }
        
        // 显示进度条
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '50%';
        progressText.innerHTML = '<span class="badge bg-primary">正在转换...</span>';
        
        const formData = new FormData();
        formData.append('pdf', file);
        
        fetch('/convert-to-word', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                progressBar.style.width = '100%';
                progressText.innerHTML = '<span class="badge bg-success">转换成功</span>';
                
                // 获取文件名
                const contentDisposition = response.headers.get('content-disposition');
                let filename = 'converted.docx';
                if (contentDisposition) {
                    const matches = /filename=(.+)/.exec(contentDisposition);
                    if (matches && matches[1]) {
                        filename = decodeURIComponent(matches[1].replace(/["']/g, ''));
                    }
                }
                
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();
                    
                    showDebug('转换成功，开始下载', 'success');
                });
            } else {
                return response.json().then(error => {
                    throw new Error(error.error || '转换失败');
                });
            }
        })
        .catch(error => {
            progressBar.style.width = '100%';
            progressBar.classList.add('bg-danger');
            progressText.innerHTML = '<span class="badge bg-danger">转换失败</span>';
            showDebug(error.message || '转换失败', 'danger');
        })
        .finally(() => {
            setTimeout(() => {
                progressContainer.classList.add('d-none');
                progressBar.style.width = '0%';
                progressBar.classList.remove('bg-danger');
            }, 2000);
        });
    }
}); 