<div align="center">

# 🤖 AI Daily Digest

**全自动 AI 每日要闻 · 推送到微信 · 完全免费**

[![GitHub Actions](https://img.shields.io/badge/powered%20by-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![WeChat](https://img.shields.io/badge/推送-微信-07C160?logo=wechat&logoColor=white)](https://sct.ftqq.com)

每天自动从 **17+ 顶级 AI 信息源**（OpenAI、Anthropic、DeepMind、arXiv…）抓取资讯，  
用 **GPT-4o-mini** 生成中文摘要，通过 **Server酱** 免费推送到你的微信。  
Fork 即用，0 服务器，0 运维，**每月成本 ≈ ¥6**。

<img src="https://img.shields.io/badge/每月成本-≈¥6-success?style=for-the-badge" alt="cost">
<img src="https://img.shields.io/badge/服务器-0台-success?style=for-the-badge" alt="no server">
<img src="https://img.shields.io/badge/运维-0小时-success?style=for-the-badge" alt="no ops">

</div>

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🆓 **完全免费运行** | GitHub Actions 免费额度，Server酱 免费计划（每天 5 条够用） |
| 📱 **微信直达** | 通过 Server酱 推送到手机微信，无需公众号 |
| 🧠 **AI 智能摘要** | GPT-4o-mini / DeepSeek / Claude 三选一，一句话抓重点 |
| ⚙️ **一键个性化** | 只需编辑 `user_config.yaml`，改关注领域、推送时间、过滤规则 |
| 🏷️ **智能评分排序** | 关键词权重 + 来源权威度 + 时效性 + 个人兴趣，精准过滤噪音 |
| 🌐 **17+ 顶级信息源** | OpenAI、Anthropic、DeepMind、Meta AI、arXiv、量子位、机器之心… |
| 📁 **Markdown 存档** | 每次推送自动保存到 `archive/`，永久留存 |
| 🔌 **可扩展架构** | 轻松新增 RSS 源、切换 LLM 提供商、自定义推送时间 |

---

## 🚀 5 分钟快速上手

### 第一步：获取 Server酱 SendKey（2 分钟）

1. 打开 [sct.ftqq.com](https://sct.ftqq.com)，微信扫码登录
2. 进入「消息通道」→ 选择「微信服务号」→ 扫码关注
3. 复制页面顶部的 **SendKey**（格式：`SCT...`）

### 第二步：Fork 本仓库

点击右上角 **Fork** 按钮，Fork 到你自己的 GitHub 账号。

### 第三步：配置 GitHub Secrets

进入你 Fork 后的仓库 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 值 | 说明 |
|------------|---|------|
| `OPENAI_API_KEY` | `sk-...` | OpenAI API Key（或下方其他 LLM 的 Key） |
| `SERVERCHAN_KEY` | `SCT...` | 第一步复制的 SendKey |

> 💡 也可以用 DeepSeek（更便宜）或 Anthropic Claude，见下方[切换 LLM](#切换-llm)说明

### 第四步：个性化配置（可选但推荐）

编辑 `config/user_config.yaml`，自定义：
- 推送时间（如改为 08:00 早起党）
- 个人关注领域（如加入 `"diffusion model"` 等）
- 过滤规则（屏蔽词、最少分数、条目数量）

### 第五步：生成 Workflow 文件并推送

```bash
# 本地执行一次，将时间配置转换为 GitHub Actions cron
python scripts/gen_workflows.py
git add .github/workflows/
git commit -m "init: setup schedules"
git push
```

> 如果你只想用默认 09:00 推送，可以直接用仓库里已有的 workflow 文件，跳过这步。

### 第六步：手动触发测试

GitHub 仓库 → **Actions** → 选择对应 workflow → **Run workflow** → 查看执行日志  
微信收到消息 = 配置成功 🎉

---

## 📱 推送效果预览

```
🌅 早间要闻 · 2026-03-19  共12条

📋 今日概述
今日 AI 领域最重要的进展是 OpenAI 发布 GPT-5，在多项基准测试中
全面超越前代。与此同时，Anthropic 推出 Claude 3.7 Sonnet 并开放 API…

---

🔥🔥🔥 重大突破

1. GPT-5 正式发布，多项 SOTA
   支持 200K 上下文，代码能力提升 40%，API 已开放。
   🔥🔥🔥  📰 OpenAI Blog  🕐 2小时前  🔗 原文

---

⭐⭐ 值得关注

2. DeepSeek R2 论文开源
   推理模型新架构，在数学竞赛题上超越 o3-mini。
   ⭐⭐  📰 arXiv cs.LG  🕐 5小时前  🔗 原文
…
```

---

## ⚙️ 个性化配置指南

所有个性化设置都在 `config/user_config.yaml` 中完成，**无需改任何代码**。

### 修改推送时间

```yaml
schedule:
  - time: "08:00"        # 改为你想要的时间（北京时间）
    lookback_hours: 24
    label: "☀️ 早安要闻"
    enabled: true

  - time: "21:00"        # 新增一个晚间推送
    lookback_hours: 12
    label: "🌙 晚间精选"
    enabled: true         # 设为 true 启用
```

修改后运行 `python scripts/gen_workflows.py` 重新生成 workflow。

### 添加个人关注领域

```yaml
personal_interests:
  - "diffusion model"       # 扩散模型
  - "embodied AI"           # 具身智能
  - "code generation"       # 代码生成
  - "multimodal"            # 多模态
```

匹配到这些词的文章将额外 **+8 分**，确保不会错过。

### 只看学术论文

```yaml
filter:
  include_tags: ["academic"]   # 只保留 arXiv 等学术来源
```

### 添加新的 RSS 源

编辑 `config/sources.yaml`：

```yaml
  - name: "Cohere Blog"
    url: "https://cohere.com/blog/rss"
    priority: high
    tags: ["official"]
```

### 切换 LLM

**使用 DeepSeek（更便宜，同样好用）：**

```yaml
llm:
  provider: "deepseek"
  model: "deepseek-chat"
```

在 GitHub Secrets 中添加 `DEEPSEEK_API_KEY` 即可。

**使用 Anthropic Claude：**

```yaml
llm:
  provider: "anthropic"
  model: "claude-3-haiku-20240307"
```

---

## 📊 信息源列表

| 来源 | 类型 | 优先级 |
|------|------|--------|
| OpenAI Blog | 官方 | 🔴 Critical |
| Anthropic News | 官方 | 🔴 Critical |
| Google DeepMind | 官方 | 🔴 Critical |
| Meta AI Blog | 官方 | 🔴 Critical |
| Hugging Face Blog | 官方/开源 | 🟡 High |
| arXiv cs.AI | 学术 | 🟡 High |
| arXiv cs.LG | 学术 | 🟡 High |
| Microsoft Research | 官方 | 🟡 High |
| Mistral AI | 官方 | 🟡 High |
| TechCrunch AI | 媒体 | 🟢 Medium |
| VentureBeat AI | 媒体 | 🟢 Medium |
| MIT Technology Review | 媒体/学术 | 🟢 Medium |
| The Verge AI | 媒体 | 🟢 Medium |
| Hacker News AI | 社区 | 🟢 Medium |
| 量子位 | 中文媒体 | 🟢 Medium |
| 机器之心 | 中文媒体 | 🟢 Medium |
| xAI Blog | 官方 | 🟡 High |

---

## 💰 成本说明

| 项目 | 费用 |
|------|------|
| GitHub Actions | **免费**（公开仓库无限制） |
| Server酱 | **免费**（每天 5 条，每次推送合并后 1~2 条） |
| OpenAI API（每次约 50k tokens） | **约 ¥0.2/次** |
| 服务器 / 域名 | **$0** |
| **合计（每天1次推送）** | **约 ¥6/月** |

> 切换到 DeepSeek 可降低至 **约 ¥1/月**。

---

## 🏗️ 项目架构

```
ai-daily-digest/
├── .github/workflows/       # GitHub Actions（由 gen_workflows.py 自动生成）
│   └── push_0900.yml
├── src/
│   ├── fetcher.py           # 异步 RSS 抓取
│   ├── filter.py            # 去重 + 评分 + 过滤
│   ├── summarizer.py        # LLM 摘要生成
│   ├── notifier.py          # Server酱 微信推送
│   └── utils.py             # 工具函数
├── config/
│   ├── sources.yaml         # RSS 源列表（含 tags）
│   ├── keywords.yaml        # 关键词权重
│   └── user_config.yaml     # ⭐ 个性化配置（主要改这个）
├── archive/                 # 每次推送的 Markdown 存档
├── data/
│   └── seen_urls.json       # URL 去重记录
├── scripts/
│   └── gen_workflows.py     # 从配置生成 workflow 文件
├── main.py                  # 入口
└── requirements.txt
```

### 评分算法

```
score = keyword_score × source_weight + recency_bonus + personal_bonus

keyword_score:  在 title + summary(前200字) 中匹配 keywords.yaml
  critical 词   → +10/个
  high 词       → +5/个
  medium 词     → +2/个

source_weight:  critical=1.0  high=0.8  medium=0.5

recency_bonus:  <3h → +5  |  <6h → +3  |  <12h → +1

personal_bonus: 每匹配一个 personal_interests 词 → +8
```

---

## 🛠️ 本地开发 & 测试

```bash
# 克隆仓库
git clone https://github.com/你的用户名/ai-daily-digest.git
cd ai-daily-digest

# 安装依赖
pip install -r requirements.txt

# 配置 API Keys
cp .env.example .env
# 编辑 .env 填入真实 Key

# 手动触发第 0 个时间段（09:00 早间要闻）
python main.py --schedule-index 0

# 触发第 1 个时间段（如果启用了）
python main.py --schedule-index 1
```

---

## 🤝 Contributing

欢迎贡献！以下是常见的扩展方向：

- 新增更多 RSS 信息源（PR 格式：在 `sources.yaml` 添加，附说明）
- 适配新的 LLM 提供商
- 支持其他推送渠道（Telegram、Email、Slack…）
- 改进评分算法

---

## 📄 License

[MIT](LICENSE) — 自由使用，记得 Star ⭐

---

<div align="center">

**如果这个项目对你有帮助，请点个 Star ⭐ 让更多人发现它！**

Made with ❤️ and ☕

</div>
