# ⚙️ OPERATIONS.md - 琥珀引擎运维契约 (V1.0)

**文档编号**: `AE-CODEX-OPS-001`
**核心目标**: 确保演武场 24/7 自动驾驶的稳定性与自愈力。

---

## 🕒 自动化调度时间表 (The Cron Protocol)

| 时间 (GMT+8) | 任务项 | 核心动作 | 负责人 |
| :--- | :--- | :--- | :--- |
| **Daily 08:30** | **实战报告发布** | 生成 `reports/arena/` 损益报告并执行 GitHub 同步。 | Cheese |
| **Daily 18:00** | **演武场数据增量** | 抓取收盘价,触发评委中控二次打分与权重修订。 | Cheese |
| **Sun 18:30** | **系统全量补全** | 深度清洗 `database/`,修复本周缺失数据。 | Cheese |
| **Heartbeat** | **死锁自检** | 检查当前 Grain 进度,若滞后则重启逻辑。 | Cheese |

---

## 🩺 自愈与异常处理 (Self-Healing)

### 1. 端口与服务监控
- **监控对象**: 10168 端口 (Web 服务)。
- **动作**: 若响应超时,尝试 `systemctl restart amber-web`。
- **记录**: 将事故记录至 `LESSONS.md` 归档。

### 2. 数据断流应急
- **场景**: Tushare API 积分耗尽或响应失败。
- **策略**: 立即切换至备份数据源(如现有的历史 CSV),并在 `reports/` 中标注"带伤实战"。

### 3. 磁盘与日志清理
- **策略**: 保持 `memory/` 目录整洁。超过 30 天的日志自动归档至 `archives/`。

---

## 🔄 状态对撞机制 (Consistency Check)

在任何运维操作后,必须执行以下校验:
1. **源码同步**: 执行 `verify_readiness.sh`。
2. **指纹验证**: 确认生产环境 Build ID 与本地 Commit ID 一致。
3. **数据镜像**: 确认 `virtual_fund.json` 与实战报告数据对等。

---

## 🔧 实施状态 (Implementation Status)

### ✅ 已实现自动化 (Implemented)
- **Cron调度管理器**: `scripts/ops/cron_manager.sh` V1.0.0
- **实战报告生成器**: `scripts/reporting/arena_report_generator.py` V1.0.0
- **监控列表同步钩子**: `scripts/arena/sync_watch_list.py` V1.0.0
- **日志系统**: `logs/cron/` 目录与时间戳日志文件

### 🕒 调度时间表实施状态
| 时间 (GMT+8) | 状态 | 实施详情 |
| :--- | :--- | :--- |
| **Daily 08:30** | ✅ 就绪 | 执行 `./cron_manager.sh` 生成报告并同步 |
| **Daily 18:00** | ✅ 就绪 | 同08:30流程，额外触发评委权重修订 |
| **Sun 18:30** | 🔄 待测试 | 全量数据清洗功能待集成 |
| **Heartbeat** | ✅ 就绪 | GRAIN.md 颗粒化追踪 + HEARTBEAT.md 检查 |

### 📋 后续优化项
1. **全量补全脚本**: 实现周日18:30的深度清洗功能
2. **端口监控**: 集成10168端口健康检查
3. **数据断流应急**: 完善Tushare API失败时的备份数据源切换
4. **Cron作业部署**: 将调度脚本部署到系统Cron服务

---
**"运维的最高境界是无感，自愈的本质是逻辑的预判。"**