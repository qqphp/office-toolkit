// 全局变量
let cropper = null;
let selectedFiles = [];
let processedImages = new Map();
let currentImageIndex = 0;
let currentAspectRatio = NaN;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeUpload();
    initializeControls();
});

// 初始化上传功能
function initializeUpload() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    // 处理拖放
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    // 处理文件选择
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

// 处理选择的文件
function handleFiles(files) {
    if (files.length === 0) return;
    
    selectedFiles = Array.from(files);
    currentImageIndex = 0;
    processedImages.clear();
    
    // 显示工作区
    document.getElementById('workspaceContainer').classList.remove('d-none');
    
    // 显示第一张图片
    showImage(0);
    
    // 更新导航按钮
    updateNavigationButtons();
}

// 初始化控制按钮
function initializeControls() {
    // 宽高比控制
    document.querySelectorAll('input[name="aspectRatio"]').forEach(input => {
        input.addEventListener('change', function() {
            currentAspectRatio = parseFloat(this.value);
            if (cropper) {
                cropper.setAspectRatio(currentAspectRatio);
            }
        });
    });
    
    // 旋转控制
    document.getElementById('rotateLeft').addEventListener('click', () => cropper.rotate(-90));
    document.getElementById('rotateRight').addEventListener('click', () => cropper.rotate(90));
    
    // 翻转控制
    document.getElementById('flipHorizontal').addEventListener('click', () => {
        cropper.scaleX(cropper.getData().scaleX * -1);
    });
    document.getElementById('flipVertical').addEventListener('click', () => {
        cropper.scaleY(cropper.getData().scaleY * -1);
    });
    
    // 缩放控制
    document.getElementById('zoomRange').addEventListener('input', function() {
        cropper.zoomTo(parseFloat(this.value));
    });
    
    // 重置按钮
    document.getElementById('resetBtn').addEventListener('click', () => {
        cropper.reset();
        document.getElementById('zoomRange').value = 1;
    });
    
    // 确认裁剪按钮
    document.getElementById('cropBtn').addEventListener('click', function() {
        if (!cropper) return;
        
        // 获取裁剪数据
        const canvas = cropper.getCroppedCanvas();
        if (!canvas) {
            showToast('裁剪失败，请重试', 'danger');
            return;
        }

        // 将裁剪后的图片转换为 base64
        const croppedImageUrl = canvas.toDataURL('image/png');
        
        // 保存处理后的图片
        processedImages.set(currentImageIndex, croppedImageUrl);
        
        // 更新预览图片
        const cropImage = document.getElementById('cropImage');
        cropImage.src = croppedImageUrl;
        
        // 销毁当前的 cropper 实例
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
        
        // 使用新图片初始化 cropper
        initCropper(cropImage);
        
        // 显示下载按钮
        document.getElementById('downloadBtn').classList.remove('d-none');
        if (selectedFiles.length > 1) {
            document.getElementById('downloadAllBtn').classList.remove('d-none');
        }
        
        showToast('裁剪成功', 'success');
    });
    
    // 导航按钮
    document.getElementById('prevButton').addEventListener('click', showPreviousImage);
    document.getElementById('nextButton').addEventListener('click', showNextImage);
    
    // 下载按钮
    document.getElementById('downloadBtn').addEventListener('click', downloadCurrentImage);
    document.getElementById('downloadAllBtn').addEventListener('click', downloadAllImages);
}

// 显示图片
function showImage(index) {
    if (index < 0 || index >= selectedFiles.length) return;
    
    const file = selectedFiles[index];
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const cropImage = document.getElementById('cropImage');
        
        // 如果存在已处理的图片，显示已处理的图片
        if (processedImages.has(index)) {
            cropImage.src = processedImages.get(index);
        } else {
            cropImage.src = e.target.result;
        }
        
        // 销毁现有的 cropper 实例
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
        
        // 初始化新的 cropper
        initCropper(cropImage);
        
        // 更新下载按钮状态
        updateDownloadButtons();
    };
    
    reader.readAsDataURL(file);
}

// 导航功能
function showPreviousImage() {
    if (currentImageIndex > 0) {
        currentImageIndex--;
        showImage(currentImageIndex);
    }
}

function showNextImage() {
    if (currentImageIndex < selectedFiles.length - 1) {
        currentImageIndex++;
        showImage(currentImageIndex);
    }
}

function updateNavigationButtons() {
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const imageCounter = document.getElementById('imageCounter');
    const navigation = document.querySelector('.image-navigation');
    
    if (selectedFiles.length > 1) {
        navigation.classList.remove('d-none');
        prevButton.disabled = currentImageIndex === 0;
        nextButton.disabled = currentImageIndex === selectedFiles.length - 1;
        imageCounter.textContent = `${currentImageIndex + 1}/${selectedFiles.length}`;
    } else {
        navigation.classList.add('d-none');
    }
}

// 下载功能
async function downloadCurrentImage() {
    const imageUrl = processedImages.get(currentImageIndex);
    if (!imageUrl) return;
    
    try {
        showProgress('正在处理下载...');
        
        // 将 base64 图片数据转换为 Blob
        const response = await fetch(imageUrl);
        const blob = await response.blob();
        
        // 创建 FormData 对象
        const formData = new FormData();
        formData.append('image', blob, `cropped_${selectedFiles[currentImageIndex].name}`);
        
        // 发送到后端
        const downloadResponse = await fetch('/download-cropped', {
            method: 'POST',
            body: formData
        });
        
        if (!downloadResponse.ok) {
            throw new Error('下载失败');
        }
        
        // 获取文件并下载
        const downloadBlob = await downloadResponse.blob();
        const downloadUrl = URL.createObjectURL(downloadBlob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `cropped_${selectedFiles[currentImageIndex].name}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(downloadUrl);
        
        hideProgress();
        showToast('下载成功', 'success');
    } catch (error) {
        console.error('Download error:', error);
        hideProgress();
        showToast('下载失败', 'danger');
    }
}

async function downloadAllImages() {
    if (processedImages.size === 0) return;
    
    try {
        showProgress('正在创建压缩包...');
        
        // 创建 FormData 对象
        const formData = new FormData();
        
        // 添加所有处理过的图片
        for (const [index, imageUrl] of processedImages.entries()) {
            const response = await fetch(imageUrl);
            const blob = await response.blob();
            formData.append('images', blob, `cropped_${selectedFiles[index].name}`);
        }
        
        // 发送到后端
        const downloadResponse = await fetch('/download-all-cropped', {
            method: 'POST',
            body: formData
        });
        
        if (!downloadResponse.ok) {
            throw new Error('打包下载失败');
        }
        
        // 获取压缩包并下载
        const downloadBlob = await downloadResponse.blob();
        const downloadUrl = URL.createObjectURL(downloadBlob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = 'cropped_images.zip';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(downloadUrl);
        
        hideProgress();
        showToast('下载成功', 'success');
    } catch (error) {
        console.error('Download error:', error);
        hideProgress();
        showToast('打包下载失败', 'danger');
    }
}

// 辅助函数：将 base64 转换为 blob
function b64toBlob(b64Data, contentType = '', sliceSize = 512) {
    const byteCharacters = atob(b64Data);
    const byteArrays = [];
    
    for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
        const slice = byteCharacters.slice(offset, offset + sliceSize);
        const byteNumbers = new Array(slice.length);
        
        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
    }
    
    return new Blob(byteArrays, {type: contentType});
}

// 更新下载按钮状态
function updateDownloadButtons() {
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadAllBtn = document.getElementById('downloadAllBtn');
    
    if (processedImages.has(currentImageIndex)) {
        downloadBtn.classList.remove('d-none');
    } else {
        downloadBtn.classList.add('d-none');
    }
    
    if (processedImages.size > 1) {
        downloadAllBtn.classList.remove('d-none');
    } else {
        downloadAllBtn.classList.add('d-none');
    }
}

// 进度提示
function showProgress(message) {
    // 检查是否已存在进度条容器
    let progressContainer = document.getElementById('progressContainer');
    
    // 如果不存在，创建进度条容器和相关元素
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'progressContainer';
        progressContainer.className = 'progress-section mb-4';
        
        progressContainer.innerHTML = `
            <div class="progress">
                <div id="progressBar" 
                     class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%" 
                     aria-valuenow="0" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                </div>
            </div>
            <div id="progressText" class="text-center mt-2">
                <span class="badge bg-primary"></span>
            </div>
        `;
        
        // 将进度条插入到上传区域后面
        const uploadContainer = document.querySelector('.upload-container');
        uploadContainer.parentNode.insertBefore(progressContainer, uploadContainer.nextSibling);
    }
    
    // 更新进度和文本
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText').querySelector('.badge');
    
    progressBar.style.width = '100%';
    progressText.textContent = message;
    progressContainer.classList.remove('d-none');
}

function hideProgress() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.classList.add('d-none');
    }
}

// Toast 提示
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
}

// 初始化 Cropper
function initCropper(image) {
    const options = {
        viewMode: 2,
        dragMode: 'move',
        aspectRatio: currentAspectRatio,
        autoCropArea: 0.9,
        restore: false,
        guides: true,
        center: true,
        highlight: false,
        cropBoxMovable: true,
        cropBoxResizable: true,
        toggleDragModeOnDblclick: false,
        ready: function() {
            // 更新缩放滑块的值
            const zoomRange = document.getElementById('zoomRange');
            if (zoomRange) {
                zoomRange.value = 1;
            }
        }
    };
    
    cropper = new Cropper(image, options);
    updateNavigationButtons();
}