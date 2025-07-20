/**
 * 情報技術者試験学習システム - チャート機能
 */

// チャート設定
const ChartConfig = {
    colors: [
        '#3498db', // Blue
        '#e74c3c', // Red
        '#2ecc71', // Green
        '#f39c12', // Orange
        '#9b59b6', // Purple
        '#1abc9c', // Turquoise
        '#34495e', // Dark Gray
        '#e67e22'  // Dark Orange
    ],
    
    defaultLayout: {
        font: { family: 'Segoe UI, sans-serif', size: 14 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        showlegend: true,
        legend: {
            x: 0,
            y: 1.02,
            orientation: 'h'
        },
        margin: { t: 40, l: 60, r: 40, b: 60 }
    },
    
    responsive: true,
    displayModeBar: false
};

// チャート作成クラス
class ChartCreator {
    constructor() {
        this.config = ChartConfig;
    }
    
    /**
     * 進捗チャートを作成
     */
    createProgressChart(containerId, data) {
        if (!data || data.length === 0) {
            this.createEmptyChart(containerId, '進捗データがありません');
            return;
        }
        
        const dates = data.map(d => d.study_date);
        const correctRates = data.map(d => d.correct_rate);
        const totalQuestions = data.map(d => d.total_questions);
        
        const trace1 = {
            x: dates,
            y: correctRates,
            mode: 'lines+markers',
            name: '正答率',
            line: { color: this.config.colors[0], width: 3 },
            marker: { size: 8 },
            yaxis: 'y',
            hovertemplate: '<b>%{x}</b><br>正答率: %{y:.1f}%<extra></extra>'
        };
        
        const trace2 = {
            x: dates,
            y: totalQuestions,
            type: 'bar',
            name: '学習量',
            marker: { color: this.config.colors[1] },
            yaxis: 'y2',
            hovertemplate: '<b>%{x}</b><br>学習量: %{y}問<extra></extra>'
        };
        
        const layout = {
            ...this.config.defaultLayout,
            title: '学習進捗の推移',
            xaxis: { title: '日付' },
            yaxis: { 
                title: '正答率 (%)',
                side: 'left',
                range: [0, 100]
            },
            yaxis2: {
                title: '学習量 (問)',
                side: 'right',
                overlaying: 'y',
                range: [0, Math.max(...totalQuestions) * 1.1]
            }
        };
        
        // 合格ライン（60%）を追加
        layout.shapes = [{
            type: 'line',
            x0: dates[0],
            x1: dates[dates.length - 1],
            y0: 60,
            y1: 60,
            line: { color: 'red', width: 2, dash: 'dash' }
        }];
        
        layout.annotations = [{
            x: dates[Math.floor(dates.length / 2)],
            y: 65,
            text: '合格ライン (60%)',
            showarrow: false,
            font: { color: 'red' }
        }];
        
        Plotly.newPlot(containerId, [trace1, trace2], layout, {
            responsive: true,
            displayModeBar: false
        });
    }
    
    /**
     * 分野別パフォーマンスチャートを作成
     */
    createCategoryChart(containerId, data) {
        if (!data || data.length === 0) {
            this.createEmptyChart(containerId, '分野別データがありません');
            return;
        }
        
        const categories = data.map(d => d.category);
        const correctRates = data.map(d => d.correct_rate);
        const totalQuestions = data.map(d => d.total_questions);
        
        // 正答率に基づいて色を設定
        const colors = correctRates.map(rate => {
            if (rate >= 80) return this.config.colors[2]; // Green
            if (rate >= 60) return this.config.colors[0]; // Blue
            if (rate >= 40) return this.config.colors[3]; // Orange
            return this.config.colors[1]; // Red
        });
        
        const trace1 = {
            x: categories,
            y: correctRates,
            type: 'bar',
            name: '正答率',
            marker: { color: colors },
            text: correctRates.map(rate => `${rate.toFixed(1)}%`),
            textposition: 'auto',
            hovertemplate: '<b>%{x}</b><br>正答率: %{y:.1f}%<extra></extra>'
        };
        
        const trace2 = {
            x: categories,
            y: totalQuestions,
            type: 'bar',
            name: '学習量',
            marker: { color: this.config.colors[4] },
            text: totalQuestions,
            textposition: 'auto',
            yaxis: 'y2',
            hovertemplate: '<b>%{x}</b><br>学習量: %{y}問<extra></extra>'
        };
        
        const layout = {
            ...this.config.defaultLayout,
            title: '分野別パフォーマンス',
            xaxis: { title: '分野', tickangle: 45 },
            yaxis: { 
                title: '正答率 (%)',
                side: 'left',
                range: [0, 100]
            },
            yaxis2: {
                title: '学習量 (問)',
                side: 'right',
                overlaying: 'y'
            },
            barmode: 'group'
        };
        
        Plotly.newPlot(containerId, [trace1, trace2], layout, {
            responsive: true,
            displayModeBar: false
        });
    }
    
    /**
     * 円グラフを作成
     */
    createPieChart(containerId, data, title) {
        if (!data || data.length === 0) {
            this.createEmptyChart(containerId, 'データがありません');
            return;
        }
        
        const trace = {
            labels: data.map(d => d.label),
            values: data.map(d => d.value),
            type: 'pie',
            marker: { colors: this.config.colors },
            textinfo: 'label+percent',
            textposition: 'auto',
            hovertemplate: '<b>%{label}</b><br>%{value}<br>%{percent}<extra></extra>'
        };
        
        const layout = {
            ...this.config.defaultLayout,
            title: title || '分布',
            height: 400
        };
        
        Plotly.newPlot(containerId, [trace], layout, {
            responsive: true,
            displayModeBar: false
        });
    }
    
    /**
     * 学習パターンチャートを作成
     */
    createStudyPatternChart(containerId, hourlyData) {
        if (!hourlyData || Object.keys(hourlyData).length === 0) {
            this.createEmptyChart(containerId, '学習パターンデータがありません');
            return;
        }
        
        const hours = Object.keys(hourlyData).map(h => parseInt(h)).sort((a, b) => a - b);
        const correctRates = hours.map(h => {
            const stats = hourlyData[h];
            return (stats.correct / stats.total * 100).toFixed(1);
        });
        const questionCounts = hours.map(h => hourlyData[h].total);
        
        const trace1 = {
            x: hours,
            y: correctRates,
            mode: 'lines+markers',
            name: '正答率',
            line: { color: this.config.colors[0], width: 3 },
            marker: { size: 8 },
            yaxis: 'y',
            hovertemplate: '<b>%{x}時</b><br>正答率: %{y}%<extra></extra>'
        };
        
        const trace2 = {
            x: hours,
            y: questionCounts,
            type: 'bar',
            name: '学習量',
            marker: { color: this.config.colors[2] },
            yaxis: 'y2',
            hovertemplate: '<b>%{x}時</b><br>学習量: %{y}問<extra></extra>'
        };
        
        const layout = {
            ...this.config.defaultLayout,
            title: '時間帯別学習パターン',
            xaxis: { 
                title: '時間',
                tickvals: hours,
                ticktext: hours.map(h => `${h}時`)
            },
            yaxis: { 
                title: '正答率 (%)',
                side: 'left',
                range: [0, 100]
            },
            yaxis2: {
                title: '学習量 (問)',
                side: 'right',
                overlaying: 'y'
            }
        };
        
        Plotly.newPlot(containerId, [trace1, trace2], layout, {
            responsive: true,
            displayModeBar: false
        });
    }
    
    /**
     * 成長傾向チャートを作成
     */
    createGrowthTrendChart(containerId, weeklyRates) {
        if (!weeklyRates || weeklyRates.length === 0) {
            this.createEmptyChart(containerId, '成長傾向データがありません');
            return;
        }
        
        const weeks = weeklyRates.map((_, index) => `第${index + 1}週`);
        
        const trace = {
            x: weeks,
            y: weeklyRates.map(rate => rate * 100),
            mode: 'lines+markers',
            name: '週別正答率',
            line: { color: this.config.colors[4], width: 4 },
            marker: { size: 10 },
            fill: 'tonexty',
            fillcolor: 'rgba(155, 89, 182, 0.2)',
            hovertemplate: '<b>%{x}</b><br>正答率: %{y:.1f}%<extra></extra>'
        };
        
        const layout = {
            ...this.config.defaultLayout,
            title: '週別成長傾向',
            xaxis: { title: '週' },
            yaxis: { 
                title: '正答率 (%)',
                range: [0, 100]
            }
        };
        
        Plotly.newPlot(containerId, [trace], layout, {
            responsive: true,
            displayModeBar: false
        });
    }
    
    /**
     * 空のチャートを作成
     */
    createEmptyChart(containerId, message) {
        const layout = {
            ...this.config.defaultLayout,
            title: message,
            xaxis: { visible: false },
            yaxis: { visible: false },
            showlegend: false
        };
        
        layout.annotations = [{
            x: 0.5,
            y: 0.5,
            text: message,
            xref: 'paper',
            yref: 'paper',
            showarrow: false,
            font: { size: 16, color: 'gray' }
        }];
        
        Plotly.newPlot(containerId, [], layout, {
            responsive: true,
            displayModeBar: false
        });
    }
    
    /**
     * 全チャートをレスポンシブに更新
     */
    updateAllCharts() {
        const charts = document.querySelectorAll('.plotly-graph-div');
        charts.forEach(chart => {
            Plotly.Plots.resize(chart);
        });
    }
}

// アニメーション関数
class AnimationHelper {
    /**
     * 要素をフェードイン
     */
    static fadeIn(element, duration = 500) {
        element.style.opacity = '0';
        element.style.transition = `opacity ${duration}ms ease-in-out`;
        
        requestAnimationFrame(() => {
            element.style.opacity = '1';
        });
    }
    
    /**
     * 要素をスライドイン
     */
    static slideIn(element, direction = 'left', duration = 500) {
        const transform = direction === 'left' ? 'translateX(-20px)' : 'translateY(20px)';
        
        element.style.opacity = '0';
        element.style.transform = transform;
        element.style.transition = `all ${duration}ms ease-in-out`;
        
        requestAnimationFrame(() => {
            element.style.opacity = '1';
            element.style.transform = 'translate(0, 0)';
        });
    }
    
    /**
     * 数値をアニメーション
     */
    static animateNumber(element, start, end, duration = 1000) {
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // イージング関数 (ease-out)
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = start + (end - start) * easeOut;
            
            element.textContent = Math.round(current);
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }
    
    /**
     * プログレスバーをアニメーション
     */
    static animateProgressBar(element, targetWidth, duration = 1000) {
        element.style.width = '0%';
        element.style.transition = `width ${duration}ms ease-out`;
        
        requestAnimationFrame(() => {
            element.style.width = targetWidth + '%';
        });
    }
}

// ページロード時の初期化
document.addEventListener('DOMContentLoaded', function() {
    const chartCreator = new ChartCreator();
    
    // レスポンシブ対応
    window.addEventListener('resize', function() {
        chartCreator.updateAllCharts();
    });
    
    // 統計カードのアニメーション
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        setTimeout(() => {
            AnimationHelper.slideIn(card, 'bottom', 500);
        }, index * 100);
    });
    
    // 数値のアニメーション
    const valueElements = document.querySelectorAll('.stat-card .value');
    valueElements.forEach(element => {
        const value = parseInt(element.textContent);
        if (!isNaN(value)) {
            AnimationHelper.animateNumber(element, 0, value, 1000);
        }
    });
    
    // プログレスバーのアニメーション
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach((bar, index) => {
        const width = bar.dataset.width || 0;
        setTimeout(() => {
            AnimationHelper.animateProgressBar(bar, width, 1000);
        }, index * 200);
    });
    
    // チャートの遅延読み込み
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach((container, index) => {
        setTimeout(() => {
            AnimationHelper.fadeIn(container, 800);
        }, 500 + index * 300);
    });
});

// ユーティリティ関数
const ChartUtils = {
    /**
     * データをCSVでエクスポート
     */
    exportToCSV(data, filename = 'chart_data.csv') {
        const csv = this.convertToCSV(data);
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    },
    
    /**
     * データをCSV形式に変換
     */
    convertToCSV(data) {
        if (!data || data.length === 0) return '';
        
        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header => `"${row[header]}"`).join(','))
        ];
        
        return csvContent.join('\n');
    },
    
    /**
     * チャートを画像として保存
     */
    saveChartAsImage(containerId, filename = 'chart.png') {
        const container = document.getElementById(containerId);
        if (container) {
            Plotly.toImage(container, {
                format: 'png',
                width: 800,
                height: 600
            }).then(function(url) {
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                link.click();
            });
        }
    },
    
    /**
     * カラーパレットを取得
     */
    getColorPalette(count) {
        const colors = ChartConfig.colors;
        const palette = [];
        
        for (let i = 0; i < count; i++) {
            palette.push(colors[i % colors.length]);
        }
        
        return palette;
    }
};

// グローバルに公開
window.ChartCreator = ChartCreator;
window.AnimationHelper = AnimationHelper;
window.ChartUtils = ChartUtils;