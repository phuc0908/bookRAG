"""
src/agent.py

BookRAG Agent — lấy cảm hứng từ Information Foraging Theory (IFT)

Paper: arXiv 2512.03413
"BookRAG: A Hierarchical Structure-aware Index-based Approach
 for Retrieval-Augmented Generation on Complex Documents"

Agent phân loại query thành 3 loại rồi gọi operator phù hợp:

  Single-hop → Selector
    Câu hỏi về một thực thể/sự kiện cụ thể, chỉ cần 1 section
    Ví dụ: "Thúy Kiều là ai?", "Lâm Tri ở đâu?"

  Multi-hop → Reasoner
    Câu hỏi cần kết hợp thông tin từ nhiều section qua quan hệ
    Ví dụ: "Ai đã lừa dẫn đến cái chết của Từ Hải?"

  Global → Skyline_Ranker
    Câu hỏi về toàn bộ tài liệu, cần tổng hợp nhiều phần
    Ví dụ: "Tóm tắt tác phẩm", "Truyện Kiều có những chủ đề gì?"

Information Foraging Theory:
  Động vật tìm thức ăn theo vết thơm (scent) — dừng khi vết thơm yếu dần.
  Agent tìm thông tin theo "information scent" — dừng khi relevance score
  không còn tăng nữa. Điều này giúp tránh lãng phí token vào nội dung
  không liên quan.
"""

from __future__ import annotations

import os
import re
from enum import Enum, auto
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from .book_index import BookIndex, TreeNode
from .operators import Selector, Reasoner, SkylineRanker

console = Console()


# ══════════════════════════════════════════════════════════════
# QUERY TYPES
# ══════════════════════════════════════════════════════════════

class QueryType(Enum):
    SINGLE_HOP = auto()   # Cần 1 section cụ thể
    MULTI_HOP  = auto()   # Cần kết hợp nhiều section qua quan hệ
    GLOBAL     = auto()   # Cần tổng hợp toàn tài liệu


# ══════════════════════════════════════════════════════════════
# QUERY CLASSIFIER
# ══════════════════════════════════════════════════════════════

# Từ khóa gợi ý loại query
_GLOBAL_SIGNALS = [
    "tóm tắt", "toàn bộ", "tổng quan", "overview", "summarize",
    "chủ đề chính", "nội dung chính", "toàn tác phẩm", "khái quát",
    "giới thiệu", "describe overall", "nói về gì", "về gì",
]

_MULTI_HOP_SIGNALS = [
    "ai đã", "người nào", "vì sao", "tại sao", "nguyên nhân",
    "dẫn đến", "mối quan hệ", "liên quan", "kết quả của",
    "hậu quả", "do ai", "gây ra", "ai làm", "connection between",
    "relationship between", "how did", "why did", "what caused",
]

_RELATION_WORDS = [
    "yêu", "ghét", "cứu", "giết", "lừa", "bán", "cưới",
    "hại", "chuộc", "bắt", "trốn", "gặp", "tha",
]


def classify_query(query: str, index: BookIndex) -> QueryType:
    """
    Phân loại query dựa trên heuristic ngôn ngữ + cấu trúc query.

    Trong paper gốc, bước này dùng LLM để phân loại chính xác hơn.
    Demo này dùng rule-based để chạy không cần API key.
    """
    q = query.lower()

    # ── Global signals ─────────────────────────────────────────
    for signal in _GLOBAL_SIGNALS:
        if signal in q:
            return QueryType.GLOBAL

    # ── Multi-hop signals ──────────────────────────────────────
    # Cách 1: từ khóa gợi ý multi-hop
    for signal in _MULTI_HOP_SIGNALS:
        if signal in q:
            # Kiểm tra có nhắc đến entity không
            for entity in index.links.all_entities():
                if entity.lower() in q:
                    return QueryType.MULTI_HOP

    # Cách 2: đề cập 2+ entity + từ quan hệ → multi-hop
    mentioned_entities = [e for e in index.links.all_entities() if e.lower() in q]
    has_relation_word = any(w in q for w in _RELATION_WORDS)
    if len(mentioned_entities) >= 2 or (len(mentioned_entities) >= 1 and has_relation_word):
        return QueryType.MULTI_HOP

    # ── Default: Single-hop ────────────────────────────────────
    return QueryType.SINGLE_HOP


# ══════════════════════════════════════════════════════════════
# LLM ANSWER GENERATOR
# ══════════════════════════════════════════════════════════════

def _build_context(nodes: list[TreeNode], index: BookIndex) -> str:
    """
    Ghép nội dung các node được retrieve thành context cho LLM.
    Giữ thông tin phân cấp (đường dẫn từ root) để LLM hiểu ngữ cảnh.
    """
    parts = []
    for i, node in enumerate(nodes):
        path = " > ".join(node.path_from_root())
        content = node.content or node.full_context()
        parts.append(f"[Nguồn {i+1}: {path}]\n{content}")
    return "\n\n".join(parts)


def generate_answer(query: str, nodes: list[TreeNode],
                    index: BookIndex) -> str:
    """
    Sinh câu trả lời từ retrieved nodes.
    Đọc LLM_PROVIDER từ .env để chọn provider:
      - gemini  → Google Gemini (free, khuyến nghị)
      - groq    → Groq (free, nhanh nhất)
      - openai  → OpenAI GPT (trả phí)
      - (trống) → Demo mode, không cần key
    """
    context  = _build_context(nodes, index)
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()

    if provider == "gemini":
        return _gemini_answer(query, context)
    elif provider == "groq":
        return _groq_answer(query, context)
    elif provider == "openai":
        return _openai_answer(query, context)
    else:
        return _demo_answer(query, context, nodes)


def _make_prompt(query: str, context: str) -> str:
    return (
        "Bạn là trợ lý đọc sách thông minh sử dụng hệ thống BookRAG.\n"
        "Trả lời câu hỏi CHỈ dựa trên ngữ cảnh từ sách được cung cấp.\n"
        "Nếu không có thông tin trong ngữ cảnh, hãy nói rõ ràng.\n"
        "Trả lời bằng tiếng Việt, rõ ràng và có cấu trúc.\n\n"
        f"Ngữ cảnh từ sách (truy xuất bằng BookRAG):\n{context}\n\n"
        f"Câu hỏi: {query}\n\nCâu trả lời:"
    )


def _gemini_answer(query: str, context: str) -> str:
    """Google Gemini — free 15 req/phút, 1500 req/ngày."""
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("Thiếu GEMINI_API_KEY trong file .env")

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    model    = genai.GenerativeModel(model_name)
    response = model.generate_content(
        _make_prompt(query, context),
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=800,
        )
    )
    return response.text.strip()


def _groq_answer(query: str, context: str) -> str:
    """Groq — free tier, tốc độ cực nhanh (LLaMA 3 / Gemma 2)."""
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("Thiếu GROQ_API_KEY trong file .env")

    client   = Groq(api_key=api_key)
    model    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _make_prompt(query, context)}],
        temperature=0.3,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()


def _openai_answer(query: str, context: str) -> str:
    """OpenAI GPT — trả phí."""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("Thiếu OPENAI_API_KEY trong file .env")

    client   = OpenAI(api_key=api_key)
    model    = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _make_prompt(query, context)}],
        temperature=0.3,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()


def _demo_answer(query: str, context: str, nodes: list[TreeNode]) -> str:
    """Demo mode: không cần API key, hiển thị sections tìm được."""
    sections = []
    for node in nodes:
        path    = " > ".join(node.path_from_root())
        preview = node.content[:300].strip() + ("..." if len(node.content) > 300 else "")
        sections.append(f"📍 {path}\n{preview}")
    joined = "\n\n".join(sections)
    return (
        "[DEMO MODE — chưa cấu hình LLM_PROVIDER trong .env]\n"
        f"BookRAG đã retrieve {len(nodes)} sections liên quan:\n\n"
        f"{joined}"
    )


# ══════════════════════════════════════════════════════════════
# BOOKRAG AGENT
# ══════════════════════════════════════════════════════════════

class BookRAGAgent:
    """
    Agent trung tâm của BookRAG, lấy cảm hứng từ Information Foraging Theory.

    Workflow:
    1. Nhận query từ user
    2. Classify query → SINGLE_HOP / MULTI_HOP / GLOBAL
    3. Gọi operator phù hợp → retrieve relevant TreeNodes
    4. Build context từ nodes
    5. Gọi LLM (hoặc demo mode) → sinh câu trả lời

    IFT (Information Foraging Theory):
    Giống như thú săn mồi, agent "đánh mùi" thông tin (information scent)
    qua cấu trúc tài liệu thay vì quét toàn bộ — hiệu quả hơn, ít tốn
    token hơn, chính xác hơn.
    """

    def __init__(self, index: BookIndex, embed_fn):
        self.index = index
        self.embed_fn = embed_fn
        self.selector = Selector(embed_fn, top_k=3)
        self.reasoner = Reasoner(embed_fn, hop_depth=2, top_k=4)
        self.ranker   = SkylineRanker(embed_fn, top_k=5)

    def query(self, question: str, verbose: bool = True) -> dict:
        """
        Thực hiện BookRAG query.

        Returns:
          {
            "question": str,
            "query_type": str,
            "retrieved_nodes": list[TreeNode],
            "answer": str,
          }
        """
        console.print(f"\n{'='*55}")
        console.print(f"[bold blue]QUERY:[/bold blue] {question}")
        console.print('='*55)

        # ── Bước 1: Classify ──────────────────────────────────────
        query_type = classify_query(question, self.index)
        type_labels = {
            QueryType.SINGLE_HOP: "[green]SINGLE-HOP[/green] → Selector",
            QueryType.MULTI_HOP:  "[yellow]MULTI-HOP[/yellow] → Reasoner",
            QueryType.GLOBAL:     "[magenta]GLOBAL[/magenta] → Skyline Ranker",
        }
        console.print(f"[bold]Query Type:[/bold] {type_labels[query_type]}")

        # ── Bước 2: Retrieve ──────────────────────────────────────
        if query_type == QueryType.SINGLE_HOP:
            nodes = self.selector.run(question, self.index)
        elif query_type == QueryType.MULTI_HOP:
            nodes = self.reasoner.run(question, self.index)
        else:
            nodes = self.ranker.run(question, self.index)

        # ── Bước 3: Generate ──────────────────────────────────────
        console.print(f"\n[bold]Generate:[/bold] Sinh câu trả lời từ {len(nodes)} sections...")
        answer = generate_answer(question, nodes, self.index)

        # ── Bước 4: Hiển thị ──────────────────────────────────────
        console.print(Panel(
            answer,
            title=f"[bold green]Câu trả lời[/bold green] (via BookRAG {query_type.name})",
            border_style="green",
            padding=(1, 2)
        ))

        return {
            "question":       question,
            "query_type":     query_type.name,
            "retrieved_nodes": nodes,
            "answer":         answer,
        }
