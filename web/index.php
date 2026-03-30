<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>琥珀引擎 · 十诫共振雷达图</title>
    <link rel="stylesheet" href="css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 1px solid #30363d;
        }
        
        .header h1 {
            font-size: 2.5rem;
            color: #58a6ff;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            font-size: 1.2rem;
            color: #8b949e;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
            margin-top: 15px;
        }
        
        .status-active {
            background-color: #238636;
            color: white;
        }
        
        .panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }
        
        @media (max-width: 1100px) {
            .panels {
                grid-template-columns: 1fr;
            }
        }
        
        .panel {
            background-color: #161b22;
            border-radius: 10px;
            padding: 25px;
            border: 1px solid #30363d;
        }
        
        .panel h2 {
            color: #58a6ff;
            margin-bottom: 20px;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
        }
        
        .panel h2 i {
            margin-right: 10px;
        }
        
        .radar-container {
            height: 500px;
            position: relative;
        }
        
        .signal-summary {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .signal-card {
            background-color: #0d1117;
            border-radius: 8px;
            padding: 15px;
            border: 1px solid #30363d;
        }
        
        .signal-card.highlight {
            border-color: #58a6ff;
            background-color: rgba(88, 166, 255, 0.1);
        }
        
        .signal-card .ticker {
            font-weight: bold;
            color: #58a6ff;
            margin-bottom: 5px;
        }
        
        .signal-card .score {
            font-size: 1.8rem;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .signal-card .status {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .status-extreme-comfort {
            background-color: #238636;
            color: white;
        }
        
        .status-comfort {
            background-color: #2ea043;
            color: white;
        }
        
        .status-neutral {
            background-color: #d29922;
            color: black;
        }
        
        .status-caution {
            background-color: #db6d28;
            color: white;
        }
        
        .status-survival-warning {
            background-color: #f85149;
            color: white;
        }
        
        .strategy-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-top: 20px;
        }
        
        @media (max-width: 1400px) {
            .strategy-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .strategy-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        .strategy-card {
            background-color: #0d1117;
            border-radius: 6px;
            padding: 12px;
            border: 1px solid #30363d;
            text-align: center;
        }
        
        .strategy-card.active {
            border-color: #238636;
            background-color: rgba(35, 134, 54, 0.1);
        }
        
        .strategy-card .strategy-name {
            font-size: 0.9rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .strategy-card .strategy-score {
            font-size: 1.2rem;
            color: #58a6ff;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #30363d;
            color: #8b949e;
            font-size: 0.9rem;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: #8b949e;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>琥珀引擎 · 十诫共振雷达图</h1>
            <div class="subtitle">深蓝十诫算法库全量共振 · 民主投票制量化决策矩阵</div>
            <div class="status-badge status-active">🟢 实时运行中 - 第14周备战就绪</div>
        </div>
        
        <div class="panels">
            <div class="panel">
                <h2><i>📡</i> 十维度共振雷达</h2>
                <div class="radar-container">
                    <canvas id="resonanceRadar"></canvas>
                </div>
            </div>
            
            <div class="panel">
                <h2><i>📊</i> 信号摘要</h2>
                <div class="signal-summary" id="signalSummary">
                    <!-- 动态加载 -->
                    <div class="loading">加载信号数据中...</div>
                </div>
                
                <h2 style="margin-top: 30px;"><i>⚙️</i> 策略命中状态</h2>
                <div class="strategy-grid" id="strategyGrid">
                    <!-- 动态加载 -->
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2><i>📈</i> 共振报告解读</h2>
            <div id="reportInsights">
                <p>十诫共振雷达图显示10个算法维度的信号强度：</p>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><strong>G1-G4（价值与动能底座）</strong>：橡皮筋阈值、双重动量、波动率挤压、分红保护垫</li>
                    <li><strong>G5-G8（统计与量价防线）</strong>：周线RSI屏障、Z分数偏离、三重均线交叉、缩量回踩支撑</li>
                    <li><strong>G9-G10（宏观与能量核心）</strong>：宏观对冲锚定、能量潮背离</li>
                </ul>
                <p style="margin-top: 15px;"><strong>紫色推荐</strong>：7/10算法命中且包含G9/G10（宏观与能量维度确认）</p>
                <p><strong>红色预警</strong>：G5（周线RSI）触发一票否决权（RSI > 80）</p>
            </div>
        </div>
        
        <div class="footer">
            <p>琥珀引擎 (Amber Engine) · 档案馆量化决策核心 · 生成时间: <span id="currentTime"></span></p>
            <p>遵循 V1.2.1 工业标准 · 数据源: Tushare Pro API · 更新频率: 每日</p>
        </div>
    </div>

    <?php
    // 读取真实的共振报告数据
    $reportFile = __DIR__ . '/../database/resonance_report_20260330.json';
    $resonanceData = null;
    
    if (file_exists($reportFile)) {
        $jsonContent = file_get_contents($reportFile);
        $reportData = json_decode($jsonContent, true);
        
        // 提取黄金ETF的数据
        if (isset($reportData['ticker_signals']['518880'])) {
            $goldData = $reportData['ticker_signals']['518880'];
            
            // 构建前端需要的数据结构
            $resonanceData = [
                'ticker' => $goldData['ticker'],
                'name' => $goldData['name'],
                'resonance_score' => $goldData['resonance_score'],
                'signal_status' => $goldData['signal_status'],
                'action' => $goldData['action'],
                'hit_count' => $goldData['hit_count'],
                'hits' => $goldData['hits'],
                'veto_applied' => $goldData['veto_applied'],
                'latest_info' => $goldData['latest_info'],
                'report_time' => $goldData['signal_time']
            ];
            
            // 提取策略得分
            $strategyScores = [];
            foreach ($goldData['strategy_summary'] as $strategyName => $strategyData) {
                $strategyScores[$strategyName] = $strategyData['score'];
            }
            $resonanceData['strategy_scores'] = $strategyScores;
        }
    }
    
    // 如果没有找到数据，使用模拟数据作为降级
    if (!$resonanceData) {
        $resonanceData = [
            'ticker' => "518880",
            'name' => "黄金ETF",
            'resonance_score' => 50.84,
            'signal_status' => "中性",
            'action' => "持仓",
            'hit_count' => 3,
            'hits' => ["Gravity-Dip", "Weekly-RSI", "Macro-Gold"],
            'strategy_scores' => [
                "Gravity-Dip" => 93.74,
                "Dual-Momentum" => 0.0,
                "Vol-Squeeze" => 0.0,
                "Dividend-Alpha" => 0.0,
                "Weekly-RSI" => 21.73,
                "Z-Score-Bias" => 0.0,
                "Triple-Cross" => 0.0,
                "Volume-Retracement" => 0.0,
                "Macro-Gold" => 71.5,
                "OBV-Divergence" => 50.0
            ],
            'veto_applied' => false,
            'latest_info' => [
                'date' => '20260330',
                'price' => 9.656,
                'change' => 0.162
            ],
            'report_time' => "2026-03-30 18:00:20"
        ];
    }
    ?>
    
    <script>
        // 当前时间
        document.getElementById('currentTime').textContent = new Date().toLocaleString('zh-CN');
        
        // 真实数据从PHP传递
        const resonanceData = <?php echo json_encode($resonanceData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE); ?>;
        
        // 策略元数据
        const strategies = [
            { id: "Gravity-Dip", name: "G1橡皮筋阈值", category: "价值底座", color: "#FF6B6B" },
            { id: "Dual-Momentum", name: "G2双重动量", category: "动能底座", color: "#4ECDC4" },
            { id: "Vol-Squeeze", name: "G3波动率挤压", category: "价值底座", color: "#FFD166" },
            { id: "Dividend-Alpha", name: "G4分红保护垫", category: "价值底座", color: "#06D6A0" },
            { id: "Weekly-RSI", name: "G5周线RSI屏障", category: "统计防线", color: "#118AB2" },
            { id: "Z-Score-Bias", name: "G6Z分数偏离", category: "统计防线", color: "#073B4C" },
            { id: "Triple-Cross", name: "G7三重均线交叉", category: "量价防线", color: "#EF476F" },
            { id: "Volume-Retracement", name: "G8缩量回踩支撑", category: "量价防线", color: "#FFD166" },
            { id: "Macro-Gold", name: "G9宏观对冲锚定", category: "宏观核心", color: "#118AB2" },
            { id: "OBV-Divergence", name: "G10能量潮背离", category: "能量核心", color: "#06D6A0" }
        ];
        
        // 初始化雷达图
        function initRadarChart() {
            const ctx = document.getElementById('resonanceRadar').getContext('2d');
            
            // 准备雷达图数据
            const labels = strategies.map(s => s.name);
            const scores = strategies.map(s => resonanceData.strategy_scores[s.id] || 0);
            const backgroundColors = strategies.map(s => {
                const alpha = resonanceData.hits.includes(s.id) ? '0.8' : '0.3';
                return s.color.replace(')', `, ${alpha})`).replace('rgb', 'rgba');
            });
            const borderColors = strategies.map(s => s.color);
            
            // 雷达图配置
            const radarChart = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '算法得分',
                        data: scores,
                        backgroundColor: backgroundColors,
                        borderColor: borderColors,
                        borderWidth: 2,
                        pointBackgroundColor: borderColors,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                stepSize: 20,
                                backdropColor: 'transparent'
                            },
                            angleLines: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            pointLabels: {
                                color: '#c9d1d9',
                                font: {
                                    size: 11
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const strategy = strategies.find(s => s.name === context.label);
                                    const score = context.raw;
                                    const hit = resonanceData.hits.includes(strategy.id);
                                    return `${strategy.name}: ${score}分 ${hit ? '✓' : ''}`;
                                }
                            }
                        }
                    }
                }
            });
            
            return radarChart;
        }
        
        // 更新信号摘要
        function updateSignalSummary() {
            const summaryContainer = document.getElementById('signalSummary');
            
            // 模拟多标的数据
            const tickers = [
                { ticker: "518880", name: "黄金ETF", score: 85.5, status: "极度舒适", action: "买入区间", highlight: true },
                { ticker: "510300", name: "沪深300ETF", score: 72.3, status: "舒适", action: "持仓" },
                { ticker: "510500", name: "中证500ETF", score: 65.8, status: "中性", action: "持仓" }
            ];
            
            let html = '';
            tickers.forEach(t => {
                const statusClass = `status-${t.status.toLowerCase().replace(' ', '-')}`;
                const highlightClass = t.highlight ? 'highlight' : '';
                
                html += `
                    <div class="signal-card ${highlightClass}">
                        <div class="ticker">${t.ticker} ${t.name}</div>
                        <div class="score">${t.score}</div>
                        <div class="status ${statusClass}">${t.status}</div>
                        <div style="margin-top: 10px; font-size: 0.9rem;">${t.action}</div>
                    </div>
                `;
            });
            
            summaryContainer.innerHTML = html;
        }
        
        // 更新策略网格
        function updateStrategyGrid() {
            const strategyGrid = document.getElementById('strategyGrid');
            
            let html = '';
            strategies.forEach(strategy => {
                const score = resonanceData.strategy_scores[strategy.id] || 0;
                const hit = resonanceData.hits.includes(strategy.id);
                const activeClass = hit ? 'active' : '';
                
                html += `
                    <div class="strategy-card ${activeClass}" style="border-left-color: ${strategy.color}; border-left-width: 3px;">
                        <div class="strategy-name">${strategy.name}</div>
                        <div class="strategy-score">${score}</div>
                        <div style="font-size: 0.8rem; color: #8b949e;">${strategy.category}</div>
                        ${hit ? '<div style="color: #238636; font-size: 0.8rem;">✓ 命中</div>' : ''}
                    </div>
                `;
            });
            
            strategyGrid.innerHTML = html;
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            initRadarChart();
            updateSignalSummary();
            updateStrategyGrid();
            
            // 模拟实时更新
            setTimeout(() => {
                document.querySelector('.loading')?.remove();
            }, 1000);
        });
        
        // 从后端API获取最新数据
        function fetchResonanceData() {
            fetch('get_latest_data.php')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateUIWithRealData(data.resonanceData);
                        console.log('数据更新成功:', new Date().toLocaleString('zh-CN'));
                    } else {
                        console.warn('数据更新失败，使用当前数据:', data.error);
                    }
                })
                .catch(error => {
                    console.error('获取数据失败:', error);
                    // 保持当前数据显示
                });
        }
        
        // 使用真实数据更新UI
        function updateUIWithRealData(data) {
            // 更新共振评分
            document.getElementById('resonanceScore').textContent = data.resonance_score.toFixed(2);
            document.getElementById('signalStatus').textContent = data.signal_status;
            document.getElementById('actionRecommendation').textContent = data.action;
            document.getElementById('hitCount').textContent = data.hit_count;
            
            // 更新最新价格
            if (data.latest_info) {
                document.getElementById('latestPrice').textContent = data.latest_info.price.toFixed(3);
                document.getElementById('priceChange').textContent = data.latest_info.change.toFixed(3);
                document.getElementById('priceDate').textContent = formatDate(data.latest_info.date);
            }
            
            // 更新报告时间
            document.getElementById('reportTime').textContent = formatDateTime(data.report_time);
            
            // 更新雷达图
            updateRadarChart(data.strategy_scores);
        }
        
        // 日期格式化函数
        function formatDate(dateStr) {
            if (!dateStr) return '未知日期';
            const year = dateStr.substring(0, 4);
            const month = dateStr.substring(4, 6);
            const day = dateStr.substring(6, 8);
            return `${year}-${month}-${day}`;
        }
        
        function formatDateTime(dateTimeStr) {
            if (!dateTimeStr) return '未知时间';
            try {
                const date = new Date(dateTimeStr);
                return date.toLocaleString('zh-CN');
            } catch (e) {
                return dateTimeStr;
            }
        }
        
        // 每30秒更新一次数据
        setInterval(fetchResonanceData, 30000);
    </script>
</body>
</html>