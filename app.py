import json
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import streamlit as st
from pypdf import PdfReader

from graph import graph
from memory.memory_utils import (
    append_message,
    create_conversation,
    delete_conversation,
    get_conversation,
    get_latest_conversation,
    load_conversations,
    rename_conversation,
)

st.set_page_config(page_title="AI 学习助手 Agent", page_icon="🤖", layout="wide")

MODES = ["快速过一遍", "深入学习", "项目驱动学习", "面试模式"]
MODE_HELP = {
    "快速过一遍": "适合快速了解概念和关键结论。",
    "深入学习": "适合系统掌握原理、细节和使用场景。",
    "项目驱动学习": "适合结合代码、项目和简历展示来学习。",
    "面试模式": "适合提炼高频问题、标准回答和追问点。",
}
CODE_EXTENSIONS = [".py", ".ipynb", ".md", ".txt"]
PROJECT_SKIP_DIRS = {".venv", "__pycache__", ".git", "github", "data"}
PROJECT_MAX_CHARS = 16000


def set_active_conversation(conversation_id):
    st.session_state["active_conversation_id"] = conversation_id
    st.session_state["draft_input"] = ""


def start_new_chat():
    conversation = create_conversation()
    set_active_conversation(conversation["conversation_id"])


def start_rename_conversation(conversation):
    st.session_state["renaming_conversation_id"] = conversation.get("conversation_id")
    st.session_state["rename_title"] = conversation.get("title", "")


def compact_title(text, max_len=24):
    title = " ".join((text or "").strip().split()) or "新对话"
    noisy_prefixes = [
        "请基于这次学习记录，继续生成下一步学习任务",
        "请基于上次学习记录，生成下一步学习任务",
        "请根据当前项目自动生成 README",
    ]
    for prefix in noisy_prefixes:
        if title.startswith(prefix):
            title = title.replace(prefix, "继续学习", 1)
    return title[:max_len] + "..." if len(title) > max_len else title


def get_history_title(conversation):
    title = conversation.get("title", "")
    if not title or title == "新对话":
        for message in conversation.get("messages", []):
            if message.get("role") == "user":
                title = message.get("content", "")
                break
    return compact_title(title)


def get_last_messages(conversation):
    messages = conversation.get("messages", []) if conversation else []
    last_user = ""
    last_assistant = ""
    last_metadata = {}

    for message in reversed(messages):
        if not last_assistant and message.get("role") == "assistant":
            last_assistant = message.get("content", "")
            last_metadata = message.get("metadata", {})
        if not last_user and message.get("role") == "user":
            last_user = message.get("content", "")
        if last_user and last_assistant:
            break

    return last_user, last_assistant, last_metadata


def group_label(timestamp):
    if not timestamp:
        return "更早"
    try:
        day = datetime.fromisoformat(timestamp).date()
    except ValueError:
        try:
            day = datetime.strptime(timestamp, "%Y-%m-%d").date()
        except ValueError:
            return "更早"

    delta = (date.today() - day).days
    if delta == 0:
        return "今天"
    if delta == 1:
        return "昨天"
    if delta < 7:
        return "最近 7 天"
    return "更早"


def read_pdf_pages(uploaded_file):
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = " ".join((page.extract_text() or "").split())
        if text:
            pages.append({"page": index, "text": text})
    return pages


def retrieve_pdf_context(query, pages, max_pages=4, max_chars=9000):
    if not pages:
        return "", []

    query_lower = query.lower()
    terms = [term for term in query_lower.split() if len(term) > 1]
    keyword_terms = ["核心", "方法", "第三章", "总结", "概念", "术语", "公式", "代码", "学习路线"]

    scored_pages = []
    for page in pages:
        text_lower = page["text"].lower()
        score = sum(1 for term in terms if term in text_lower)
        score += sum(1 for term in keyword_terms if term in query_lower and term in page["text"])
        scored_pages.append((score, page))

    matched_pages = [
        page for score, page in sorted(scored_pages, key=lambda item: item[0], reverse=True) if score > 0
    ]
    matched_pages = matched_pages[:max_pages] if matched_pages else pages[:max_pages]

    chunks = []
    used_pages = []
    total_chars = 0
    for page in matched_pages:
        chunk = f"第 {page['page']} 页：{page['text']}"
        if total_chars + len(chunk) > max_chars:
            break
        chunks.append(chunk)
        used_pages.append(page["page"])
        total_chars += len(chunk)
    return "\n\n".join(chunks), used_pages


def read_code_upload(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    raw_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    if suffix == ".ipynb":
        notebook = json.loads(raw_text)
        cells = []
        for cell in notebook.get("cells", []):
            source = "".join(cell.get("source", []))
            if source.strip():
                cells.append(f"# {cell.get('cell_type', 'cell')} cell\n{source}")
        return "\n\n".join(cells)
    return raw_text


def build_code_context(files, max_chars=PROJECT_MAX_CHARS):
    chunks = []
    names = []
    total_chars = 0
    for uploaded_file in files:
        name = uploaded_file.name
        if Path(name).suffix.lower() not in CODE_EXTENSIONS:
            continue
        content = read_code_upload(uploaded_file)
        chunk = f"===== {name} =====\n{content}"
        if total_chars + len(chunk) > max_chars:
            chunk = chunk[: max_chars - total_chars]
        chunks.append(chunk)
        names.append(name)
        total_chars += len(chunk)
        if total_chars >= max_chars:
            break
    return "\n\n".join(chunks), names


def collect_project_snapshot(max_chars=PROJECT_MAX_CHARS):
    root = Path.cwd()
    chunks = []
    names = []
    total_chars = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in PROJECT_SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in CODE_EXTENSIONS:
            continue
        relative_path = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8", errors="ignore")
        chunk = f"===== {relative_path} =====\n{content}"
        if total_chars + len(chunk) > max_chars:
            chunk = chunk[: max_chars - total_chars]
        chunks.append(chunk)
        names.append(relative_path)
        total_chars += len(chunk)
        if total_chars >= max_chars:
            break
    return "\n\n".join(chunks), names


def save_readme(content):
    Path("README.md").write_text(content.strip() + "\n", encoding="utf-8")


def build_workflow_logs(node_name, node_output):
    if node_name == "router":
        return f"[Router] task_type = {node_output.get('task_type', '')}"
    if node_name == "planner":
        return "[Planner] plan generated"
    if node_name == "teacher":
        return "[Teacher] answer generated"
    if node_name == "code":
        return "[Code] answer generated"
    if node_name == "project":
        return "[Project] answer generated"
    if node_name == "document":
        return "[Document] PDF answer generated"
    if node_name == "code_study":
        return "[Code Study] code answer generated"
    if node_name == "review":
        return "[Review] summary and next suggestion generated"
    if node_name == "memory":
        return "[Memory] saved"
    return f"[{node_name}] executed"


def task_display(task_type):
    mapping = {
        "learn": ("学习讲解", "teacher-card"),
        "code": ("代码分析", "code-card"),
        "project": ("项目建议", "project-card"),
        "document": ("文档分析", "document-card"),
        "code_study": ("代码学习", "code-card"),
    }
    return mapping.get(task_type, ("学习内容", "teacher-card"))


def render_user_message(content):
    st.markdown(
        f"<div class='chat-row user'><div class='user-bubble'>{content}</div></div>",
        unsafe_allow_html=True,
    )


def render_ai_card(content, metadata=None):
    metadata = metadata or {}
    task_type = metadata.get("task_type", "")
    title, card_class = task_display(task_type)

    st.markdown("<div class='chat-row ai'>", unsafe_allow_html=True)
    with st.container():
        st.markdown(f"<div class='ai-card {card_class}'><div class='ai-card-title'>{title}</div>", unsafe_allow_html=True)
        st.markdown(content or "")

        if metadata.get("pdf_sources"):
            pages = "、".join([f"第 {page} 页" for page in metadata["pdf_sources"]])
            st.caption(f"引用来源：{pages}")

        if metadata.get("plan"):
            with st.expander("学习计划", expanded=False):
                st.markdown(metadata["plan"])

        if metadata.get("learning_summary") or metadata.get("next_suggestion"):
            with st.expander("学习总结与下一步", expanded=False):
                if metadata.get("learning_summary"):
                    st.markdown(metadata["learning_summary"])
                if metadata.get("next_suggestion"):
                    st.markdown(metadata["next_suggestion"])

        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_node_output(node_name, node_output, pdf_sources=None):
    if node_name == "planner":
        with st.container():
            st.markdown("<div class='ai-card plan-card'><div class='ai-card-title'>学习计划</div>", unsafe_allow_html=True)
            st.markdown(node_output.get("plan", ""))
            st.markdown("</div>", unsafe_allow_html=True)
    elif node_name == "teacher":
        with st.container():
            st.markdown("<div class='ai-card teacher-card'><div class='ai-card-title'>学习讲解</div>", unsafe_allow_html=True)
            st.markdown(node_output.get("answer", ""))
            st.markdown("</div>", unsafe_allow_html=True)
    elif node_name == "code":
        with st.container():
            st.markdown("<div class='ai-card code-card'><div class='ai-card-title'>代码分析</div>", unsafe_allow_html=True)
            st.markdown(node_output.get("answer", ""))
            st.markdown("</div>", unsafe_allow_html=True)
    elif node_name == "project":
        with st.container():
            st.markdown("<div class='ai-card project-card'><div class='ai-card-title'>项目建议</div>", unsafe_allow_html=True)
            st.markdown(node_output.get("answer", ""))
            st.markdown("</div>", unsafe_allow_html=True)
    elif node_name == "document":
        with st.container():
            st.markdown("<div class='ai-card document-card'><div class='ai-card-title'>文档分析</div>", unsafe_allow_html=True)
            st.markdown(node_output.get("answer", ""))
            if pdf_sources:
                pages = "、".join([f"第 {page} 页" for page in pdf_sources])
                st.caption(f"引用来源：{pages}")
            st.markdown("</div>", unsafe_allow_html=True)
    elif node_name == "code_study":
        with st.container():
            st.markdown("<div class='ai-card code-card'><div class='ai-card-title'>代码学习</div>", unsafe_allow_html=True)
            st.markdown(node_output.get("answer", ""))
            st.markdown("</div>", unsafe_allow_html=True)
    elif node_name == "review":
        with st.container():
            st.markdown("<div class='ai-card review-card'><div class='ai-card-title'>学习复盘</div>", unsafe_allow_html=True)
            if node_output.get("learning_summary"):
                st.markdown(node_output.get("learning_summary", ""))
            if node_output.get("next_suggestion"):
                st.markdown(node_output.get("next_suggestion", ""))
            st.markdown("</div>", unsafe_allow_html=True)
    elif node_name == "memory":
        with st.expander("学习记录", expanded=False):
            st.write(node_output.get("memory_note", ""))


st.markdown(
    """
    <style>
    .block-container { max-width: 1080px; padding-top: 1.25rem; padding-bottom: 2rem; }
    section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.08); }
    section[data-testid="stSidebar"] .stButton > button {
        justify-content: flex-start; border-radius: 10px; min-height: 40px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    section[data-testid="stSidebar"] .stButton > button p {
        text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .current-chat {
        border-radius: 10px; padding: 10px 12px; margin: 4px 0 12px 0;
        background: rgba(65, 126, 255, 0.18); border: 1px solid rgba(65, 126, 255, 0.45);
        font-weight: 700;
    }
    .history-day { margin-top: 14px; margin-bottom: 6px; font-size: 0.76rem; color: rgba(255,255,255,0.58); font-weight: 700; }
    .status-card {
        border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; padding: 18px 20px;
        background: rgba(255,255,255,0.04); margin-bottom: 16px;
    }
    .status-title { font-size: 1.18rem; font-weight: 800; margin-bottom: 8px; }
    .status-muted { color: rgba(255,255,255,0.72); font-size: 0.94rem; margin-bottom: 5px; }
    .chat-row { display: flex; margin: 12px 0; }
    .chat-row.user { justify-content: flex-end; }
    .chat-row.ai { justify-content: flex-start; }
    .user-bubble {
        max-width: 66%; padding: 10px 14px; border-radius: 16px 16px 5px 16px;
        line-height: 1.6; background: rgba(65,126,255,0.38); word-break: break-word;
    }
    .ai-card {
        max-width: 86%; width: 86%; padding: 16px 18px; border-radius: 14px;
        line-height: 1.75; background: rgba(255,255,255,0.055);
        border: 1px solid rgba(255,255,255,0.09); word-break: break-word;
    }
    .ai-card-title { font-weight: 800; font-size: 1rem; margin-bottom: 10px; color: rgba(255,255,255,0.92); }
    .teacher-card { border-left: 4px solid #6ea8fe; }
    .review-card { border-left: 4px solid #b197fc; }
    .document-card { border-left: 4px solid #63e6be; }
    .code-card { border-left: 4px solid #ffd43b; }
    .project-card { border-left: 4px solid #ff922b; }
    .plan-card { border-left: 4px solid #74c0fc; margin-bottom: 12px; }
    .section-title { margin-top: 20px; margin-bottom: 8px; font-weight: 800; color: rgba(255,255,255,0.86); }
    </style>
    """,
    unsafe_allow_html=True,
)

defaults = {
    "selected_mode": MODES[0],
    "draft_input": "",
    "clear_draft_input": False,
    "active_conversation_id": None,
    "pdf_name": "",
    "pdf_pages": [],
    "pdf_file_id": "",
    "code_context": "",
    "code_files": [],
    "code_file_id": "",
    "code_action": "",
    "renaming_conversation_id": None,
    "rename_title": "",
    "developer_mode": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.get("clear_draft_input"):
    st.session_state["draft_input"] = ""
    st.session_state["clear_draft_input"] = False

conversations = load_conversations()
if not st.session_state["active_conversation_id"]:
    latest_conversation = get_latest_conversation()
    if latest_conversation:
        st.session_state["active_conversation_id"] = latest_conversation["conversation_id"]

active_conversation = get_conversation(st.session_state["active_conversation_id"])
active_conversation_id = active_conversation.get("conversation_id") if active_conversation else None
last_user, last_answer, last_metadata = get_last_messages(active_conversation)

with st.sidebar:
    st.title("AI 学习助手")

    if st.button("＋ 新建学习会话", type="primary", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.caption("新对话会开启新的学习记录，历史内容不会丢失。")
    st.divider()

    st.subheader("当前会话")
    if active_conversation:
        st.markdown(f"<div class='current-chat'>● {get_history_title(active_conversation)}</div>", unsafe_allow_html=True)
    else:
        st.caption("暂无当前会话")

    st.subheader("历史会话")
    if not conversations:
        st.caption("暂无历史会话")
    else:
        sorted_conversations = sorted(
            conversations,
            key=lambda item: item.get("updated_at", item.get("created_at", "")),
            reverse=True,
        )
        current_group = None
        for conversation in sorted_conversations:
            conversation_id = conversation.get("conversation_id")
            if conversation_id == active_conversation_id:
                continue
            label_group = group_label(conversation.get("updated_at", conversation.get("created_at", "")))
            if label_group != current_group:
                st.markdown(f"<div class='history-day'>{label_group}</div>", unsafe_allow_html=True)
                current_group = label_group

            title_col, menu_col = st.columns([0.82, 0.18])
            with title_col:
                if st.button(get_history_title(conversation), key=f"conversation_{conversation_id}", use_container_width=True):
                    set_active_conversation(conversation_id)
                    st.rerun()
            with menu_col:
                with st.popover("⋯", use_container_width=True):
                    if st.button("重命名", key=f"rename_{conversation_id}", use_container_width=True):
                        st.session_state["renaming_conversation_id"] = conversation_id
                        st.session_state["rename_title"] = conversation.get("title", "")
                        st.rerun()
                    if st.button("删除", key=f"delete_{conversation_id}", use_container_width=True):
                        delete_conversation(conversation_id)
                        st.rerun()

            if st.session_state.get("renaming_conversation_id") == conversation_id:
                with st.form(f"rename_form_{conversation_id}"):
                    new_title = st.text_input("新名称", value=st.session_state.get("rename_title", ""))
                    save_col, cancel_col = st.columns(2)
                    submitted = save_col.form_submit_button("保存")
                    cancelled = cancel_col.form_submit_button("取消")
                    if submitted:
                        rename_conversation(conversation_id, new_title)
                        st.session_state["renaming_conversation_id"] = None
                        st.rerun()
                    if cancelled:
                        st.session_state["renaming_conversation_id"] = None
                        st.rerun()

    st.divider()
    with st.expander("学习档案", expanded=False):
        st.write("当前用户：user_001")
        st.write("当前项目：AI 学习助手 Agent")
        st.write("当前阶段：展示层优化")
    st.session_state["developer_mode"] = st.checkbox("开发者模式", value=st.session_state.get("developer_mode", False))

st.title("AI 学习助手 Agent")

current_topic = get_history_title(active_conversation) if active_conversation else "新的学习"
progress_percent = last_metadata.get("progress_percent", 0)
completed_topics = last_metadata.get("completed_topics", [])
unfinished_topics = last_metadata.get("unfinished_topics", [])
next_suggestion = last_metadata.get("next_suggestion", "")

if active_conversation and active_conversation.get("messages"):
    welcome_title = "欢迎回来"
    recent_question = compact_title(last_user, 42) if last_user else "还没有开始提问"
    progress_label = f"{progress_percent}%" if progress_percent else "刚开始"
else:
    welcome_title = "欢迎开始新的学习"
    recent_question = "可以输入：学习 LangChain、总结 PDF、分析代码项目"
    progress_label = "刚开始"

st.markdown(
    f"""
    <div class="status-card">
        <div class="status-title">{welcome_title}</div>
        <div class="status-muted">当前主题：{current_topic}</div>
        <div class="status-muted">学习进度：{progress_label}</div>
        <div class="status-muted">最近提问：{recent_question}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("继续学习", use_container_width=True, disabled=not active_conversation_id):
        st.session_state["draft_input"] = "请根据当前会话，继续安排下一步学习任务"
        st.rerun()
with col_b:
    if st.button("总结上次内容", use_container_width=True, disabled=not active_conversation_id):
        st.session_state["draft_input"] = "请总结这个会话里我上次学到的内容"
        st.rerun()
with col_c:
    if st.button("生成复习题", use_container_width=True, disabled=not active_conversation_id):
        st.session_state["draft_input"] = "请根据当前学习内容生成 5 道复习题"
        st.rerun()

if completed_topics or unfinished_topics or next_suggestion:
    with st.expander("学习进度详情", expanded=False):
        st.write("已掌握：", "、".join(completed_topics) if completed_topics else "暂无")
        st.write("待学习：", "、".join(unfinished_topics) if unfinished_topics else "暂无")
        if next_suggestion:
            st.markdown(next_suggestion)

with st.expander("导入资料", expanded=False):
    st.markdown("**上传 PDF 文档**")
    uploaded_pdf = st.file_uploader("课程讲义、论文、官方文档或面试资料", type=["pdf"])
    if uploaded_pdf:
        file_id = f"{uploaded_pdf.name}-{uploaded_pdf.size}"
        if st.session_state["pdf_file_id"] != file_id:
            st.session_state["pdf_pages"] = read_pdf_pages(uploaded_pdf)
            st.session_state["pdf_name"] = uploaded_pdf.name
            st.session_state["pdf_file_id"] = file_id
        if st.session_state["pdf_pages"]:
            st.success(f"已读取 {st.session_state['pdf_name']}，共 {len(st.session_state['pdf_pages'])} 页可用文本。")
            col1, col2, col3 = st.columns(3)
            if col1.button("提取知识点", use_container_width=True):
                st.session_state["draft_input"] = "请提取这份 PDF 的核心概念、关键术语、重要公式、代码示例和学习重点"
                st.rerun()
            if col2.button("生成学习路线", use_container_width=True):
                st.session_state["draft_input"] = "请根据这份 PDF 生成一个 4 天学习路线"
                st.rerun()
            if col3.button("总结文档", use_container_width=True):
                st.session_state["draft_input"] = "请总结这份 PDF 的核心内容"
                st.rerun()

    st.divider()
    st.markdown("**上传代码 / 分析项目**")
    uploaded_code_files = st.file_uploader(
        "上传 .py、.ipynb、.md、.txt 文件",
        type=["py", "ipynb", "md", "txt"],
        accept_multiple_files=True,
    )
    if uploaded_code_files:
        file_id = "|".join([f"{file.name}-{file.size}" for file in uploaded_code_files])
        if st.session_state["code_file_id"] != file_id:
            code_context, code_files = build_code_context(uploaded_code_files)
            st.session_state["code_context"] = code_context
            st.session_state["code_files"] = code_files
            st.session_state["code_file_id"] = file_id
            st.session_state["code_action"] = ""
        st.success(f"已读取 {len(st.session_state['code_files'])} 个代码文件。")

    col1, col2, col3 = st.columns(3)
    if col1.button("分析项目结构", use_container_width=True):
        if not st.session_state["code_context"]:
            code_context, code_files = collect_project_snapshot()
            st.session_state["code_context"] = code_context
            st.session_state["code_files"] = code_files
        st.session_state["code_action"] = "structure"
        st.session_state["draft_input"] = "请分析这些代码的项目结构，说明每个主要文件和目录的作用"
        st.rerun()
    if col2.button("代码优化建议", use_container_width=True):
        if not st.session_state["code_context"]:
            code_context, code_files = collect_project_snapshot()
            st.session_state["code_context"] = code_context
            st.session_state["code_files"] = code_files
        st.session_state["code_action"] = "optimize"
        st.session_state["draft_input"] = "请给出这些代码的优化建议，包括模块拆分、重复代码、异常处理和可维护性"
        st.rerun()
    if col3.button("自动生成 README", use_container_width=True):
        code_context, code_files = collect_project_snapshot()
        st.session_state["code_context"] = code_context
        st.session_state["code_files"] = code_files
        st.session_state["code_action"] = "readme"
        st.session_state["draft_input"] = "请根据当前项目自动生成 README"
        st.rerun()

with st.expander("学习模式", expanded=False):
    mode = st.radio(
        "选择 AI 回复的深度和节奏",
        MODES,
        index=MODES.index(st.session_state["selected_mode"]) if st.session_state["selected_mode"] in MODES else 0,
        horizontal=True,
    )
    st.caption(MODE_HELP.get(mode, ""))

st.markdown("<div class='section-title'>学习对话</div>", unsafe_allow_html=True)
if active_conversation and active_conversation.get("messages"):
    for message in active_conversation.get("messages", []):
        if message.get("role") == "user":
            render_user_message(message.get("content", ""))
        else:
            render_ai_card(message.get("content", ""), message.get("metadata", {}))
else:
    st.info("你可以直接输入问题，也可以先点击上方的“继续学习”“总结上次内容”或导入资料。")

st.text_area(
    "输入消息",
    key="draft_input",
    height=130,
    placeholder="输入你的问题，例如：我想学习 LangChain 的核心概念",
)

if st.button("发送", type="primary", disabled=not active_conversation_id):
    user_input = st.session_state["draft_input"]
    if not user_input.strip():
        st.warning("请先输入消息")
        st.stop()

    st.session_state["selected_mode"] = mode
    active_conversation = get_conversation(active_conversation_id)
    previous_question, previous_answer, previous_metadata = get_last_messages(active_conversation)
    pdf_context, pdf_sources = retrieve_pdf_context(user_input, st.session_state.get("pdf_pages", []))

    status_box = st.empty()
    output_box = st.empty()
    debug_box = st.empty()

    initial_state = {
        "user_input": user_input,
        "mode": mode,
        "task_type": "",
        "plan": "",
        "answer": "",
        "memory_note": "",
        "learning_summary": "",
        "next_suggestion": "",
        "progress_percent": 0,
        "completed_topics": [],
        "unfinished_topics": [],
        "continue_from_history": bool(active_conversation and active_conversation.get("messages")),
        "previous_question": previous_question,
        "previous_mode": previous_metadata.get("mode", ""),
        "previous_plan": previous_metadata.get("plan", ""),
        "previous_answer": previous_answer,
        "pdf_name": st.session_state.get("pdf_name", ""),
        "pdf_context": pdf_context,
        "pdf_sources": pdf_sources,
        "code_context": st.session_state.get("code_context", ""),
        "code_files": st.session_state.get("code_files", []),
        "code_action": st.session_state.get("code_action", ""),
    }
    final_state = initial_state.copy()
    execution_logs = []

    with st.spinner("AI 正在思考..."):
        for event in graph.stream(initial_state, config={"configurable": {"thread_id": active_conversation_id}}):
            for node_name, node_output in event.items():
                final_state.update(node_output)
                execution_logs.append(build_workflow_logs(node_name, node_output))

                if st.session_state.get("developer_mode"):
                    with debug_box.container():
                        with st.expander("开发者调试信息", expanded=False):
                            st.write(f"conversation_id: {active_conversation_id}")
                            st.subheader("节点执行日志")
                            st.code("\n".join(execution_logs), language="text")
                            st.subheader("当前 State")
                            st.json(final_state)

                if node_name == "router":
                    status_box.info("正在理解你的问题...")
                elif node_name == "planner":
                    status_box.info("正在整理学习思路...")
                elif node_name in ["teacher", "code", "project", "document", "code_study"]:
                    status_box.success("AI 正在生成内容...")
                elif node_name == "review":
                    status_box.info("正在生成学习复盘...")
                elif node_name == "memory":
                    status_box.info("正在保存学习记录...")

                if node_name in ["planner", "teacher", "code", "project", "document", "code_study", "review", "memory"]:
                    with output_box.container():
                        render_node_output(node_name, node_output, pdf_sources)

    if final_state.get("code_action") == "readme" and final_state.get("answer"):
        save_readme(final_state["answer"])
        st.success("README.md 已生成并写入项目根目录。")

    metadata = {
        "mode": mode,
        "task_type": final_state.get("task_type", ""),
        "plan": final_state.get("plan", ""),
        "learning_summary": final_state.get("learning_summary", ""),
        "next_suggestion": final_state.get("next_suggestion", ""),
        "progress_percent": final_state.get("progress_percent", 0),
        "completed_topics": final_state.get("completed_topics", []),
        "unfinished_topics": final_state.get("unfinished_topics", []),
        "memory_note": final_state.get("memory_note", ""),
        "time": date.today().isoformat(),
        "pdf_name": final_state.get("pdf_name", ""),
        "pdf_sources": final_state.get("pdf_sources", []),
        "code_files": final_state.get("code_files", []),
        "code_action": final_state.get("code_action", ""),
        "execution_logs": execution_logs,
        "final_state": final_state,
    }

    append_message(active_conversation_id, "user", user_input)
    append_message(active_conversation_id, "assistant", final_state.get("answer", ""), metadata)
    st.session_state["clear_draft_input"] = True
    st.session_state["code_action"] = ""
    status_box.success("完成")
    st.rerun()
