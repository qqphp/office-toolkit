// 全局变量
let selectedFiles = [];
let currentImageIndex = 0;
let processedImages = new Map(); // 存储处理后的图片信息

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化拖放区域
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    // 拖放事件处理
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    // 文件选择和拖放处理
    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });
    
    // 导航按钮事件处理
    document.getElementById('prevButton').addEventListener('click', showPreviousImage);
    document.getElementById('nextButton').addEventListener('click', showNextImage);
    
    // 下载按钮事件处理
    document.getElementById('downloadBtn').addEventListener('click', downloadCurrentImage);
    document.getElementById('downloadAllBtn').addEventListener('click', downloadAllImages);
});

// 处理文件
function handleFiles(files) {
    if (files.length === 0) return;
    
    const validFiles = Array.from(files).filter(file => {
        const isValid = file.type.startsWith('image/');
        if (!isValid) {
            console.log(`Invalid file type: ${file.type} for ${file.name}`);
        }
        return isValid;
    });
    
    if (validFiles.length === 0) {
        showToast('请选择有效的图片文件', 'danger');
        return;
    }
    
    selectedFiles = validFiles;
    currentImageIndex = 0;
    processedImages.clear();
    
    // 显示导航按钮
    document.querySelector('.image-navigation').classList.remove('d-none');
    
    // 显示进度条
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    progressContainer.classList.remove('d-none');
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', 0);
    progressText.innerHTML = `<span class="badge bg-primary">准备处理 ${validFiles.length} 张图片</span>`;
    
    // 处理第一张图片
    processImage(0);
}

// 处理单张图片
function processImage(index) {
    if (index >= selectedFiles.length) {
        document.getElementById('downloadAllBtn').classList.remove('d-none');
        return;
    }
    
    const file = selectedFiles[index];
    const formData = new FormData();
    formData.append('image', file);
    
    // 更新进度条
    const progress = ((index + 1) / selectedFiles.length) * 100;
    updateProgress(progress, `正在处理第 ${index + 1}/${selectedFiles.length} 张图片`);
    
    // 显示原图预览
    showOriginalPreview(file);
    
    // 发送请求处理图片
    fetch('/api/blur-face', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            processedImages.set(index, data.image_url);
            showProcessedImage(data.image_url);
            document.getElementById('downloadBtn').classList.remove('d-none');
            
            // 处理下一张图片
            processImage(index + 1);
        } else {
            throw new Error(data.error || '处理失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast(error.message, 'danger');
        updateProgress(0, '处理失败');
    });
}

// 显示原图预览
function showOriginalPreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('originalPreview').src = e.target.result;
        document.getElementById('previewContainer').classList.remove('d-none');
    };
    reader.readAsDataURL(file);
}

// 显示处理后的图片
function showProcessedImage(imageUrl) {
    document.getElementById('resultPreview').src = imageUrl;
}

// 更新进度条
function updateProgress(progress, text) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
    progressText.innerHTML = `<span class="badge bg-primary">${text}</span>`;
}

// 导航功能
function showPreviousImage() {
    if (currentImageIndex > 0) {
        currentImageIndex--;
        showImage(currentImageIndex);
        updateNavigationButtons();
    }
}

function showNextImage() {
    if (currentImageIndex < selectedFiles.length - 1) {
        currentImageIndex++;
        showImage(currentImageIndex);
        updateNavigationButtons();
    }
}

function showImage(index) {
    showOriginalPreview(selectedFiles[index]);
    if (processedImages.has(index)) {
        showProcessedImage(processedImages.get(index));
    }
}

// 更新导航按钮状态
function updateNavigationButtons() {
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const imageCounter = document.getElementById('imageCounter');
    
    prevButton.disabled = currentImageIndex === 0;
    nextButton.disabled = currentImageIndex === selectedFiles.length - 1;
    imageCounter.textContent = `${currentImageIndex + 1}/${selectedFiles.length}`;
}

// 下载功能
function downloadCurrentImage() {
    const imageUrl = processedImages.get(currentImageIndex);
    if (imageUrl) {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = `blurred_${selectedFiles[currentImageIndex].name}`;
        link.click();
    }
}

async function downloadAllImages() {
    const zip = new JSZip();
    const promises = [];
    
    processedImages.forEach((imageUrl, index) => {
        const promise = fetch(imageUrl)
            .then(response => response.blob())
            .then(blob => {
                zip.file(`blurred_${selectedFiles[index].name}`, blob);
            });
        promises.push(promise);
    });
    
    try {
        await Promise.all(promises);
        const content = await zip.generateAsync({type: 'blob'});
        const link = document.createElement('a');
        link.href = URL.createObjectURL(content);
        link.download = 'blurred_images.zip';
        link.click();
    } catch (error) {
        console.error('Error creating zip:', error);
        showToast('创建压缩包失败', 'danger');
    }
}

// 工具函数
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    document.getElementById('dropZone').classList.add('dragover');
}

function unhighlight(e) {
    document.getElementById('dropZone').classList.remove('dragover');
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 如果项目中有使用 Bootstrap Toast 或其他提示组件，在这里实现
    console.log(`${type}: ${message}`);
} 