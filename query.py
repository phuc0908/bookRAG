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
    from src.operators import cosine_similarity
    from src.agent import generate_answer
    from rich.table import Table
    from rich import box

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

    # Bảng rank toàn bộ leaf nodes để tra cứu sau
    flat_rank_map = {n.node_id: (rank + 1, score) for rank, (score, n) in enumerate(flat_scored)}

    console.print(f"Top-3 / {len(flat_scored)} chunks (flat cosine similarity):")
    for score, node in flat_top:
        console.print(f"  [{score:.3f}] {node.title}")
        console.print(f"    {node.content[:150].strip()[:150]}...")

    flat_answer = generate_answer(question, [n for _, n in flat_top], agent.index)
    console.print(Panel(
        flat_answer,
        title="[yellow]Câu trả lời Flat RAG[/yellow]",
        border_style="yellow",
        padding=(1, 2),
    ))

    # ── BookRAG: dùng agent với operator phù hợp ────────────────
    console.print("\n[green]=== BOOKRAG (agent + operator) ===[/green]")
    result = agent.query(question)
    bookrag_nodes = result["retrieved_nodes"]

    # ── Phân tích khác biệt ──────────────────────────────────────
    flat_ids  = {n.node_id for _, n in flat_top}
    book_ids  = {n.node_id for n in bookrag_nodes}
    common    = flat_ids & book_ids
    only_flat = flat_ids - book_ids
    only_book = book_ids - flat_ids

    # Gộp tất cả nodes cần hiển thị
    node_map: dict = {}
    for rank, (score, n) in enumerate(flat_top):
        node_map[n.node_id] = {"node": n, "flat_rank": rank + 1, "flat_score": score, "book_rank": None}
    for rank, n in enumerate(bookrag_nodes):
        if n.node_id not in node_map:
            fr, fs = flat_rank_map.get(n.node_id, (None, 0.0))
            node_map[n.node_id] = {"node": n, "flat_rank": fr, "flat_score": fs, "book_rank": rank + 1}
        else:
            node_map[n.node_id]["book_rank"] = rank + 1

    def _sort_key(item):
        nid, info = item
        if nid in common:    return (0, info["flat_rank"] or 99)
        if nid in only_flat: return (1, info["flat_rank"] or 99)
        return (2, info["book_rank"] or 99)

    console.print("\n[bold cyan]══ Phân tích chi tiết: ai tìm thấy gì? ══[/bold cyan]")
    tbl = Table(
        title="Nodes truy xuất được", box=box.ROUNDED, show_lines=True,
        caption=f"Tổng {len(flat_scored)} leaf nodes trong index",
    )
    tbl.add_column("Title", min_width=36)
    tbl.add_column("Flat rank", justify="center", width=12)
    tbl.add_column("BookRAG rank", justify="center", width=13)
    tbl.add_column("Phân loại", width=14)
    tbl.add_column("BookRAG tìm qua", min_width=28)

    for nid, info in sorted(node_map.items(), key=_sort_key):
        n  = info["node"]
        fr = info["flat_rank"]
        br = info["book_rank"]

        flat_str = f"#{fr}" if fr else "ngoài bảng"
        book_str = f"#{br}" if br else "—"

        if nid in common:
            label = "[green]CẢ HAI[/green]"
            via   = "similarity + KG"
        elif nid in only_flat:
            label = "[yellow]FLAT ONLY[/yellow]"
            via   = "—"
            book_str = "[dim]—[/dim]"
        else:
            label = "[cyan]BOOKRAG ONLY[/cyan]"
            entities = agent.index.links.get_entities_in_node(nid)
            via = f"KG: {', '.join(entities[:3])}" if entities else "KG traversal"
            # Làm nổi bật khi flat rank rất thấp (BookRAG đã vượt qua giới hạn similarity)
            if fr is None:
                flat_str = "[red bold]không tìm thấy[/red bold]"
            elif fr > 5:
                flat_str = f"[red]#{fr}[/red]"
            else:
                flat_str = f"[dim]#{fr}[/dim]"

        tbl.add_row(n.title[:44], flat_str, book_str, label, via)

    console.print(tbl)

    # ── Insight box ──────────────────────────────────────────────
    insights = []
    for nid, info in node_map.items():
        n  = info["node"]
        fr = info["flat_rank"]
        if nid in only_book:
            entities = agent.index.links.get_entities_in_node(nid)
            via_str  = ", ".join(entities[:2]) if entities else "KG"
            if fr and fr > 3:
                insights.append(
                    f"  [cyan]+[/cyan] \"{n.title}\"\n"
                    f"     Flat RAG bỏ lỡ (rank #{fr}/{len(flat_scored)})\n"
                    f"     BookRAG tìm được qua KG entities: {via_str}"
                )
            else:
                insights.append(
                    f"  [cyan]+[/cyan] \"{n.title}\"\n"
                    f"     BookRAG tìm được qua KG entities: {via_str}"
                )
        elif nid in only_flat:
            insights.append(
                f"  [yellow]-[/yellow] \"{n.title}\"\n"
                f"     Flat RAG lấy theo similarity (rank #{fr})\n"
                f"     BookRAG bỏ qua — không nằm trong KG subgraph của query"
            )

    if insights:
        console.print(Panel(
            "[bold]Điểm khác biệt:[/bold]\n" + "\n".join(insights),
            border_style="magenta",
            title="Analysis",
        ))

    # ── Tóm tắt cuối ────────────────────────────────────────────
    console.print(Panel(
        f"[bold]Tổng kết:[/bold]\n"
        f"  Flat RAG  : {len(flat_top)} chunks | phương pháp: cosine similarity\n"
        f"  BookRAG   : {len(bookrag_nodes)} nodes  | phương pháp: {result['query_type']} (KG + GT-Links)\n\n"
        f"  [green]✓ Cùng tìm thấy : {len(common)} nodes[/green]\n"
        f"  [cyan]+ Chỉ BookRAG   : {len(only_book)} nodes[/cyan]  (qua KG graph traversal)\n"
        f"  [yellow]− Chỉ Flat RAG  : {len(only_flat)} nodes[/yellow]  (bị BookRAG loại khỏi subgraph)",
        border_style="cyan",
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
    parser.add_argument("--compare-query",
                        default="Tại sao Chabashira có thể buộc Ayanokoji hành động theo ý muốn của bà?",
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
