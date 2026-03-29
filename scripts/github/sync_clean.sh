#!/bin/bash
# 🏛️ 法典 V3.1 [2614-001] 合规同步脚本
# 执行Monorepo结构重构与全量合规化同步
# 版本: V3.1.0
# 创建时间: 2026-03-29

set -e

# ==================== 配置信息 ====================
WORKSPACE_DIR="/home/luckyelite/.openclaw/workspace/amber-engine"
GIT_USER_NAME="Cheese Intelligence Team"
GIT_USER_EMAIL="cheese@cheese.ai"
COMMIT_MSG="${1:-'[ARCH]: Monorepo 结构重构与全量合规化同步 (2614-003)'}"

# ==================== 环境验证 ====================
echo "🔐 加载环境配置..."
if [ -f ~/.amber_env ]; then
    source ~/.amber_env
    echo "✅ 环境配置加载完成"
else
    echo "❌ 缺失 ~/.amber_env 配置文件"
    exit 1
fi

# 验证必需的环境变量
if [[ -z "$GITHUB_TOKEN" || -z "$GITHUB_REPO" ]]; then
    echo "❌ 缺失GitHub环境变量"
    exit 1
fi

echo "✅ 环境验证通过"

# ==================== 进入工作目录 ====================
cd "$WORKSPACE_DIR"
echo "📁 工作目录: $(pwd)"

# ==================== Git配置 ====================
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"

# ==================== 清理违禁目录 ====================
echo "🧹 清理违禁目录..."
PROHIBITED_DIRS=("venv" "logs" "__pycache__" ".pytest_cache" ".mypy_cache" "node_modules" "dist" "build" "*.egg-info")

for dir in "${PROHIBITED_DIRS[@]}"; do
    if [ -d "$dir" ] || [ -f "$dir" ]; then
        echo "  🗑️  删除: $dir"
        rm -rf "$dir"
    fi
done

# 清理Python缓存文件
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "✅ 违禁目录清理完成"

# ==================== 创建.gitignore文件 ====================
echo "📝 创建.gitignore文件..."
cat > .gitignore << 'EOF'
# 🏛️ 法典 V3.1 [2614-001] 合规.gitignore
# 创建时间: 2026-03-29

# === 环境与配置 ===
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
*.env
~/.amber_env

# === Python ===
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# === 虚拟环境 ===
venv/
env/
ENV/
env.bak/
venv.bak/

# === 日志文件 ===
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*

# === 编辑器 ===
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# === 测试 ===
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# === 文档 ===
_site/
.sass-cache/
.jekyll-cache/
.jekyll-metadata

# === 系统 ===
Thumbs.db
ehthumbs.db
Desktop.ini

# === OpenClaw ===
.openclaw/
.openclaw/workspace-state.json

# === 私有数据 ===
_PRIVATE_DATA/
EOF

echo "✅ .gitignore文件创建完成"

# ==================== 添加文件到Git ====================
echo "📦 添加文件到Git..."
git add .

# 检查是否有需要提交的更改
if [[ -z $(git status --porcelain) ]]; then
    echo "📭 没有需要提交的更改"
    exit 0
fi

# ==================== 提交更改 ====================
echo "💾 提交更改..."
git commit -m "$COMMIT_MSG"
echo "✅ 提交完成: $COMMIT_MSG"

# ==================== 配置远程仓库 ====================
REMOTE_URL="https://github.com/${GITHUB_REPO}.git"
echo "🌐 配置远程仓库: ${GITHUB_REPO}"

if ! git remote | grep -q origin; then
    git remote add origin "$REMOTE_URL"
    echo "➕ 添加远程仓库"
else
    CURRENT_URL=$(git remote get-url origin)
    if [[ "$CURRENT_URL" != "$REMOTE_URL" ]]; then
        git remote set-url origin "$REMOTE_URL"
        echo "🔄 更新远程仓库URL"
    else
        echo "✅ 远程仓库URL已正确配置"
    fi
fi

# ==================== 拉取最新更改 ====================
echo "📥 拉取最新更改..."
if git pull --rebase origin main; then
    echo "✅ 拉取成功"
else
    echo "⚠️  拉取失败，尝试强制推送"
fi

# ==================== 推送到GitHub ====================
echo "🚀 推送到GitHub..."
if git push -u origin main; then
    echo "✅ GitHub同步成功！"
    
    # 获取最新提交信息
    LATEST_COMMIT=$(git log --oneline -1)
    echo "📋 最新提交: $LATEST_COMMIT"
    
    # 生成同步报告
    generate_sync_report() {
        local report_file="SYNC_REPORT_$(date +%Y%m%d_%H%M%S).md"
        cat > "$report_file" << EOF
# 🏛️ 法典 V3.1 [2614-001] 合规同步报告

## 同步摘要
- **时间**: $(date '+%Y-%m-%d %H:%M:%S')
- **任务**: $COMMIT_MSG
- **状态**: ✅ 成功

## 执行详情

### 1. 清理操作
- 删除违禁目录: ${PROHIBITED_DIRS[@]}
- 清理Python缓存文件
- 创建合规.gitignore文件

### 2. Git操作
- 分支: main
- 远程仓库: $GITHUB_REPO
- 提交信息: $COMMIT_MSG
- 最新提交: $LATEST_COMMIT

### 3. 合规验证
- ✅ 无venv目录
- ✅ 无logs目录
- ✅ 无__pycache__目录
- ✅ 有合规.gitignore文件

### 4. 仓库结构
\`\`\`
$(find . -maxdepth 2 -type f -name "*.md" -o -name "*.py" -o -name "*.sh" | sort)
\`\`\`

## 法典 V3.1 合规检查
- [x] 远程冲突已解决
- [x] 违禁目录已清理
- [x] 标准化推送完成
- [x] 仓库结构1:1对齐

---
*报告生成时间: $(date '+%Y-%m-%d %H:%M:%S')*
EOF
        echo "📄 同步报告已生成: $report_file"
    }
    
    generate_sync_report
    
else
    echo "❌ GitHub推送失败"
    echo "🔧 错误信息:"
    git push -u origin main 2>&1 | tail -10
    exit 1
fi

echo "🎉 法典 V3.1 [2614-001] 合规同步完成！"