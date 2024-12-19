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
    document.getElementById('cropBtn').addEventListener('click', processCrop);
    
    // 导航按钮
    document.getElementById('prevButton').addEventListener('click', showPreviousImage);
    document.getElementById('nextButton').addEventListener('click', showNextImage);
    
    // 下载按钮
    document.getElementById('downloadBtn').addEventListener('click', downloadCurrentImage);
    document.getElementById('downloadAllBtn').addEventListener('click', downloadAllImages);
}

// 显示图片
function showImage(index, config = {}) {
    const file = selectedFiles[index];
    const image = document.getElementById('cropImage');
    
    if (image.src) {
        URL.revokeObjectURL(image.src);
    }
    
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
    
    const objectUrl = URL.createObjectURL(file);
    image.src = objectUrl;
    
    image.onload = function() {
        const options = {
            viewMode: 2,
            dragMode: 'move',
            aspectRatio: config.aspectRatio || currentAspectRatio,
            autoCropArea: 0.9,
            restore: false,
            guides: true,
            center: true,
            highlight: false,
            cropBoxMovable: true,
            cropBoxResizable: true,
            toggleDragModeOnDblclick: false,
            ready: () => {
                if (config.initialCanvasData) {
                    cropper.setCanvasData(config.initialCanvasData);
                }
                if (config.initialCropBoxData) {
                    cropper.setCropBoxData(config.initialCropBoxData);
                }
            }
        };
        
        cropper = new Cropper(image, options);
        updateNavigationButtons();
        updateDownloadButtons();
    };
}

// 处理裁剪
async function processCrop() {
    if (!cropper || !selectedFiles[currentImageIndex]) return;
    
    try {
        // 保存当前的裁剪器设置
        const currentCropperData = cropper.getData();
        const currentCanvasData = cropper.getCanvasData();
        const currentContainerData = cropper.getContainerData();
        
        // 获取裁剪数据和图片数据
        const cropData = cropper.getData(true);
        const imageData = cropper.getImageData();
        
        // 验证裁剪区域是否有效
        if (cropData.width <= 0 || cropData.height <= 0) {
            throw new Error('裁剪区域太小');
        }
        
        // 创建表单数据
        const formData = new FormData();
        formData.append('image', selectedFiles[currentImageIndex]);
        formData.append('cropData', JSON.stringify({
            ...cropData,
            rotate: cropData.rotate,
            scaleX: cropData.scaleX,
            scaleY: cropData.scaleY,
            naturalWidth: imageData.naturalWidth,
            naturalHeight: imageData.naturalHeight
        }));
        
        showProgress('正在处理图片...');
        
        const response = await fetch('/crop-image', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            processedImages.set(currentImageIndex, data.image_url);
            showToast('裁剪成功', 'success');
            updateDownloadButtons();
            
            // 重新初始化裁剪器，保持之前的状态
            showImage(currentImageIndex, {
                aspectRatio: currentAspectRatio,
                initialCanvasData: currentCanvasData,
                initialCropBoxData: currentCropperData
            });
        } else {
            throw new Error(data.error || '处理失败');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || '处理失败', 'danger');
    } finally {
        hideProgress();
    }
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
        showProgress('准备下载...');
        
        // 获取图片数据
        const response = await fetch(imageUrl);
        if (!response.ok) throw new Error('下载失败');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        // 创建下载链接
        const link = document.createElement('a');
        link.href = url;
        link.download = `cropped_${selectedFiles[currentImageIndex].name}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 清理URL对象
        window.URL.revokeObjectURL(url);
        
        showToast('下载开始', 'success');
    } catch (error) {
        console.error('Download error:', error);
        showToast('下载失败', 'danger');
    } finally {
        hideProgress();
    }
}

async function downloadAllImages() {
    if (processedImages.size === 0) return;
    
    try {
        showProgress('正在创建压缩包...');
        
        const zip = new JSZip();
        const promises = [];
        
        processedImages.forEach((imageUrl, index) => {
            const promise = fetch(imageUrl)
                .then(response => {
                    if (!response.ok) throw new Error('获取图片失败');
                    return response.blob();
                })
                .then(blob => {
                    const filename = selectedFiles[index].name;
                    zip.file(`cropped_${filename}`, blob);
                })
                .catch(error => {
                    console.error(`Error processing image ${index}:`, error);
                    showToast(`处理第 ${index + 1} 张图片失败`, 'warning');
                });
            promises.push(promise);
        });
        
        await Promise.all(promises);
        
        // 生成压缩包
        showProgress('正在生成压缩包...');
        const content = await zip.generateAsync({
            type: 'blob',
            compression: 'DEFLATE',
            compressionOptions: {
                level: 6
            }
        });
        
        // 下载压缩包
        const url = window.URL.createObjectURL(content);
        const link = document.createElement('a');
        link.href = url;
        link.download = `cropped_images_${new Date().getTime()}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 清理URL对象
        window.URL.revokeObjectURL(url);
        
        showToast('下载已开始', 'success');
    } catch (error) {
        console.error('Error:', error);
        showToast('创建压缩包失败', 'danger');
    } finally {
        hideProgress();
    }
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