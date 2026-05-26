# AI Study Agent

English | [中文](README_CN.md)

AI Study Agent is an AI learning assistant built with Streamlit, LangGraph, and DeepSeek.

The project supports multi-turn learning conversations, PDF-assisted learning, code/project analysis, learning review workflows, and local memory persistence.

It is designed for practicing AI Agent application development and showcasing practical LLM workflow systems.

---

## Features

### Multi-mode Learning

Supports multiple learning modes:

- Quick learning
- Deep learning
- Project-driven learning
- Interview preparation mode

### PDF Learning

- Upload PDF documents
- Extract related content
- Generate summaries
- Extract key knowledge points
- Create learning roadmaps

### Code Learning

- Upload code files
- Analyze project structures
- Generate optimization suggestions
- Generate README drafts

### LangGraph Workflow

The system organizes Agent workflows using nodes such as:

- router
- planner
- teacher
- code
- project
- document
- review
- memory

### Local Memory

- Save learning conversations locally as JSON files
- Support conversation history
- Rename and delete sessions

### Developer Mode

- View node execution logs
- Inspect workflow states
- Debug LangGraph workflows

---

## Tech Stack

- Python
- Streamlit
- LangGraph
- LangChain DeepSeek
- PyPDF
- python-dotenv

---

## Project Structure

```text
.
├── app.py                    # Streamlit frontend and interaction entry
├── graph.py                  # LangGraph Agent workflow
├── memory/
│   ├── memory_utils.py       # Local memory utilities
│   └── learning_state.py     # Reserved learning state module
├── agents/                   # Reserved Agent modules
├── prompts/                  # Reserved Prompt modules
├── data/                     # Local runtime data
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable example
└── README.md
```

---

## Quick Start

### 1. Create Virtual Environment

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

---

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and add your DeepSeek API Key:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Note:
`.env` contains sensitive information and should not be uploaded to GitHub.

---

### 4. Run the Application

```bash
streamlit run app.py
```

After launching, open the local Streamlit address in your browser.

---

## Usage

1. Create a new learning session
2. Select a learning mode
3. Ask questions or upload PDF/code files
4. Review AI-generated learning plans and code analysis
5. Enable developer mode to inspect LangGraph workflow logs

---

## Notes Before Uploading to GitHub

- Do not upload `.env`, `.venv/`, `__pycache__/`, logs, or personal learning history
- `data/learning_history.json` is ignored by default
- It is recommended to add anonymized screenshots for demonstrations

---

## Future Improvements

- Split PDF processing, project scanning, and UI rendering into separate modules
- Move prompts into `prompts/`
- Refactor Agent nodes into `agents/`
- Add centralized configuration management
- Improve test coverage
- Add streaming response support

---

## Author

Yefan Ye

AI Application Developer focused on AI Agents, RAG systems, and workflow-driven LLM applications.
