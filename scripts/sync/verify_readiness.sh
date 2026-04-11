#!/bin/bash
# 琥珀引擎 · 同步预检脚本
# 依据: AE-Web-Sync-001-V1.0 开发/生产隔离与强制同步法典
# 功能: 执行同步前的全面检查，确保系统就绪

set -e

echo "🔍 琥珀引擎同步预检开始 (依据法典 AE-Web-Sync-001-V1.0)"
echo "=================================================="

# 1. 语法静态检查
echo "📝 1. PHP语法静态检查..."
for php_file in $(find web -name "*.php"); do
    echo "  检查: $php_file"
    if ! php -l "$php_file" > /dev/null; then
        echo "❌ 语法错误: $php_file"
        exit 1
    fi
done
echo "✅ PHP语法检查通过"

# 2. 数据新鲜度检查
echo "📊 2. 数据新鲜度检查..."
RESONANCE_FILE="database/resonance_signal.json"
if [ -f "$RESONANCE_FILE" ]; then
    file_mtime=$(stat -c %Y "$RESONANCE_FILE")
    current_time=$(date +%s)
    age_hours=$(( (current_time - file_mtime) / 3600 ))
    
    if [ $age_hours -gt 1 ]; then
        echo "⚠️  警告: 共振信号数据已超过1小时 (${age_hours}小时)"
        echo "   文件: $RESONANCE_FILE"
        echo "   最后修改: $(date -d @$file_mtime '+%Y-%m-%d %H:%M:%S')"
    else
        echo "✅ 数据新鲜度通过 (${age_hours}小时前更新)"
    fi
else
    echo "❌ 错误: 共振信号文件不存在: $RESONANCE_FILE"
    exit 1
fi

# 3. 指纹生成
echo "🔑 3. 生成数据指纹..."
if [ -d ".git" ]; then
    COMMIT_ID=$(git rev-parse --short HEAD)
    echo "✅ Git指纹: $COMMIT_ID"
    echo "$COMMIT_ID" > .sync_fingerprint
else
    echo "⚠️  警告: 非Git仓库，使用时间戳作为指纹"
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    echo "✅ 时间戳指纹: $TIMESTAMP"
    echo "$TIMESTAMP" > .sync_fingerprint
fi

# 4. 目录结构检查
echo "📁 4. 目录结构检查..."
required_dirs=("web" "database" "scripts")
for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ 错误: 必需目录不存在: $dir"
        exit 1
    fi
done
echo "✅ 目录结构完整"

# 5. 敏感文件检查
echo "🔒 5. 敏感文件检查..."
sensitive_files=(".env" "_PRIVATE_DATA/secrets.json")
for file in "${sensitive_files[@]}"; do
    if [ -f "$file" ]; then
        echo "⚠️  发现敏感文件: $file (将在同步时排除)"
    fi
done

echo "=================================================="
echo "🎉 预检完成！系统就绪，可以开始同步投送"
echo "指纹: $(cat .sync_fingerprint)"
echo "执行同步命令: ./scripts/sync/deploy_to_production.sh"