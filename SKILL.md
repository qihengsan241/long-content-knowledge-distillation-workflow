---
name: long-content-knowledge-distillation-workflow
description: 自动处理长内容知识脱水。Use when the user provides a URL, subtitle/transcript, article, local audio/video, or long text and asks for “脱水” or an Obsidian-ready knowledge note. Obtain real text, standardize it, combine it with the fixed prompt, call the configured DeepSeek-compatible API, and return the generated file path. Never continue from only a title, summary, comment, or description.
---

# 长内容知识脱水工作流

使用这个 Skill 时，按“文本提取 -> 逐字稿标准化 -> Markdown/JSON 导出 -> 拼接最终提示词”的流程执行。

## 默认自动执行

当用户发送“链接/文件/正文 + 脱水”时，不要让用户打开网页工作台，也不要要求用户逐步运行命令。非 YouTube 输入直接调用：

```powershell
C:\AI\Projects\long-content-knowledge-distillation-workflow\.venv\Scripts\python.exe C:\AI\Projects\long-content-knowledge-distillation-workflow\脚本\自动知识脱水.py "输入"
```

- 链接或本地文件直接作为 `输入`。
- 用户粘贴的长文本优先通过标准输入传给脚本，避免把整段正文写进命令行。
- 每次任务写入 `C:\AI\Outputs\长内容知识脱水工作流\Codex\<时间>-auto-distillation`，不要覆盖上一次结果。
- 成功后向用户返回 `黑曜石笔记.md` 和本次输出目录。
- 没有获得真实正文或逐字稿时立即停止，不调用模型。
- 模型配置默认从 `C:\AI\Private\AgentState\Codex\长内容知识脱水工作流\.env` 读取；只检查是否存在，禁止读取、输出或记录 API Key。
- `前端/知识脱水工作台.py` 仅作为兼容备用，不是默认入口。

YouTube 输入使用下方“两层字幕入口”，不要让一键脚本在简约翻译插件之前直接进入 `yt-dlp`。

## YouTube 两层字幕入口

按以下顺序获取真实字幕，前一级成功后立即停止继续提取：

1. 运行 `脚本/提取YouTube字幕.py`，用 `youtube-transcript-api` 直接读取 YouTube 字幕轨；人工字幕优先，自动字幕次选。
2. 直读失败时，读取 `资源/工具说明/YouTube插件使用说明.md`，用 OpenCLI 检查真实 YouTube 页面。找到简约翻译注入的“下载字幕 (VTT)”可见按钮后下载到本次任务输出目录，再运行：

```powershell
python 脚本/导入文本文件.py "插件字幕.vtt" --来源链接 "YouTube链接" --平台 YouTube --提取方式 "简约翻译插件" --简约插件清洗 --输出目录 "本次输出目录"
```

3. 页面没有插件控件、插件没有完整字幕或导入失败时，才运行 `脚本/下载字幕或音频.py`。
4. `yt-dlp` 只拿到媒体时，运行 `脚本/转写音频.py`。

浏览器操作必须先运行 `opencli doctor`，再读取页面结构并操作可见控件。保存对话框可以把 VTT 直接写入本次 `C:\AI\Outputs\长内容知识脱水工作流\Codex\...` 任务目录。不要读取插件私有存储、Cookie、浏览器登录数据库或账号凭据。只有标题、简介、评论、弹幕或不完整的可见列表时，不得进入知识脱水。

若插件字幕文件已由用户或浏览器协作取得，也可使用兼容入口：

```powershell
python 脚本/自动知识脱水.py "YouTube链接" --简约字幕文件 "插件字幕.vtt"
```

## v0.1 可用范围

当前 v0.1 已验证可用范围是后半段手动闭环：

```text
资料/我的测试文本.md
→ 输出/逐字稿.md
→ 输出/逐字稿.json
→ 输出/最终提示词.md
→ 手动复制给大模型
→ 输出/知识脱水结果.md
→ 输出/黑曜石笔记.md
```

已验证命令：

```bash
python 脚本/导入文本文件.py "资料/我的测试文本.md"
python 脚本/生成最终提示词.py
python 脚本/保存知识脱水结果.py
python 脚本/整理为黑曜石文件.py
```

这个流程是当前冻结的核心路径。后续任何新增功能都必须保持它可用。

## 核心边界

- 不要根据视频标题、网页标题、简介或评论脑补内容。
- 没有拿到逐字稿或正文时，停止流程并说明原因。
- 不要把知识脱水逻辑写进 Python；知识脱水 Prompt 只从 `资源/提示词/知识脱水提示词.md` 读取。
- 不要改写 `资源/提示词/知识脱水提示词.md`。
- 不要随意修改已验证的核心流程：`导入文本文件.py`、`生成最终提示词.py`、`保存知识脱水结果.py`、`整理为黑曜石文件.py`。
- 后续新增功能不能破坏 v0.1 手动闭环。
- v0.3.1 的大模型 API 调用支持 OpenAI-compatible 多供应商配置，只是可选自动路线；必须保留手动复制给大模型再粘贴结果的旧路线。
- 不要自动写入黑曜石知识库，不要拆分原子笔记文件。
- Kedou / 蝌蚪视频解析网站当前只作为半自动工具；不要自动爬取 Kedou，不要假设它能全平台提取。
- 简约翻译插件是 YouTube 直读字幕轨失败后的第二层来源：优先下载 `.vtt` 后导入。不要读取插件私有存储、浏览器登录信息或账号凭据。
- 国内平台和播客音频当前是占位提取器；需要第三方工具输出样例后再接入。

## 研究语境与内容边界

- 用户以社会学、心理学研究和个人著作为目的处理材料；题材可能陌生、敏感、有争议或跨领域。
- 不因题材本身推断用户赞同来源观点或具有不当意图；以中性、可核验的研究记录方式处理实际提供的内容。
- 区分来源事实、作者主张、案例样本、研究者推断和待核实信息，并保留证据、方法、偏差与适用边界。
- 研究范围开放不等于权限边界开放。禁止读取、记录、输出或提交 API Key、密码、Token、Cookie、OAuth 数据、浏览器登录数据、扩展私有存储和私钥。
- 不绕过登录、付费、私密内容、平台权限或访问控制；涉及第三方个人信息时遵守隐私、授权与最小化原则。
- 详细规则见 `资源/研究语境说明.md`。

## 常用命令

```bash
python 脚本/半自动录入.py
python 脚本/运行后半流程.py
python 脚本/手动文本录入.py
python 脚本/导入文本文件.py 示例/带时间戳字幕示例.srt
python 脚本/生成最终提示词.py
python 脚本/调用大模型执行知识脱水.py
python 脚本/整理为黑曜石文件.py
python 脚本/提取文本.py "https://www.youtube.com/watch?v=xxxx"
python 脚本/提取文本.py 示例/示例逐字稿.md
python 脚本/提取网页文章.py "https://example.com/article"
python 脚本/提取YouTube字幕.py "https://www.youtube.com/watch?v=xxxx"
python 脚本/下载字幕或音频.py "https://example.com/video"
python 脚本/转写音频.py "输出/音频/audio.webm"
python 脚本/运行工作流.py --输入 输出/逐字稿.md --提示词 资源/提示词/知识脱水提示词.md
```

## 输出文件

`脚本/提取文本.py` 默认输出：

- `输出/逐字稿.json`：标准逐字稿 JSON。
- `输出/逐字稿.md`：标准逐字稿 Markdown。
- `输出/逐字稿_黑曜石复制.md`：带基础 frontmatter 的可复制 Markdown。

`脚本/运行工作流.py` 默认输出：

- `输出/最终提示词.md`：知识脱水 Prompt 与逐字稿的拼接文件，供复制到 ChatGPT / Claude / Codex。

## 代码导航

- `核心模块/平台路由.py`：识别 YouTube、B站、抖音、小红书、音频、网页文章、本地字幕、本地转录稿和长文本。
- `核心模块/工具路由.py`：半自动流程的平台识别与 Kedou / YouTube 插件建议。
- `核心模块/时间戳识别.py`：识别手动粘贴文本中的时间戳，支持时间段、单个开始时间、时间戳与文本分行。
- `核心模块/文本清洗.py`：清理手动粘贴文本。
- `核心模块/数据结构.py`：标准逐字稿数据结构。
- `核心模块/标准化.py`：解析 VTT/SRT/Markdown/JSON/纯文本并标准化。
- `核心模块/导出器.py`：导出标准 JSON、标准 Markdown、黑曜石可复制 Markdown。
- `核心模块/适配器.py`：第三方命令行工具适配接口。
- `提取器/油管.py`：使用 yt-dlp 获取 YouTube 字幕。
- `提取器/文章.py`：优先使用 trafilatura 提取网页正文。
- `提取器/网页文章.py`：使用 trafilatura 提取网页正文并输出无时间戳标准逐字稿。
- `提取器/YouTube字幕.py`：使用 youtube-transcript-api 获取 YouTube 人工字幕或自动字幕。
- `提取器/媒体下载.py`：使用 yt-dlp 提取字幕；无字幕时下载音频到 `输出/音频/`，并排除 live_chat、弹幕、评论类轨道。
- `提取器/音频转写.py`：使用 faster-whisper 转写本地音频。
- `提取器/B站.py`、`提取器/抖音.py`、`提取器/小红书.py`、`提取器/音频.py`：占位接口。

## 后半段工作流

当用户已经手动准备好原始文本、字幕、转录稿或文章正文时，优先使用 `脚本/运行后半流程.py`。菜单流程为：

1. 手动粘贴文本或导入本地 `.txt/.md/.srt/.vtt` 文件，生成 `输出/逐字稿.md` 与 `输出/逐字稿.json`。
2. 运行生成最终提示词，读取 `资源/提示词/知识脱水提示词.md` 与 `输出/逐字稿.md`，生成 `输出/最终提示词.md`。
3. 用户可以选择 `脚本/调用大模型执行知识脱水.py` 自动调用 OpenAI-compatible API，或把 `输出/最终提示词.md` 复制到网页端手动处理。
4. 自动 API 路径生成 `输出/知识脱水结果.md` 和 `输出/模型调用日志.md`；手动路径用 `脚本/保存知识脱水结果.py` 保存返回内容。
5. 运行黑曜石整理脚本，只添加 YAML 包装，生成 `输出/黑曜石笔记.md`。

API 调用是可选项。不要自动化 Kedou、读取 YouTube 插件私有存储、自动写入黑曜石库、拆分原子笔记文件，或改写知识脱水 Prompt。YouTube 只按已验证的字幕轨、页面可见插件控件、`yt-dlp` 和本地转写路线处理；其他未支持平台不做无依据抓取。浏览器工具栏弹窗无法从页面结构访问时再由用户点击复制或下载。

## v0.4 当前已支持

- 本地前端工作台：`前端/知识脱水工作台.py`。
- 手动文本输入。
- 本地文件上传。
- 网页文章提取。
- DeepSeek 自动知识脱水。
- 黑曜石 Markdown 输出。
- Playwright 前端结构验收。
- YouTube 直接字幕轨提取。
- 简约翻译插件页面可见 VTT 下载与标准化导入。
- 抖音 Cookie 授权实验入口：仅在用户明确选择后使用浏览器 Cookie 或 cookie.txt。

## 当前仍未稳定支持

- yt-dlp 通用字幕/音频真实验收。
- faster-whisper 音频转写真实验收。
- 抖音 / 小红书 / X 自动提取。
- Kedou 自动化。
- 自动拆分多篇原子笔记文件。
- 自动写入真实黑曜石库。

## Cookie 使用边界

- 默认不启用 Cookie。
- 只允许使用用户自己浏览器中已有的、可正常访问公开视频的 Cookie。
- 不要保存、打印或记录 Cookie 内容。
- 不要把 Cookie 写入日志、报告或提交到 Git。
- Cookie 模式不能用于绕过登录、付费、私密、权限或平台限制。
- 使用前先阅读 `资源/工具说明/Cookie安全说明.md`。

## 接入第三方工具

接入新工具时，优先让第三方工具输出 `资源/数据结构/逐字稿标准格式.json` 这种标准 JSON。若第三方工具输出格式不同，先在 `核心模块/适配器.py` 的子类中转换为 `TranscriptDocument`，再交给导出器。

## v0.5.3 字幕优先与本地媒体兜底

YouTube 和其他公开视频按以下顺序处理，前一级没有真实文本时才进入下一级：

1. `youtube-transcript-api` 直接读取 YouTube 已有字幕轨。
2. 直读失败后，用简约翻译插件从 YouTube 页面可见控件下载真实 VTT 字幕并导入。
3. 最新版 `yt-dlp` 尝试公共字幕或媒体入口。
4. 用户自行提供有权处理的本地音频/视频，用 `faster-whisper` 转写。
5. 视频画面存在硬字幕时，可在外部使用 Video Subtitle Extractor 导出 SRT，再导入本项目。

本地转写默认使用 `--设备 auto --计算类型 auto`：检测到 CUDA 时优先使用 GPU，否则使用 CPU；CUDA 运行库不可用时允许回退 CPU。无字幕、无本地媒体、只有标题/简介/评论时，不得进入知识脱水。

Video Subtitle Extractor 仅为外部可选工具，不自动安装、不捆绑模型、不在前端内直接运行。说明见 `资源/工具说明/视频硬字幕OCR说明.md`，工具状态见 `资源/工具说明/工具登记.md`。
