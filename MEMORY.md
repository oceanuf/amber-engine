# 🏛️ MEMORY.md - 长久记忆存档

*这是档案馆项目的关键记忆，包含技术标准、架构决策、重要事件和协作模式。*

## 📅 创建信息
**创建时间**: 2026-03-29  
**创建者**: Cheese 🧀 (工程师)  
**依据**: 档案馆开发技术标准 V1.2.1

## 🎯 核心身份与协作模式

### 项目参与者
- **首席架构师**: Gemini ⚖️ - 负责技术标准和架构设计
- **工程师**: Cheese 🧀 - 负责代码实现和模块开发  
- **批准人**: 主编 Haiyang ⚓ - 负责项目决策和批准

### 协作原则
1. **认知对齐**: 通过共同记忆文件和GitHub同步保持信息一致
2. **明确分工**: 架构师制定标准，工程师实现，主编批准
3. **工业级质量**: 代码需符合原子性、容错、监控、安全要求

## 🏗️ 档案馆开发技术标准 V1.2.1

### 文档元数据
**文档编号**: `AE-Web-STD-001-V1.2.1`  
**版本状态**: 🟢 正式发行 (Week 14 准备就绪)  
**制定日期**: 2026-03-29  
**核心宗旨**: 模组化设计、各自独立、相互协同、统一调度

### 设计准则 (The Core Principles)
1. **积木式模组化 (Lego-style)**
   - 网站由彼此独立的模组构成
   - 共享底层单体仓库(Monorepo)框架
   - 执行逻辑上互不干扰

2. **下层不依赖上层 (Bottom-up Hierarchy)**
   - 下层模块不感知上层模块的存在
   - 下层只产生标准化的 JSON 接口
   - 上层可订阅下层接口，但必须具备"数据失效降级"能力

3. **故障隔离 (Resilience)**
   - 单一模组故障仅导致局部功能不可用
   - 严禁引发系统级崩溃

### 业务链条 (8个标准化节点)
| 节点 | 模块名称 | 职能定义 | 输出物 |
|------|----------|----------|--------|
| 1 | **Ingest** | 数据提取 | `raw_data.json` |
| 2 | **Cleaner** | 数据验伪 | 抽检逻辑，失败熔断 |
| 3 | **Storer** | 数据入库 | 存入 `database/` |
| 4 | **Analyzer** | 数据分析 | 基础运算结果 |
| 5 | **Synthesizer** | 算法合成 | **核心算法层**，`result.json` |
| 6 | **Targeter** | 标的命中 | 筛选匹配标的 |
| 7 | **Advisor** | 投资建议 | 深度研报逻辑 |
| 8 | **Notary** | 报告管理 | 转化为 `vaults/` MD档案 |

**调度器**: `scripts/orchestrator.py` 统一调度

### 网站三层架构规范
1. **逻辑层 (Logic - PHP)**
   - 职责: URL路由、模版填充、安全审计
   - 准则: 非必要不在浏览器端计算，SSR服务端渲染

2. **表现层 (Presentation - CSS/HTML)**
   - 职责: 视觉对齐、Obsidian深色主题适配
   - 准则: 与逻辑层解耦，CSS丢失时HTML仍可读

3. **数据层 (Data - Multi-tier)**
   - **静态数据**: `/vaults/` MD文档，应用层缓存
   - **中间态数据**: `/database/` JSON，逻辑层唯一数据源
   - **动态更新**: Cron每24小时更新
   - **降级逻辑**: JSON超24小时未更新显示 `[Data Stale]` 警告

### 技术接口与运维规范
1. **数据交换格式**: JSON
2. **通信协议**: File-Base API (上游写文件，下游读文件)
3. **日志规范**: `/logs/` 目录，关键错误生成审计报告 (`docs/reports/`)
4. **运行环境**: Monorepo独立进程，通过 `scripts/github/sync_clean.sh` 确保纯净

### 物理拓扑准则
| 路径 | 映射模块 | 同步约束 |
|------|----------|----------|
| `/web/` | 逻辑层+表现层 | 包含 `index.php`，绝对路径禁令 |
| `/vaults/` | 数据层(静态) | 仅限 `.md`，内容与逻辑分离 |
| `/database/` | 数据层(中间态) | 仅限 `.json` 模板与脱敏数据 |
| `/scripts/` | 中央调度+模组 | 分子目录存放 Ingest/Algo 等 |
| `/docs/reports/` | 审计中心 | 任务执行报告与法典归档 |

### 工业加固补丁 (V1.2.1)
1. **原子性写入协议**
   - `Write(.tmp) -> Validate -> Rename(.json)`
   - PHP逻辑层对 `database/` 仅限只读权限

2. **日志分级与轮转**
   - `INFO`: 常规执行记录
   - `WARN`: 数据过期 (Stale Data)
   - `ERROR`: 脚本崩溃或校验失败
   - 策略: 单文件上限10MB，保留7天，`logrotate`管理

3. **双语调用契约**
   - 调度器(`Python`) ➡️ 执行器(`Python/PHP/Shell`)
   - 统一通过**退出码**通信: `0`=成功，非`0`=重试/熔断

4. **预留高速通道**
   - 允许高性能模组使用 `SQLite` 代替 JSON
   - 路径限制: `database/sqlite/`

5. **安全加固**
   - 关键敏感文件权限强制为 `600`
   - `.gitignore` 必须覆盖 `.tmp` 和 `.bak` 文件

## 🔧 已实现的核心组件

### Task-20260330-A 成果 (2026-03-29)
**任务**: 将518880(黄金)数据提取逻辑重构为第一个"标准积木模组"

**交付组件**:
1. `scripts/ingest/etf_gold.py`
   - 原子写入协议实现
   - 结构化错误传递 (`[ERR_CODE]: Reason`)
   - 密钥感知 (环境变量 `GOLD_API_KEY`)
   - 重试逻辑 (最大3次，网络超时可重试)

2. `scripts/validate.py`
   - JSON语法检查
   - Schema校验 (支持 `jsonschema` 库)
   - 文件完整性验证

3. `scripts/orchestrator.py`
   - 模块调度
   - 熔断器 (错误码 `SCHEMA_MISMATCH`, `AUTH_FAIL` 触发熔断)
   - 密钥加载 (`_PRIVATE_DATA/secrets.json`)
   - 执行报告生成 (`docs/reports/`)

4. `config/schema_ingest.json`
   - JSON Schema验证模板
   - 严格字段类型和格式约束

5. `_PRIVATE_DATA/secrets.json`
   - 密钥管理模板
   - 环境变量注入机制

### Task-20260330-B 成果 (2026-03-29)
**任务**: Ingest 矩阵构建 - 数据提取全量标准化

**交付组件**:
1. `scripts/ingest/etf_index.py`
   - 宽基ETF数据提取 (沪深300、中证500等)
   - 多ETF统一输出格式
   - 频率标签: Daily

2. `scripts/ingest/macro_logic.py`
   - 宏观经济指标提取 (M2、CPI、PMI等)
   - 月度/季度数据分层
   - 频率标签: Weekly

3. `scripts/ingest/sentiment_monitor.py`
   - 市场情绪指标提取 (恐慌指数、资金流向、波动率)
   - 综合情绪评分系统
   - 频率标签: Daily

4. `config/schema_etf_index.json`
   - 宽基ETF数据Schema
   - 支持多ETF数组验证

5. `config/schema_macro.json`
   - 宏观经济指标Schema
   - 月度/季度数据结构验证

6. `config/schema_sentiment.json`
   - 市场情绪指标Schema
   - 复杂嵌套对象验证

7. `scripts/orchestrator.py` 更新
   - 新增三个Ingest模组调度
   - 频率标签配置 (Daily/Weekly)
   - 统一错误处理与熔断

**架构师深蓝视阈实现**:
- 所有数据输出包含 `fetch_time` 字段
- 支持Web逻辑层数据新鲜度检测 (`[Data Stale]` 警告)
- 为8节点流水线奠定标准化数据提取基础

**工业规范遵循**:
- ✅ 原子性写入协议 (Write.tmp → Validate → Rename)
- ✅ 退出码契约 (0=成功, 101=网络超时, 102=Schema校验失败)
- ✅ 结构化错误传递 (`[ERR_CODE]: Reason`)
- ✅ 密钥安全隔离 (环境变量注入)
- ✅ 调度器容错 (重试、熔断、持久化)

### Task-20260330-C 成果 (2026-03-29)
**任务**: 数据验伪与降噪 (Cleaner) - 标准链条第2节点

**交付组件**:
1. `scripts/cleaner/etf_purify.py`
   - ETF数据净化与验伪模组
   - 空值处理 (Forward Fill 前一日数据)
   - 异常值拦截 (单日波动超过±10%触发警告)
   - 格式对齐 (日期YYYY-MM-DD，价格小数点后四位)
   - 原子写入协议遵循

2. `config/schema_cleaned.json`
   - 清洗后数据Schema验证模板
   - 支持ETF指数数据与单个ETF数据
   - 包含清洗元数据 (`cleaned_time`, `cleaned_by`)

3. `scripts/validate.py` 增强
   - 已支持清洗后数据Schema校验
   - 数值边界检查集成 (单日波动±15%，年化回报±100%)

4. `scripts/orchestrator.py` 升级
   - 依赖关系支持 (`dependencies`字段)
   - Cleaner模组调度 (依赖Ingest成功)
   - 模块执行状态跟踪

**核心清洗逻辑**:
- **数据读取**: 自动扫描 `database/` 目录下的原始JSON文件
- **降噪算法**: 
  - 空值处理: 净值为0或null时，自动向前填充
  - 异常值拦截: 单日波动率超过±10%标记为异常 (涨跌停情况特殊处理)
  - 格式对齐: 统一日期格式为YYYY-MM-DD，统一数值精度至小数点后四位
- **数据输出**: 清洗后文件保存至 `database/cleaned/` 目录，添加 `_cleaned` 后缀

**工业规范遵循**:
- ✅ 原子性写入协议: Temp-Write → Validate → Rename 闭环实现
- ✅ 错误契约: 结构化错误码 (`[MISSING_DATA]`, `[INVALID_DATE_FORMAT]`等)
- ✅ 调度器集成: 依赖Ingest模块，成功后才执行Cleaner
- ✅ 验证中枢: 使用 `schema_cleaned.json` 进行严格校验
- ✅ 日志分级: INFO/WARN/ERROR 三级日志，结构化stderr输出

**架构师智慧锚点实现**:
- "质量即生命线": Cleaner作为最"毒舌"的关卡，对数据烂得太厉害的情况直接报错拒绝输出
- "宁愿模块因校验失败而熔断，也绝不允许任何一条格式错误的数据进入系统"
- 为后续 Storer, Analyzer, Synthesizer 等节点提供净化后的高质量数据

### Task-20260330-D 成果 (2026-03-29)
**任务**: 数据入库与标准化存储 (Storer) - 标准链条第3节点

**交付组件**:
1. `scripts/storer/vault_storer.py`
   - 数据入库与标准化存储模组
   - 增量逻辑: 检查 `fetch_time`，避免重复入库
   - 合并算法: 日期已存在则跳过，不存在则追加至长期历史文件
   - 写前备份策略: 修改前在 `_PRIVATE_DATA/backups/` 下生成 `.bak` 备份
   - 安全性加固: 长期历史文件权限强制为 `600` (仅所有者可读写)
   - 原子写入协议遵循

2. `scripts/orchestrator.py` 升级
   - 新增 Storer 模块配置 (`storer_vault_storer`)
   - 依赖链配置: Ingest → Cleaner → Storer 三级跳逻辑
   - 错误码扩展: `BACKUP_FAIL`, `PERMISSION_FAIL`, `MERGE_FAIL` 等

**核心存储逻辑**:
- **增量检查**: 基于 `fetch_time` 与现有历史记录对比，避免数据重复
- **合并策略**: 
  - 日期存在: 跳过（保持数据唯一性）
  - 日期不存在: 追加到历史记录数组
  - 排序优化: 长期历史记录按日期降序排列（最新的在前）
- **备份机制**: 修改长期库前自动创建时间戳备份，防止数据损坏
- **权限控制**: 所有长期历史文件权限设置为 `600`，防止 Web 进程意外修改

**工业规范遵循**:
- ✅ 原子性写入协议: Temp-Write → Validate → Rename 闭环实现
- ✅ 错误契约: 结构化错误码 (`[BACKUP_FAIL]`, `[PERMISSION_FAIL]`, `[MERGE_FAIL]`等)
- ✅ 调度器集成: 依赖 Cleaner 模块，建立完整三级依赖链
- ✅ 安全加固: 文件权限控制、写前备份、敏感目录隔离
- ✅ 日志分级: INFO/WARN/ERROR 三级日志，结构化stderr输出

**架构师智慧锚点实现**:
- "存储即记忆": Storer 作为档案馆的"外存"核心，采用写前备份策略
- "一旦长期历史文件损坏，回测基准就会消失。V1.2.1 框架下，Storer 在修改长期库前，必须先在 _PRIVATE_DATA/backups/ 下生成一个 .bak。"
- 为后续 Analyzer（分析层）提供标准化的长期历史数据，支持矩阵运算

### Task-20260330-E 成果 (2026-03-29)
**任务**: 数据分析与量化建模 (Analyzer) - 标准链条第4节点

**交付组件**:
1. `scripts/analyzer/indicator_engine.py`
   - ETF技术指标分析模组
   - 移动平均线系统 (MA5, MA20, MA60)
   - 乖离率 (Bias) 计算，评估"生存线"核心指标
   - 动能指标 (ROC5) 计算，衡量短期价格动能
   - 多标度对比架构，支持一键扩展到其他ETF

2. `config/schema_analysis.json`
   - 技术分析指标Schema验证模板
   - 支持null值处理 (数据不足时的智能降级)
   - 严格类型检查确保数值计算安全

3. `scripts/orchestrator.py` 升级
   - 新增Analyzer模块配置 (`analyzer_indicator_engine`)
   - 依赖链配置: Ingest → Cleaner → Storer → Analyzer 四级联动
   - 错误码扩展: `HISTORY_NOT_FOUND`, `ANALYSIS_FAIL`, `SCHEMA_VALIDATE_FAIL` 等

**核心分析逻辑**:
- **移动平均线**: 计算5日、20日、60日移动平均线，数据不足时返回null
- **乖离率**: (现价 - 20日均线) / 20日均线 × 100%，评估价格偏离程度
- **变化率**: (现价 - 5日前价格) / 5日前价格 × 100%，衡量短期动能
- **多标度对比**: 模块化设计支持后续扩展到沪深300、货币基金等资产矩阵

**工业规范遵循**:
- ✅ 原子性写入协议: Temp-Write → Validate → Rename 闭环实现
- ✅ 错误契约: 结构化错误码 (`[HISTORY_NOT_FOUND]`, `[ANALYSIS_FAIL]`, `[SCHEMA_VALIDATE_FAIL]`等)
- ✅ 调度器集成: 依赖Storer模块，建立完整四级依赖链
- ✅ 验证中枢: 使用 `schema_analysis.json` 进行严格校验 (支持null值)
- ✅ 日志分级: INFO/WARN/ERROR 三级日志，结构化stderr输出

**架构师智慧锚点实现**:
- "从数据到智慧": Analyzer作为档案馆的"大脑"，将原始价格序列转化为投资指导意义的技术指标
- "多标度对比潜力": 代码结构支持一键扩展到其他资产，为资产矩阵动态分析奠定基础
- "宁愿返回null也不计算错误指标": 数据不足时智能降级，避免生成误导性信号
- 为后续 Synthesizer（算法合成）提供标准化技术指标输入

### Task-20260330-F 成果 (2026-03-29)
**任务**: 算法合成与信号生成 (Synthesizer) - 标准链条第5节点

**交付组件**:
1. `scripts/synthesizer/score_engine.py`
   - 策略信号合成模组
   - 多维度加权评分系统 (安全、趋势、动能)
   - 参数外部化架构，支持逻辑透明
   - 状态映射引擎 (极度舒适、舒适、中性、谨慎、生存预警)

2. `config/strategy_params.json`
   - 策略参数外部化配置文件
   - 支持阈值、权重、评分规则动态配置
   - 实现"逻辑透明"最高境界 (主编调整策略只需修改JSON)

3. `config/schema_strategy_params.json`
   - 策略参数Schema验证模板
   - 确保参数配置符合规范

4. `config/schema_signal.json`
   - 策略信号输出Schema验证模板
   - 严格验证信号数据结构完整性

5. `scripts/orchestrator.py` 升级
   - 新增Synthesizer模块配置 (`synthesizer_score_engine`)
   - 依赖链配置: Ingest → Cleaner → Storer → Analyzer → Synthesizer 五级联动
   - 错误码扩展: `ANALYSIS_NOT_FOUND`, `PARAMS_NOT_FOUND`, `SYNTHESIS_FAIL` 等

**核心合成逻辑**:
- **安全维度**: Bias20 < -2% (超卖安全区) 得30分
- **趋势维度**: Price > MA20 得40分 (趋势确立)
- **动能维度**: ROC5 > 0 得30分 (正向动能)
- **加权总分**: 根据维度权重计算加权总分 (0-100分)
- **状态映射**: 80分以上"极度舒适"，30分以下"生存预警"

**工业规范遵循**:
- ✅ 原子性写入协议: Temp-Write → Validate → Rename 闭环实现
- ✅ 错误契约: 结构化错误码 (`[ANALYSIS_NOT_FOUND]`, `[PARAMS_NOT_FOUND]`, `[SYNTHESIS_FAIL]`等)
- ✅ 调度器集成: 依赖Analyzer模块，建立完整五级依赖链
- ✅ 验证中枢: 使用 `schema_signal.json` 进行严格校验
- ✅ 日志分级: INFO/WARN/ERROR 三级日志，结构化stderr输出

**架构师智慧锚点实现**:
- "从分析到决策": Synthesizer作为档案馆的"发令枪"，将技术指标转化为操作倾向信号
- "参数外部化": 算法层保持参数外部化，阈值和权重配置在JSON文件中，实现逻辑透明
- "逻辑透明最高境界": 主编调整策略只需修改配置文件，无需修改Python代码
- 为后续 Targeter（标的命中）提供标准化的策略信号输入

### 架构师审计与工业强化 (2614-012号)
**审计时间**: 2026-03-29 13:23  
**审计结论**: 🟢 满分通过，生产线已具备大规模流水线作业条件

**审计要点**:
1. **记忆锚点稳固**: MEMORY.md 完整收录 V1.2.1 标准
2. **原子性协议达标**: Temp-Write → Validate → Rename 闭环实现
3. **验证中枢就绪**: validate.py + schema 文件建立第一道"隔离墙"
4. **调度逻辑闭环**: orchestrator.py 具备根据退出码进行逻辑分发能力

**工业强化实施**:
1. **fetch_time 字段强制校验**:
   - 更新 `config/schema_ingest.json`，增加 `fetch_time` 必需字段
   - 所有Ingest模组输出必须包含数据抓取时间戳
   - 支持Web逻辑层新鲜度检测 (`[Data Stale]` 警告)

2. **数值边界检查集成**:
   - `scripts/validate.py` 新增 `--check-boundary` 参数和 `numeric_boundary_check` 函数
   - 单日净值波动超过15%触发 WARN 级别日志
   - 年化回报异常检查 (±100% 阈值)
   - 支持严格模式 (警告视为错误)

3. **调度器升级完成**:
   - 频率分层配置 (Daily/Weekly) 已实现
   - 结构化错误代码捕获强化 (`[NET_TIMEOUT]`, `[SCHEMA_MISMATCH]`)
   - 错误摘要完整记录至审计报告

**架构师智慧锚点**: "数据即生命 - 宁愿模块因校验失败而熔断，也绝不允许任何一条格式错误的数据进入系统。"

### 错误码规范
| 错误码 | 含义 | 调度器动作 |
|--------|------|------------|
| `NET_TIMEOUT` | 网络超时 | 重试 (最多3次) |
| `SCHEMA_MISMATCH` | 数据不符合Schema | 熔断，人工介入 |
| `AUTH_FAIL` | 认证失败 | 熔断，检查密钥 |
| `FILE_WRITE_FAIL` | 文件写入失败 | 重试 |
| `VALIDATE_FAIL` | 验证失败 | 重试或熔断 |

## 🗂️ 目录结构标准

### 五大合法区 (架构锚点)
1. `/web/` - Web中枢 (PHP + HTML + CSS)
2. `/vaults/` - 档案核心 (仅 `.md` 文件)
3. `/database/` - 数据模板 (仅 `.json`，脱敏)
4. `/scripts/` - 自动化工具 (Python/Shell脚本)
5. `/docs/reports/` - 审计留痕 (任务执行报告)

### 违禁目录 (自动清理)
- `venv/`, `env/`, `__pycache__/`
- `logs/` (Git忽略，但本地保留)
- `_PRIVATE_DATA/` (密钥和敏感数据，Git忽略)

### 同步规范
1. **同步脚本**: `scripts/github/sync_clean.sh`
2. **提交前缀**: `[ARCH]`, `[VAULT]`, `[DOC]`, `[SEC]`, `[DATA]`, `[SYNC]`
3. **禁止**: 手动 `git push`，必须使用合规脚本
4. **环境配置**: `~/.amber_env` (包含 `GITHUB_TOKEN`, `GITHUB_REPO`)

## 📝 重要决策记录

### 2026-03-29: 工业加固标准确立
**决策**: 采纳V1.2.1标准的5项工业加固补丁
**原因**: 将静态标准升级为动态自愈系统，建立工业级异常监控
**执行者**: Cheese 🧀 (实现验证标准化和结构化错误传递)

### 2026-03-29: 首个标准模组验收
**决策**: Task-20260330-A成果通过合金级验收
**架构师判定**: "第一个标准积木模组已通过合金级验收。代码完全遵循 V1.2.1 实战增补协议，具备原子性、容错、监控和安全隔离特性。档案馆的深蓝生产线现已启动。"
**意义**: 确立模组开发模板，为后续7个节点奠定基础

## 🔄 记忆维护机制

### 记忆层次
1. **长久记忆 (MEMORY.md)**: 核心标准、架构决策、关键事件
2. **当日记忆 (memory/YYYY-MM-DD.md)**: 日常进展、技术细节、临时记录
3. **审计报告 (docs/reports/)**: 任务执行记录、错误日志、性能数据

### 更新频率
1. **长久记忆**: 重要标准发布或架构变更时更新
2. **当日记忆**: 每天工作结束时创建/更新
3. **审计报告**: 每次任务执行自动生成

### 认知对齐
1. **GitHub同步**: 确保所有参与者访问相同代码和文档
2. **记忆存档**: 确保所有参与者了解项目历史和决策依据
3. **标准遵循**: 确保所有实现符合技术标准和架构规范

## 🚀 未来方向

### 技术演进路径
1. **短期 (Week 14)**: 扩展模块链 (Cleaner, Storer, Analyzer...)
2. **中期**: CI/CD集成，告警系统，性能优化
3. **长期**: 完整8节点流水线，自动化研报，决策辅助

### 质量标准
1. **代码质量**: 原子性、容错性、可监控性
2. **安全标准**: 密钥隔离、权限控制、敏感数据处理
3. **运维标准**: 日志轮转、错误告警、性能监控

### 协作标准
1. **沟通模式**: 明确角色分工，定期认知对齐
2. **文档标准**: 及时更新记忆存档，保持信息一致
3. **代码审查**: 符合架构标准，通过验收测试

---
**最后更新**: 2026-03-29 14:26  
**更新者**: Cheese 🧀  
**更新原因**: Task-20260330-F (Synthesizer) 完成，五级联动流水线就绪  

*"深蓝生产线已启动，合金级标准护航。" - 架构师 Gemini ⚖️*