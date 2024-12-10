document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在PDF转换页面
    const dropZone = document.getElementById('pdfDropZone');
    if (!dropZone) {
        console.log('Not in PDF conversion page');
        return;
    }
    
    // PDF页面特定的初始化
    const fileInput = document.getElementById('pdfFileInput');
    const previewContainer = document.getElementById('pdfPreviewContainer');
    const imagesList = document.getElementById('selectedImagesList');
    const convertBtn = document.getElementById('convertPdfBtn');
    
    // 存储选择的图片文件
    let selectedFiles = [];
    
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
    
    // 修改调试函数为弹出提示
    function showDebug(message, type = 'info') {
        // 先移除旧的 alert（如果存在）
        const oldAlert = document.getElementById('debugInfo');
        if (oldAlert) {
            oldAlert.remove();
        }
        
        // 创建新的 alert 元素
        const debugInfo = document.createElement('div');
        debugInfo.id = 'debugInfo';
        debugInfo.className = `alert alert-${type} alert-dismissible fade show`;
        debugInfo.setAttribute('role', 'alert');
        debugInfo.innerHTML = `
            <span class="message">${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // 插入到页面中
        document.querySelector('.row').insertAdjacentElement('beforebegin', debugInfo);
        
        // 2秒后自动关闭
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(debugInfo);
            bsAlert.close();
        }, 2000);
    }
    
    // 修改文件处理函数
    function handleFiles(files) {
        const validFiles = Array.from(files).filter(file => {
            const isValid = file.type.startsWith('image/');
            if (!isValid) {
                console.log(`Invalid file type: ${file.type} for ${file.name}`);
            }
            return isValid;
        });
        
        if (validFiles.length === 0) {
            showDebug('请选择有效的图片文件', 'danger');
            return;
        }
        
        showDebug(`成功添加 ${validFiles.length} 个有效图片`, 'success');
        selectedFiles = [...selectedFiles, ...validFiles];
        updatePreview();
    }
    
    // 更新预览
    function updatePreview() {
        if (!imagesList) {
            console.error('imagesList element not found');
            return;
        }
        
        if (selectedFiles.length > 0) {
            previewContainer.classList.remove('d-none');
            imagesList.innerHTML = '';
            
            // 使用 Promise.all 处理所有图片
            Promise.all(selectedFiles.map((file, index) => {
                return new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        resolve({
                            file,
                            dataUrl: e.target.result,
                            index
                        });
                    };
                    reader.readAsDataURL(file);
                });
            })).then(results => {
                results.forEach(({file, dataUrl, index}) => {
                    const item = createImageItem(file, dataUrl, index);
                    imagesList.appendChild(item);
                });
            });
        } else {
            previewContainer.classList.add('d-none');
        }
    }
    
    // 创建图片预览项
    function createImageItem(file, imgUrl, index) {
        const div = document.createElement('div');
        div.className = 'image-item';
        div.innerHTML = `
            <img src="${imgUrl}" alt="${file.name}">
            <div class="image-info">
                <p class="image-name">${file.name}</p>
                <p class="image-size">${formatFileSize(file.size)}</p>
            </div>
            <div class="image-actions">
                ${index > 0 ? `
                    <button class="btn btn-outline-secondary btn-move" onclick="moveImage(${index}, -1)">
                        <i class="bi bi-arrow-up"></i>
                    </button>
                ` : ''}
                ${index < selectedFiles.length - 1 ? `
                    <button class="btn btn-outline-secondary btn-move" onclick="moveImage(${index}, 1)">
                        <i class="bi bi-arrow-down"></i>
                    </button>
                ` : ''}
                <button class="btn btn-outline-danger btn-remove" onclick="removeImage(${index})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        return div;
    }
    
    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // 移动图片位置
    window.moveImage = function(index, direction) {
        // 检查参数有效性
        if (typeof index !== 'number' || typeof direction !== 'number') {
            console.error('Invalid parameters for moveImage');
            return;
        }
        
        // 检查索引范围
        if (index < 0 || index >= selectedFiles.length) {
            console.error('Invalid index for moveImage:', index);
            return;
        }
        
        const newIndex = index + direction;
        
        // 检查新位置是否有效
        if (newIndex < 0 || newIndex >= selectedFiles.length) {
            console.error('Invalid new index for moveImage:', newIndex);
            return;
        }
        
        // 使用解构赋值交换位置
        [selectedFiles[index], selectedFiles[newIndex]] = [selectedFiles[newIndex], selectedFiles[index]];
        
        // 立即更新预览
        requestAnimationFrame(() => {
            updatePreview();
        });
    };
    
    // 删除图片
    window.removeImage = function(index) {
        selectedFiles.splice(index, 1);
        updatePreview();
    };
    
    // 修改转换函数
    convertBtn.addEventListener('click', async function() {
        if (selectedFiles.length === 0) {
            alert('请先选择图片');
            return;
        }
        
        showDebug('正在转换...');
        const formData = new FormData();
        selectedFiles.forEach((file, index) => {
            formData.append('images', file);
            console.log(`Adding file: ${file.name} (${file.type})`);
        });
        
        try {
            const response = await fetch('/convert-to-pdf', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                showDebug('转换成功，准备下载...');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'converted.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                showDebug('下载完成');
            } else {
                const error = await response.json();
                showDebug(`转换失败: ${error.error || '未知错误'}`);
                alert(error.error || '转换失败');
            }
        } catch (error) {
            console.error('Error:', error);
            showDebug(`发生错误: ${error.message}`);
            alert('转换过程中发生错误');
        }
    });
}); 