# AI Study Agent

一个基于 Streamlit、LangGraph 和 DeepSeek 的 AI 学习助手。项目提供多轮学习对话、PDF 文档辅助学习、代码/项目分析、学习复盘和本地历史记录能力，适合用来练习 AI Agent 应用开发和个人学习场景展示。

## 功能特点

- 多模式学习：快速了解、深入学习、项目驱动学习、面试模式。
- PDF 学习：上传 PDF 后提取相关页面内容，支持总结、知识点提取和学习路线生成。
- 代码学习：上传代码文件或读取当前项目快照，生成结构分析、优化建议和 README 草稿。
- LangGraph 工作流：通过 router、planner、teacher/code/project/document/review/memory 等节点组织 Agent 流程。
- 本地记忆：将学习会话保存到本地 JSON 文件，支持历史会话、重命名和删除。
- 开发者模式：可查看节点执行日志和当前状态，方便调试 Agent 流程。

## 技术栈

- Python
- Streamlit
- LangGraph
- LangChain DeepSeek
- pypdf
- python-dotenv

## 项目结构

```text
.
├── app.py                    # Streamlit 前端和交互入口
├── graph.py                  # LangGraph Agent 工作流
├── memory/
│   ├── memory_utils.py       # 本地会话读写工具
│   └── learning_state.py     # 预留学习状态模块
├── agents/                   # 预留 Agent 模块
├── prompts/                  # 预留 Prompt 模块
├── data/                     # 本地运行时数据目录，不建议提交私人历史
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量示例
└── README.md
```

## 快速开始

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，并填入自己的 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

注意：`.env` 包含敏感信息，已经被 `.gitignore` 忽略，不要上传到 GitHub。

### 4. 启动应用

```bash
streamlit run app.py
```

启动后在浏览器打开 Streamlit 输出的本地地址即可使用。

## 使用方式

1. 新建学习会话。
2. 选择学习模式。
3. 直接输入学习问题，或上传 PDF / 代码文件。
4. 查看 AI 生成的学习计划、讲解、代码分析和复盘建议。
5. 打开开发者模式可查看 LangGraph 节点日志。

## 上传 GitHub 前的注意事项

- 不要提交 `.env`、`.venv/`、`__pycache__/`、日志文件和个人学习历史。
- `data/learning_history.json` 是本地运行数据，默认被忽略。
- 如果需要展示效果，建议单独放置脱敏截图到 `docs/` 或 README 中。
- 如果计划长期维护，建议继续补充测试、拆分模块，并完善异常处理。

## 后续优化方向

- 将 `app.py` 中的 PDF 处理、项目扫描、UI 渲染拆成独立模块。
- 将 Prompt 文本迁移到 `prompts/`，方便维护和复用。
- 将 Agent 节点逻辑拆到 `agents/`，降低 `graph.py` 复杂度。
- 增加配置模块，统一管理模型名称、温度、数据路径和上下文长度。
- 增加基础测试，覆盖历史记录读写、PDF 文本提取和路由逻辑。

