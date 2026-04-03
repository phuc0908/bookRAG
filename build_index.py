"""
build_index.py — BƯỚC 1: Xây dựng BookIndex từ tài liệu

Chạy một lần, lưu BookIndex xuống disk.
Sau đó dùng query.py để hỏi đáp nhiều lần mà không cần build lại.

Chạy:
  python build_index.py
  python build_index.py --file data/truyen_kieu.txt --output bookindex.pkl
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.book_index import build_book_index, BookIndex


def get_embed_fn():
    """
    Trả về hàm embed text → vector.
    Dùng sentence-transformers (local, miễn phí, hỗ trợ tiếng Việt).
    """
    from sentence_transformers import SentenceTransformer
    console.print("[cyan]Đang load embedding model (lần đầu ~500MB)...[/cyan]")
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    def embed(text: str) -> list[float]:
        return model.encode(text, normalize_embeddings=True).tolist()

    console.print("[green]✓ Embedding model sẵn sàng[/green]")
    return embed


def embed_all_nodes(index: BookIndex, embed_fn) -> None:
    """
    Pre-compute embedding cho tất cả nodes trong cây.
    Lưu vào node.embedding để không phải tính lại khi query.
    """
    nodes = [n for n in index.tree.all_nodes() if n.level > 0 and n.content]
    console.print(f"\n[bold]BƯỚC 4:[/bold] Pre-compute embeddings cho {len(nodes)} nodes")

    for i, node in enumerate(nodes):
        node.embedding = embed_fn(f"{node.title}\n{node.content}")
        if (i + 1) % 5 == 0 or (i + 1) == len(nodes):
            console.print(f"  [{i+1}/{len(nodes)}] {node.title[:50]}")

    console.print(f"  [green]✓ Đã embed {len(nodes)} nodes[/green]")


def main():
    parser = argparse.ArgumentParser(description="BookRAG — Build BookIndex")
    parser.add_argument("--file", default="data/classroom_elite.txt",
                        help="Đường dẫn file tài liệu")
    parser.add_argument("--output", default="bookindex.pkl",
                        help="File lưu BookIndex")
    args = parser.parse_args()

    console.print("\n" + "="*55)
    console.print("[bold magenta]  BookRAG — BUILD BOOK INDEX[/bold magenta]")
    console.print("  Paper: arXiv 2512.03413")
    console.print("="*55)

    # Bước 1-3: Xây dựng Tree + KG + GT-Links
    index = build_book_index(args.file)

    # Bước 4: Pre-compute embeddings
    embed_fn = get_embed_fn()
    embed_all_nodes(index, embed_fn)

    # Lưu xuống disk
    console.print(f"\n[bold]BƯỚC 5:[/bold] Lưu BookIndex")
    index.save(args.output)

    console.print("\n" + "="*55)
    console.print("[bold green]  HOÀN THÀNH![/bold green]")
    console.print(f"  BookIndex đã lưu: [yellow]{args.output}[/yellow]")
    console.print("  Chạy tiếp: [cyan]python query.py[/cyan]")
    console.print("="*55 + "\n")


if __name__ == "__main__":
    main()
