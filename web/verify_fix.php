<?php
/**
 * 修复验证脚本
 * 确认Web数据显示问题已修复
 */
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>琥珀引擎 · 修复验证</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        h1, h2 {
            color: #58a6ff;
        }
        
        .status {
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border: 2px solid;
        }
        
        .status-success {
            background-color: rgba(35, 134, 54, 0.2);
            border-color: #238636;
            color: #58ff6b;
        }
        
        .status-warning {
            background-color: rgba(210, 153, 34, 0.2);
            border-color: #d29922;
            color: #ffd166;
        }
        
        .status-error {
            background-color: rgba(248, 81, 73, 0.2);
            border-color: #f85149;
            color: #ff6b6b;
        }
        
        .check-item {
            margin: 10px 0;
            padding: 10px;
            background-color: #161b22;
            border-radius: 6px;
            border: 1px solid #30363d;
        }
        
        .check-item.success:before {
            content: "✅ ";
            color: #238636;
        }
        
        .check-item.error:before {
            content: "❌ ";
            color: #f85149;
        }
        
        .check-item.warning:before {
            content: "⚠️ ";
            color: #d29922;
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
            text-decoration: none;
            display: inline-block;
        }
        
        .action-button:hover {
            background-color: #2ea043;
        }
        
        .data-box {
            background-color: #0d1117;
            border-radius: 8px;
            padding: 15px;
            margin-top: 10px;
            border: 1px solid #30363d;
            font-family: monospace;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <h1>琥珀引擎 · 修复验证</h1>
    <p>验证时间: <?php echo date('Y-m-d H:i:s'); ?></p>
    
    <?php
    // 检查关键文件
    $checks = [];
    
    // 1. 检查index.php文件
    $indexPath = __DIR__ . '/index.php';
    if (file_exists($indexPath)) {
        $content = file_get_contents($indexPath);
        $checks['index_exists'] = true;
        $checks['index_size'] = filesize($indexPath);
        $checks['index_contains_injection'] = (strpos($content, 'PHP原生数据注入') !== false);
        $checks['index_contains_simulated'] = (strpos($content, 'resonance_score: 85.5') !== false);
        $checks['index_contains_real'] = (strpos($content, 'resonance_score: 50.84') !== false);
    } else {
        $checks['index_exists'] = false;
    }
    
    // 2. 检查数据文件
    $dataPath = __DIR__ . '/../database/cleaned/resonance_signal_cleaned.json';
    if (file_exists($dataPath)) {
        $content = file_get_contents($dataPath);
        $data = json_decode($content, true);
        $checks['data_exists'] = true;
        $checks['data_valid'] = ($data !== null);
        if ($checks['data_valid']) {
            $checks['data_score'] = $data['resonance_score'] ?? null;
            $checks['data_status'] = $data['signal_status'] ?? null;
        }
    } else {
        $checks['data_exists'] = false;
    }
    
    // 3. 检查Web访问
    $webUrl = 'https://gemini.googlemanager.cn:10168/index.php';
    $webContent = @file_get_contents($webUrl);
    if ($webContent !== false) {
        $checks['web_accessible'] = true;
        $checks['web_contains_injection'] = (strpos($webContent, 'PHP原生数据注入') !== false);
        $checks['web_contains_real'] = (strpos($webContent, '50.84') !== false);
        $checks['web_contains_simulated'] = (strpos($webContent, '85.5') !== false);
    } else {
        $checks['web_accessible'] = false;
    }
    
    // 评估修复状态
    $allGood = true;
    $issues = [];
    
    if (!$checks['index_exists']) {
        $allGood = false;
        $issues[] = 'index.php文件不存在';
    } elseif ($checks['index_contains_simulated']) {
        $allGood = false;
        $issues[] = 'index.php包含模拟数据(85.5分)';
    } elseif (!$checks['index_contains_real']) {
        $allGood = false;
        $issues[] = 'index.php不包含真实数据(50.84分)';
    }
    
    if (!$checks['data_exists']) {
        $allGood = false;
        $issues[] = '数据文件不存在';
    } elseif (!$checks['data_valid']) {
        $allGood = false;
        $issues[] = '数据文件无效';
    } elseif ($checks['data_score'] != 50.84) {
        $allGood = false;
        $issues[] = '数据文件评分不是50.84分';
    }
    
    if (!$checks['web_accessible']) {
        $allGood = false;
        $issues[] = 'Web页面无法访问';
    } elseif ($checks['web_contains_simulated']) {
        $allGood = false;
        $issues[] = 'Web页面包含模拟数据';
    }
    ?>
    
    <div class="status <?php echo $allGood ? 'status-success' : 'status-error'; ?>">
        <h2><?php echo $allGood ? '✅ 修复成功' : '❌ 修复未完成'; ?></h2>
        <?php if ($allGood): ?>
        <p>Web数据显示问题已修复。现在显示真实数据(50.84分)。</p>
        <?php else: ?>
        <p>仍有问题需要解决:</p>
        <ul>
            <?php foreach ($issues as $issue): ?>
            <li><?php echo htmlspecialchars($issue); ?></li>
            <?php endforeach; ?>
        </ul>
        <?php endif; ?>
    </div>
    
    <h2>详细检查结果</h2>
    
    <div class="check-item <?php echo $checks['index_exists'] ? 'success' : 'error'; ?>">
        index.php文件: <?php echo $checks['index_exists'] ? '存在 (' . $checks['index_size'] . ' bytes)' : '不存在'; ?>
    </div>
    
    <div class="check-item <?php echo $checks['index_contains_injection'] ? 'success' : 'error'; ?>">
        PHP原生注入: <?php echo $checks['index_contains_injection'] ? '已实现' : '未实现'; ?>
    </div>
    
    <div class="check-item <?php echo !$checks['index_contains_simulated'] ? 'success' : 'error'; ?>">
        模拟数据清理: <?php echo !$checks['index_contains_simulated'] ? '已清理' : '未清理'; ?>
    </div>
    
    <div class="check-item <?php echo $checks['index_contains_real'] ? 'success' : 'error'; ?>">
        真实数据注入: <?php echo $checks['index_contains_real'] ? '已注入' : '未注入'; ?>
    </div>
    
    <div class="check-item <?php echo $checks['data_exists'] ? 'success' : 'error'; ?>">
        数据文件: <?php echo $checks['data_exists'] ? '存在' : '不存在'; ?>
    </div>
    
    <div class="check-item <?php echo $checks['data_valid'] ? 'success' : 'error'; ?>">
        数据有效性: <?php echo $checks['data_valid'] ? '有效' : '无效'; ?>
    </div>
    
    <div class="check-item <?php echo ($checks['data_score'] == 50.84) ? 'success' : 'error'; ?>">
        共振评分: <?php echo $checks['data_score'] ?? 'N/A'; ?> (期望: 50.84)
    </div>
    
    <div class="check-item <?php echo $checks['web_accessible'] ? 'success' : 'error'; ?>">
        Web访问: <?php echo $checks['web_accessible'] ? '可访问' : '不可访问'; ?>
    </div>
    
    <div class="check-item <?php echo $checks['web_contains_injection'] ? 'success' : 'error'; ?>">
        Web注入代码: <?php echo $checks['web_contains_injection'] ? '已加载' : '未加载'; ?>
    </div>
    
    <div class="check-item <?php echo !$checks['web_contains_simulated'] ? 'success' : 'error'; ?>">
        Web模拟数据: <?php echo !$checks['web_contains_simulated'] ? '已清除' : '存在'; ?>
    </div>
    
    <div class="check-item <?php echo $checks['web_contains_real'] ? 'success' : 'error'; ?>">
        Web真实数据: <?php echo $checks['web_contains_real'] ? '已显示' : '未显示'; ?>
    </div>
    
    <?php if ($checks['data_valid']): ?>
    <div class="data-box">
        <strong>当前数据状态:</strong><br>
        共振评分: <?php echo $checks['data_score']; ?><br>
        信号状态: <?php echo $checks['data_status']; ?><br>
        数据时间: <?php echo date('Y-m-d H:i:s'); ?><br>
        文件位置: <?php echo htmlspecialchars($dataPath); ?>
    </div>
    <?php endif; ?>
    
    <h2>操作</h2>
    <a href="index.php" class="action-button">访问主页面</a>
    <a href="diagnostic.php" class="action-button">诊断工具</a>
    <a href="index.php?force=<?php echo time(); ?>" class="action-button">强制刷新</a>
    
    <script>
        // 自动刷新验证
        setTimeout(function() {
            if (confirm('验证完成。是否刷新页面查看最新状态？')) {
                location.reload();
            }
        }, 5000);
    </script>
</body>
</html>