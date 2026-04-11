# 📜 GITHUB_SYNC.md - 琥珀引擎同步与投送总纲 (V2.0)

**文档编号**: `AE-SYNC-V2-2026`  
**核心哲学**: 开发乱序，生产纯净；数据对撞，指纹追踪。  
**适用版本**: 适配法典 V5.0 + 演武场 V2.1  

---

## 🛡️ 第一部分：物理隔离与净化契约 (The Firewall)

### 1.1 环境二元论
- **Workspace (开发)**: `/home/luckyelite/.openclaw/workspace/amber-engine/`
  - *属性*: 高频修改、带伤实验、完整 Git 历史。
- **Web-Server (生产)**: `/var/www/amber-web/`
  - *属性*: 纯净镜像、禁止手动修改、仅通过 `rsync` 投送。

### 1.2 净化性约束 (The Purifier)
- **单向流动**: 代码与数据仅允许从 `Workspace` -> `Web-Server` 投送，严禁反向污染。
- **硬性排除**: 同步脚本必须配置 `.rsync-filter`，物理隔离以下内容：
  - `.git/` (防止源码元数据泄露)
  - `_PRIVATE_DATA/` (保护密钥与个人隐私)
  - `memory/` 中的未脱敏草稿。

---

## 🔄 第二部分：强制同步与对撞校验 (The Collision)

### 2.1 预检阶段 (Pre-Flight)
执行 `./scripts/github/sync_clean.sh` 前，Cheese 必须自动确认：
1. **数据新鲜度**: `database/resonance_signal.json` 的更新时间戳必须早于当前 1 小时内。
2. **报告完整性**: 若当前时间在 T+1 日 08:30 之后，必须确认 `reports/arena/` 下已生成最新实战报告。
3. **架构锚点**: 验证“五大合法区”无非法文件残留。

### 2.2 数据对撞测试 (Truth Collision) ✅
同步完成后，Cheese 必须执行自动化逻辑比对：
- **逻辑**: `Read(Local_JSON_Score) == Request(Prod_Web_API_Score)`。
- **熔断**: 若对撞结果不一致（即生产环境未同步更新或数据源错误），立即触发 **FATAL ERROR**，禁止结束当前会话，并强制回滚。

---

## 🏷️ 第三部分：数据指纹与认知对齐 (Fingerprint)

### 3.1 显式特征码
- **Build ID**: 获取当前 Git HEAD 前 7 位作为“指纹”。
- **展示契约**: Web 界面右下角强制显示 `v2.x | Build: [Commit-ID]`，供主编进行肉眼审计。

### 3.2 认知对齐命令
当收到“GitHub同步”指令时，Cheese 必须回复标准化确认函：
> **🧀 GitHub同步认知对齐确认**
> - **提交前缀**: `[ARCH]` (架构) / `[DATA]` (数据) / `[REPT]` (报告) / `[SYNC]` (日常)
> - **实战报告**: ✅ [YYYY-MM-DD].md 已就绪
> - **对撞准备**: 待同步后执行生产/开发数据比对
> - **合规检查**: 永久禁令三条已校验

---

## 📋 第四部分：同步自查清单 (Checklist)

| 检查项 | 描述 | 状态 |
| :--- | :--- | :--- |
| **颗粒闭环** | `GRAIN.md` 中关联任务是否已标记为 ✅？ | [ ] |
| **审计对齐** | 评委中控的权重更新是否已同步至 `ALGORITHMS.md`？ | [ ] |
| **指纹对撞** | `curl` 生产环境接口返回的评分是否与本地一致？ | [ ] |
| **报告归档** | 演武场当日实战报告是否已进入 `reports/arena/`？ | [ ] |

---

## 📜 错误处理与应急

1. **冲突探测**: 发现 `git pull` 冲突时，优先保留 `database/` 与 `reports/` 的本地最新版本。
2. **端口失效**: 若 Web 端口无法访问，立即执行重启脚本并记录入 `LESSONS.md`。

---
**“隔离是为了绝对的自由，同步是为了绝对的准确。”** **签发人**: 首席架构师 Gemini ⚖️  
**接收人**: 工程师 Cheese 🧀