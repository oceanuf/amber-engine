<?php
/**
 * 缓存测试脚本
 * 用于诊断PHP文件缓存问题
 */
header('Content-Type: text/plain; charset=utf-8');

echo "=== 缓存测试脚本 ===\n";
echo "当前时间: " . date('Y-m-d H:i:s') . "\n";
echo "文件修改时间: " . date('Y-m-d H:i:s', filemtime(__FILE__)) . "\n";
echo "随机数: " . rand(1000, 9999) . "\n";
echo "服务器: " . ($_SERVER['SERVER_SOFTWARE'] ?? 'Unknown') . "\n";
echo "PHP版本: " . PHP_VERSION . "\n";

// 检查opcache状态
if (function_exists('opcache_get_status')) {
    $opcache = opcache_get_status(false);
    echo "OPcache启用: " . ($opcache['opcache_enabled'] ? '是' : '否') . "\n";
    if ($opcache['opcache_enabled']) {
        echo "OPcache缓存文件数: " . $opcache['opcache_statistics']['num_cached_scripts'] . "\n";
        echo "OPcache命中率: " . round($opcache['opcache_statistics']['opcache_hit_rate'], 2) . "%\n";
    }
} else {
    echo "OPcache: 未安装或未启用\n";
}

// 检查文件是否被缓存
echo "\n=== 文件状态 ===\n";
$files = [
    'index.php' => __DIR__ . '/index.php',
    'get_latest_data.php' => __DIR__ . '/get_latest_data.php',
];

foreach ($files as $name => $path) {
    if (file_exists($path)) {
        echo "$name:\n";
        echo "  存在: 是\n";
        echo "  大小: " . filesize($path) . " bytes\n";
        echo "  修改时间: " . date('Y-m-d H:i:s', filemtime($path)) . "\n";
        echo "  内容前100字符: " . substr(file_get_contents($path), 0, 100) . "...\n";
    } else {
        echo "$name: 不存在\n";
    }
}

// 检查index.php是否包含PHP注入代码
echo "\n=== index.php 内容检查 ===\n";
$indexContent = file_get_contents(__DIR__ . '/index.php');
if (strpos($indexContent, 'PHP原生数据注入') !== false) {
    echo "✅ index.php 包含PHP原生注入代码 (v1.3.0)\n";
} else {
    echo "❌ index.php 不包含PHP原生注入代码 (可能是旧版本)\n";
}

if (strpos($indexContent, 'resonance_score: 85.5') !== false) {
    echo "❌ index.php 包含模拟数据 (85.5分)\n";
} else {
    echo "✅ index.php 不包含模拟数据\n";
}

echo "\n=== 建议操作 ===\n";
echo "1. 重启PHP-FPM: sudo systemctl restart php-fpm\n";
echo "2. 清除OPcache: 创建 opcache_reset.php 并访问\n";
echo "3. 检查Web服务器配置\n";
echo "4. 使用诊断页面: diagnostic.php\n";
?>