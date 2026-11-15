# 长内容知识脱水工作流

一个本地运行的 Codex Skill，将长文章、字幕、转录稿和手动文本统一整理为标准逐字稿，拼接固定知识脱水 Prompt，并可选调用 OpenAI-compatible API，最终输出适合保存到 Obsidian 的 Markdown。

> 当前本地版本：`v0.6`

## 核心原则

- 必须先获得真实字幕、逐字稿或正文，不能根据标题、简介、评论脑补内容。
- 知识脱水 Prompt 作为独立资源文件保存，不硬编码在 Python 中。
- 手动流程始终保留；API 调用失败时可以复制最终提示词到大模型网页端处理。
- 默认不提交 `.env`、API Key、Cookie、真实资料、运行输出或缓存。

## 稳定流程

```text
手动粘贴 / 本地文件 / 网页文章
→ 标准逐字稿 Markdown + JSON
→ 最终提示词
→ 当前 Codex、手动处理或可选 OpenAI-compatible API
→ 知识脱水结果
→ Obsidian Markdown
```

已经验证的主要能力：

- 手动粘贴长文本
- 导入 `.txt`、`.md`、`.srt`、`.vtt`
- 使用 `trafilatura` 提取网页文章正文
- 标准化时间戳与无时间戳文本
- 生成统一逐字稿 JSON 和 Markdown
- 拼接知识脱水 Prompt
- 可由当前 Codex 直接执行知识脱水，也可选调用 DeepSeek 或其他 OpenAI-compatible API
- 将结果包装为 Obsidian Markdown
- Streamlit 本地工作台
- YouTube 字幕优先路由：字幕 Skill / 插件 → youtube-transcript-api → yt-dlp → 本地媒体转写
- faster-whisper 自动选择 CUDA/CPU，CUDA 不可用时回退 CPU
- 外部硬字幕 OCR 路线：Video Subtitle Extractor 导出 SRT 后导入

## 实验能力

以下能力受平台限制、本机环境、字幕可用性、Cookie、ffmpeg 或模型下载状态影响：

- YouTube 字幕自动提取
- `yt-dlp` 通用字幕与音频下载
- `faster-whisper` 本地音频/视频转写的真实媒体验收
- 抖音、B站、小红书、X 等平台链接处理

这些入口失败时，请回退到手动提供字幕、正文或本地转录稿。项目不会根据标题、简介、评论或弹幕生成逐字稿，也不会绕过登录、付费、私密内容或平台权限限制。

## 环境要求

- Python 3.10 或更高版本
- 本地音视频处理需要单独安装 `ffmpeg` 并加入 `PATH`
- 自动 API 路线需要使用者自己的 API Key；在 Codex 会话中也可以直接按固定 Prompt 处理，无需额外 API

安装依赖：

```bash
python -m pip install -r requirements.txt
```

## 快速开始

默认使用无网页自动流程：

```powershell
.\.venv\Scripts\python.exe "脚本\自动知识脱水.py" "文章链接或本地文件路径"
```

每次任务会在 `C:\AI\Outputs\长内容知识脱水工作流\Codex` 下创建独立目录，并自动生成逐字稿、最终提示词、知识脱水结果、模型调用日志和黑曜石笔记。

Streamlit 本地工作台仅作为兼容备用：

```bash
streamlit run 前端/知识脱水工作台.py
```

或者使用稳定的命令行手动流程：

```bash
python 脚本/导入文本文件.py "资料/我的测试文本.md"
python 脚本/生成最终提示词.py
python 脚本/保存知识脱水结果.py
python 脚本/整理为黑曜石文件.py
```

输出文件位于 `输出/`：

- `逐字稿.md`
- `逐字稿.json`
- `最终提示词.md`
- `知识脱水结果.md`
- `模型调用日志.md`
- `黑曜石笔记.md`

## API 配置

当前 Codex 本机配置保存在私密状态目录，不放入 Git 项目：

```text
C:\AI\Private\AgentState\Codex\长内容知识脱水工作流\.env
```

可以用 `--env` 或环境变量 `KNOWLEDGE_DISTILLATION_ENV_FILE` 指定其他私密配置路径。支持以下供应商模式：

- `openai`
- `deepseek`
- `custom`，用于 OpenAI-compatible 服务

不要提交、分享或记录 API Key。仓库中的配置示例不包含真实凭据。

## 安装为 Codex Skill

将整个仓库文件夹放入 Codex Skills 目录，保持文件夹名为：

```text
long-content-knowledge-distillation-workflow
```

Codex 会从根目录的 `SKILL.md` 读取技能说明。完整使用方法见 [使用说明.md](使用说明.md)。

## 目录结构

```text
long-content-knowledge-distillation-workflow/
├── SKILL.md
├── agents/
├── 前端/
├── 脚本/
├── 核心模块/
├── 提取器/
├── 资源/
├── 示例/
├── 资料/
└── 输出/
```

## 安全说明

- `.env`、Cookie、用户资料和输出目录已通过 `.gitignore` 排除。
- Cookie 只允许用于本人有权限正常访问的内容，不应上传、打印或写入日志。
- 使用不可信中转站前，请自行评估隐私、合规、计费和稳定性风险。
- 发布包不包含模型文件、浏览器会话、缓存或真实处理结果。

## 许可证

本项目使用 [MIT License](LICENSE)。
