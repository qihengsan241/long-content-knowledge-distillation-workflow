from __future__ import annotations

import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "脚本"
OUTPUT_DIR = PROJECT_ROOT / "输出"
TEMP_DIR = OUTPUT_DIR / "前端临时文件"
ENV_PATH = PROJECT_ROOT / ".env"

STATUS_STEPS = [
    "获取文本",
    "标准化逐字稿",
    "生成最终提示词",
    "模型知识脱水",
    "黑曜石 Markdown 输出",
]

OUTPUT_FILES = {
    "逐字稿": OUTPUT_DIR / "逐字稿.md",
    "最终提示词": OUTPUT_DIR / "最终提示词.md",
    "知识脱水结果": OUTPUT_DIR / "知识脱水结果.md",
    "黑曜石笔记": OUTPUT_DIR / "黑曜石笔记.md",
    "模型调用日志": OUTPUT_DIR / "模型调用日志.md",
}


def main() -> None:
    st.set_page_config(page_title="长内容知识脱水工作台", page_icon="📝", layout="wide")
    init_state()
    st.title("长内容知识脱水工作台")

    render_top_status()
    render_source_center()
    render_douyin_experiment_area()
    render_route_recommendation()
    render_workflow_controls()
    render_progress_area()
    render_output_preview()
    render_file_operations()
    render_error_area()


def init_state() -> None:
    if "step_status" not in st.session_state:
        st.session_state.step_status = {step: "未开始" for step in STATUS_STEPS}
    if "flow_message" not in st.session_state:
        st.session_state.flow_message = "等待输入"
    if "last_error" not in st.session_state:
        st.session_state.last_error = ""
    if "last_success" not in st.session_state:
        st.session_state.last_success = ""
    if "route_input" not in st.session_state:
        st.session_state.route_input = ""


def render_top_status() -> None:
    provider, model, base_url = read_model_config()
    file_summary = summarize_output_dir()
    st.header("顶部状态区")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("当前工作流版本", "v0.4")
    col2.metric("当前模型供应商", provider or "未配置")
    col3.metric("当前模型名称", model or "未配置")
    col4.metric("输出目录状态", file_summary)
    col5.metric("当前流程状态", st.session_state.flow_message)
    if base_url:
        st.caption(f"当前 Base URL：{base_url}")


def render_source_center() -> None:
    st.header("文本来源中心")
    tab_article, tab_file, tab_paste, tab_youtube, tab_video, tab_audio = st.tabs(
        ["网页文章链接", "本地文本/字幕文件上传", "手动粘贴文本", "YouTube 链接（实验）", "通用视频链接（实验）", "本地音频/视频转写"]
    )

    with tab_article:
        url = st.text_input("网页文章链接", key="article_url", placeholder="https://example.com/article")
        if url:
            st.session_state.route_input = url
        if st.button("提取网页正文", key="extract_article"):
            if not url.strip():
                show_error("没有填写网页链接。", "请先输入网页文章链接。")
            else:
                run_and_report(
                    ["提取网页文章.py", url.strip()],
                    success_message="网页正文提取完成，已生成逐字稿。",
                    success_steps=["获取文本", "标准化逐字稿"],
                    failure_hint="网页正文提取失败。请手动复制正文到文本粘贴区。",
                )

    with tab_file:
        uploaded_file = st.file_uploader("上传 .txt / .md / .srt / .vtt 文件", type=["txt", "md", "srt", "vtt"])
        file_title = st.text_input("来源标题（可选）", key="upload_title")
        file_platform = st.text_input("平台（可选）", key="upload_platform")
        if uploaded_file and st.button("导入并生成逐字稿", key="import_uploaded_file"):
            saved_path = save_uploaded_file(uploaded_file)
            args = ["导入文本文件.py", str(saved_path)]
            if file_title.strip():
                args.extend(["--标题", file_title.strip()])
            if file_platform.strip():
                args.extend(["--平台", file_platform.strip()])
            run_and_report(
                args,
                success_message="本地文件导入完成，已生成逐字稿。",
                success_steps=["获取文本", "标准化逐字稿"],
                failure_hint="导入失败。请确认文件后缀是 .txt / .md / .srt / .vtt，或改用手动粘贴文本。",
            )

    with tab_paste:
        content_type = st.selectbox(
            "内容来源类型",
            ["视频字幕", "播客转录稿", "长篇文章", "访谈记录", "课程文稿", "带时间戳文本", "不带时间戳文本"],
        )
        title = st.text_input("来源标题", key="paste_title")
        source_url = st.text_input("来源链接（可为空）", key="paste_source_url")
        author = st.text_input("作者（可为空）", key="paste_author")
        platform = st.text_input("平台（可为空）", key="paste_platform")
        pasted_text = st.text_area("粘贴全文", height=280, placeholder="粘贴字幕、转录稿或文章正文...")
        if st.button("保存为逐字稿", key="save_pasted_text"):
            if not pasted_text.strip():
                show_error("没有粘贴文本。", "请先粘贴字幕、转录稿或文章正文。")
            else:
                TEMP_DIR.mkdir(parents=True, exist_ok=True)
                paste_path = TEMP_DIR / "手动粘贴文本.md"
                paste_path.write_text(pasted_text.strip() + "\n", encoding="utf-8")
                args = ["导入文本文件.py", str(paste_path), "--类型", content_type]
                if title.strip():
                    args.extend(["--标题", title.strip()])
                if source_url.strip():
                    args.extend(["--来源链接", source_url.strip()])
                    st.session_state.route_input = source_url.strip()
                if author.strip():
                    args.extend(["--作者", author.strip()])
                if platform.strip():
                    args.extend(["--平台", platform.strip()])
                run_and_report(
                    args,
                    success_message="手动粘贴文本已标准化为逐字稿。",
                    success_steps=["获取文本", "标准化逐字稿"],
                    failure_hint="标准化失败。请检查文本是否为空，或改用本地文件导入。",
                )

    with tab_youtube:
        youtube_url = st.text_input("YouTube 链接", key="youtube_url")
        if youtube_url:
            st.session_state.route_input = youtube_url
        dependency_notice("youtube_transcript_api", "youtube-transcript-api")
        if st.button("实验：尝试提取 YouTube 字幕", key="extract_youtube"):
            if not youtube_url.strip():
                show_error("没有填写 YouTube 链接。", "请先输入 YouTube 视频链接。")
            else:
                run_and_report(
                    ["提取YouTube字幕.py", youtube_url.strip()],
                    success_message="YouTube 字幕提取完成，已生成逐字稿。",
                    success_steps=["获取文本", "标准化逐字稿"],
                    failure_hint="YouTube 字幕提取失败。请尝试 yt-dlp，或手动复制字幕到文本粘贴区。",
                )

    with tab_video:
        video_url = st.text_input("通用视频链接", key="video_url")
        if video_url:
            st.session_state.route_input = video_url
        dependency_notice("yt_dlp", "yt-dlp")
        if st.button("实验：尝试 yt-dlp 提取字幕/音频", key="extract_video"):
            if not video_url.strip():
                show_error("没有填写视频链接。", "请先输入视频链接。")
            else:
                run_and_report(
                    ["下载字幕或音频.py", video_url.strip()],
                    success_message="yt-dlp 已完成处理。若只下载了音频，请进入音频转写。",
                    success_steps=["获取文本"],
                    failure_hint="yt-dlp 不可用或未提取成功。请安装依赖，或手动提供字幕/音频。",
                )

    with tab_audio:
        audio_file = st.file_uploader("上传本地音频/视频文件", type=["mp3", "m4a", "wav", "webm", "mp4"], key="audio_upload")
        dependency_notice("faster_whisper", "faster-whisper")
        whisper_model = st.text_input("faster-whisper 模型", value="small")
        st.caption("如果上传 webm/mp4 视频文件，需要 ffmpeg 可用并加入系统 PATH。")
        if audio_file and st.button("音频转写", key="transcribe_audio"):
            saved_path = save_uploaded_file(audio_file)
            run_and_report(
                ["转写音频.py", str(saved_path), "--模型", whisper_model.strip() or "small"],
                success_message="音频转写完成，已生成逐字稿。",
                success_steps=["获取文本", "标准化逐字稿"],
                failure_hint="音频转写失败。请安装 faster-whisper；如果是视频文件，请安装 ffmpeg；也可以先使用手动转录稿。",
            )


def render_douyin_experiment_area() -> None:
    st.header("抖音实验处理区")
    st.warning("Cookie 类似临时通行证。只用于你自己有权限访问的视频，不要公开、上传或写入日志。")
    douyin_url = st.text_input("抖音链接输入框", key="douyin_experiment_url", placeholder="https://v.douyin.com/...")
    if douyin_url:
        st.session_state.route_input = douyin_url

    cookie_confirmed = st.checkbox("我确认只使用自己浏览器中已有的、可正常访问公开视频的 Cookie", key="douyin_cookie_confirmed")
    browser = st.selectbox("浏览器 Cookie 来源", ["chrome", "edge", "firefox"], key="douyin_cookie_browser")
    cookie_file = st.file_uploader("上传 cookie.txt 尝试", type=["txt"], key="douyin_cookie_file")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("抖音普通尝试", key="douyin_plain_try"):
            if not douyin_url.strip():
                show_error("没有填写抖音链接。", "请先输入抖音视频链接。")
            else:
                run_and_report(
                    ["下载字幕或音频.py", douyin_url.strip()],
                    success_message="抖音普通尝试完成。若只下载了音频，请进入音频转写。",
                    success_steps=["获取文本"],
                    failure_hint="普通 yt-dlp 尝试失败。若提示 fresh cookies，可在确认安全风险后尝试浏览器 Cookie 模式，或改用本地文件兜底。",
                )
    with col2:
        if st.button("使用浏览器 Cookie 尝试", key="douyin_browser_cookie_try", disabled=not cookie_confirmed):
            if not douyin_url.strip():
                show_error("没有填写抖音链接。", "请先输入抖音视频链接。")
            else:
                run_and_report(
                    ["下载字幕或音频.py", douyin_url.strip(), "--cookies-from-browser", browser],
                    success_message=f"抖音浏览器 Cookie 模式完成：{browser}。若只下载了音频，请进入音频转写。",
                    success_steps=["获取文本"],
                    failure_hint="浏览器 Cookie 模式失败。请确认你能在该浏览器中正常访问视频；也可以改用本地文件兜底。",
                )
    with col3:
        if cookie_file and st.button("使用 cookie.txt 尝试", key="douyin_cookie_file_try", disabled=not cookie_confirmed):
            if not douyin_url.strip():
                show_error("没有填写抖音链接。", "请先输入抖音视频链接。")
            else:
                cookie_path = save_cookie_file(cookie_file)
                run_and_report(
                    ["下载字幕或音频.py", douyin_url.strip(), "--cookies-file", str(cookie_path)],
                    success_message="抖音 cookie.txt 模式完成。若只下载了音频，请进入音频转写。",
                    success_steps=["获取文本"],
                    failure_hint="cookie.txt 模式失败。请确认 cookie.txt 有效且没有过期；用完后可以删除该文件。",
                )

    st.subheader("本地文件兜底")
    fallback_file = st.file_uploader("上传本地视频/音频文件", type=["mp3", "m4a", "wav", "webm", "mp4"], key="douyin_fallback_media")
    col4, col5 = st.columns(2)
    with col4:
        if fallback_file and st.button("音频转写入口", key="douyin_fallback_transcribe"):
            saved_path = save_uploaded_file(fallback_file)
            run_and_report(
                ["转写音频.py", str(saved_path)],
                success_message="本地文件音频转写完成，已生成逐字稿。",
                success_steps=["获取文本", "标准化逐字稿"],
                failure_hint="音频转写失败。请安装 faster-whisper；如果是视频文件，请安装 ffmpeg；也可以手动转写后导入文本。",
            )
    with col5:
        if st.button("OCR 字幕提取入口（占位）", key="douyin_ocr_placeholder"):
            show_error(
                "OCR 字幕提取暂未自动接入。",
                "如果视频画面中有硬字幕，请先用半自动 OCR 工具导出 srt，再通过“本地文本/字幕文件上传”导入。",
            )


def render_route_recommendation() -> None:
    st.header("平台识别与推荐路线区")
    link = st.text_input("用于识别的平台链接", value=st.session_state.route_input, key="route_link")
    if link:
        st.session_state.route_input = link
    platform = detect_platform(link)
    st.write(f"识别结果：**{platform}**")
    st.info(recommend_route(platform))


def render_workflow_controls() -> None:
    st.header("流程操作区")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("生成最终提示词"):
            if not OUTPUT_FILES["逐字稿"].exists():
                show_error("没有找到逐字稿。", "请先导入文本、提取网页正文或上传字幕文件。")
            else:
                run_and_report(
                    ["生成最终提示词.py"],
                    success_message="最终提示词已生成。",
                    success_steps=["生成最终提示词"],
                    failure_hint="生成最终提示词失败。请确认逐字稿和知识脱水 Prompt 都存在。",
                )
    with col2:
        if st.button("调用 DeepSeek 知识脱水"):
            if not OUTPUT_FILES["最终提示词"].exists():
                show_error("没有找到最终提示词。", "请先点击“生成最终提示词”。")
            else:
                run_and_report(
                    ["调用大模型执行知识脱水.py"],
                    success_message="模型知识脱水完成。",
                    success_steps=["模型知识脱水"],
                    failure_hint="DeepSeek 调用失败。请检查 .env 中的 LLM_PROVIDER、DEEPSEEK_API_KEY 和 DEEPSEEK_MODEL。",
                )
    with col3:
        if st.button("整理为黑曜石 Markdown"):
            if not OUTPUT_FILES["知识脱水结果"].exists():
                show_error("没有找到知识脱水结果。", "请先调用模型，或手动保存知识脱水结果。")
            else:
                run_and_report(
                    ["整理为黑曜石文件.py"],
                    success_message="黑曜石 Markdown 已生成。",
                    success_steps=["黑曜石 Markdown 输出"],
                    failure_hint="整理失败。请确认知识脱水结果文件非空。",
                )
    with col4:
        if st.button("一键运行完整流程"):
            if not OUTPUT_FILES["逐字稿"].exists():
                show_error("没有找到逐字稿。", "请先导入文本、提取网页正文或上传字幕文件。")
                return
            run_pipeline()


def render_progress_area() -> None:
    st.header("流程进度区")
    columns = st.columns(len(STATUS_STEPS))
    for column, step in zip(columns, STATUS_STEPS):
        column.write(f"**{step}**")
        column.write(st.session_state.step_status.get(step, "未开始"))


def render_output_preview() -> None:
    st.header("输出预览区")
    if st.button("刷新全部预览"):
        st.rerun()
    for label, path in OUTPUT_FILES.items():
        with st.expander(f"{label}：{relative_path(path)}", expanded=False):
            if not path.exists():
                st.warning("文件不存在。")
                continue
            content = read_text(path)
            st.caption(f"文件大小：{path.stat().st_size} 字节；更新时间：{datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"刷新 {label}", key=f"refresh_{label}"):
                    st.rerun()
            with col2:
                render_copy_button(f"复制 {label}", content, key=f"copy_{label}")
            st.text_area(f"{label} 内容预览", value=content[:20000], height=260, key=f"preview_{label}")


def render_file_operations() -> None:
    st.header("文件操作区")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("打开输出文件夹"):
            open_output_folder()
    with col2:
        obsidian = OUTPUT_FILES["黑曜石笔记"]
        if obsidian.exists():
            st.download_button("下载黑曜石 Markdown", data=read_text(obsidian), file_name="黑曜石笔记.md", mime="text/markdown")
        else:
            st.button("下载黑曜石 Markdown", disabled=True)
    with col3:
        final_prompt = OUTPUT_FILES["最终提示词"]
        if final_prompt.exists():
            render_copy_button("复制最终提示词", read_text(final_prompt), key="copy_final_prompt_top")
        else:
            st.button("复制最终提示词", disabled=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        obsidian = OUTPUT_FILES["黑曜石笔记"]
        if obsidian.exists():
            render_copy_button("复制黑曜石 Markdown", read_text(obsidian), key="copy_obsidian_top")
        else:
            st.button("复制黑曜石 Markdown", disabled=True)
    with col5:
        if st.button("查看模型调用日志"):
            st.session_state.show_model_log = True
    with col6:
        confirm_clear = st.checkbox("确认清空本次输出")
        if st.button("清空本次输出", disabled=not confirm_clear):
            clear_outputs()

    if st.session_state.get("show_model_log"):
        log_path = OUTPUT_FILES["模型调用日志"]
        st.subheader("模型调用日志")
        st.text_area("日志内容", read_text(log_path) if log_path.exists() else "日志不存在。", height=220)


def render_error_area() -> None:
    st.header("错误提示区")
    if st.session_state.last_success:
        st.success(st.session_state.last_success)
    if st.session_state.last_error:
        st.error(st.session_state.last_error)
    if not st.session_state.last_error and not st.session_state.last_success:
        st.info("暂无错误。")


def run_pipeline() -> None:
    st.session_state.flow_message = "一键流程进行中"
    commands = [
        (["生成最终提示词.py"], "生成最终提示词", "生成最终提示词失败。请确认逐字稿存在。"),
        (["调用大模型执行知识脱水.py"], "模型知识脱水", "DeepSeek 调用失败。请检查 .env 配置，或退回手动流程。"),
        (["整理为黑曜石文件.py"], "黑曜石 Markdown 输出", "整理黑曜石文件失败。请确认知识脱水结果非空。"),
    ]
    for args, step, hint in commands:
        set_step(step, "进行中")
        result = run_script(args)
        if result.returncode != 0:
            set_step(step, "失败")
            show_error(humanize_error(result), hint)
            st.session_state.flow_message = "一键流程失败"
            return
        set_step(step, "成功")
    st.session_state.flow_message = "一键流程完成"
    st.session_state.last_success = "完整流程已完成，黑曜石 Markdown 已生成。"
    st.session_state.last_error = ""


def run_and_report(args: list[str], *, success_message: str, success_steps: list[str], failure_hint: str) -> None:
    for step in success_steps:
        set_step(step, "进行中")
    result = run_script(args)
    if result.returncode == 0:
        for step in success_steps:
            set_step(step, "成功")
        st.session_state.flow_message = success_message
        st.session_state.last_success = success_message
        st.session_state.last_error = ""
        st.code(result.stdout.strip() or "执行成功。")
    else:
        for step in success_steps:
            set_step(step, "失败")
        show_error(humanize_error(result), failure_hint)
        st.code((result.stderr or result.stdout or "").strip())


def run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT_DIR / args[0]), *args[1:]]
    return subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def save_uploaded_file(uploaded_file) -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "_", uploaded_file.name)
    path = TEMP_DIR / safe_name
    path.write_bytes(uploaded_file.getbuffer())
    return path


def save_cookie_file(uploaded_file) -> Path:
    cookie_dir = PROJECT_ROOT / "cookies"
    cookie_dir.mkdir(parents=True, exist_ok=True)
    path = cookie_dir / "uploaded.cookie.txt"
    path.write_bytes(uploaded_file.getbuffer())
    return path


def read_model_config() -> tuple[str, str, str]:
    values = read_env_values()
    provider = values.get("LLM_PROVIDER", "").strip().lower()
    if provider in {"openai", "deepseek", "custom"}:
        prefix = provider.upper()
        model = values.get(f"{prefix}_MODEL", "").strip()
        base_url = values.get(f"{prefix}_BASE_URL", "").strip()
        if provider == "deepseek" and not base_url:
            base_url = "https://api.deepseek.com"
        if provider == "openai" and not base_url:
            base_url = "https://api.openai.com/v1"
        return provider, model, base_url
    return provider or "未配置", "", ""


def read_env_values() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def summarize_output_dir() -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = sum(1 for path in OUTPUT_FILES.values() if path.exists())
    return f"{existing}/{len(OUTPUT_FILES)} 个关键文件"


def detect_platform(value: str) -> str:
    value = value.strip()
    if not value:
        return "未知链接"
    lower = value.lower()
    parsed = urlparse(lower if re.match(r"https?://", lower) else "https://" + lower)
    host = parsed.netloc
    if "youtube.com" in host or "youtu.be" in host:
        return "YouTube"
    if "bilibili.com" in host or "b23.tv" in host:
        return "B站"
    if "douyin.com" in host:
        return "抖音"
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return "小红书"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "X"
    if any(token in lower for token in [".mp3", ".m4a", ".wav", "podcast", "rss"]):
        return "播客音频"
    if Path(value).suffix.lower() in {".srt", ".vtt", ".txt", ".md"}:
        return "本地字幕"
    if Path(value).suffix.lower() in {".mp3", ".m4a", ".wav", ".webm", ".mp4", ".mkv"}:
        return "本地音频"
    if parsed.scheme in {"http", "https"} and host:
        return "普通网页"
    return "未知链接"


def recommend_route(platform: str) -> str:
    routes = {
        "普通网页": "网页正文尝试：trafilatura → 逐字稿 → 知识脱水。若失败，手动复制正文到粘贴区。",
        "网页文章": "trafilatura → 逐字稿 → 知识脱水。",
        "YouTube": "youtube-transcript-api → 失败则 yt-dlp → 失败则音频转写 → 失败则手动粘贴。",
        "B站": "yt-dlp 尝试字幕/音频 → 音频转写 → 手动粘贴。",
        "抖音": "yt-dlp 尝试 → 音频转写 → 手动粘贴。",
        "小红书": "网页正文尝试 / 音频转写 / 手动粘贴。",
        "X": "网页正文尝试 / 手动粘贴 / 音视频另行处理。",
        "播客音频": "下载音频 → faster-whisper 转写 → 逐字稿 → 知识脱水。",
        "本地字幕": "直接导入 → 标准化逐字稿 → 知识脱水。",
        "本地音频": "faster-whisper 转写 → 逐字稿 → 知识脱水。",
    }
    return routes.get(platform, "先尝试网页正文提取；如果失败，请手动复制正文或字幕到粘贴区。")


def dependency_notice(module_name: str, package_name: str) -> None:
    if importlib.util.find_spec(module_name) is None:
        st.warning(f"{package_name} 当前不可用。请安装依赖，或使用手动粘贴/本地转录稿兜底。")
    else:
        st.success(f"{package_name} 可用。")


def set_step(step: str, status: str) -> None:
    st.session_state.step_status[step] = status


def show_error(message: str, next_step: str) -> None:
    st.session_state.last_error = f"{message}\n\n下一步建议：{next_step}"
    st.session_state.last_success = ""
    st.session_state.flow_message = "需要人工处理"


def humanize_error(result: subprocess.CompletedProcess[str]) -> str:
    raw = (result.stderr or result.stdout or "").strip()
    if not raw:
        return f"命令执行失败，退出码：{result.returncode}。"
    if "找不到逐字稿" in raw or "逐字稿文件" in raw:
        return "没有找到逐字稿。"
    if "DeepSeek" in raw or "Authentication" in raw or "API" in raw:
        return "DeepSeek 调用失败。"
    if "网页文章提取失败" in raw:
        return "网页正文提取失败。"
    if "faster-whisper" in raw:
        return "音频转写依赖缺失或转写失败。"
    if "yt-dlp" in raw:
        return "yt-dlp 不可用或提取失败。"
    return raw.splitlines()[0]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def render_copy_button(label: str, content: str, key: str) -> None:
    safe_label = html.escape(label)
    text_json = json.dumps(content, ensure_ascii=False)
    components.html(
        f"""
        <button id="{key}" style="padding: 0.45rem 0.75rem; border: 1px solid #bbb; border-radius: 6px; background: white; cursor: pointer;">{safe_label}</button>
        <span id="{key}_status" style="margin-left: 0.5rem; color: #555;"></span>
        <script>
        const button = document.getElementById({json.dumps(key)});
        const status = document.getElementById({json.dumps(key + "_status")});
        button.onclick = async () => {{
            try {{
                await navigator.clipboard.writeText({text_json});
                status.textContent = "已复制";
            }} catch (error) {{
                status.textContent = "复制失败，请在预览框中手动复制";
            }}
        }};
        </script>
        """,
        height=42,
    )


def open_output_folder() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            os.startfile(str(OUTPUT_DIR))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(OUTPUT_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])
        st.success("已尝试打开输出文件夹。")
    except OSError as exc:
        show_error("打开输出文件夹失败。", f"请手动打开：{OUTPUT_DIR}。错误：{exc}")


def clear_outputs() -> None:
    for path in OUTPUT_FILES.values():
        if path.exists():
            path.unlink()
    st.session_state.step_status = {step: "未开始" for step in STATUS_STEPS}
    st.session_state.flow_message = "已清空本次输出"
    st.session_state.last_success = "本次输出已清空。"
    st.session_state.last_error = ""


if __name__ == "__main__":
    main()
