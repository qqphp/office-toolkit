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
        
        const totalFiles = files.length;
        let processedCount = 0;
        
        // 显示进度条并重置状态
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        // 重置进度条状态
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressText.innerHTML = `<span class="badge bg-primary">准备处理 ${totalFiles} 张图片</span>`;
        
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
            uploadAndProcessImage(file, index).then(() => {
                processedCount++;
                // 更新进度条
                const progress = (processedCount / totalFiles) * 100;
                progressBar.style.width = `${progress}%`;
                progressBar.setAttribute('aria-valuenow', progress);
                
                // 更新进度文本
                if (processedCount === totalFiles) {
                    progressText.innerHTML = '<span class="badge bg-success">所有图片处理完成</span>';
                } else {
                    progressText.innerHTML = `<span class="badge bg-primary">正在处理第 ${processedCount}/${totalFiles} 张图片</span>`;
                }
                
                // 所有图片处理完成
                if (processedCount === totalFiles) {
                    setTimeout(() => {
                        progressContainer.classList.add('d-none');
                        if (totalFiles > 1) {
                            downloadAllBtn.classList.remove('d-none');
                        }
                    }, 1500); // 延长显示完成状态的时间
                }
            }).catch(() => {
                processedCount++;
                // 即使处理失败也更新进度
                const progress = (processedCount / totalFiles) * 100;
                progressBar.style.width = `${progress}%`;
                progressBar.setAttribute('aria-valuenow', progress);
                
                if (processedCount === totalFiles) {
                    progressText.innerHTML = '<span class="badge bg-warning">处理完成，部分图片可能失败</span>';
                    setTimeout(() => {
                        progressContainer.classList.add('d-none');
                    }, 1500);
                }
            });
        });
        
        previewContainer.classList.remove('d-none');
        updateImageCounter();
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

    async function uploadAndProcessImage(file, index) {
        const formData = new FormData();
        formData.append('image', file);

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
            console.error('Upload error:', error);
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
        // 使用进度条来显示下载状态
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '100%';
        progressBar.setAttribute('aria-valuenow', 100);
        progressText.innerHTML = '<span class="badge bg-primary">正在打包下载...</span>';

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
                
                // 显示成功状态
                progressText.innerHTML = '<span class="badge bg-success">下载已开始</span>';
            } else {
                const error = await response.json();
                showError(error.error || '下载失败，请重试');
            }
        } catch (error) {
            showError('下载失败，请重试');
            console.error('Download error:', error);
        } finally {
            // 延迟隐藏进度条
            setTimeout(() => {
                progressContainer.classList.add('d-none');
            }, 1000);
        }
    };
}); 