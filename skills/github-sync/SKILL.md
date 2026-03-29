---
name: github-sync
description: |
  基于[2614-001号]档案馆单体仓库同步法典与琥珀引擎共同记忆核心记忆法典(V5.0)的GitHub合规同步技能。
  当用户下达"GitHub同步"命令时，确保认知对齐，高效完成同步任务。
---

# 🏛️ GitHub同步技能 - 基于法典V5.0

## 技能概述

本技能基于以下法典制定：
1. **[2614-001号]**: 档案馆单体仓库同步法典
2. **琥珀引擎共同记忆核心记忆法典(V5.0)**

## 认知对齐检查清单

当用户下达"GitHub同步"命令时，必须确认以下认知对齐：

### ✅ 前置检查
1. **环境配置**: 确认 `~/.amber_env` 文件存在且包含有效的 `GITHUB_TOKEN` 和 `GITHUB_REPO`
2. **法典版本**: 确认当前遵循法典 V5.0 (Monorepo架构)
3. **架构合规**: 确认根目录结构符合五大合法区要求
4. **禁令状态**: 确认永久禁令未被违反

### ✅ 同步前验证
1. **违禁目录**: 检查并清理 `venv/`, `logs/`, `__pycache__/` 等
2. **敏感数据**: 确认 `_PRIVATE_DATA/` 未被跟踪
3. **提交前缀**: 准备合适的语义化前缀 (`[ARCH]`, `[VAULT]`, `[DOC]`, `[SEC]`, `[DATA]`)
4. **同步工具**: 确认使用 `scripts/github/sync_clean.sh` (严禁手动 `git push`)

## 标准操作流程

### 1. 快速同步 (默认)
当用户简单说"GitHub同步"时，执行标准流程：

```bash
# 进入工作目录
cd /home/luckyelite/.openclaw/workspace/amber-engine

# 加载环境配置
source ~/.amber_env

# 执行合规同步脚本
./scripts/github/sync_clean.sh "[SYNC]: 日常合规同步 $(date '+%Y-%m-%d %H:%M')"
```

### 2. 带提交信息的同步
当用户提供具体提交信息时：

```bash
./scripts/github/sync_clean.sh "[PREFIX]: 用户提供的提交信息"
```

**前缀选择指南**:
- `[ARCH]`: 架构变更、目录结构调整
- `[VAULT]`: ETF金库内容更新 (`vaults/` 目录)
- `[DOC]`: 文档更新 (`docs/` 目录)
- `[SEC]`: 安全相关变更
- `[DATA]`: 数据更新 (`database/` 目录)
- `[SYNC]`: 日常同步任务

### 3. 紧急同步 (冲突解决)
当检测到冲突时：

```bash
# 1. 拉取最新更改
git pull --rebase origin main

# 2. 解决冲突
# 3. 执行标准同步
./scripts/github/sync_clean.sh "[ARCH]: 冲突解决与同步 $(date '+%Y-%m-%d %H:%M')"
```

## 错误处理与恢复

### 常见错误及解决方案

#### 错误1: GitHub推送保护阻止
```
remote: error: GH013: Repository rule violations found
```
**解决方案**:
1. 检查并删除包含敏感信息的文件
2. 使用 `git commit --amend` 修改提交
3. 重新推送

#### 错误2: 权限不足
```
remote: Permission to user/repo.git denied to user
```
**解决方案**:
1. 验证 `GITHUB_TOKEN` 有效性
2. 确认令牌具有仓库写入权限
3. 更新 `~/.amber_env` 中的令牌

#### 错误3: 分支冲突
```
! [rejected] main -> main (non-fast-forward)
```
**解决方案**:
1. 执行 `git pull --rebase origin main`
2. 解决冲突
3. 重新推送

## 同步后验证

每次同步后必须验证：

### 1. 本地验证
```bash
# 检查提交状态
git log --oneline -3

# 检查文件状态
git status

# 验证架构合规
ls -la | grep -E "(venv|logs|__pycache__)"
```

### 2. 远程验证
```bash
# 验证GitHub提交
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_REPO/commits?per_page=1" | \
  jq -r '.[0] | .sha[0:7] + " " + .commit.message'
```

### 3. 服务验证 (10168端口)
```bash
# 测试页面加载
time curl -s -k "https://localhost:10168/" --connect-timeout 3
```

## 认知对齐确认模板

当用户下达"GitHub同步"命令时，回复以下确认：

```
🧀 **GitHub同步认知对齐确认**

基于法典V5.0，确认以下信息：

✅ **环境配置**: ~/.amber_env 已加载
✅ **法典版本**: V5.0 (Monorepo架构)  
✅ **仓库路径**: amber-engine 单体仓库
✅ **同步工具**: scripts/github/sync_clean.sh
✅ **提交前缀**: [SYNC] (默认) / [用户指定]
✅ **架构合规**: 五大合法区检查通过

**执行摘要**:
- 违禁目录清理: 自动执行
- 敏感数据保护: _PRIVATE_DATA/ 已排除
- 同步方式: 合规脚本 (非手动git push)
- 验证机制: 同步后三重验证

**预计操作**:
1. 环境加载与验证
2. 违禁目录清理  
3. Git添加与提交
4. 远程拉取与推送
5. 同步结果验证

请确认以上认知对齐，我将开始执行同步任务。
```

## 技能配置

### 环境要求
```bash
# 必需的环境变量 (~/.amber_env)
export GITHUB_TOKEN="your_token"
export GITHUB_REPO="username/repository"
export GIT_USER_NAME="Your Name"
export GIT_USER_EMAIL="your@email.com"
```

### 文件权限
```bash
# 同步脚本权限
chmod +x /home/luckyelite/.openclaw/workspace/amber-engine/scripts/github/sync_clean.sh

# 环境文件权限
chmod 600 ~/.amber_env
```

### 定时任务 (可选)
```bash
# 每日自动同步 (cron job)
0 9 * * * cd /home/luckyelite/.openclaw/workspace/amber-engine && source ~/.amber_env && ./scripts/github/sync_clean.sh "[SYNC]: 每日自动同步 $(date '+%Y-%m-%d')"
```

## 法典引用

### [2614-001号] 关键条款
- **条款1**: 必须使用标准化同步脚本
- **条款2**: 提交必须包含语义化前缀  
- **条款3**: 严禁手动执行 `git push`
- **条款4**: 必须维护架构锚点合规性

### 法典V5.0 关键条款
- **角色定义**: 工程师(Cheese)负责同步实施
- **架构锚点**: 五大合法区 (web/, vaults/, docs/, scripts/, database/)
- **永久禁令**: 无硬编码Token、_PRIVATE_DATA/脱敏、vaults/无脚本
- **第14周协议**: 每日同步、审计触发、紧急回滚

## 技能维护

### 版本记录
- **V1.0.0** (2026-03-29): 基于法典V5.0创建初始版本
- **维护者**: 工程师 Cheese 🧀
- **法典依据**: [2614-001号] + 法典V5.0

### 更新机制
1. 当法典更新时，同步更新本技能
2. 当同步流程变更时，更新操作流程
3. 当出现新错误模式时，更新错误处理

### 技能测试
```bash
# 测试技能功能
cd /home/luckyelite/.openclaw/workspace/amber-engine
./skills/github-sync/test_sync.sh
```

---

**技能守卫者**: 工程师 Cheese 🧀  
**法典依据**: [2614-001号] + 法典V5.0  
**创建时间**: 2026-03-29  
**生效时间**: 立即生效  

*本技能确保每次GitHub同步都符合法典要求，实现认知对齐的高效协作。*