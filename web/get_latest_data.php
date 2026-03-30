<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// 查找最新的共振报告文件
function findLatestResonanceReport() {
    $databaseDir = __DIR__ . '/../database/';
    $latestFile = null;
    $latestTime = 0;
    
    // 扫描database目录下的共振报告文件
    $files = glob($databaseDir . 'resonance_report_*.json');
    
    foreach ($files as $file) {
        // 从文件名提取日期
        if (preg_match('/resonance_report_(\d{8})\.json$/', $file, $matches)) {
            $fileDate = $matches[1];
            $fileTime = strtotime($fileDate);
            
            if ($fileTime > $latestTime) {
                $latestTime = $fileTime;
                $latestFile = $file;
            }
        }
    }
    
    return $latestFile;
}

// 获取最新的共振信号文件
function findLatestResonanceSignal() {
    // 优先使用cleaned版本（更稳定，经过清洗）
    $cleanedSignalFile = __DIR__ . '/../database/cleaned/resonance_signal_cleaned.json';
    if (file_exists($cleanedSignalFile)) {
        return $cleanedSignalFile;
    }
    
    // 降级使用原始版本
    $signalFile = __DIR__ . '/../database/resonance_signal.json';
    if (file_exists($signalFile)) {
        return $signalFile;
    }
    
    return null;
}

// 主处理逻辑
try {
    // 优先使用共振信号文件（更轻量）
    $signalFile = findLatestResonanceSignal();
    $data = null;
    
    if ($signalFile && file_exists($signalFile)) {
        $jsonContent = file_get_contents($signalFile);
        $signalData = json_decode($jsonContent, true);
        
        if ($signalData && isset($signalData['ticker']) && $signalData['ticker'] === '518880') {
            $data = [
                'ticker' => $signalData['ticker'],
                'name' => $signalData['name'],
                'resonance_score' => $signalData['resonance_score'],
                'signal_status' => $signalData['signal_status'],
                'action' => $signalData['action'],
                'hit_count' => $signalData['hit_count'],
                'hits' => $signalData['hits'],
                'veto_applied' => $signalData['veto_applied'],
                'latest_info' => $signalData['latest_info'],
                'report_time' => $signalData['signal_time']
            ];
            
            // 提取策略得分
            $strategyScores = [];
            foreach ($signalData['strategy_summary'] as $strategyName => $strategyData) {
                $strategyScores[$strategyName] = $strategyData['score'];
            }
            $data['strategy_scores'] = $strategyScores;
        }
    }
    
    // 如果共振信号文件不存在或数据不完整，尝试使用共振报告文件
    if (!$data) {
        $reportFile = findLatestResonanceReport();
        if ($reportFile && file_exists($reportFile)) {
            $jsonContent = file_get_contents($reportFile);
            $reportData = json_decode($jsonContent, true);
            
            if (isset($reportData['ticker_signals']['518880'])) {
                $goldData = $reportData['ticker_signals']['518880'];
                
                $data = [
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
                $data['strategy_scores'] = $strategyScores;
            }
        }
    }
    
    // 如果都没有数据，返回错误
    if (!$data) {
        echo json_encode([
            'success' => false,
            'error' => '未找到共振数据文件',
            'timestamp' => date('Y-m-d H:i:s')
        ]);
        exit;
    }
    
    // 返回成功响应
    $dataSource = 'unknown';
    if ($signalFile) {
        $dataSource = basename($signalFile);
        if (strpos($signalFile, 'cleaned/') !== false) {
            $dataSource = 'cleaned/' . $dataSource;
        }
    } elseif ($reportFile) {
        $dataSource = basename($reportFile);
    }
    
    echo json_encode([
        'success' => true,
        'resonanceData' => $data,
        'timestamp' => date('Y-m-d H:i:s'),
        'data_source' => $dataSource
    ]);
    
} catch (Exception $e) {
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage(),
        'timestamp' => date('Y-m-d H:i:s')
    ]);
}
?>