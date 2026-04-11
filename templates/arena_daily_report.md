# 🏟️ 琥珀引擎演武场实战报告

**报告日期**: {{ report_date }} (T日)  
**生成时间**: {{ generated_at }}  
**报告编号**: {{ report_id }}  
**状态**: {{ report_status }}  

---

## 📊 一、持仓损益总览

### 资金状态
- **初始资金**: {{ initial_capital }} CNY
- **当前资本**: {{ current_capital }} CNY
- **总收益率**: {{ total_return_pct }}% {{ total_return_emoji }}
- **现金储备**: {{ cash_reserve_pct }}% ({{ cash_reserve_amount }} CNY)
- **风险资产**: {{ risk_asset_pct }}% ({{ risk_asset_amount }} CNY)

### 绩效指标
- **年化收益率**: {{ annualized_return }}%
- **夏普比率**: {{ sharpe_ratio }}
- **最大回撤**: {{ max_drawdown }}%
- **胜率**: {{ win_rate }}%

---

## 📋 二、持仓明细 (按盈亏排序)

| 代码 | 名称 | 行业 | 持仓数量 | 成本均价 | 当前价格 | 持仓市值 | 累计盈亏 | 盈亏率 | 在仓天数 | 状态 |
|------|------|------|----------|----------|----------|----------|----------|--------|----------|------|
{% for position in positions %}
| {{ position.ticker }} | {{ position.name }} | {{ position.sector }} | {{ position.quantity }} | {{ position.avg_cost }} | {{ position.current_price }} | {{ position.market_value }} | {{ position.unrealized_pnl }} {{ position.pnl_emoji }} | {{ position.unrealized_pnl_pct }}% | {{ position.days_in_position }} | {{ position.status }} |
{% endfor %}

*注：{{ pnl_emoji_legend }}*

---

## 🚀 三、新晋标的解析

{% if new_entries %}
### 新进入1队标的
{% for entry in new_entries if entry.team == "1队" %}
- **{{ entry.ticker }} {{ entry.name }}**: {{ entry.reason }} (共振评分: {{ entry.resonance_score }})
{% endfor %}

### 新进入2队标的  
{% for entry in new_entries if entry.team == "2队" %}
- **{{ entry.ticker }} {{ entry.name }}**: {{ entry.reason }} (共振评分: {{ entry.resonance_score }})
{% endfor %}
{% else %}
**今日无新晋标的**
{% endif %}

---

## 🔄 四、调仓操作复盘

{% if transactions_today %}
### 今日交易记录
| 时间 | 操作 | 代码 | 名称 | 数量 | 价格 | 金额 | 原因 |
|------|------|------|------|------|------|------|------|
{% for tx in transactions_today %}
| {{ tx.timestamp }} | {{ tx.action }} | {{ tx.ticker }} | {{ tx.name }} | {{ tx.quantity }} | {{ tx.price }} | {{ tx.total_amount }} | {{ tx.reason }} |
{% endfor %}
{% else %}
**今日无调仓操作**
{% endif %}

### 强制止损检查
- **单日止损线**: -10% ({{ stop_loss_daily_check }})
- **累计止损线**: -15% ({{ stop_loss_total_check }})
- **锁仓状态**: {{ lock_status_summary }}

---

## 🧠 五、评委中控点评

### 算法权重分布 (前日→今日)
{% for algo in algorithm_changes %}
- **{{ algo.name }}**: {{ algo.previous_weight }}% → {{ algo.current_weight }}% ({{ algo.change_direction }} {{ algo.change_value }}%)
{% endfor %}

### 市场情绪评估
{{ market_sentiment_comment }}

### 共振引擎表现
- **平均共振评分**: {{ avg_resonance_score }}
- **信号分布**: {{ signals_distribution }}
- **Top策略**: {{ top_strategies }}

---

## ⚠️ 六、风险提示

### 数据完整性检查
{{ data_integrity_check }}

### 系统状态
{{ system_status_check }}

### 后续关注
{{ follow_up_actions }}

---

**报告生成**: 琥珀引擎演武场报告生成器 V1.0  
**数据来源**: virtual_fund.json + Tushare Pro API + 共振报告  
**更新频率**: T+1日 08:30 (GMT+8)  
**法典依据**: ARENA-SOP.md V2.1 + OPERATIONS.md V1.0  

> "数据不撒谎，逻辑在进化。盈亏是算法的终极审判官。"