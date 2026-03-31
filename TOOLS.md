# TOOLS.md - 琥珀引擎工具配置与技能索引

## 📋 重要提示
**技能索引已独立为专门文件**: [SKILLS_INDEX.md](./SKILLS_INDEX.md)
- 包含OpenClaw学院学习的28门全技能详细索引
- 基于实际学习记录和技能目录验证
- 每次接到任务时**必须首先查阅**
- 遵循"先查表，后动手"原则

## 🎯 本文件用途
本文件用于记录**环境特定的配置**，而非技能索引。包括：

- 服务器连接信息
- API密钥别名
- 环境变量配置
- 硬件设备映射
- 个性化设置

## 🔧 环境配置示例

### API密钥别名
```yaml
# Tushare Pro
TUSHARE_TOKEN: "your_tushare_token_here"

# AkShare 配置
AKSHARE_PROXY: "http://proxy.example.com:8080"

# 邮件通知
GMAIL_CREDENTIALS: "path/to/credentials.json"
```

### 服务器连接
```yaml
# 生产服务器
PRODUCTION_SERVER: "ssh://user@amber-web.example.com"
PRODUCTION_PATH: "/var/www/amber-web/"

# 备份服务器
BACKUP_SERVER: "ssh://backup@backup.example.com"
BACKUP_PATH: "/backup/amber-engine/"
```

### 监控配置
```yaml
# 健康检查URL
HEALTH_CHECK_URLS:
  - "https://amber-web.example.com/api/health"
  - "https://amber-web.example.com/api/data"

# 告警阈值
ALERT_THRESHOLDS:
  data_freshness: 3600  # 数据新鲜度阈值(秒)
  error_rate: 0.05      # 错误率阈值
  response_time: 5.0    # 响应时间阈值(秒)
```

## 🚀 快速参考

### 常用命令别名
```bash
# 同步到生产环境
alias sync-prod="bash scripts/sync/deploy_to_production.sh"

# 运行健康检查
alias health-check="python3 scripts/automation/alert_system.py --check"

# 查看技能索引
alias skills="cat SKILLS_INDEX.md | head -50"
```

### 环境变量
```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
export AMBER_ENGINE_HOME="/home/luckyelite/.openclaw/workspace/amber-engine"
export PYTHONPATH="$AMBER_ENGINE_HOME:$PYTHONPATH"
export PATH="$AMBER_ENGINE_HOME/scripts:$PATH"
```

## 🔗 相关文件

### 核心文档
1. **[SKILLS_INDEX.md](./SKILLS_INDEX.md)** - OpenClaw学院28门技能完整索引 **(必读)**
2. **[MEMORY.md](./MEMORY.md)** - 长久记忆与架构决策
3. **[docs/sync_workflow.md](./docs/sync_workflow.md)** - 同步工作流文档

### 配置文件
1. **~/.amber_env** - 环境变量配置文件
2. **config/** - 应用程序配置目录
3. **_PRIVATE_DATA/** - 敏感数据目录

## ⚠️ 安全注意事项

### 敏感信息处理
1. **严禁提交**: API密钥、密码等敏感信息严禁提交到Git
2. **环境变量**: 所有敏感信息必须通过环境变量注入
3. **权限控制**: 敏感文件权限设置为600

### 备份策略
1. **每日备份**: 使用Backup-Service技能进行每日备份
2. **异地备份**: 重要数据需要异地备份
3. **版本控制**: 所有代码和配置必须纳入Git版本控制

---

## 📝 更新日志

### 2026-03-31
- **重大变更**: 将技能索引分离到独立文件SKILLS_INDEX.md
- **原因**: 遵循"单一职责原则"，避免文件功能混杂
- **效果**: 工具配置和技能索引分离，提高查阅效率

### 使用原则
1. **配置信息** → 记录在本文件
2. **技能索引** → 查阅SKILLS_INDEX.md
3. **架构决策** → 查阅MEMORY.md
4. **工作流程** → 查阅docs/目录下相关文档

---

**最后更新**: 2026-03-31 13:45 GMT+8  
**维护者**: 工程师 Cheese 🧀  
**状态**: ✅ 与SKILLS_INDEX.md分离完成
