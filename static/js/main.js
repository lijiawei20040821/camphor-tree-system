// 主JavaScript文件
class CamphorTreeSystem {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupAjax();
        this.checkAuth();
    }

    setupEventListeners() {
        // 全局点击事件
        document.addEventListener('click', this.handleGlobalClick.bind(this));
        
        // 表单提交事件
        document.addEventListener('submit', this.handleFormSubmit.bind(this));
        
        // 页面加载完成事件
        document.addEventListener('DOMContentLoaded', this.onPageLoad.bind(this));
    }

    setupAjax() {
        // 设置AJAX全局配置
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                    xhr.setRequestHeader("X-CSRFToken", this.getCSRFToken());
                }
            }.bind(this)
        });
    }

    getCSRFToken() {
        // 从meta标签获取CSRF token
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    handleGlobalClick(e) {
        // 处理全局点击事件
        const target = e.target;
        
        // 处理下拉菜单
        if (target.classList.contains('dropdown-toggle')) {
            this.toggleDropdown(target);
        }
        
        // 处理模态框关闭
        if (target.classList.contains('modal-close') || target.closest('.modal-close')) {
            this.closeModal(target);
        }
    }

    handleFormSubmit(e) {
        const form = e.target;
        
        // 防止默认提交
        e.preventDefault();
        
        // 验证表单
        if (!this.validateForm(form)) {
            return false;
        }
        
        // 处理AJAX表单提交
        if (form.classList.contains('ajax-form')) {
            this.submitAjaxForm(form);
            return false;
        }
        
        return true;
    }

    validateForm(form) {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.showFieldError(input, '此字段为必填项');
                isValid = false;
            } else {
                this.clearFieldError(input);
            }
        });
        
        return isValid;
    }

    submitAjaxForm(form) {
        const formData = new FormData(form);
        const url = form.getAttribute('action') || window.location.href;
        const method = form.getAttribute('method') || 'POST';
        
        this.showLoading();
        
        fetch(url, {
            method: method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            this.hideLoading();
            
            if (data.success) {
                this.showAlert(data.message, 'success');
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1500);
                }
            } else {
                this.showAlert(data.message, 'error');
            }
        })
        .catch(error => {
            this.hideLoading();
            this.showAlert('请求失败，请检查网络连接', 'error');
            console.error('AJAX请求错误:', error);
        });
    }

    showLoading() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.style.display = 'block';
        }
    }

    hideLoading() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alertId = 'alert-' + Date.now();
        const alertClass = `alert alert-${type} alert-dismissible fade show`;
        
        const alertHTML = `
            <div id="${alertId}" class="${alertClass}" role="alert">
                <strong>${this.getAlertTitle(type)}</strong> ${message}
                <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHTML);
        
        // 自动消失
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }

    getAlertTitle(type) {
        const titles = {
            'success': '成功!',
            'error': '错误!',
            'warning': '警告!',
            'info': '提示!'
        };
        return titles[type] || '提示!';
    }

    showFieldError(input, message) {
        this.clearFieldError(input);
        
        input.classList.add('is-invalid');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        input.parentNode.appendChild(errorDiv);
    }

    clearFieldError(input) {
        input.classList.remove('is-invalid');
        
        const existingError = input.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
    }

    toggleDropdown(button) {
        const dropdown = button.closest('.dropdown');
        dropdown.classList.toggle('show');
    }

    closeModal(button) {
        const modal = button.closest('.modal');
        modal.style.display = 'none';
    }

    onPageLoad() {
        // 页面特定的初始化
        this.initializeCharts();
        this.initializeDataTables();
        this.initializeDatePickers();
    }

    initializeCharts() {
        // 初始化图表
        const chartElements = document.querySelectorAll('[data-chart]');
        chartElements.forEach(element => {
            const chartType = element.getAttribute('data-chart');
            const chartData = element.getAttribute('data-chart-data');
            
            if (chartData) {
                this.createChart(element, chartType, JSON.parse(chartData));
            }
        });
    }

    createChart(canvas, type, data) {
        return new Chart(canvas, {
            type: type,
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    initializeDataTables() {
        // 初始化数据表格
        const tables = document.querySelectorAll('.data-table');
        tables.forEach(table => {
            if (typeof $.fn.DataTable !== 'undefined') {
                $(table).DataTable({
                    language: {
                        url: '//cdn.datatables.net/plug-ins/1.10.25/i18n/Chinese.json'
                    },
                    responsive: true
                });
            }
        });
    }

    initializeDatePickers() {
        // 初始化日期选择器
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            if (typeof flatpickr !== 'undefined') {
                flatpickr(input, {
                    dateFormat: 'Y-m-d',
                    locale: 'zh'
                });
            }
        });
    }

    checkAuth() {
        // 检查用户认证状态
        const authRequired = document.body.getAttribute('data-auth-required');
        if (authRequired && !this.isAuthenticated()) {
            window.location.href = '/login';
        }
    }

    isAuthenticated() {
        // 检查用户是否已认证
        return document.body.getAttribute('data-user-authenticated') === 'true';
    }

    // 工具方法
    formatNumber(num) {
        return new Intl.NumberFormat('zh-CN').format(num);
    }

    formatDate(date) {
        return new Intl.DateTimeFormat('zh-CN').format(new Date(date));
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// 初始化系统
document.addEventListener('DOMContentLoaded', function() {
    window.camphorSystem = new CamphorTreeSystem();
});

// 工具函数
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        window.camphorSystem.showAlert('已复制到剪贴板', 'success');
    });
}