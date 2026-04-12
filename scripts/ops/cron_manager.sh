#!/bin/bash
# 🛰️ Amber Engine - Event-Driven Dispatcher

STAGE=$2 # 获取参数 --stage MACRO/INGEST/SIMULATE/REPORT

log_action() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2"
}

case $STAGE in
    "MACRO")
        log_action "INFO" "Starting Stage: MACRO_PULSE (09:10)"
        python3 scripts/pipeline/news_sentinel.py
        python3 scripts/pipeline/macro_pulse_dispatcher.py
        ;;
    "INGEST")
        log_action "INFO" "Starting Stage: DATA_INGEST (15:30)"
        python3 scripts/orchestrator.py # 执行全量同步
        ;;
    "SIMULATE")
        log_action "INFO" "Starting Stage: ARENA_SIM (20:30)"
        ./scripts/arena_rebuild_auto.sh
        ;;
    "REPORT")
        log_action "INFO" "Starting Stage: HINDSIGHT_AUDIT (08:30)"
        # 核心审计节点
        python3 scripts/finance/nav_recorder.py
        # 执行自动归档清理
        python3 scripts/ops/grain_vacuum.py
        log_action "SUCCESS" "Daily audit and vacuum completed."
        ;;
    *)
        echo "Usage: ./cron_manager.sh --stage [MACRO|INGEST|SIMULATE|REPORT]"
        ;;
esac
