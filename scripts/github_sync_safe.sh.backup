#!/bin/bash
# 🏛️ GitHub同步脚本 (符合[2613-182号]规范V1.0.0)
# 集成自毁式敏感信息扫描，环境锚定验证

set -e

# ==================== 安全扫描模块 ====================
# 3.1 自毁式敏感信息扫描
echo "🔍 执行安全扫描..."
if grep -r "ghp_[A-Za-z0-9]\{36\}" . 2>/dev/null; then
    echo "🚨 检测到硬编码 GitHub Token，脚本自毁终止"
    echo "📋 违规文件:"
    grep -r "ghp_[A-Za-z0-9]\{36\}" . 2>/dev/null
    exit 1
fi

# 3.3 用户权限检查 (环境锚定)
if [[ "$(whoami)" != "luckyelite" ]]; then
    echo "❌ 非法用户权限，必须在 luckyelite 用户下执行"
    echo "当前用户: $(whoami)"
    exit 1
fi
echo "✅ 用户权限验证通过: $(whoami)"

# ==================== 环境变量验证 ====================
# 3.2 环境变量验证
REQUIRED_ENV_VARS=("GITHUB_TOKEN" "GITHUB_REPO")
for var in "${REQUIRED_ENV_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ 缺失环境变量: $var"
        echo "请设置: export $var=\"value\""
        exit 1
    fi
done
echo "✅ 环境变量验证通过"

# ==================== 配置信息 ====================
WORKSPACE_DIR="/home/luckyelite/.openclaw/workspace/amber-engine/amber-sentry-logs"
GIT_USER_NAME="Cheese Intelligence Team"
GIT_USER_EMAIL="cheese@cheese.ai"
LOG_FILE="logs/github_sync_$(date +%Y%m%d).log"

# 进入工作目录
cd "$WORKSPACE_DIR"
echo "📁 工作目录: $(pwd)"

# ==================== 日志记录 ====================
log_message() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local message="$1"
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

log_message "🚀 开始GitHub同步"

# ==================== Git配置 ====================
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"

# ==================== 检查Git状态 ====================
log_message "🔍 检查Git状态..."
git status

# ==================== 提交处理 ====================
if [[ -n $(git status --porcelain) ]]; then
    log_message "📝 发现未提交的更改"
    
    # 使用提供的提交信息或默认信息
    COMMIT_MSG="${1:-"[CHORE]: 自动同步 $(date '+%Y-%m-%d %H:%M:%S')"}"
    
    # 验证提交信息格式
    if [[ ! "$COMMIT_MSG" =~ ^\[(FEAT|FIX|DOCS|REFACTOR|TEST|CHORE)\]: ]]; then
        log_message "⚠️  提交信息格式不符合规范，自动修正"
        COMMIT_MSG="[CHORE]: $COMMIT_MSG"
    fi
    
    # 添加所有更改
    git add .
    
    # 提交
    git commit -m "$COMMIT_MSG"
    log_message "✅ 提交完成: $COMMIT_MSG"
else
    log_message "📭 没有需要提交的更改"
    COMMIT_MSG="No changes to commit"
fi

# ==================== 远程仓库配置 ====================
REMOTE_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"
log_message "🌐 配置远程仓库: ${GITHUB_REPO}"

if ! git remote | grep -q origin; then
    git remote add origin "$REMOTE_URL"
    log_message "➕ 添加远程仓库"
else
    CURRENT_URL=$(git remote get-url origin)
    if [[ "$CURRENT_URL" != "$REMOTE_URL" ]]; then
        git remote set-url origin "$REMOTE_URL"
        log_message "🔄 更新远程仓库URL"
    else
        log_message "✅ 远程仓库URL已正确配置"
    fi
fi

# ==================== 拉取最新更改 ====================
log_message "📥 拉取最新更改..."
if git pull origin main --rebase --autostash 2>/dev/null; then
    log_message "✅ 拉取成功"
else
    log_message "⚠️  拉取失败或无需拉取，继续推送"
fi

# ==================== 推送到GitHub ====================
log_message "🚀 推送到GitHub..."
if git push -u origin main; then
    log_message "✅ GitHub同步成功！"
    
    # 获取最新提交信息
    LATEST_COMMIT=$(git log --oneline -1)
    log_message "📋 最新提交: $LATEST_COMMIT"
    
    # 更新共同记忆
    update_system_memory() {
        local task_desc="$1"
        local current_time=$(date '+%H:%M')
        local memory_file="SYSTEM_MEMORY.md"
        
        # 在最近任务部分添加记录
        sed -i "/## 6. 最近任务 (Recent Tasks)/a\\
### $(date '+%Y-%m-%d')\\
- **[${current_time}] GitHub同步**: ${task_desc}\\
  - 安全扫描通过，无硬编码敏感信息\\
  - 环境变量验证通过\\
  - 用户权限验证通过 (luckyelite)\\
  - 成功推送到 ${GITHUB_REPO}" "$memory_file"
        
        log_message "📖 共同记忆已更新"
    }
    
    update_system_memory "$COMMIT_MSG"
    
else
    log_message "❌ GitHub推送失败"
    log_message "🔧 错误信息已记录到日志"
    exit 1
fi

# ==================== 磁盘空间检查 ====================
# 5.3 磁盘空间检查
if [[ $(df /home --output=pcent | tail -1 | tr -d '% ') -gt 90 ]]; then
    log_message "⚠️  磁盘空间不足 90%，请清理"
fi

log_message "🎉 GitHub同步流程完成"
echo "📊 详细日志: $LOG_FILE"

# ==================== 健康检查 ====================
# 执行健康检查
if [[ -f "scripts/github_health_check.sh" ]]; then
    log_message "🩺 执行健康检查..."
    ./scripts/github_health_check.sh
fi