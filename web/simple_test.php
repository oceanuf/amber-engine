<?php
// 简单测试脚本
header('Content-Type: text/plain; charset=utf-8');

echo "=== 简单测试 ===\n";

// 测试1: 检查index.php
$indexPath = __DIR__ . '/index.php';
echo "1. index.php: ";
if (file_exists($indexPath)) {
    $content = file_get_contents($indexPath);
    $hasInjection = (strpos($content, 'PHP原生数据注入') !== false);
    $hasSimulated = (strpos($content, 'resonance_score: 85.5') !== false);
    $hasReal = (strpos($content, '50.84') !== false);
    
    echo "存在 (" . filesize($indexPath) . " bytes)\n";
    echo "  包含注入代码: " . ($hasInjection ? '是' : '否') . "\n";
    echo "  包含模拟数据: " . ($hasSimulated ? '是' : '否') . "\n";
    echo "  包含真实数据: " . ($hasReal ? '是' : '否') . "\n";
} else {
    echo "不存在\n";
}

// 测试2: 检查数据文件
$dataPath = __DIR__ . '/../database/cleaned/resonance_signal_cleaned.json';
echo "\n2. 数据文件: ";
if (file_exists($dataPath)) {
    $content = file_get_contents($dataPath);
    $data = json_decode($content, true);
    
    if ($data) {
        $score = $data['resonance_score'] ?? 'N/A';
        $status = $data['signal_status'] ?? 'N/A';
        echo "存在 (评分: $score, 状态: $status)\n";
    } else {
        echo "存在但JSON无效\n";
    }
} else {
    echo "不存在\n";
}

// 测试3: 检查Web访问
echo "\n3. Web页面内容检查:\n";
$url = 'https://gemini.googlemanager.cn:10168/index.php';
$context = stream_context_create([
    'ssl' => [
        'verify_peer' => false,
        'verify_peer_name' => false,
    ],
    'http' => [
        'timeout' => 5,
    ]
]);

$webContent = @file_get_contents($url, false, $context);
if ($webContent !== false) {
    $hasInjectionWeb = (strpos($webContent, 'PHP原生数据注入') !== false);
    $hasSimulatedWeb = (strpos($webContent, '85.5') !== false && strpos($webContent, 'resonance_score') !== false);
    $hasRealWeb = (strpos($webContent, '50.84') !== false && strpos($webContent, 'resonance_score') !== false);
    
    echo "  可访问\n";
    echo "  包含注入代码: " . ($hasInjectionWeb ? '是' : '否') . "\n";
    echo "  包含模拟数据: " . ($hasSimulatedWeb ? '是' : '否') . "\n";
    echo "  包含真实数据: " . ($hasRealWeb ? '是' : '否') . "\n";
    
    // 提取实际显示的评分
    if (preg_match('/共振评分:\s*<[^>]*>([0-9.]+)/', $webContent, $matches)) {
        echo "  实际显示评分: " . $matches[1] . "\n";
    }
} else {
    echo "  不可访问\n";
}

echo "\n=== 总结 ===\n";
if ($hasRealWeb && !$hasSimulatedWeb) {
    echo "✅ 修复成功: Web页面显示真实数据(50.84分)\n";
} elseif ($hasSimulatedWeb) {
    echo "❌ 修复失败: Web页面仍显示模拟数据(85.5分)\n";
} else {
    echo "⚠️  状态未知\n";
}
?>