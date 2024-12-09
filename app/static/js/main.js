document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const previewContainer = document.getElementById('previewContainer');
    const originalPreview = document.getElementById('originalPreview');
    const resultPreview = document.getElementById('resultPreview');
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadAllBtn = document.getElementById('downloadAllBtn');

    // 添加全局变量来存储图片
    let currentImageIndex = 0;
    let processedImages = [];

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
        
        processedImages = [];
        currentImageIndex = 0;
        
        // 显示导航按钮
        document.querySelector('.image-navigation').classList.remove('d-none');
        
        // 处理每个文件
        Array.from(files).forEach((file, index) => {
            if (!file.type.startsWith('image/')) {
                showError('请只选择图片文件');
                return;
            }
            
            processedImages.push({
                original: null,
                processed: null,
                file: file
            });
            
            // 读取原图
            const reader = new FileReader();
            reader.onload = function(e) {
                processedImages[index].original = e.target.result;
                if (index === 0) {
                    showPreview(0);
                }
            }
            reader.readAsDataURL(file);
            
            // 上传并处理图片
            uploadAndProcessImage(file, index);
        });
        
        previewContainer.classList.remove('d-none');
        updateImageCounter();
        
        if (files.length > 1) {
            downloadAllBtn.classList.remove('d-none');
        }
    }

    function showPreview(index) {
        if (index >= 0 && index < processedImages.length) {
            currentImageIndex = index;
            originalPreview.src = processedImages[index].original || '';
            resultPreview.src = processedImages[index].processed || '';
            updateImageCounter();
            
            // 更新下载按钮状态
            if (processedImages[index].processed) {
                downloadBtn.classList.remove('d-none');
            } else {
                downloadBtn.classList.add('d-none');
            }
        }
    }

    function updateImageCounter() {
        const counter = document.getElementById('imageCounter');
        counter.textContent = `${currentImageIndex + 1}/${processedImages.length}`;
    }

    // 添加导航按钮事件监听
    document.getElementById('prevOriginal').addEventListener('click', () => {
        if (currentImageIndex > 0) {
            showPreview(currentImageIndex - 1);
        }
    });

    document.getElementById('nextOriginal').addEventListener('click', () => {
        if (currentImageIndex < processedImages.length - 1) {
            showPreview(currentImageIndex + 1);
        }
    });

    function showLoading() {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="loading-text">正在处理图片，请稍候...</div>
        `;
        document.body.appendChild(overlay);
        return overlay;
    }

    function hideLoading(overlay) {
        if (overlay && overlay.parentNode) {
            overlay.remove();
        }
    }

    async function uploadAndProcessImage(file, index) {
        const formData = new FormData();
        formData.append('image', file);
        
        const loadingOverlay = showLoading();

        try {
            const response = await fetch('/remove-background', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                processedImages[index].processed = data.image_url;
                if (index === currentImageIndex) {
                    resultPreview.src = data.image_url;
                    downloadBtn.classList.remove('d-none');
                }
            } else {
                showError(data.error || '处理失败，请重试');
            }
        } catch (error) {
            showError('网络错误，请重试');
        } finally {
            hideLoading(loadingOverlay);
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
        // 移除已存在的错误消息
        const existingError = document.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);

        // 3秒后自动移除
        setTimeout(() => {
            if (errorDiv && errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 3000);
    }

    // 修改下载功能
    downloadBtn.onclick = () => {
        if (processedImages[currentImageIndex].processed) {
            downloadImage(processedImages[currentImageIndex].processed);
        }
    };

    // 修改批量下载功能
    document.getElementById('downloadAllBtn').onclick = async () => {
        const loadingOverlay = showLoading();
        try {
            // 收集所有已处理的图片URL
            const processedFiles = processedImages
                .filter(image => image.processed)
                .map(image => image.processed);

            if (processedFiles.length === 0) {
                showError('没有可下载的文件');
                return;
            }

            const response = await fetch('/download-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    files: processedFiles
                })
            });

            if (response.ok) {
                // 获取blob数据
                const blob = await response.blob();
                // 创建下载链接
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = response.headers.get('content-disposition')?.split('filename=')[1] || 'processed_images.zip';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            } else {
                const error = await response.json();
                showError(error.error || '下载失败，请重试');
            }
        } catch (error) {
            showError('下载失败，请重试');
            console.error('Download error:', error);
        } finally {
            hideLoading(loadingOverlay);
        }
    };
}); 