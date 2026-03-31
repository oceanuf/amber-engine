# 琥珀引擎 · 开发/生产同步工作流
**依据**: AE-Web-Sync-001-V1.0 开发/生产隔离与强制同步法典  
**版本**: v1.0  
**生效日期**: 2026-03-31  

---

## 📋 概述

本工作流实现了开发环境与生产环境的物理隔离，确保决策准确性和系统可靠性。通过强制同步与真实性对撞测试，彻底杜绝"版本不统一"导致的决策风险。

## 🏗️ 环境架构

### 开发环境 (Workspace)
```
/home/luckyelite/.openclaw/workspace/amber-engine/
├── web/                    # Web应用代码
├── database/              # 数据文件 (JSON)
├── scripts/              # 自动化脚本
├── _PRIVATE_DATA/        # 敏感数据 (Git忽略)
└── .git/                 # 版本控制
```

### 生产环境 (Web-Server)
```
/var/www/amber-web/       # 独立的生产目录
├── index.php             # 通过同步从开发环境复制
├── css/                  # 样式文件
├── database/             # 只读软链接到开发环境数据
│   ├── resonance_signal.json -> ../../workspace/amber-engine/database/resonance_signal.json
│   └── ...
└── version.txt           # 数据指纹文件
```

## 🔄 同步工作流

### 第一步：预检 (Pre-Flight)
```bash
cd /home/luckyelite/.openclaw/workspace/amber-engine
./scripts/sync/verify_readiness.sh
```
**检查项**:
1. PHP语法静态检查
2. 数据新鲜度 (1小时内)
3. 生成数据指纹 (Git Commit ID)
4. 目录结构完整性
5. 敏感文件排除

### 第二步：同步投送 (Deployment)
```bash
./scripts/sync/deploy_to_production.sh
```
**执行操作**:
1. 原子化覆盖同步 (`rsync --delete`)
2. 创建数据软链接
3. 更新指纹文件
4. 权限锁定 (文件644, 目录755)
5. **真实性对撞测试** (核心加固项)

### 第三步：验证 (Verification)
```bash
./scripts/sync/truth_collision_test.sh
./scripts/sync/web_checklist.sh
```
**验证内容**:
1. 开发与生产环境数据一致性
2. Nginx配置正确性
3. 权限与隔离性检查

## ⚡ 真实性对撞测试 (核心加固项)

### 测试逻辑
1. **抓取开发值**: 读取 `database/resonance_signal.json` 中的原始评分
2. **抓取生产值**: 通过HTTP API或直接文件读取获取生产环境评分
3. **逻辑判定**: 若两值不一致，立即触发 **FATAL ERROR**

### 错误处理
- **评分不一致**: 触发回滚，禁止工程师结束会话
- **生产环境不可达**: 警告但不阻止同步
- **数据文件损坏**: 触发紧急修复流程

## 🏷️ 数据指纹系统

### 指纹格式
```
v1.3.x | Build: [Commit-ID]
```
**示例**: `v1.3.x | Build: a1b2c3d`

### 显示位置
- **Web界面**: 右下角固定位置 (CSS: `#data-fingerprint`)
- **指纹文件**: `/var/www/amber-web/version.txt`
- **同步记录**: `.sync_fingerprint`

### 生成逻辑
1. 优先: Git Commit ID (前7位)
2. 备选: 同步时间戳
3. 回退: 当前时间戳

## 📋 Web更新自查清单

### 自动化检查脚本
```bash
./scripts/sync/web_checklist.sh
```

### 检查项矩阵
| 检查项 | 描述 | 修复命令 |
|--------|------|----------|
| **隔离性** | Nginx是否指向开发目录 | `sed -i 's|/workspace/output|/var/www/amber-web|g' nginx配置` |
| **数据源** | 数据文件是否为软链接 | `ln -sf 开发路径 生产路径` |
| **指纹更新** | 指纹文件是否存在且一致 | `./scripts/sync/deploy_to_production.sh` |
| **对撞测试** | 开发与生产数据是否一致 | `./scripts/sync/truth_collision_test.sh` |
| **权限锁定** | 文件权限是否为644/755 | `find /var/www/amber-web -type f -exec chmod 644 {} \;` |

## 🔧 紧急修复流程

### 场景1: 生产环境数据损坏
```bash
# 1. 停止Web服务
sudo systemctl stop nginx

# 2. 强制重新同步
./scripts/sync/deploy_to_production.sh --force

# 3. 验证修复
./scripts/sync/truth_collision_test.sh

# 4. 恢复服务
sudo systemctl start nginx
```

### 场景2: 同步失败导致版本不一致
```bash
# 1. 检查当前状态
./scripts/sync/web_checklist.sh

# 2. 手动修复Nginx配置
sudo nano /etc/nginx/sites-available/amber.googlemanager.cn
# 修改 root 指向 /var/www/amber-web

# 3. 测试配置
sudo nginx -t
sudo systemctl reload nginx

# 4. 重新同步
./scripts/sync/deploy_to_production.sh
```

### 场景3: 真实性对撞测试失败
```bash
# 1. 分析差异
diff -u 开发文件 生产文件

# 2. 检查数据源
ls -la /var/www/amber-web/database/

# 3. 重建软链接
rm -f /var/www/amber-web/database/*.json
ln -sf /home/luckyelite/.openclaw/workspace/amber-engine/database/*.json /var/www/amber-web/database/

# 4. 重新测试
./scripts/sync/truth_collision_test.sh
```

## 🚀 快速开始

### 首次部署
```bash
# 1. 创建生产目录
sudo mkdir -p /var/www/amber-web
sudo chown luckyelite:luckyelite /var/www/amber-web

# 2. 更新Nginx配置
sudo sed -i 's|/home/luckyelite/.openclaw/workspace/amber-engine/output|/var/www/amber-web|g' /etc/nginx/sites-available/amber.googlemanager.cn
sudo nginx -t && sudo systemctl reload nginx

# 3. 执行完整同步
cd /home/luckyelite/.openclaw/workspace/amber-engine
./scripts/sync/deploy_to_production.sh

# 4. 验证部署
./scripts/sync/web_checklist.sh
```

### 日常更新
```bash
cd /home/luckyelite/.openclaw/workspace/amber-engine
./scripts/sync/verify_readiness.sh
./scripts/sync/deploy_to_production.sh
```

### 监控检查
```bash
# 定期检查 (可加入Cron)
0 * * * * /home/luckyelite/.openclaw/workspace/amber-engine/scripts/sync/truth_collision_test.sh
```

## 📊 合规性检查

### 法典要求 vs 实现状态
| 法典要求 | 实现状态 | 检查命令 |
|----------|----------|----------|
| 物理路径解耦 | ✅ 实现 | `./scripts/sync/web_checklist.sh` |
| 原子性写入协议 | ✅ 实现 | `grep -r "rsync.*--delete" scripts/` |
| 真实性对撞测试 | ✅ 实现 | `./scripts/sync/truth_collision_test.sh` |
| 数据指纹显示 | ✅ 实现 | 查看Web界面右下角 |
| 权限锁定 | ✅ 实现 | `ls -la /var/www/amber-web/` |
| 敏感信息脱敏 | ✅ 实现 | `cat .rsync-filter` |

## 🎯 最佳实践

### 同步时机
1. **数据更新后**: 每次算法执行生成新数据后
2. **代码修改后**: Web界面或逻辑修改后
3. **定期检查**: 每天至少执行一次对撞测试

### 版本控制
1. **提交前同步**: 确保生产环境与代码仓库一致
2. **标签对应**: Git标签与生产环境指纹对应
3. **回滚能力**: 通过Git历史快速回滚到任意版本

### 监控告警
1. **对撞失败告警**: 立即通知工程师
2. **数据陈旧告警**: 数据超过1小时未更新
3. **权限异常告警**: 生产环境文件权限变更

---

## 📜 法典引用

本法典工作流严格遵循 **AE-Web-Sync-001-V1.0** 要求：

> "隔离带来的不便，是支付给'安全'与'准确'的必要溢价。" —— 首席架构师 Gemini

**签发人**: 首席架构师 Gemini ⚖️  
**执行人**: 工程师 Cheese 🧀  
**最后更新**: 2026-03-31