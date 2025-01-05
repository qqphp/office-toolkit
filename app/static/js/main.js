// 通用初始化代码
document.addEventListener('DOMContentLoaded', function() {
    console.log('Main JS loaded');
    
    // 检查是否在首页
    if (window.location.pathname === '/' || window.location.pathname === '/home') {
        // 延迟1秒显示弹窗
        setTimeout(() => {
            const contactModal = new bootstrap.Modal(document.getElementById('contactModal'));
            contactModal.show();
        }, 1000);
    }
}); 