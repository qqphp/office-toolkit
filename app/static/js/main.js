document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const previewContainer = document.getElementById('previewContainer');
    const originalPreview = document.getElementById('originalPreview');
    const resultPreview = document.getElementById('resultPreview');
    const downloadBtn = document.getElementById('downloadBtn');

    // 拖放处理
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
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

    // 处理文件拖放
    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFileSelect, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length === 0) return;
        
        const file = files[0];
        if (!file.type.startsWith('image/')) {
            showError('请选择图片文件');
            return;
        }

        // 显示原图预览
        const reader = new FileReader();
        reader.onload = function(e) {
            originalPreview.src = e.target.result;
            previewContainer.classList.remove('d-none');
            resultPreview.src = ''; // 清除之前的结果
            downloadBtn.classList.add('d-none');
        }
        reader.readAsDataURL(file);

        // 上传并处理图片
        uploadAndProcessImage(file);
    }

    async function uploadAndProcessImage(file) {
        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await fetch('/remove-background', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                resultPreview.src = data.image_url;
                downloadBtn.classList.remove('d-none');
                downloadBtn.onclick = () => downloadImage(data.image_url);
            } else {
                showError(data.error || '处理失败，请重试');
            }
        } catch (error) {
            showError('网络错误，请重试');
        }
    }

    function downloadImage(url) {
        const link = document.createElement('a');
        link.href = url;
        link.download = 'processed-image.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        dropZone.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 3000);
    }
}); 