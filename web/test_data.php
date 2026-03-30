<?php
// 测试数据集成
$reportFile = __DIR__ . '/../database/resonance_report_20260330.json';
echo "测试文件: " . $reportFile . "\n";
echo "文件存在: " . (file_exists($reportFile) ? '是' : '否') . "\n\n";

if (file_exists($reportFile)) {
    $jsonContent = file_get_contents($reportFile);
    $reportData = json_decode($jsonContent, true);
    
    echo "JSON解析成功: " . (json_last_error() === JSON_ERROR_NONE ? '是' : '否') . "\n";
    echo "数据版本: " . ($reportData['metadata']['report_id'] ?? '未知') . "\n";
    echo "生成时间: " . ($reportData['metadata']['generated_at'] ?? '未知') . "\n\n";
    
    if (isset($reportData['ticker_signals']['518880'])) {
        $goldData = $reportData['ticker_signals']['518880'];
        echo "=== 黄金ETF数据 ===\n";
        echo "代码: " . $goldData['ticker'] . "\n";
        echo "名称: " . $goldData['name'] . "\n";
        echo "共振评分: " . $goldData['resonance_score'] . "\n";
        echo "信号状态: " . $goldData['signal_status'] . "\n";
        echo "操作建议: " . $goldData['action'] . "\n";
        echo "命中算法: " . $goldData['hit_count'] . "/10\n";
        echo "命中列表: " . implode(', ', $goldData['hits']) . "\n";
        echo "最新价格: " . ($goldData['latest_info']['price'] ?? '未知') . "\n";
        echo "价格变化: " . ($goldData['latest_info']['change'] ?? '未知') . "\n";
        echo "报告时间: " . $goldData['signal_time'] . "\n\n";
        
        echo "=== 策略得分 ===\n";
        foreach ($goldData['strategy_summary'] as $strategyName => $strategyData) {
            echo sprintf("%-20s: %6.2f (命中: %s)\n", 
                $strategyName, 
                $strategyData['score'],
                $strategyData['hit'] ? '是' : '否'
            );
        }
    } else {
        echo "错误: 未找到黄金ETF数据\n";
    }
} else {
    echo "错误: 报告文件不存在\n";
    
    // 尝试查找其他文件
    $databaseDir = __DIR__ . '/../database/';
    $files = glob($databaseDir . 'resonance_*.json');
    echo "\n可用的共振文件:\n";
    foreach ($files as $file) {
        echo "  - " . basename($file) . "\n";
    }
}
?>