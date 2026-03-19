
# AI Daily Digest — 微信推送版完整实现规格文档
> 本文档用于直接交给 Cursor 实现，请完整阅读后按模块顺序开发

---

## 0. 项目概述

构建一个 **全自动 AI 每日要闻聚合工具**：
- 运行在 **GitHub Actions**（免费，无需服务器）
- 通过 **微信**（Server酱）推送到手机
- 支持每位用户**个性化配置**：推送次数、推送时间、关注话题、屏蔽词等
- 支持手动触发（用于测试）
- 代码完全开源，clone 后只需填写配置即可运行

---

## 1. 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 运行环境 | GitHub Actions (ubuntu-latest, Python 3.12) | 免费，无需服务器 |
| HTTP 客户端 | `httpx` + `asyncio` | 异步并发抓取 |
| RSS 解析 | `feedparser` | 成熟稳定 |
| LLM 摘要 | OpenAI API (`gpt-4o-mini`) | 可配置切换 |
| 微信推送 | **Server酱 (ftqq.com)** | 免费，绑定微信服务号，一行代码发送 |
| 配置管理 | YAML 文件 | 用户直接编辑，无需改代码 |
| 数据持久化 | JSON 文件 commit 进仓库 | 去重记录 |

### 为什么选 Server酱？
- 免费套餐每天 5 条消息，足够日常使用
- 无需开发微信公众号，扫码绑定即可
- API 极简：一个 POST 请求即完成推送
- 支持 Markdown 渲染（微信内查看格式化内容）

---

## 2. 目录结构

```
ai-daily-digest/
├── .github/
│   └── workflows/
│       ├── push_0600.yml      # 根据用户配置自动生成的 workflow
│       ├── push_1200.yml
│       └── push_1800.yml
├── src/
│   ├── __init__.py
│   ├── fetcher.py             # RSS 抓取模块
│   ├── filter.py              # 过滤与评分模块
│   ├── summarizer.py          # LLM 摘要模块
│   ├── notifier.py            # 微信推送模块（Server酱）
│   └── utils.py               # 公共工具函数
├── config/
│   ├── sources.yaml           # RSS 信息源列表（含分组 tag）
│   ├── keywords.yaml          # 关键词权重（含用户自定义区块）
│   └── user_config.yaml       # ⭐ 核心：所有个性化配置集中在此
├── archive/
│   └── .gitkeep               # 每日摘要 Markdown 存档
├── data/
│   └── seen_urls.json         # URL 去重记录
├── scripts/
│   └── gen_workflows.py       # 根据 user_config 自动生成 workflow 文件
├── main.py                    # 主入口
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. 核心设计：`user_config.yaml`

**这是整个项目可扩展性的核心文件，所有个性化选项都在此配置，用户无需改动任何代码。**

```yaml
# ============================================================
#  AI Daily Digest · 个人配置文件
#  修改此文件后，commit 并 push，GitHub Actions 自动生效
# ============================================================

# ── 推送计划 ──────────────────────────────────────────────
# 支持配置多个推送时间段，每个时间段独立抓取、独立推送
# time: 北京时间，HH:MM 格式
# lookback_hours: 该时间段往回抓多少小时的内容（建议与推送间隔一致）
# label: 推送消息的标题前缀

schedule:
  - time: "09:00"
    lookback_hours: 24
    label: "🌅 早间要闻"
    enabled: true

  - time: "18:00"
    lookback_hours: 9
    label: "🌆 晚间速报"
    enabled: false          # 设为 false 即禁用此时段

  - time: "22:00"
    lookback_hours: 4
    label: "🌙 深夜简报"
    enabled: false


# ── 内容过滤 ──────────────────────────────────────────────

filter:
  # 每次推送最多发送的条目数（建议 5~20）
  max_items: 12

  # 最低评分阈值，低于此分数的条目直接丢弃（0 = 不过滤）
  min_score: 3

  # 屏蔽词：标题或摘要中包含以下词的条目直接跳过（不区分大小写）
  block_keywords:
    - "sponsored"
    - "advertisement"
    - "crypto"
    - "NFT"

  # 只看这些来源 tag（留空 = 看全部）
  # 可用 tag 见 sources.yaml 中每个源的 tags 字段
  include_tags: []
  # 示例：只看学术和官方博客
  # include_tags: ["academic", "official"]

  # 排除这些来源 tag
  exclude_tags: []
  # 示例：不看媒体报道
  # exclude_tags: ["media"]


# ── 个人关注方向 ──────────────────────────────────────────
# 在标准关键词权重之外，额外加权你个人关注的方向
# 命中这里的词会额外 +8 分（可在 filter.py 中调整）

personal_interests:
  - "RLHF"
  - "alignment"
  - "mechanistic interpretability"
  - "reasoning"
  - "agent"
  # 根据自己研究方向自由增删


# ── LLM 配置 ──────────────────────────────────────────────

llm:
  # 可选: openai / deepseek / anthropic
  provider: "openai"
  model: "gpt-4o-mini"
  summary_language: "zh"      # zh = 中文摘要, en = 英文摘要
  # 单条摘要最大字数
  max_summary_chars: 60
  # 是否生成今日综述（会多消耗约 500 tokens）
  generate_overview: true


# ── 推送格式 ──────────────────────────────────────────────

display:
  # 是否在微信消息中显示原文链接
  show_links: true
  # 是否显示评分星级
  show_stars: true
  # 是否显示来源名称
  show_source: true
  # 是否显示发布时间
  show_time: true
  # 分档阈值（score）
  tier_thresholds:
    critical: 15   # score >= 15 → ⭐⭐⭐
    high: 8        # score >= 8  → ⭐⭐
    # 其余          →  ⭐
```

---

## 4. `config/sources.yaml`

每个源增加 `tags` 字段，配合 `user_config.yaml` 的 `include_tags` / `exclude_tags` 实现来源过滤。

```yaml
sources:
  - name: "OpenAI Blog"
    url: "https://openai.com/blog/rss.xml"
    priority: critical
    tags: ["official", "openai"]

  - name: "Anthropic News"
    url: "https://www.anthropic.com/news/rss.xml"
    priority: critical
    tags: ["official", "anthropic"]

  - name: "Google DeepMind"
    url: "https://deepmind.google/blog/rss.xml"
    priority: critical
    tags: ["official", "google"]

  - name: "Meta AI Blog"
    url: "https://ai.meta.com/blog/feed/"
    priority: critical
    tags: ["official", "meta"]

  - name: "Microsoft Research"
    url: "https://www.microsoft.com/en-us/research/feed/"
    priority: high
    tags: ["official", "microsoft"]

  - name: "Mistral AI"
    url: "https://mistral.ai/news/rss.xml"
    priority: high
    tags: ["official"]

  - name: "xAI Blog"
    url: "https://x.ai/blog/rss.xml"
    priority: high
    tags: ["official"]

  - name: "Hugging Face Blog"
    url: "https://huggingface.co/blog/feed.xml"
    priority: high
    tags: ["official", "open-source"]

  - name: "arXiv cs.AI"
    url: "http://arxiv.org/rss/cs.AI"
    priority: high
    tags: ["academic"]

  - name: "arXiv cs.LG"
    url: "http://arxiv.org/rss/cs.LG"
    priority: high
    tags: ["academic"]

  - name: "TechCrunch AI"
    url: "https://techcrunch.com/tag/artificial-intelligence/feed/"
    priority: medium
    tags: ["media"]

  - name: "VentureBeat AI"
    url: "https://venturebeat.com/category/ai/feed/"
    priority: medium
    tags: ["media"]

  - name: "MIT Technology Review"
    url: "https://www.technologyreview.com/feed/"
    priority: medium
    tags: ["media", "academic"]

  - name: "The Verge AI"
    url: "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
    priority: medium
    tags: ["media"]

  - name: "Hacker News AI"
    url: "https://hnrss.org/newest?q=AI+LLM&points=50"
    priority: medium
    tags: ["community"]

  - name: "量子位"
    url: "https://www.qbitai.com/feed"
    priority: medium
    tags: ["media", "chinese"]

  - name: "机器之心"
    url: "https://www.jiqizhixin.com/rss"
    priority: medium
    tags: ["media", "chinese"]
```

---

## 5. `config/keywords.yaml`

```yaml
keywords:
  critical:          # 权重: 10
    - "model release"
    - "open source"
    - "open weights"
    - "benchmark"
    - "SOTA"
    - "AGI"
    - "reasoning"
    - "multimodal"
    - "GPT"
    - "Claude"
    - "Gemini"
    - "Llama"
    - "Mistral"
    - "DeepSeek"
    - "Qwen"

  high:              # 权重: 5
    - "fine-tuning"
    - "alignment"
    - "RLHF"
    - "inference"
    - "training"
    - "funding"
    - "acquisition"
    - "agent"
    - "RAG"
    - "context window"

  medium:            # 权重: 2
    - "regulation"
    - "safety"
    - "partnership"
    - "deployment"
    - "API"

# 注意：个人关注词在 user_config.yaml 的 personal_interests 中配置
# 不要在此处重复添加
```

---

## 6. 各模块详细实现规格

### 6.1 `src/fetcher.py`

**功能**：并发抓取所有 RSS 源，返回原始条目列表

**实现要求**：
- 读取 `config/sources.yaml`，根据 `user_config.yaml` 中的 `include_tags` / `exclude_tags` 过滤源列表
- 使用 `asyncio` + `httpx.AsyncClient` 并发请求，超时 **10秒**
- 单个源失败时静默跳过，打印警告
- 每条返回条目结构：

```python
{
    "title": str,
    "url": str,
    "summary": str,           # RSS 原始摘要，arXiv 保留完整摘要
    "published": datetime,    # 统一转为 UTC-aware datetime
    "source_name": str,
    "source_priority": str,   # critical / high / medium
    "source_tags": list[str], # 来源的 tags，如 ["academic"]
}
```

**时间解析**：`feedparser` 返回的 `time_struct` 用 `datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)` 转换，解析失败时回退到 `datetime.now(timezone.utc)`

---

### 6.2 `src/filter.py`

**功能**：去重、时间过滤、评分、屏蔽词过滤、排序

**实现要求**：

**步骤一：时间过滤**
- 接收参数 `lookback_hours`（从 `user_config.yaml` 对应时段读取）
- 只保留 `published` 在 `lookback_hours` 内的条目

**步骤二：URL 去重**
- 加载 `data/seen_urls.json`，格式：
```json
{
  "urls": [
    {"url": "https://...", "date": "2026-03-19"},
    ...
  ]
}
```
- 过滤已见过的 URL
- 处理完成后追加新 URL，**只保留最近7天**的记录

**步骤三：屏蔽词过滤**
- 读取 `user_config.yaml` → `filter.block_keywords`
- 标题或摘要中包含任意屏蔽词（不区分大小写）的条目直接丢弃

**步骤四：评分**

```
base_score = keyword_score × source_weight + recency_bonus + personal_bonus

keyword_score:
  遍历 title + summary（前200字），匹配 keywords.yaml
  critical 命中 → +10/词
  high 命中     → +5/词
  medium 命中   → +2/词

source_weight:
  critical → 1.0 | high → 0.8 | medium → 0.5

recency_bonus:
  Δt < 3h  → +5
  Δt < 6h  → +3
  Δt < 12h → +1
  其他      → +0

personal_bonus:
  遍历 user_config.personal_interests，每命中一词 → +8
```

**步骤五：最低分过滤 + 排序截断**
- 丢弃 `score < user_config.filter.min_score` 的条目
- 按 score 降序，截取前 `user_config.filter.max_items` 条

---

### 6.3 `src/summarizer.py`

**功能**：调用 LLM 生成中文摘要和今日综述

**Provider 路由**（根据 `user_config.llm.provider`）：

```python
# openai / deepseek 使用相同的 openai 库，只需切换 base_url 和 key
providers = {
    "openai":   {"base_url": "https://api.openai.com/v1",        "key_env": "OPENAI_API_KEY"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1",      "key_env": "DEEPSEEK_API_KEY"},
    "anthropic":{"base_url": None,  "key_env": "ANTHROPIC_API_KEY"},  # 单独处理
}
```

**单条摘要 System Prompt**：
```
你是一位 AI 领域的资深研究员，正在为同行整理每日要闻。
请根据以下新闻的标题和摘要，用{language}生成一句话要点（不超过{max_chars}字）。
要求：
1. 直接说核心信息，不要说"本文介绍了"之类的废话
2. 如果是模型发布，必须包含模型名称和最关键的性能指标或特性
3. 如果是论文，必须包含方法名和核心贡献
4. 如果是商业新闻，说明金额/合作方/战略意义
```

**今日综述 Prompt**（仅 `generate_overview: true` 时调用）：
```
以下是今天 AI 领域的 {n} 条要闻摘要，请用 3-5 句话写一段今日综述，
指出最重要的趋势或事件，语言简洁专业，面向 AI 研究员。
```

**降级处理**：任意 API 调用失败时，返回 `summary` 字段前 `max_chars` 字，不中断整体流程

---

### 6.4 `src/notifier.py`

**功能**：通过 Server酱将内容推送到微信

**Server酱 API**：
```
POST https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send
Body (form-data):
  title: str   # 消息标题，≤32字
  desp:  str   # 消息正文，Markdown 格式，≤32KB
```

**消息结构设计**（考虑 Server酱免费版每天5条限制，合并为1~2条发送）：

**当条目 ≤ 10 条时**：合并为 1 条消息发送

**当条目 > 10 条时**：拆为 2 条消息（前半 + 后半）

**消息 title**（来自 `user_config.schedule[i].label`）：
```
🌅 早间要闻 · 2026-03-19 · 共12条
```

**消息 desp 格式**（Markdown）：

```markdown
## 📋 今日综述
{overall_summary}

---

## ⭐⭐⭐ 重大进展

**1. {title}**
{summary_zh}
📌 {source_name} · {时间描述}{" · [原文](" + url + ")" if show_links}

**2. {title}**
...

---

## ⭐⭐ 值得关注

...

---

## ⭐ 行业动态

...

---
*由 AI Daily Digest 自动生成 · {timestamp}*
```

**时间描述**格式：
- `< 1h` → "刚刚"
- `< 24h` → "N小时前"
- 其他 → "昨天"

**display 选项**：根据 `user_config.display` 中的开关决定是否渲染对应字段（链接、星级、来源、时间）

---

### 6.5 `src/utils.py`

提供以下公共函数：

```python
def load_yaml(path: str) -> dict
def load_user_config() -> dict          # 加载并验证 user_config.yaml
def get_enabled_schedules() -> list     # 返回 enabled=true 的时段列表
def get_beijing_time() -> datetime      # 返回当前北京时间
def format_time_delta(dt: datetime) -> str  # 返回"3小时前"格式
def save_seen_urls(urls: list)          # 带7天清理的写入
def load_seen_urls() -> set             # 返回 url 字符串集合
```

---

### 6.6 `main.py`

接收命令行参数 `--schedule-index`，用于区分不同时段的 workflow 调用：

```python
# 调用方式:
# python main.py --schedule-index 0   # 执行第0个时段（09:00 早间要闻）
# python main.py --schedule-index 1   # 执行第1个时段（18:00 晚间速报）

async def main(schedule_index: int):
    user_cfg = load_user_config()
    schedule = user_cfg["schedule"][schedule_index]

    # 1. 加载信息源（按 include/exclude tags 过滤）
    sources = load_sources_with_filter(user_cfg)

    # 2. 并发抓取
    raw_items = await fetch_all(sources)

    # 3. 过滤 & 评分（传入当前时段的 lookback_hours）
    filtered = filter_and_score(raw_items, user_cfg, lookback_hours=schedule["lookback_hours"])

    # 4. LLM 摘要
    items = await summarize_all(filtered, user_cfg)
    overview = await generate_overview(items, user_cfg) if user_cfg["llm"]["generate_overview"] else ""

    # 5. 存档
    save_archive(items, overview, schedule["label"])

    # 6. 微信推送
    await send_wechat(items, overview, schedule, user_cfg)
```

---

## 7. GitHub Actions Workflow 设计

### 核心思路
每个**启用的推送时段**对应一个独立的 `.yml` 文件，通过 `scripts/gen_workflows.py` 根据 `user_config.yaml` 自动生成，用户无需手动改 YAML。

### `scripts/gen_workflows.py`

```
功能：读取 user_config.yaml 中 enabled=true 的时段，
     为每个时段生成对应的 .github/workflows/push_{HHMM}.yml 文件

调用时机：用户修改 user_config.yaml 后，在本地运行一次：
  python scripts/gen_workflows.py
  git add .github/workflows/
  git commit -m "update schedules"
  git push
```

**生成的 workflow 模板**（以 09:00 为例）：

```yaml
# 此文件由 scripts/gen_workflows.py 自动生成，请勿手动修改
name: "🌅 早间要闻 (09:00)"

on:
  schedule:
    - cron: '0 1 * * *'      # UTC 01:00 = 北京 09:00
  workflow_dispatch:
    inputs:
      schedule_index:
        description: '时段序号'
        default: '0'

jobs:
  digest:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install -r requirements.txt

      - name: Run digest
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SERVERCHAN_KEY: ${{ secrets.SERVERCHAN_KEY }}
        run: python main.py --schedule-index 0

      - name: Commit data
        run: |
          git config user.name "digest-bot"
          git config user.email "bot@digest.local"
          git add data/seen_urls.json archive/
          git diff --staged --quiet || git commit -m "📰 早间要闻 $(date +%Y-%m-%d)"
          git push
```

**时区换算表**（`gen_workflows.py` 内置）：
```python
BEIJING_TO_UTC = {
    "06:00": "22 * * * *",  # 前一天 UTC 22:00
    "07:00": "23 * * * *",
    "08:00": "0 0 * * *",
    "09:00": "0 1 * * *",
    "12:00": "0 4 * * *",
    "18:00": "0 10 * * *",
    "20:00": "0 12 * * *",
    "22:00": "0 14 * * *",
    # 可按需扩展
}
```

---

## 8. `.env.example`

```bash
# ── LLM（必填其一）──
OPENAI_API_KEY=sk-...
# DEEPSEEK_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-...

# ── 微信推送（必填）──
# 获取方式：https://sct.ftqq.com 登录后在「消息通道」获取 SendKey
SERVERCHAN_KEY=SCT...
```

---

## 9. `requirements.txt`

```
feedparser==6.0.11
httpx==0.27.0
openai==1.30.0
pyyaml==6.0.1
python-dotenv==1.0.1
```

---

## 10. 部署步骤（README 核心内容）

### 第一步：获取 Server酱 SendKey（5分钟）
1. 访问 [sct.ftqq.com](https://sct.ftqq.com)，微信扫码登录
2. 进入「消息通道」→ 选择「微信服务号」→ 扫码关注
3. 复制页面上的 **SendKey**（格式：`SCT...`）

### 第二步：Fork 仓库到自己的 GitHub

### 第三步：配置 GitHub Secrets
仓库 → Settings → Secrets and variables → Actions → New repository secret：
- `OPENAI_API_KEY`（或对应 provider 的 key）
- `SERVERCHAN_KEY`

### 第四步：个性化配置
编辑 `config/user_config.yaml`，按需调整推送时间、关注方向、屏蔽词等

### 第五步：生成 Workflow 文件
```bash
# 本地执行一次，将你的时间配置转换为 GitHub Actions cron
python scripts/gen_workflows.py
git add .github/workflows/
git commit -m "init: setup schedules"
git push
```

### 第六步：手动触发测试
GitHub 仓库 → Actions → 选择任意 workflow → Run workflow
微信收到消息即部署成功 ✅

---

## 11. 可扩展性设计总结

| 用户想做的事 | 操作方式 |
|-------------|---------|
| 改推送时间 | 改 `user_config.yaml` → 重跑 `gen_workflows.py` |
| 增加一个推送时段 | 在 `schedule` 下加一条 → 重跑 `gen_workflows.py` |
| 只看学术论文 | `include_tags: ["academic"]` |
| 屏蔽某类内容 | 在 `block_keywords` 中添加 |
| 加自己的研究兴趣词 | 在 `personal_interests` 中添加 |
| 换 LLM 服务商 | 改 `llm.provider` 和对应 Secret |
| 增加新的 RSS 源 | 在 `sources.yaml` 中添加一条 |
| 不想要综述只看条目 | `generate_overview: false` |
| 不显示原文链接 | `display.show_links: false` |

---

## 12. 成本估算

| 项目 | 费用 |
|------|------|
| GitHub Actions | **免费**（公开仓库） |
| Server酱 | **免费**（每天 5 条，足够用） |
| OpenAI API（每日约 50k tokens） | **约 ¥0.2/天** |
| 服务器 / 域名 | **$0** |
| **合计** | **约 ¥6/月** |
