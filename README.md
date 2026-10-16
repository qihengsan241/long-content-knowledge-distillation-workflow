# 长内容知识脱水工作流

一个本地运行的 Codex Skill，将长文章、字幕、转录稿和手动文本统一整理为标准逐字稿，拼接固定知识脱水 Prompt，并可选调用 OpenAI-compatible API，最终输出适合保存到 Obsidian 的 Markdown。

> 当前发布版本：`v0.5.1`

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
→ DeepSeek / OpenAI-compatible API 或手动处理
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
- 调用 DeepSeek 或其他 OpenAI-compatible API
- 将结果包装为 Obsidian Markdown
- Streamlit 本地工作台

## 实验能力

以下能力受平台限制、本机环境、字幕可用性、Cookie、ffmpeg 或模型下载状态影响：

- YouTube 字幕自动提取
- `yt-dlp` 通用字幕与音频下载
- `faster-whisper` 本地音频/视频转写
- 抖音、B站、小红书、X 等平台链接处理

这些入口失败时，请回退到手动提供字幕、正文或本地转录稿。项目不会绕过登录、付费、私密内容或平台权限限制。

## 环境要求

- Python 3.10 或更高版本
- 本地音视频处理需要单独安装 `ffmpeg` 并加入 `PATH`
- 自动知识脱水需要使用者自己的 API Key

安装依赖：

```bash
python -m pip install -r requirements.txt
```

## 快速开始

启动本地工作台：

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

复制配置模板：

```powershell
Copy-Item .env.example .env
```

然后只在本机填写 `.env`。支持以下供应商模式：

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
