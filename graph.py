from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.3,
    streaming=True,
)


class StudyState(TypedDict):
    user_input: str
    mode: str
    task_type: str
    plan: str
    answer: str
    memory_note: str
    learning_summary: str
    next_suggestion: str
    progress_percent: int
    completed_topics: list[str]
    unfinished_topics: list[str]
    continue_from_history: bool
    previous_question: str
    previous_mode: str
    previous_plan: str
    previous_answer: str
    pdf_name: str
    pdf_context: str
    pdf_sources: list[int]
    code_context: str
    code_files: list[str]
    code_action: str


LANGGRAPH_TOPICS = [
    "State",
    "Node",
    "Edge",
    "Conditional Edge",
    "Streaming",
    "Persistence",
    "Human-in-the-loop",
    "Multi-Agent",
]


def router_node(state: StudyState):
    text = state["user_input"]

    if state.get("code_context"):
        task_type = "code_study"
    elif state.get("pdf_context"):
        task_type = "document"
    elif state.get("continue_from_history"):
        task_type = "learn"
    elif "代码" in text or "报错" in text or "def " in text or "class " in text:
        task_type = "code"
    elif "项目" in text or "推荐" in text:
        task_type = "project"
    else:
        task_type = "learn"

    return {"task_type": task_type}


def planner_node(state: StudyState):
    if state.get("task_type") == "code_study":
        prompt = f"""
你是一个代码学习规划助手。

用户需求：{state["user_input"]}
代码文件：{state["code_files"]}

请给出阅读这批代码的学习计划，要求：
1. 先说明建议从哪个文件开始看。
2. 按模块拆分阅读顺序。
3. 给出今天可以完成的代码理解任务。
4. 如果用户要生成 README，只给出 README 写作思路。
"""
    elif state.get("task_type") == "document":
        prompt = f"""
你是一个文档学习规划助手。

用户上传的文档：{state["pdf_name"]}
用户需求：{state["user_input"]}

文档片段：
{state["pdf_context"]}

请基于文档内容生成学习计划，要求：
1. 不要脱离文档内容。
2. 如果用户是在问答，给出简短阅读路径。
3. 如果用户要求学习路线，按天拆分任务。
4. 引用文档页码，例如：根据第 3 页内容。
"""
    elif state.get("continue_from_history"):
        prompt = f"""
你是一个 AI 学习规划助手。

用户想基于某一次学习记录继续学习，请你生成“下一步学习任务”。

当前学习模式：{state["mode"]}

上次问题：
{state["previous_question"]}

上次学习模式：
{state["previous_mode"]}

上次学习计划：
{state["previous_plan"]}

上次回答：
{state["previous_answer"]}

用户本次补充需求：
{state["user_input"]}

请生成一个清晰、可执行的下一步学习任务，要求：
1. 先总结上次已经学到什么。
2. 给出本次下一步学习目标。
3. 拆成 3-5 个小任务。
4. 每个小任务都要有完成标准。
5. 给出一个今天可以完成的小练习。
"""
    else:
        prompt = f"""
你是一个 AI 学习规划助手。

用户学习模式：{state["mode"]}
用户需求：{state["user_input"]}

请生成一个清晰的学习计划，要求：
1. 分阶段。
2. 每个阶段说明要学什么。
3. 每个阶段给出练习任务。
4. 适合初学者。
"""

    result = llm.invoke(prompt)
    return {"plan": result.content}


def teacher_node(state: StudyState):
    prompt = f"""
你是一个耐心的 AI 老师。

学习计划：
{state["plan"]}

用户问题：
{state["user_input"]}

请用通俗但专业的方式讲解。
"""

    full_response = ""

    for chunk in llm.stream(prompt):
        if chunk.content:
            full_response += chunk.content
            yield {"answer": full_response}


def document_node(state: StudyState):
    prompt = f"""
你是一个严谨的文档学习助手。你只能根据用户上传的 PDF 内容回答。

文档名称：{state["pdf_name"]}
相关页码：{state["pdf_sources"]}

用户问题：
{state["user_input"]}

文档内容：
{state["pdf_context"]}

请回答用户问题，要求：
1. 必须基于文档内容回答，不要凭空编造。
2. 如果文档片段无法回答，就明确说“当前文档片段里没有足够信息”。
3. 回答中要写清楚引用来源，例如“根据第 3 页内容...”。
4. 如果用户要求总结，按要点输出。
5. 如果用户要求提取知识点，包含核心概念、关键术语、重要公式、代码示例、学习重点。
6. 如果用户要求学习路线，按天输出学习安排。
"""

    full_response = ""

    for chunk in llm.stream(prompt):
        if chunk.content:
            full_response += chunk.content
            yield {"answer": full_response}


def code_study_node(state: StudyState):
    readme_extra = ""
    if state.get("code_action") == "readme":
        readme_extra = """
用户要自动生成 README。请直接输出完整 README.md 内容，必须包含：
1. 项目介绍
2. 功能特点
3. 技术栈
4. 运行方法
5. 项目结构
6. 效果截图
7. 未来计划
不要把 README 包在 Markdown 代码块里。
"""

    prompt = f"""
你是一个适合求职展示的代码学习助手。

用户需求：
{state["user_input"]}

代码文件：
{state["code_files"]}

代码内容：
{state["code_context"]}

{readme_extra}

如果不是生成 README，请按用户需求输出：
1. 项目结构分析：说明每个主要文件/目录的作用。
2. 代码学习说明：解释这批代码的核心流程。
3. 代码优化建议：包含当前代码问题、可以拆分的模块、重复代码、异常处理、可维护性建议。
4. 求职展示建议：说明这段项目经历可以怎么写。
"""

    full_response = ""

    for chunk in llm.stream(prompt):
        if chunk.content:
            full_response += chunk.content
            yield {"answer": full_response}


def code_node(state: StudyState):
    prompt = f"""
你是一个 Python / LangChain / LangGraph 代码讲解助手。

用户输入：
{state["user_input"]}

请按下面结构回答：
1. 这段代码/报错在做什么。
2. 核心问题是什么。
3. 逐行解释关键代码。
4. 给出修改建议。
"""

    result = llm.invoke(prompt)
    return {"answer": result.content}


def project_node(state: StudyState):
    prompt = f"""
你是一个 AI 项目推荐助手。

用户当前需求：
{state["user_input"]}

请推荐适合当前阶段的项目，要求：
1. 项目名称。
2. 项目功能。
3. 技术栈。
4. 简历写法。
5. 下一步怎么做。
"""

    result = llm.invoke(prompt)
    return {"answer": result.content}


def review_node(state: StudyState):
    prompt = f"""
你是一个 AI 学习复盘助手。

用户问题：
{state["user_input"]}

学习计划：
{state["plan"]}

Agent 回答：
{state["answer"]}

请生成两段内容：

本次学习总结：
用 3-5 句话总结用户本次学到了什么。

下一步建议：
用编号列表给出 3 个下一步学习任务。
"""

    result = llm.invoke(prompt)
    content = result.content

    if "下一步建议" in content:
        summary, suggestion = content.split("下一步建议", 1)
        learning_summary = summary.replace("本次学习总结", "").strip("：:\n ")
        next_suggestion = "下一步建议" + suggestion
    else:
        learning_summary = content
        next_suggestion = ""

    progress_text = " ".join(
        [
            state["user_input"],
            state["plan"],
            state["answer"],
        ]
    ).lower()

    completed_topics = [
        topic
        for topic in LANGGRAPH_TOPICS
        if topic.lower() in progress_text or topic.replace("-", " ").lower() in progress_text
    ]

    if not completed_topics and "langgraph" in progress_text:
        completed_topics = ["State", "Node", "Edge"]

    unfinished_topics = [
        topic for topic in LANGGRAPH_TOPICS if topic not in completed_topics
    ]
    progress_percent = int(len(completed_topics) / len(LANGGRAPH_TOPICS) * 100)

    return {
        "learning_summary": learning_summary,
        "next_suggestion": next_suggestion,
        "progress_percent": progress_percent,
        "completed_topics": completed_topics,
        "unfinished_topics": unfinished_topics,
    }


def memory_node(state: StudyState):
    note = f"""
本轮学习记录：
- 学习模式：{state["mode"]}
- 任务类型：{state["task_type"]}
- 用户问题：{state["user_input"]}
"""

    if state.get("continue_from_history"):
        note += f"- 承接记录：{state['previous_question']}\n"

    if state.get("pdf_name"):
        note += f"- 使用文档：{state['pdf_name']}\n"
        note += f"- 引用页码：{state['pdf_sources']}\n"

    if state.get("code_files"):
        note += f"- 使用代码文件：{', '.join(state['code_files'])}\n"

    return {"memory_note": note}


def route_by_type(
    state: StudyState,
) -> Literal["teacher", "code", "project", "document", "code_study"]:
    if state["task_type"] == "code_study":
        return "code_study"
    if state["task_type"] == "document":
        return "document"
    if state["task_type"] == "code":
        return "code"
    if state["task_type"] == "project":
        return "project"
    return "teacher"


builder = StateGraph(StudyState)

builder.add_node("router", router_node)
builder.add_node("planner", planner_node)
builder.add_node("teacher", teacher_node)
builder.add_node("code", code_node)
builder.add_node("project", project_node)
builder.add_node("document", document_node)
builder.add_node("code_study", code_study_node)
builder.add_node("review", review_node)
builder.add_node("memory", memory_node)

builder.add_edge(START, "router")
builder.add_edge("router", "planner")

builder.add_conditional_edges(
    "planner",
    route_by_type,
    {
        "teacher": "teacher",
        "code": "code",
        "project": "project",
        "document": "document",
        "code_study": "code_study",
    },
)

builder.add_edge("teacher", "review")
builder.add_edge("code", "review")
builder.add_edge("project", "review")
builder.add_edge("document", "review")
builder.add_edge("code_study", "review")
builder.add_edge("review", "memory")
builder.add_edge("memory", END)

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)
