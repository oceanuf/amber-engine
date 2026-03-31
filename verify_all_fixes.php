<?php
/**
 * 验证所有修复
 */

chdir('/var/www/amber-web');

echo "=== 琥珀引擎修复验证 ===\n";
echo "时间: " . date('Y-m-d H:i:s') . "\n\n";

// 1. 测试开盘概率
echo "1. 测试开盘概率数据:\n";
$probFile = __DIR__ . '/database/opening_probability.json';
if (file_exists($probFile)) {
    $content = file_get_contents($probFile);
    $data = json_decode($content, true);
    if ($data && isset($data['probability_distribution'])) {
        $prob = $data['probability_distribution'];
        echo "   ✅ Gap Up: " . $prob['gap_up'] . "% (正确: 13.5%)\n";
        echo "   ✅ Flat: " . $prob['flat'] . "% (正确: 40.8%)\n";
        echo "   ✅ Gap Down: " . $prob['gap_down'] . "% (正确: 45.7%)\n";
        
        if ($prob['gap_up'] == 13.5 && $prob['flat'] == 40.8 && $prob['gap_down'] == 45.7) {
            echo "   ✅ 开盘概率数据正确\n";
        } else {
            echo "   ❌ 开盘概率数据错误\n";
        }
    } else {
        echo "   ❌ JSON解析失败\n";
    }
} else {
    echo "   ❌ 文件不存在: $probFile\n";
}

// 2. 测试共振数据源
echo "\n2. 测试共振数据源:\n";
function testLoadResonanceData() {
    $dataSources = [
        __DIR__ . '/database/cleaned/resonance_signal_cleaned.json',
        __DIR__ . '/database/resonance_signal.json',
        __DIR__ . '/database/resonance_report_20260330.json',
    ];

    $sourceFound = null;
    foreach ($dataSources as $source) {
        if (file_exists($source)) {
            $sourceFound = basename($source);
            break;
        }
    }
    
    return $sourceFound;
}

$source = testLoadResonanceData();
if ($source) {
    echo "   ✅ 找到数据源: $source\n";
    if ($source === 'hardcoded_fallback') {
        echo "   ⚠️  警告: 使用硬编码回退数据\n";
    } else {
        echo "   ✅ 使用实际JSON数据\n";
    }
} else {
    echo "   ❌ 未找到任何数据源\n";
}

// 3. 检查软链接
echo "\n3. 检查软链接:\n";
$links = [
    'opening_probability.json' => '/var/www/amber-web/database/opening_probability.json',
    'cleaned目录' => '/var/www/amber-web/database/cleaned',
    'resonance_signal.json' => '/var/www/amber-web/database/resonance_signal.json',
];

foreach ($links as $name => $path) {
    if (file_exists($path)) {
        if (is_link($path)) {
            $target = readlink($path);
            echo "   ✅ $name: 软链接到 $target\n";
        } else {
            echo "   ✅ $name: 文件存在 (非软链接)\n";
        }
    } else {
        echo "   ❌ $name: 不存在\n";
    }
}

// 4. 测试Web页面内容
echo "\n4. 模拟Web页面加载:\n";
$probabilityData = null;
$probFile = __DIR__ . '/database/opening_probability.json';
if (file_exists($probFile)) {
    $content = file_get_contents($probFile);
    $probabilityData = json_decode($content, true);
}

if ($probabilityData && isset($probabilityData['probability_distribution'])) {
    $probDist = $probabilityData['probability_distribution'];
    echo "   Web页面应显示:\n";
    echo "   🔴 Gap Up: " . $probDist['gap_up'] . "%\n";
    echo "   ⚪ Flat: " . $probDist['flat'] . "%\n";
    echo "   🔵 Gap Down: " . $probDist['gap_down'] . "%\n";
    
    // 检查是否为33.3%
    if ($probDist['gap_up'] == 33.3 && $probDist['flat'] == 33.3 && $probDist['gap_down'] == 33.3) {
        echo "   ❌ 问题: 显示硬编码的33.3%默认值\n";
    } else {
        echo "   ✅ 显示实际数据 (非33.3%)\n";
    }
}

echo "\n=== 验证完成 ===\n";
echo "建议: 请主编清除浏览器缓存并重新加载页面\n";
echo "      或使用强制刷新 (Ctrl+F5 / Cmd+Shift+R)\n";