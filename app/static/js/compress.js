let selectedFiles = [];
let currentImageIndex = 0;
let processedImages = [];

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeDropZone();
    initializeQualitySlider();
    initializeFileInput();
    initializeAspectRatioControl();
});

// 初始化拖放区域
function initializeDropZone() {
    const dropZone = document.getElementById('dropZone');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    dropZone.addEventListener('drop', handleDrop, false);
}

// 初始化质量滑块
function initializeQualitySlider() {
    const quality = document.getElementById('quality');
    const qualityValue = document.getElementById('qualityValue');
    
    quality.addEventListener('input', function() {
        qualityValue.textContent = this.value + '%';
    });
}

// 初始化文件输入
function initializeFileInput() {
    const fileInput = document.getElementById('fileInput');
    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });
}

// 添加宽高比控制初始化
function initializeAspectRatioControl() {
    const keepAspectRatio = document.getElementById('keepAspectRatio');
    const maxWidth = document.getElementById('maxWidth');
    const maxHeight = document.getElementById('maxHeight');
    
    // 监听复选框变化
    keepAspectRatio.addEventListener('change', function() {
        maxWidth.disabled = this.checked;
        maxHeight.disabled = this.checked;
    });
    
    // 监听输入值变化
    maxWidth.addEventListener('input', function() {
        validateDimension(this, 100, 7680);
    });
    
    maxHeight.addEventListener('input', function() {
        validateDimension(this, 100, 4320);
    });
}

// 验证尺寸输入
function validateDimension(input, min, max) {
    let value = parseInt(input.value);
    if (isNaN(value)) {
        value = min;
    } else {
        value = Math.max(min, Math.min(max, value));
    }
    input.value = value;
}

// 处理文件
async function handleFiles(files) {
    if (files.length === 0) return;
    
    selectedFiles = Array.from(files);
    processedImages = [];
    currentImageIndex = 0;
    
    // 显示进度条
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    progressContainer.classList.remove('d-none');
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', 0);
    progressText.innerHTML = `<span class="badge bg-primary">准备处理 ${files.length} 张图片</span>`;
    
    // 处理每个文件
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        await processImage(file);
        
        // 更新进度
        const progress = ((i + 1) / files.length) * 100;
        progressBar.style.width = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
        progressText.innerHTML = `<span class="badge bg-primary">已处理 ${i + 1}/${files.length} 张图片</span>`;
    }
    
    // 显示预览
    showImage(0);
    document.getElementById('previewContainer').classList.remove('d-none');
    updateNavigationButtons();
    
    // 处理完所有文件后
    if (files.length > 1) {
        document.getElementById('downloadAllBtn').classList.remove('d-none');
    }
}

// 修改处理图片函数，考虑宽高比设置
async function processImage(file) {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('quality', document.getElementById('quality').value);
    
    const keepAspectRatio = document.getElementById('keepAspectRatio').checked;
    if (keepAspectRatio) {
        // 如果保持宽高比，使用默认的最大尺寸
        formData.append('max_width', 1920);
        formData.append('max_height', 1080);
    } else {
        // 如果不保持宽高比，使用用户输入的值
        formData.append('max_width', document.getElementById('maxWidth').value);
        formData.append('max_height', document.getElementById('maxHeight').value);
    }
    
    try {
        const response = await fetch('/compress-image', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            processedImages.push(data.image_url);
        } else {
            throw new Error(data.error || '处理失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert(error.message || '处理失败');
    }
}

// 显示图片
function showImage(index) {
    const file = selectedFiles[index];
    const processedUrl = processedImages[index];
    
    // 显示原图
    const originalPreview = document.querySelector('.original-preview');
    const originalSize = document.querySelector('.original-size');
    
    originalPreview.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="原图">`;
    originalSize.textContent = `原始大小: ${formatFileSize(file.size)}`;
    
    // 显示压缩后的图片
    const compressedPreview = document.querySelector('.compressed-preview');
    const compressedSize = document.querySelector('.compressed-size');
    const compressionRatio = document.querySelector('.compression-ratio');
    
    // 获取压缩后的图片大小
    fetch(processedUrl)
        .then(response => response.blob())
        .then(blob => {
            compressedPreview.innerHTML = `<img src="${processedUrl}" alt="压缩后">`;
            compressedSize.textContent = `压缩后大小: ${formatFileSize(blob.size)}`;
            const ratio = ((1 - blob.size / file.size) * 100).toFixed(2);
            compressionRatio.textContent = `压缩率: ${ratio}%`;
        });
}

// 下载当前图片
document.getElementById('downloadBtn').addEventListener('click', async function() {
    const currentUrl = processedImages[currentImageIndex];
    if (!currentUrl) return;
    
    try {
        const response = await fetch('/download-compressed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_url: currentUrl
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `compressed_${selectedFiles[currentImageIndex].name}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            throw new Error('下载失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('下载失败');
    }
});

// 导航函数
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

// 更新导航按钮状态
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

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 在现有代码后添加批量下载功能
async function downloadAllImages() {
    if (!processedImages.length) return;
    
    try {
        const response = await fetch('/download-all-compressed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                files: processedImages
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `compressed_images_${Date.now()}.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            throw new Error('下载失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('批量下载失败');
    }
}

// 添加批量下载按钮事件监听
document.getElementById('downloadAllBtn').addEventListener('click', downloadAllImages); 