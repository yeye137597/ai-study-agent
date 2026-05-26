# AI Study Agent

English | [中文](README_CN.md)

A LangGraph-based AI learning assistant with task routing, document parsing, multi-turn memory, and developer debugging workflows.

---

## Overview

AI Study Agent is a workflow-driven AI learning assistant built with LangGraph and Streamlit.

The project supports multiple learning modes including:

- AI knowledge learning
- PDF document analysis
- Code file analysis
- Multi-turn conversation workflows
- Developer debugging mode

The system is designed to explore practical AI Agent workflows using LLM-based applications.

---

## Features

- Task routing with LangGraph
- Multi-turn conversational workflows
- PDF document parsing
- Code file analysis
- Local memory persistence
- Developer debugging mode
- Streamlit-based WebUI
- Workflow state visualization

---

## Tech Stack

- Python
- LangChain
- LangGraph
- Streamlit
- OpenAI API
- DeepSeek API
- FAISS
- PyPDF
- python-dotenv

---

## Project Structure

```text
.
├── app.py                 # Streamlit frontend
├── graph.py               # LangGraph workflow
├── memory/                # Conversation memory
├── agents/                # Agent modules
├── prompts/               # Prompt templates
├── requirements.txt       # Dependencies
└── README.md
```

---

## Installation

```bash
git clone https://github.com/yeye137597/ai-study-agent

cd ai-study-agent

pip install -r requirements.txt
```

---

## Usage

```bash
streamlit run app.py
```

---

## Demo

### Chat Interface

(Add screenshot here)

### Workflow Debugging

(Add screenshot here)

---

## Roadmap

- [ ] Add online deployment support
- [ ] Add vector database integration
- [ ] Improve Agent memory management
- [ ] Add multi-agent workflows
- [ ] Add streaming response support

---

## Author

Yefan Ye

AI Application Developer focused on AI Agents, RAG systems, and workflow-driven LLM applications.
