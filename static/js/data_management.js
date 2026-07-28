// 数据管理功能修复
document.addEventListener('DOMContentLoaded', function() {
    console.log('数据管理页面加载完成');
    
    // 绑定导出按钮事件
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', function() {
            exportData('excel');
        });
    }
    
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            exportData('csv');
        });
    }
    
    // 绑定删除按钮事件
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const treeId = this.getAttribute('data-id');
            const treeRegion = this.getAttribute('data-region');
            deleteTreeData(treeId, treeRegion);
        });
    });
    
    // 绑定文件上传事件
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }
});

// 导出数据函数
function exportData(format) {
    const url = format === 'excel' ? '/api/export/trees' : '/api/export/csv';
    
    // 显示加载状态
    showLoading('正在导出数据...');
    
    fetch(url)
        .then(response => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error('导出失败: ' + response.status);
        })
        .then(blob => {
            // 创建下载链接
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // 设置文件名
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            const extension = format === 'excel' ? '.xlsx' : '.csv';
            a.download = `樟树数据_${timestamp}${extension}`;
            
            // 触发下载
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            hideLoading();
            showAlert('数据导出成功！', 'success');
        })
        .catch(error => {
            hideLoading();
            console.error('导出错误:', error);
            showAlert('导出失败: ' + error.message, 'error');
        });
}

// 删除数据函数
function deleteTreeData(treeId, treeRegion) {
    if (!confirm(`确定要删除区域为"${treeRegion}"的樟树数据吗？此操作不可撤销！`)) {
        return;
    }
    
    showLoading('正在删除数据...');
    
    fetch(`/api/trees/${treeId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            showAlert('数据删除成功！', 'success');
            // 刷新页面或移除对应行
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showAlert('删除失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('删除错误:', error);
        showAlert('删除失败: ' + error.message, 'error');
    });
}

// 文件上传处理
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 验证文件类型
    const allowedTypes = ['.xlsx', '.xls', '.csv'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(fileExtension)) {
        showAlert('请选择Excel或CSV格式的文件！', 'error');
        return;
    }
    
    // 验证文件大小（最大10MB）
    if (file.size > 10 * 1024 * 1024) {
        showAlert('文件大小不能超过10MB！', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading('正在上传文件...');
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            showAlert(`成功导入 ${data.count} 条数据！`, 'success');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showAlert('导入失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('上传错误:', error);
        showAlert('上传失败: ' + error.message, 'error');
    });
}

// 工具函数
function showLoading(message = '处理中...') {
    let loadingDiv = document.getElementById('loadingOverlay');
    if (!loadingDiv) {
        loadingDiv = document.createElement('div');
        loadingDiv.id = 'loadingOverlay';
        loadingDiv.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;
        loadingDiv.innerHTML = `
            <div style="background: white; padding: 20px; border-radius: 10px; text-align: center;">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">${message}</p>
            </div>
        `;
        document.body.appendChild(loadingDiv);
    }
}

function hideLoading() {
    const loadingDiv = document.getElementById('loadingOverlay');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function showAlert(message, type = 'info') {
    // 简单的alert替代方案
    alert(`${type.toUpperCase()}: ${message}`);
}