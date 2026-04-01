#!/bin/bash
# 琥珀引擎Web服务修复脚本
# 修复Nginx端口10168配置问题

set -e

echo "🚀 开始修复琥珀引擎Web服务配置..."

# 1. 检查PHP-FPM socket
if [ -S "/run/php/php8.3-fpm.sock" ]; then
    echo "✅ PHP-FPM socket存在: /run/php/php8.3-fpm.sock"
else
    echo "❌ PHP-FPM socket不存在"
    echo "   检查服务状态: systemctl status php8.3-fpm"
    exit 1
fi

# 2. 检查生产目录
if [ -d "/var/www/amber-web" ]; then
    echo "✅ 生产目录存在: /var/www/amber-web"
    echo "   文件数量: $(ls /var/www/amber-web | wc -l)"
else
    echo "❌ 生产目录不存在"
    exit 1
fi

# 3. 创建测试PHP文件
echo "<?php echo '琥珀引擎 PHP 测试 ' . date('Y-m-d H:i:s'); ?>" > /var/www/amber-web/test.php
echo "✅ 创建测试文件: /var/www/amber-web/test.php"

# 4. 检查当前Nginx配置
echo "📋 当前Nginx配置检查:"
if nginx -t 2>&1 | grep -q "successful"; then
    echo "✅ Nginx配置语法正确"
else
    echo "⚠️ Nginx配置可能有错误"
fi

# 5. 创建标准配置（如果端口10168未配置）
CONFIG_FILE="/etc/nginx/sites-available/amber-web"
ENABLED_FILE="/etc/nginx/sites-enabled/amber-web"

# 检查是否已配置端口10168
if ss -tln | grep -q ":10168"; then
    echo "✅ 端口10168已在监听"
    echo "   当前监听状态:"
    ss -tln | grep ":10168"
else
    echo "⚠️ 端口10168未监听，创建配置..."
    
    # 创建配置内容
    cat > /tmp/amber-web.conf << 'EOF'
# 琥珀引擎Web服务配置
server {
    listen 10168;
    server_name localhost;
    root /var/www/amber-web;
    index index.php index.html index.htm;

    location / {
        try_files $uri $uri/ =404;
    }

    # PHP处理配置
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    # 禁止访问隐藏文件
    location ~ /\.ht {
        deny all;
    }
}
EOF
    
    echo "📝 配置内容已生成到 /tmp/amber-web.conf"
    echo "   请使用sudo执行以下命令安装配置:"
    echo ""
    echo "   sudo cp /tmp/amber-web.conf $CONFIG_FILE"
    echo "   sudo ln -sf $CONFIG_FILE $ENABLED_FILE"
    echo "   sudo nginx -t && sudo systemctl reload nginx"
    echo ""
fi

# 6. 创建验证脚本
cat > /tmp/verify_web.sh << 'EOF'
#!/bin/bash
echo "🔍 验证Web服务状态..."
echo "1. 测试端口响应:"
curl -s -o /dev/null -w "HTTP状态码: %{http_code}\n" http://localhost:10168/ || echo "连接失败"

echo "2. 测试PHP功能:"
curl -s http://localhost:10168/test.php || echo "PHP测试失败"

echo "3. 测试琥珀引擎主页面:"
curl -s http://localhost:10168/index.php | grep -o "琥珀引擎.*" | head -1 || echo "主页面访问失败"
EOF

chmod +x /tmp/verify_web.sh

echo ""
echo "🎯 修复步骤完成!"
echo "📋 下一步操作:"
echo "1. 如果端口10168未监听，请使用sudo安装上述配置"
echo "2. 运行验证脚本: bash /tmp/verify_web.sh"
echo "3. 检查琥珀引擎页面: http://localhost:10168/index.php"
echo ""
echo "📊 当前服务状态:"
echo "   Nginx进程数: $(ps aux | grep nginx | grep -v grep | wc -l)"
echo "   PHP-FPM进程数: $(ps aux | grep php-fpm | grep -v grep | wc -l)"
echo "   生产目录: /var/www/amber-web ($(ls /var/www/amber-web | wc -l)个文件)"
echo "   测试文件: /var/www/amber-web/test.php"

# 7. 检查紧急对冲报告
if [ -f "/home/luckyelite/.openclaw/workspace/amber-engine/EMERGENCY_HEDGE.md" ]; then
    echo ""
    echo "🚨 紧急对冲报告已存在:"
    echo "   文件: /home/luckyelite/.openclaw/workspace/amber-engine/EMERGENCY_HEDGE.md"
    echo "   最后修改: $(stat -c %y /home/luckyelite/.openclaw/workspace/amber-engine/EMERGENCY_HEDGE.md 2>/dev/null || echo '未知')"
else
    echo ""
    echo "⚠️ 紧急对冲报告未生成 (Z分数4.53σ触发)"
    echo "   需要检查 predict_next_open.py 脚本对冲报告生成逻辑"
fi