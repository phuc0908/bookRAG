"""
query.py — BƯỚC 2: Hỏi đáp với BookRAG Agent

Chạy:
  python query.py                          # Chế độ chat tương tác
  python query.py -q "Từ Hải là ai?"      # Hỏi một câu
  python query.py --demo                   # Chạy 3 câu demo tự động
  python query.py --compare                # So sánh BookRAG vs flat RAG
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from src.book_index import BookIndex
from src.agent import BookRAGAgent

console = Console()


def load_embed_fn():
    from sentence_transformers import SentenceTransformer
    console.print("[cyan]Loading embedding model...[/cyan]", end=" ")
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    console.print("[green]OK[/green]")
    def embed(text: str) -> list[float]:
        return model.encode(text, normalize_embeddings=True).tolist()
    return embed


def load_index(path: str) -> BookIndex:
    if not Path(path).exists():
        console.print(f"[red]Không tìm thấy BookIndex tại '{path}'[/red]")
        console.print("Hãy chạy trước: [cyan]python build_index.py[/cyan]")
        sys.exit(1)
    console.print(f"[cyan]Loading BookIndex từ {path}...[/cyan]", end=" ")
    index = BookIndex.load(path)
    console.print("[green]OK[/green]")
    return index


def run_demo(agent: BookRAGAgent):
    """Chạy 3 câu hỏi demo minh họa 3 query type."""
    demo_questions = [
        # Single-hop: về một nhân vật cụ thể
        ("SINGLE-HOP", "Kushida Kikyou là người như thế nào?"),
        # Multi-hop: cần kết hợp thông tin qua quan hệ
        ("MULTI-HOP",  "Tại sao Ryuuen lại phát hiện ra Ayanokoji?"),
        # Global: cần tổng hợp toàn tác phẩm
        ("GLOBAL",     "Tóm tắt hệ thống và cơ chế hoạt động của ngôi trường"),
    ]

    console.print(Panel(
        "[bold]Chạy 3 câu hỏi demo — minh họa 3 loại query của BookRAG[/bold]\n"
        "  Single-hop → Selector\n"
        "  Multi-hop  → Reasoner\n"
        "  Global     → Skyline Ranker",
        border_style="magenta"
    ))

    for expected_type, question in demo_questions:
        console.print(f"\n[dim]Expected type: {expected_type}[/dim]")
        agent.query(question)
        input("\n[Enter để tiếp tục...]")


def run_compare(agent: BookRAGAgent, question: str):
    """
    So sánh trực quan: BookRAG vs RAG truyền thống (flat top-K)
    trên cùng một câu hỏi.
    """
    from src.operators import Selector
    from src.operators import cosine_similarity

    console.print(Panel(
        f"[bold]So sánh BookRAG vs Flat RAG[/bold]\nQuery: {question}",
        border_style="cyan"
    ))

    embed_fn = agent.embed_fn

    # ── Flat RAG: lấy top-K leaf chunks theo cosine similarity ──
    console.print("\n[yellow]=== FLAT RAG (top-K chunks) ===[/yellow]")
    query_vec = embed_fn(question)
    all_leaves = agent.index.tree.leaf_nodes()
    flat_scored = []
    for node in all_leaves:
        if node.embedding is None:
            node.embedding = embed_fn(f"{node.title}\n{node.content}")
        score = cosine_similarity(query_vec, node.embedding)
        flat_scored.append((score, node))
    flat_scored.sort(reverse=True)
    flat_top = flat_scored[:3]

    console.print("Top-3 chunks (flat similarity):")
    for score, node in flat_top:
        console.print(f"  [{score:.3f}] {node.title}")
        console.print(f"    {node.content[:150].strip()[:150]}...")

    # ── BookRAG: dùng agent với operator phù hợp ────────────────
    console.print("\n[green]=== BOOKRAG (agent + operator) ===[/green]")
    result = agent.query(question)

    # ── Tóm tắt khác biệt ────────────────────────────────────────
    console.print(Panel(
        f"[bold]Tổng kết:[/bold]\n"
        f"  Flat RAG  : {len(flat_top)} chunks, chỉ dùng cosine similarity\n"
        f"  BookRAG   : {len(result['retrieved_nodes'])} nodes, "
        f"query_type={result['query_type']}, "
        f"dùng cấu trúc cây + KG + GT-Links",
        border_style="cyan"
    ))


def interactive_loop(agent: BookRAGAgent):
    """Chế độ chat tương tác."""
    console.print(Panel(
        "[bold]BookRAG Chat Interface[/bold]\n"
        "Gõ câu hỏi bằng tiếng Việt. Gõ 'thoát' để thoát.\n"
        "Ví dụ:\n"
        "  • Kushida là người như thế nào?    [single-hop]\n"
        "  • Tại sao Ryuuen phát hiện Ayanokoji?  [multi-hop]\n"
        "  • Tóm tắt hệ thống điểm S          [global]",
        border_style="blue"
    ))

    while True:
        try:
            question = input("\nBạn: ").strip()
            if not question:
                continue
            if question.lower() in ("thoát", "quit", "exit", "q"):
                console.print("[dim]Tạm biệt![/dim]")
                break
            agent.query(question)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Tạm biệt![/dim]")
            break


def main():
    parser = argparse.ArgumentParser(description="BookRAG Query Interface")
    parser.add_argument("-q", "--question", help="Câu hỏi trực tiếp")
    parser.add_argument("--index", default="bookindex.pkl", help="File BookIndex")
    parser.add_argument("--demo", action="store_true", help="Chạy 3 câu hỏi demo")
    parser.add_argument("--compare", action="store_true",
                        help="So sánh BookRAG vs Flat RAG")
    parser.add_argument("--compare-query", default="Ai đã phát hiện ra bí mật của Ayanokoji?",
                        help="Câu hỏi dùng để so sánh")
    args = parser.parse_args()

    console.print("\n" + "="*55)
    console.print("[bold magenta]  BookRAG — QUERY INTERFACE[/bold magenta]")
    console.print("  Paper: arXiv 2512.03413")
    console.print("="*55)

    # Khởi tạo
    embed_fn = load_embed_fn()
    index    = load_index(args.index)
    agent    = BookRAGAgent(index, embed_fn)
    agent.embed_fn = embed_fn  # lưu để dùng trong compare

    index.summary()

    if args.demo:
        run_demo(agent)
    elif args.compare:
        run_compare(agent, args.compare_query)
    elif args.question:
        agent.query(args.question)
    else:
        interactive_loop(agent)


if __name__ == "__main__":
    main()
