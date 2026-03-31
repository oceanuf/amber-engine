# 琥珀引擎：开发/生产隔离与强制同步法典
**文档编号**: AE-Web-Sync-001-V1.0 
**密级**: 核心架构准则 (Internal) 
**生效日期**: 2026-03-31 
**状态**: 🚀 正式发布 (Final)

---

## 📋 0. 前言：防火墙原则
开发环境（Workspace）是实验场，允许混乱与试错；生产环境（Web-Server）是指挥部，必须纯净且绝对准确。本法典旨在通过物理隔离与逻辑对撞，彻底杜绝"版本不统一"导致的决策风险。

---

## 🛡️ 第一部分：环境隔离与净化原则 (Isolation & Purification)

### 1.1 物理路径解耦
- **开发路径**: `/home/luckyelite/.openclaw/workspace/amber-engine/`
- **生产路径**: `/var/www/amber-web/` (或独立于开发根目录的 Web 根目录)
- **准则**: Web 服务器（Nginx/Apache）严禁直接指向开发目录，必须通过同步投送实现。

### 1.2 净化性约束
- **零调试信息**: 生产环境 `php.ini` 必须关闭 `display_errors`，防止逻辑泄露。
- **单向流动**: 代码与数据仅允许从 `Workspace` -> `Web-Server` 投送，严禁反向污染。
- **敏感信息脱敏**: 同步脚本必须配置 `.rsync-filter`，自动排除 `.git`、`.env` (开发版) 及 `_PRIVATE_DATA/`。

---

## 🔄 第二部分：强制同步与校验流程 (Synchronization & Verification)

### 2.1 预检阶段 (Pre-Flight)
在执行任何同步操作前，必须通过 `verify_readiness.sh` 脚本：
- **语法静态检查**: 执行 `php -l` 确保 Web 脚本无语法死穴。
- **数据新鲜度**: 确认 `database/resonance_signal.json` 的更新时间戳早于当前 1 小时内。
- **指纹生成**: 获取当前 Git HEAD 的前 7 位 Commit ID 作为"数据指纹"。

### 2.2 投送阶段 (Deployment)
- **原子化覆盖**: 使用 `rsync -avz --delete` 确保生产环境是开发环境 `web/` 目录的镜像。
- **数据挂载**: 生产环境通过"只读软链接"挂载必要的 JSON 数据源，确保数据真实性。

### 2.3 真实性对撞 (Truth Collision Test) ✅ [核心加固项]
同步完成后，脚本必须执行自动化比对：
1. **抓取生产值**: `curl -s [Prod-URL]/api.php` 获取当前 Web 显示的评分。
2. **抓取开发值**: 读取 `database/resonance_signal.json` 中的原始评分。
3. **逻辑判定**: 若两值不一致，立即触发 **FATAL ERROR**，发布回滚并禁止 Cheese 结束会话。

---

## 🏷️ 第三部分：数据指纹 (Digital Fingerprint)

### 3.1 显式特征码
- **展示位置**: Web 界面右下角或 Header 微小区域。
- **内容格式**: `v1.3.x | Build: [Commit-ID]`
- **目的**: 允许主编通过浏览器肉眼瞬间判定当前呈现的是否为开发修改后的最新版本。

---

## 📋 第四部分：Web 更新自查清单 (Checklist)

| 检查项 | 描述 | 状态 |
| :--- | :--- | :--- |
| **隔离性** | 是否误传了本地 `config_dev.json`？ | [ ] |
| **数据源** | `index.php` 指向的是否为生产数据路径？ | [ ] |
| **指纹更新** | 界面显示的 Commit ID 是否与本地一致？ | [ ] |
| **对撞测试** | 脚本比对结果是否为 `SUCCESS`？ | [ ] |
| **权限锁定** | 生产目录权限是否已重置为 `Read-Only`？ | [ ] |

---

## 📜 最终定论
> "隔离带来的不便，是支付给'安全'与'准确'的必要溢价。" —— 首席架构师 Gemini

**签发人**: 首席架构师 Gemini ⚖️ 
**接收人**: 工程师 Cheese 🧀