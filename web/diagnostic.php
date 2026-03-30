<?php
/**
 * 琥珀引擎诊断工具 - 强力渗透版本
 * 用于诊断Web数据显示问题
 * 执行时间: 2026-03-30 22:25 GMT+8
 */

header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>琥珀引擎 · 诊断工具</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1, h2, h3 {
            color: #58a6ff;
        }
        
        .section {
            background-color: #161b22;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #30363d;
        }
        
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .status-ok {
            background-color: #238636;
            color: white;
        }
        
        .status-warning {
            background-color: #d29922;
            color: black;
        }
        
        .status-error {
            background-color: #f85149;
            color: white;
        }
        
        .data-box {
            background-color: #0d1117;
            border-radius: 8px;
            padding: 15px;
            margin-top: 10px;
            border: 1px solid #30363d;
            font-family: monospace;
            font-size: 0.9rem;
            white-space: pre-wrap;
            overflow-x: auto;
        }
        
        .file-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        
        .file-item {
            background-color: #0d1117;
            padding: 10px;
            border-radius: 6px;
            border: 1px solid #30363d;
        }
        
        .action-button {
            background-color: #238636;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            margin-right: 10px;
            margin-top: 10px;
        }
        
        .action-button:hover {
            background-color: #2ea043;
        }
        
        .action-button.warning {
            background-color: #d29922;
        }
        
        .action-button.warning:hover {
            background-color: #e6b422;
        }
        
        .action-button.danger {
            background-color: #f85149;
        }
        
        .action-button.danger:hover {
            background-color: #ff6b6b;
        }
    </style>
</head>
<body>
    <h1>琥珀引擎 · 诊断工具</h1>
    <p>强力渗透版本 v1.3.0 · 数据真实性验证</p>
    
    <?php
    // ============================================
    // 诊断函数
    // ============================================
    
    function checkFile($path, $description) {
        $result = [
            'description' => $description,
            'path' => $path,
            'exists' => file_exists($path),
            'readable' => false,
            'size' => 0,
            'mtime' => 0,
            'content' => null,
            'json_valid' => false,
            'score' => null
        ];
        
        if ($result['exists']) {
            $result['readable'] = is_readable($path);
            $result['size'] = filesize($path);
            $result['mtime'] = filemtime($path);
            
            if ($result['readable']) {
                $content = file_get_contents($path);
                $result['content'] = $content;
                
                $json = json_decode($content, true);
                $result['json_valid'] = ($json !== null);
                
                if ($result['json_valid']) {
                    // 尝试提取共振评分
                    if (isset($json['resonance_score'])) {
                        $result['score'] = $json['resonance_score'];
                    } elseif (isset($json['ticker_signals']['518880']['resonance_score'])) {
                        $result['score'] = $json['ticker_signals']['518880']['resonance_score'];
                    }
                }
            }
        }
        
        return $result;
    }
    
    // 检查关键文件
    $files = [
        checkFile(__DIR__ . '/../database/cleaned/resonance_signal_cleaned.json', '清洗后共振信号 (主数据源)'),
        checkFile(__DIR__ . '/../database/resonance_signal.json', '原始共振信号'),
        checkFile(__DIR__ . '/../database/resonance_report_20260330.json', '共振报告'),
        checkFile(__DIR__ . '/index.php', '主页面 index.php'),
        checkFile(__DIR__ . '/get_latest_data.php', 'API端点 get_latest_data.php'),
    ];
    
    // 检查Web服务器信息
    $serverInfo = [
        'PHP Version' => PHP_VERSION,
        'Server Software' => $_SERVER['SERVER_SOFTWARE'] ?? 'Unknown',
        'Document Root' => $_SERVER['DOCUMENT_ROOT'] ?? 'Unknown',
        'Script Filename' => $_SERVER['SCRIPT_FILENAME'] ?? 'Unknown',
        'Request URI' => $_SERVER['REQUEST_URI'] ?? 'Unknown',
        'Query String' => $_SERVER['QUERY_STRING'] ?? 'None',
    ];
    
    // 检查缓存头
    $headers = headers_list();
    ?>
    
    <!-- 服务器信息 -->
    <div class="section">
        <h2>服务器信息</h2>
        <div class="data-box">
            <?php foreach ($serverInfo as $key => $value): ?>
            <strong><?php echo htmlspecialchars($key); ?>:</strong> <?php echo htmlspecialchars($value); ?><br>
            <?php endforeach; ?>
        </div>
    </div>
    
    <!-- 文件状态 -->
    <div class="section">
        <h2>数据文件状态</h2>
        <div class="file-info">
            <?php foreach ($files as $file): ?>
            <div class="file-item">
                <strong><?php echo htmlspecialchars($file['description']); ?></strong><br>
                <span class="status <?php echo $file['exists'] ? 'status-ok' : 'status-error'; ?>">
                    <?php echo $file['exists'] ? '存在' : '缺失'; ?>
                </span>
                
                <?php if ($file['exists']): ?>
                <span class="status <?php echo $file['readable'] ? 'status-ok' : 'status-error'; ?>">
                    <?php echo $file['readable'] ? '可读' : '不可读'; ?>
                </span>
                
                <?php if ($file['json_valid']): ?>
                <span class="status status-ok">JSON有效</span>
                <?php else: ?>
                <span class="status status-warning">JSON无效</span>
                <?php endif; ?>
                
                <br>
                <small>
                    大小: <?php echo number_format($file['size']); ?> bytes<br>
                    修改: <?php echo date('Y-m-d H:i:s', $file['mtime']); ?><br>
                    <?php if ($file['score'] !== null): ?>
                    共振评分: <strong style="color: #58a6ff;"><?php echo $file['score']; ?></strong>
                    <?php endif; ?>
                </small>
                <?php endif; ?>
            </div>
            <?php endforeach; ?>
        </div>
    </div>
    
    <!-- 主数据源内容 -->
    <div class="section">
        <h2>主数据源内容 (cleaned/resonance_signal_cleaned.json)</h2>
        <?php
        $mainFile = $files[0];
        if ($mainFile['exists'] && $mainFile['readable'] && $mainFile['json_valid']) {
            $json = json_decode($mainFile['content'], true);
            echo '<div class="data-box">';
            echo '<strong>共振评分:</strong> <span style="color: #58a6ff; font-weight: bold;">' . $json['resonance_score'] . '</span><br>';
            echo '<strong>信号状态:</strong> ' . $json['signal_status'] . '<br>';
            echo '<strong>操作建议:</strong> ' . $json['action'] . '<br>';
            echo '<strong>命中算法:</strong> ' . $json['hit_count'] . '/10 (' . implode(', ', $json['hits']) . ')<br>';
            echo '<strong>数据时间:</strong> ' . $json['signal_time'] . '<br>';
            echo '<strong>清洗时间:</strong> ' . $json['cleaned_time'] . '<br>';
            echo '</div>';
        } else {
            echo '<div class="data-box" style="color: #f85149;">';
            echo '无法读取主数据源文件';
            echo '</div>';
        }
        ?>
    </div>
    
    <!-- 缓存诊断 -->
    <div class="section">
        <h2>缓存诊断</h2>
        <div class="data-box">
            <strong>当前时间:</strong> <?php echo date('Y-m-d H:i:s'); ?><br>
            <strong>页面版本:</strong> v1.3.0<br>
            <strong>强制刷新:</strong> 
            <button class="action-button" onclick="location.href='index.php?force_refresh=' + Date.now()">
                强制刷新 index.php
            </button>
            <button class="action-button" onclick="location.href='diagnostic.php?force_refresh=' + Date.now()">
                刷新诊断页面
            </button>
            <br><br>
            <strong>缓存清除建议:</strong><br>
            1. 按 Ctrl+F5 (Windows) 或 Cmd+Shift+R (Mac) 强制刷新<br>
            2. 清除浏览器缓存<br>
            3. 使用无痕/隐私模式访问<br>
            4. 添加随机参数: index.php?v=<?php echo time(); ?>
        </div>
    </div>
    
    <!-- 数据真实性验证 -->
    <div class="section">
        <h2>数据真实性验证</h2>
        <div class="data-box">
            <?php
            // 验证数据一致性
            $scores = [];
            foreach ($files as $file) {
                if ($file['score'] !== null) {
                    $scores[$file['description']] = $file['score'];
                }
            }
            
            if (count($scores) > 0) {
                echo '<strong>各数据源共振评分对比:</strong><br>';
                foreach ($scores as $desc => $score) {
                    echo htmlspecialchars($desc) . ': <strong>' . $score . '</strong><br>';
                }
                
                // 检查一致性
                $uniqueScores = array_unique(array_values($scores));
                if (count($uniqueScores) === 1) {
                    echo '<br><span style="color: #238636;">✅ 所有数据源评分一致</span>';
                } else {
                    echo '<br><span style="color: #f85149;">❌ 数据源评分不一致，可能存在缓存问题</span>';
                }
            } else {
                echo '无法获取共振评分数据';
            }
            ?>
        </div>
    </div>
    
    <!-- 操作按钮 -->
    <div class="section">
        <h2>操作</h2>
        <button class="action-button" onclick="location.href='index.php'">访问主页面</button>
        <button class="action-button" onclick="location.href='index.php?v=<?php echo time(); ?>'">带时间戳访问</button>
        <button class="action-button warning" onclick="if(confirm('这将重新加载数据，确定继续？')) location.href='../scripts/orchestrator.py'">执行调度器</button>
        <button class="action-button danger" onclick="if(confirm('这将清除所有缓存，确定继续？')) location.href='clear_cache.php'">清除缓存</button>
    </div>
    
    <script>
        // 自动刷新诊断信息
        setInterval(function() {
            // 每30秒刷新一次诊断信息
            const currentTime = Math.floor(Date.now() / 1000);
            if (currentTime % 30 === 0) {
                console.log('自动刷新诊断信息: ' + new Date().toLocaleString('zh-CN'));
                // 可以在这里添加自动刷新逻辑
            }
        }, 1000);
    </script>
</body>
</html></result>
</function_params>