// 全局变量
let selectedFiles = [];
let currentImageIndex = 0;
let processedImages = new Map();  // 存储处理后的图片信息
let canvas = document.createElement('canvas');
let ctx = canvas.getContext('2d');
let currentOriginalImage = null;
let currentWatermarkImage = null;

// 添加字体加载检查函数
async function loadFonts() {
    const fonts = [
        new FontFace('Noto Sans SC', `url(${fontPath('NotoSansSC-Regular.ttf')})`),
        new FontFace('Noto Serif SC', `url(${fontPath('NotoSerifSC-Regular.ttf')})`),
        new FontFace('HarmonyOS Sans SC', `url(${fontPath('HarmonyOS_Sans_SC_Regular.ttf')})`),
        new FontFace('LXGW WenKai', `url(${fontPath('LXGWWenKai-Regular.ttf')})`),
        new FontFace('Source Han Sans CN', `url(${fontPath('SourceHanSansCN-Regular.otf')})`)
    ];

    try {
        const loadedFonts = await Promise.all(fonts.map(font => font.load()));
        loadedFonts.forEach(font => document.fonts.add(font));
        console.log('All fonts loaded successfully');
    } catch (error) {
        console.error('Error loading fonts:', error);
    }
}

function fontPath(filename) {
    return `/static/fonts/${filename}`;
}

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadFonts().then(() => {
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
        
        // 处理大小滑块的显示
        const sizeInput = document.getElementById('watermarkSize');
        if (sizeInput) {
            sizeInput.addEventListener('input', function(e) {
                document.getElementById('sizeValue').textContent = `${e.target.value}%`;
            });
        }
        
        // 监听所有水印设置的变化
        const settingsInputs = document.querySelectorAll('.watermark-settings input, .watermark-settings select');
        settingsInputs.forEach(input => {
            input.addEventListener('change', function() {
                if (currentOriginalImage) {
                    previewWatermark();
                }
            });
            
            // 对于 range 类型的输入，实现实时预览
            if (input.type === 'range') {
                input.addEventListener('input', function() {
                    // 更新显示值
                    if (this.id === 'watermarkRotation') {
                        document.getElementById('rotationValue').textContent = `${this.value}°`;
                    } else if (this.id === 'watermarkSize') {
                        document.getElementById('sizeValue').textContent = `${this.value}%`;
                    }
                    
                    if (currentOriginalImage) {
                        previewWatermark();
                    }
                });
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
    updateDownloadButtons();
}

// 显示指定引的图片
function showImage(index) {
    if (index < 0 || index >= selectedFiles.length) return;
    
    const file = selectedFiles[index];
    const reader = new FileReader();
    
    reader.onload = function(e) {
        // 显示原图
        const originalPreview = document.getElementById('originalPreview');
        originalPreview.src = e.target.result;
        
        // 加载图片用于 Canvas 处理
        currentOriginalImage = new Image();
        currentOriginalImage.onload = function() {
            // 初始化 canvas 尺寸
            canvas.width = currentOriginalImage.width;
            canvas.height = currentOriginalImage.height;
            // 预览水印
            previewWatermark();
        };
        currentOriginalImage.src = e.target.result;
    };
    
    reader.readAsDataURL(file);
}

// 新增预览水印函数
async function previewWatermark() {
    if (!currentOriginalImage) return;
    
    // 清空 canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // 绘制原图
    ctx.drawImage(currentOriginalImage, 0, 0);
    
    const type = document.getElementById('watermarkType').value;
    const position = document.getElementById('watermarkPosition').value;
    const opacity = document.getElementById('watermarkOpacity').value / 100;
    const sizePercent = parseInt(document.getElementById('watermarkSize').value);
    const rotation = parseInt(document.getElementById('watermarkRotation').value);
    
    // 保存当前上下文状态
    ctx.save();
    ctx.globalAlpha = opacity;
    
    if (type === 'text') {
        const text = document.getElementById('watermarkText').value;
        const font = document.getElementById('watermarkFont').value;
        const color = document.getElementById('watermarkColor').value;
        
        // 计算字体大小 - 使用与后端相同的逻辑
        const baseSize = Math.min(canvas.width, canvas.height);
        const minFontSize = 12;
        const maxFontSize = baseSize * 0.2; // 最大字体大小为图片较小边的 20%
        
        // 线性映射 sizePercent (1-50) 到字体大小范围
        let fontSize = minFontSize + (maxFontSize - minFontSize) * (sizePercent / 50);
        
        // 根据文字长度调整字体大小
        if (text.length > 10) {
            const adjustment = 1 - Math.log(text.length - 9) / Math.log(20);
            fontSize = fontSize * Math.max(0.5, adjustment);
        }
        
        fontSize = Math.floor(fontSize);
        
        // 设置字体
        ctx.font = `${fontSize}px "${getFontFamily(font)}"`;
        ctx.fillStyle = color;
        
        // 测量文字
        const metrics = ctx.measureText(text);
        const textWidth = metrics.width;
        const textHeight = fontSize;
        
        // 计算位置
        const { x, y } = calculatePosition(position, canvas.width, canvas.height, textWidth, textHeight);
        
        // 修改旋转处理
        ctx.translate(x + textWidth/2, y + textHeight/2);
        // 将角度转换为弧度，注意 PIL 和 Canvas 的旋转方向相反
        ctx.rotate(-rotation * Math.PI / 180);
        
        // 绘制文字，考虑垂直对齐
        ctx.textBaseline = 'middle';  // 设置文字垂直对齐方式
        ctx.textAlign = 'center';     // 设置文字水平对齐方式
        ctx.fillText(text, 0, 0);     // 在旋转中心点绘制文字
        
    } else if (type === 'image' && currentWatermarkImage) {
        // 计算水印图片大小
        const watermarkWidth = canvas.width * (sizePercent / 100);
        const watermarkHeight = (watermarkWidth / currentWatermarkImage.width) * currentWatermarkImage.height;
        
        // 计算位置
        const { x, y } = calculatePosition(position, canvas.width, canvas.height, watermarkWidth, watermarkHeight);
        
        // 修改旋转处理
        ctx.translate(x + watermarkWidth/2, y + watermarkHeight/2);
        // 将角度转换为弧度，注意 PIL 和 Canvas 的旋转方向相反
        ctx.rotate(-rotation * Math.PI / 180);
        
        // 在旋转中心点绘制图片
        ctx.drawImage(
            currentWatermarkImage, 
            -watermarkWidth/2, 
            -watermarkHeight/2, 
            watermarkWidth, 
            watermarkHeight
        );
    }
    
    ctx.restore();
    
    // 更新预览
    const resultPreview = document.getElementById('resultPreview');
    resultPreview.src = canvas.toDataURL('image/png');
    updateDownloadButtons();
}

// 添加字体映射函数
function getFontFamily(fontKey) {
    const fontMap = {
        'noto-sans': 'Noto Sans SC',
        'noto-serif': 'Noto Serif SC',
        'harmony-sans': 'HarmonyOS Sans SC',
        'lxgw': 'LXGW WenKai',
        'source-han': 'Source Han Sans CN'
    };
    return fontMap[fontKey] || 'Noto Sans SC';
}

// 修改位置计算函数，与后端保持一致
function calculatePosition(position, width, height, markWidth, markHeight) {
    // 设置边距（与后端保持一致）
    const paddingRatio = 0.05; // 边距比例为图片尺寸的 5%
    let paddingX = Math.floor(width * paddingRatio);
    let paddingY = Math.floor(height * paddingRatio);
    
    // 确保边距不会太大或太小
    paddingX = Math.max(20, Math.min(paddingX, 100));
    paddingY = Math.max(20, Math.min(paddingY, 100));
    
    let x, y;
    
    switch (position) {
        case 'center':
            x = (width - markWidth) / 2;
            y = (height - markHeight) / 2;
            break;
        case 'top-left':
            x = paddingX;
            y = paddingY;
            break;
        case 'top-right':
            x = width - markWidth - paddingX;
            y = paddingY;
            break;
        case 'bottom-left':
            x = paddingX;
            y = height - markHeight - paddingY;
            break;
        case 'bottom-right':
            x = width - markWidth - paddingX;
            y = height - markHeight - paddingY;
            break;
        default:
            x = (width - markWidth) / 2;
            y = (height - markHeight) / 2;
    }
    
    // 确保水印不会超出图片边界
    x = Math.max(0, Math.min(x, width - markWidth));
    y = Math.max(0, Math.min(y, height - markHeight));
    
    return { x, y };
}

// 修改水印图片上传处理
document.getElementById('watermarkImage').addEventListener('change', function(e) {
    if (this.files && this.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            currentWatermarkImage = new Image();
            currentWatermarkImage.onload = function() {
                previewWatermark();
            };
            currentWatermarkImage.src = e.target.result;
        };
        reader.readAsDataURL(this.files[0]);
    }
});

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
    
    // 添加通用设置 - 移到前面，确保所有类型都会传递这些参数
    formData.append('position', document.getElementById('watermarkPosition').value);
    formData.append('opacity', document.getElementById('watermarkOpacity').value);
    formData.append('size', document.getElementById('watermarkSize').value);
    formData.append('rotation', document.getElementById('watermarkRotation').value);  // 对所有类型都传递旋转角度
    
    if (type === 'text') {
        formData.append('text', document.getElementById('watermarkText').value);
        formData.append('font_name', document.getElementById('watermarkFont').value);
        formData.append('color', document.getElementById('watermarkColor').value);
    } else {
        const watermarkFile = document.getElementById('watermarkImage').files[0];
        if (watermarkFile) {
            formData.append('watermark', watermarkFile);
        }
    }
    
    try {
        const response = await fetch('/add-watermark', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            const resultPreview = document.getElementById('resultPreview');
            resultPreview.src = data.image_url;
            // 保存完整的图片URL
            processedImages.set(currentImageIndex, data.image_url.replace('/static/', ''));
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
    const formData = new FormData();
    formData.append('image', selectedFiles[currentImageIndex]);
    
    // 添加水印设置
    appendWatermarkSettings(formData);
    
    try {
        const response = await fetch('/add-watermark', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            // 下载处理后的图片
            const a = document.createElement('a');
            a.href = data.image_url;
            a.download = `watermark_${Date.now()}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            alert(data.error || '处理失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('处理失败');
    }
}

// 辅助函数：添加水印设置到 FormData
function appendWatermarkSettings(formData) {
    const type = document.getElementById('watermarkType').value;
    formData.append('type', type);
    formData.append('position', document.getElementById('watermarkPosition').value);
    formData.append('opacity', document.getElementById('watermarkOpacity').value);
    formData.append('size', document.getElementById('watermarkSize').value);
    formData.append('rotation', document.getElementById('watermarkRotation').value);
    
    if (type === 'text') {
        formData.append('text', document.getElementById('watermarkText').value);
        formData.append('font_name', document.getElementById('watermarkFont').value);
        formData.append('color', document.getElementById('watermarkColor').value);
    } else {
        const watermarkFile = document.getElementById('watermarkImage').files[0];
        if (watermarkFile) {
            formData.append('watermark', watermarkFile);
        }
    }
}

// 实现批量下载功能
async function downloadAllImages() {
    try {
        const promises = selectedFiles.map(async (file, index) => {
            const formData = new FormData();
            formData.append('image', file);
            appendWatermarkSettings(formData);
            
            const response = await fetch('/add-watermark', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`处理第 ${index + 1} 张图片失败`);
            }
            
            return response.json();
        });
        
        const results = await Promise.all(promises);
        const paths = results.map(result => result.image_url.replace('/static/', ''));
        
        if (paths.length === 0) {
            alert('没有可下载的图片');
            return;
        }
        
        const response = await fetch('/download-all-watermark', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ paths: paths })
        });
        
        if (response.ok) {
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