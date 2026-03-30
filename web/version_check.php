<?php
// 版本检查页面 - 确认服务器上的文件版本
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>琥珀引擎版本检查</title>
    <style>
        body { font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }
        .ok { color: #238636; }
        .error { color: #f85149; }
        .warning { color: #d29922; }
        pre { background: #161b22; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>琥珀引擎版本检查</h1>
    
    <?php
    $indexFile = __DIR__ . '/index.php';
    $apiFile = __DIR__ . '/get_latest_data.php';
    
    echo "<h2>文件状态检查</h2>";
    echo "<ul>";
    echo "<li>index.php: " . (file_exists($indexFile) ? '<span class="ok">存在</span>' : '<span class="error">不存在</span>') . "</li>";
    echo "<li>get_latest_data.php: " . (file_exists($apiFile) ? '<span class="ok">存在</span>' : '<span class="error">不存在</span>') . "</li>";
    echo "</ul>";
    
    echo "<h2>index.php 关键内容检查</h2>";
    if (file_exists($indexFile)) {
        $content = file_get_contents($indexFile);
        
        // 检查是否包含模拟数据
        if (strpos($content, 'resonance_score: 85.5') !== false) {
            echo '<p class="error">❌ 发现模拟数据: resonance_score: 85.5</p>';
        } else {
            echo '<p class="ok">✅ 未发现模拟数据 85.5</p>';
        }
        
        // 检查是否包含PHP代码
        if (strpos($content, '<?php') !== false) {
            echo '<p class="ok">✅ 包含PHP代码</p>';
        } else {
            echo '<p class="error">❌ 不包含PHP代码</p>';
        }
        
        // 检查是否包含cleaned数据引用
        if (strpos($content, 'cleaned/resonance_signal_cleaned.json') !== false) {
            echo '<p class="ok">✅ 引用cleaned数据源</p>';
        } else {
            echo '<p class="warning">⚠️ 未引用cleaned数据源</p>';
        }
        
        // 提取PHP生成的JSON数据
        if (preg_match('/const resonanceData = (\{.*?\});/s', $content, $matches)) {
            echo "<h3>PHP生成的JSON数据:</h3>";
            echo "<pre>" . htmlspecialchars($matches[1]) . "</pre>";
        }
    }
    
    echo "<h2>API测试</h2>";
    if (file_exists($apiFile)) {
        // 模拟API调用
        ob_start();
        include $apiFile;
        $apiResponse = ob_get_clean();
        
        $data = json_decode($apiResponse, true);
        if ($data && isset($data['success']) && $data['success']) {
            echo '<p class="ok">✅ API工作正常</p>';
            echo "<p>共振评分: <strong>" . $data['resonanceData']['resonance_score'] . "</strong></p>";
            echo "<p>信号状态: " . $data['resonanceData']['signal_status'] . "</p>";
            echo "<p>操作建议: " . $data['resonanceData']['action'] . "</p>";
            echo "<p>数据源: " . $data['data_source'] . "</p>";
        } else {
            echo '<p class="error">❌ API返回错误</p>';
            echo "<pre>" . htmlspecialchars($apiResponse) . "</pre>";
        }
    }
    
    echo "<h2>服务器信息</h2>";
    echo "<ul>";
    echo "<li>服务器时间: " . date('Y-m-d H:i:s') . "</li>";
    echo "<li>PHP版本: " . phpversion() . "</li>";
    echo "<li>文件最后修改: " . date('Y-m-d H:i:s', filemtime($indexFile)) . "</li>";
    echo "</ul>";
    
    echo "<h2>建议操作</h2>";
    echo "<ol>";
    echo "<li>请主编强制刷新浏览器 (Ctrl+F5 或 Cmd+Shift+R)</li>";
    echo "<li>清除浏览器缓存</li>";
    echo "<li>确认访问地址: https://gemini.googlemanager.cn:10168/index.php</li>";
    echo "<li>检查此页面: https://gemini.googlemanager.cn:10168/version_check.php</li>";
    echo "</ol>";
    ?>
</body>
</html>