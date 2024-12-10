// 全局变量
let selectedFiles = [];
let currentImageIndex = 0;
let processedImages = new Map();  // 使用Map存储索引和图片URL的对应关系

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeDropZone();
    initializeFileInput();
    
    // 水印类型切换
    document.getElementById('watermarkType').addEventListener('change', function(e) {
        const textSettings = document.getElementById('textSettings');
        const imageSettings = document.getElementById('imageSettings');
        
        if (this.value === 'text') {
            textSettings.classList.remove('d-none');
            imageSettings.classList.add('d-none');
        } else {
            textSettings.classList.add('d-none');
            imageSettings.classList.remove('d-none');
        }
    });
    
    // 水印设置变更时更新预览
    const settingsInputs = document.querySelectorAll('.watermark-settings input, .watermark-settings select');
    settingsInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (selectedFiles.length > 0) {
                processCurrentImage();
            }
        });
    });
});

// 初始放区域
function initializeDropZone() {
    const dropZone = document.getElementById('watermarkDropZone');
    
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

    dropZone.addEventListener('drop', handleDrop, false);
}

// 处理文件拖放
function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

// 初始化文件输入
function initializeFileInput() {
    const fileInput = document.getElementById('watermarkFileInput');
    fileInput.addEventListener('change', function(e) {
        handleFiles(this.files);
    });
}

// 处理选择的文件
function handleFiles(files) {
    if (files.length === 0) return;
    
    selectedFiles = Array.from(files);
    currentImageIndex = 0;
    
    // 显示预览容器
    document.getElementById('watermarkPreviewContainer').classList.remove('d-none');
    
    // 显示第一张图片
    showImage(currentImageIndex);
    updateNavigationButtons();
}

// 显示指定索引的图片
function showImage(index) {
    if (index < 0 || index >= selectedFiles.length) return;
    
    const file = selectedFiles[index];
    const reader = new FileReader();
    
    reader.onload = function(e) {
        // 显示原图
        const originalPreview = document.getElementById('originalPreview');
        originalPreview.src = e.target.result;
        
        // 处理水印
        processCurrentImage();
    };
    
    reader.readAsDataURL(file);
}

// 更新下载按钮状态
function updateDownloadButtons() {
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadAllBtn = document.getElementById('downloadAllBtn');
    
    downloadBtn.classList.remove('d-none');
    downloadBtn.onclick = downloadCurrentImage;
    
    if (selectedFiles.length > 1) {
        downloadAllBtn.classList.remove('d-none');
        downloadAllBtn.onclick = downloadAllImages;
    } else {
        downloadAllBtn.classList.add('d-none');
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 处理当前图片
async function processCurrentImage() {
    const file = selectedFiles[currentImageIndex];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('image', file);
    
    // 添加水印设置
    const type = document.getElementById('watermarkType').value;
    formData.append('type', type);
    
    if (type === 'text') {
        formData.append('text', document.getElementById('watermarkText').value);
    } else {
        const watermarkFile = document.getElementById('watermarkImage').files[0];
        if (watermarkFile) {
            formData.append('watermark', watermarkFile);
        }
    }
    
    formData.append('position', document.getElementById('watermarkPosition').value);
    formData.append('opacity', document.getElementById('watermarkOpacity').value);
    formData.append('size', document.getElementById('watermarkSize').value);
    
    try {
        const response = await fetch('/add-watermark', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            const resultPreview = document.getElementById('resultPreview');
            resultPreview.src = data.image_url;
            // 保存处理后的图片路径
            processedImages.set(currentImageIndex, data.image_url);
            updateDownloadButtons();
        } else {
            alert(data.error || '处理失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('处理失败');
    }
}

// 显示上一张图片
function showPreviousImage() {
    if (currentImageIndex > 0) {
        currentImageIndex--;
        showImage(currentImageIndex);
        updateNavigationButtons();
    }
}

// 显示下一张图片
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

// 下载当前图片
async function downloadCurrentImage() {
    const resultPreview = document.getElementById('resultPreview');
    const response = await fetch(resultPreview.src);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `watermark_${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// 实现批量下载功能
async function downloadAllImages() {
    try {
        // 收集所有已处理的图片路径
        const paths = Array.from(processedImages.values());
        if (paths.length === 0) {
            alert('没有可下载的图片');
            return;
        }
        
        const response = await fetch('/download-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ paths })
        });
        
        if (response.ok) {
            // 创建blob并下载
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `watermarks_${Date.now()}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const error = await response.json();
            throw new Error(error.error || '下载失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert(error.message || '下载失败');
    }
}