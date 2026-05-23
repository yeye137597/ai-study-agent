import json
import os
from datetime import datetime
from uuid import uuid4


HISTORY_FILE = "data/learning_history.json"


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _read_raw_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_raw_history(data):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _legacy_record_to_conversation(record, index):
    conversation_id = record.get("conversation_id") or f"legacy-{index}"
    question = record.get("question", "").strip() or "未命名对话"
    answer = record.get("answer", "")
    created_at = record.get("time") or _now()

    messages = []
    if question:
        messages.append(
            {
                "role": "user",
                "content": question,
                "time": created_at,
            }
        )
    if answer:
        messages.append(
            {
                "role": "assistant",
                "content": answer,
                "time": created_at,
                "metadata": {
                    "mode": record.get("mode", ""),
                    "task_type": record.get("task_type", ""),
                    "plan": record.get("plan", ""),
                    "learning_summary": record.get("learning_summary", ""),
                    "next_suggestion": record.get("next_suggestion", ""),
                    "progress_percent": record.get("progress_percent", 0),
                    "completed_topics": record.get("completed_topics", []),
                    "unfinished_topics": record.get("unfinished_topics", []),
                    "memory_note": record.get("memory_note", ""),
                    "pdf_name": record.get("pdf_name", ""),
                    "pdf_sources": record.get("pdf_sources", []),
                    "code_files": record.get("code_files", []),
                    "code_action": record.get("code_action", ""),
                },
            }
        )

    return {
        "conversation_id": conversation_id,
        "title": question,
        "created_at": created_at,
        "updated_at": created_at,
        "messages": messages,
    }


def load_conversations():
    data = _read_raw_history()

    if isinstance(data, dict) and "conversations" in data:
        return data.get("conversations", [])

    if isinstance(data, list):
        return [
            _legacy_record_to_conversation(record, index)
            for index, record in enumerate(data)
            if isinstance(record, dict)
        ]

    return []


def save_conversations(conversations):
    _write_raw_history({"conversations": conversations})


def create_conversation(title="新对话"):
    conversations = load_conversations()
    now = _now()
    conversation = {
        "conversation_id": str(uuid4()),
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    conversations.append(conversation)
    save_conversations(conversations)
    return conversation


def get_latest_conversation():
    conversations = load_conversations()
    if not conversations:
        return None

    return sorted(
        conversations,
        key=lambda item: item.get("updated_at", item.get("created_at", "")),
    )[-1]


def get_conversation(conversation_id):
    for conversation in load_conversations():
        if conversation.get("conversation_id") == conversation_id:
            return conversation
    return None


def append_message(conversation_id, role, content, metadata=None):
    conversations = load_conversations()
    now = _now()

    for conversation in conversations:
        if conversation.get("conversation_id") == conversation_id:
            conversation.setdefault("messages", []).append(
                {
                    "role": role,
                    "content": content,
                    "time": now,
                    "metadata": metadata or {},
                }
            )
            conversation["updated_at"] = now

            if role == "user" and conversation.get("title") in ["新对话", "", None]:
                conversation["title"] = content.strip()[:30] or "未命名对话"

            save_conversations(conversations)
            return conversation

    return None


def delete_conversation(conversation_id):
    conversations = load_conversations()
    conversations = [
        conversation
        for conversation in conversations
        if conversation.get("conversation_id") != conversation_id
    ]
    save_conversations(conversations)


def rename_conversation(conversation_id, title):
    conversations = load_conversations()

    for conversation in conversations:
        if conversation.get("conversation_id") == conversation_id:
            conversation["title"] = title.strip() or "未命名对话"
            conversation["updated_at"] = _now()
            break

    save_conversations(conversations)


def load_history():
    return load_conversations()


def save_history(record):
    conversation_id = record.get("conversation_id")
    if not conversation_id:
        conversation = create_conversation(record.get("question", "新对话"))
        conversation_id = conversation["conversation_id"]

    append_message(conversation_id, "user", record.get("question", ""))
    append_message(
        conversation_id,
        "assistant",
        record.get("answer", ""),
        {
            key: value
            for key, value in record.items()
            if key not in {"question", "answer", "conversation_id"}
        },
    )
