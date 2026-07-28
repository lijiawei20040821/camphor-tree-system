// 图表相关功能
class ChartManager {
    constructor() {
        this.charts = new Map();
    }

    createGrowthStatusChart(data) {
        const ctx = document.getElementById('growthStatusChart').getContext('2d');
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['正常', '衰弱', '濒危'],
                datasets: [{
                    data: [data.normal || 0, data.weak || 0, data.critical || 0],
                    backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: '生长势分布'
                    }
                }
            }
        });
    }

    createCarbonTrendChart(data) {
        const ctx = document.getElementById('carbonTrendChart').getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: '年固碳量 (kg)',
                    data: data.values || [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: '固碳量 (kg)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '年份'
                        }
                    }
                }
            }
        });
    }

    createCorrelationHeatmap(data) {
        const ctx = document.getElementById('correlationHeatmap').getContext('2d');
        return new Chart(ctx, {
            type: 'correlation',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: '相关性',
                    data: data.matrix || [],
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    x: {
                        type: 'category'
                    },
                    y: {
                        type: 'category'
                    }
                }
            }
        });
    }

    destroyChart(chartId) {
        if (this.charts.has(chartId)) {
            this.charts.get(chartId).destroy();
            this.charts.delete(chartId);
        }
    }

    updateChart(chartId, newData) {
        if (this.charts.has(chartId)) {
            const chart = this.charts.get(chartId);
            chart.data = newData;
            chart.update();
        }
    }
}

// 初始化图表管理器
window.chartManager = new ChartManager();