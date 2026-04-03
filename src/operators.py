"""
src/operators.py

Ba Operator của BookRAG theo paper arXiv 2512.03413:

  1. Selector       — thu hẹp phạm vi tìm kiếm xuống các section liên quan
  2. Reasoner       — multi-hop graph traversal qua KnowledgeGraph
  3. Skyline_Ranker — xếp hạng kết hợp semantic relevance + structural importance

Mỗi operator tương ứng với một loại query:
  Single-hop → Selector
  Multi-hop  → Reasoner
  Global     → Skyline_Ranker
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from rich.console import Console
from rich.table import Table
from rich import box

if TYPE_CHECKING:
    from .book_index import BookIndex, TreeNode

console = Console()


# ══════════════════════════════════════════════════════════════
# Utility: Cosine Similarity
# ══════════════════════════════════════════════════════════════

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Tính cosine similarity giữa hai vector."""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


# ══════════════════════════════════════════════════════════════
# OPERATOR 1: SELECTOR
# ══════════════════════════════════════════════════════════════

class Selector:
    """
    Operator cho Single-hop queries.

    Nhiệm vụ: Thu hẹp phạm vi từ toàn bộ tài liệu xuống các section
    liên quan nhất, sử dụng SEMANTIC SIMILARITY + STRUCTURAL HIERARCHY.

    Chiến lược:
    1. Top-down traversal cây: bắt đầu từ chapter level
    2. Tại mỗi cấp, chỉ đi sâu vào nhánh có semantic score cao nhất
    3. Trả về leaf nodes trong nhánh được chọn

    Ưu điểm so với flat top-K:
    - Hiểu được cấu trúc "chapter X nói về chủ đề Y"
    - Không bỏ sót nội dung liên quan trong cùng section
    - Ít tốn token hơn vì tập trung đúng nơi
    """

    def __init__(self, embed_fn, top_k: int = 3):
        """
        embed_fn: hàm nhận text → trả về vector embedding
        top_k: số lượng section trả về tối đa
        """
        self.embed_fn = embed_fn
        self.top_k = top_k

    def run(self, query: str, index: BookIndex) -> list[TreeNode]:
        console.print(f"\n[cyan]→ Selector[/cyan]: top-down traversal cho query: \"{query[:60]}\"")

        query_vec = self.embed_fn(query)
        query_lower = query.lower()

        # ── Bước 1: Tìm entity được nhắc đến trong query (GT-Links boost) ──
        # Đây là điểm khác biệt với flat RAG: Selector dùng GT-Links
        # để ưu tiên node chứa đúng entity được hỏi đến.
        entity_boosted_nodes: set[str] = set()
        for entity in index.links.all_entities():
            if entity.lower() in query_lower:
                for node_id in index.links.get_nodes(entity):
                    entity_boosted_nodes.add(node_id)
                console.print(f"  [dim]Entity match: \"{entity}\" → "
                              f"{index.links.get_nodes(entity)}[/dim]")

        # ── Bước 2: Score tất cả nodes ──────────────────────────
        scored_nodes: list[tuple[float, TreeNode]] = []
        for node in index.tree.all_nodes():
            if node.level == 0 or not node.content:
                continue
            if node.embedding is None:
                node.embedding = self.embed_fn(f"{node.title}\n{node.content}")
            score = cosine_similarity(query_vec, node.embedding)
            scored_nodes.append((score, node))

        # ── Bước 3: Kết hợp boost ────────────────────────────────
        # - Leaf node: x1.2 (section cụ thể tốt hơn chapter tổng)
        # - Entity match qua GT-Links: x1.8 (ưu tiên đúng nhân vật được hỏi)
        boosted: list[tuple[float, TreeNode]] = []
        for score, node in scored_nodes:
            boost = 1.2 if node.is_leaf() else 1.0
            if node.node_id in entity_boosted_nodes:
                boost *= 1.8
            boosted.append((score * boost, node))

        boosted.sort(key=lambda x: x[0], reverse=True)

        # ── Bước 4: Lấy top-K ────────────────────────────────────
        selected: list[TreeNode] = []
        for score, node in boosted:
            if len(selected) >= self.top_k:
                break
            if node not in selected:
                selected.append(node)

        # Build score map để display đúng score của từng node được chọn
        score_map = {node.node_id: score for score, node in boosted}
        self._display_result(selected, score_map)
        return selected

    def _display_result(self, nodes: list[TreeNode], score_map: dict):
        table = Table(title="Selector Results", box=box.SIMPLE, show_lines=False)
        table.add_column("Node ID", style="dim", width=28)
        table.add_column("Title", style="white")
        table.add_column("Level", width=5)
        table.add_column("Score", style="green", width=7)
        for node in nodes:
            score = score_map.get(node.node_id, 0.0)
            table.add_row(node.node_id, node.title[:45], str(node.level), f"{score:.3f}")
        console.print(table)


# ══════════════════════════════════════════════════════════════
# OPERATOR 2: REASONER
# ══════════════════════════════════════════════════════════════

class Reasoner:
    """
    Operator cho Multi-hop queries.

    Nhiệm vụ: Trả lời câu hỏi cần kết hợp thông tin từ nhiều section
    khác nhau thông qua graph traversal (multi-hop reasoning).

    Chiến lược:
    1. Phát hiện entity được nhắc đến trong query (bằng name matching)
    2. Với mỗi entity tìm được, lấy entities kết nối trong KnowledgeGraph
    3. Dùng GT-Links để map tất cả entities → TreeNode tương ứng
    4. Sắp xếp nodes theo semantic score, trả về top-K

    Ví dụ multi-hop:
    Query: "Ai đã gián tiếp gây ra cái chết của Từ Hải?"
    Step 1: Entity "Từ Hải" → neighbors: ["Hồ Tôn Hiến", "Thúy Kiều"]
    Step 2: "Hồ Tôn Hiến" → CAUSED_DEATH → "Từ Hải"; "Thúy Kiều" → advice
    Step 3: GT-Links → sections về Hồ Tôn Hiến và Thúy Kiều
    """

    def __init__(self, embed_fn, hop_depth: int = 2, top_k: int = 4):
        self.embed_fn = embed_fn
        self.hop_depth = hop_depth
        self.top_k = top_k

    def run(self, query: str, index: BookIndex) -> list[TreeNode]:
        console.print(f"\n[cyan]→ Reasoner[/cyan]: multi-hop graph traversal cho: \"{query[:60]}\"")

        query_vec = self.embed_fn(query)
        query_lower = query.lower()

        # ── Bước 1: Tìm entity được đề cập trong query ──────────
        seed_entities: list[str] = []
        for entity in index.links.all_entities():
            if entity.lower() in query_lower:
                seed_entities.append(entity)
                console.print(f"  → Seed entity: [yellow]{entity}[/yellow]")

        # ── Bước 2: Graph traversal lấy related entities ─────────
        related_entities: set[str] = set(seed_entities)
        for entity in seed_entities:
            neighbors = index.graph.neighbors(entity, depth=self.hop_depth)
            related_entities.update(neighbors)
            if neighbors:
                console.print(f"  → {entity} neighbors (depth={self.hop_depth}): "
                              f"[dim]{', '.join(neighbors[:5])}[/dim]")

        # Hiển thị quan hệ tìm được
        for entity in seed_entities:
            for rel in index.graph.get_relations(entity):
                console.print(f"    [dim]{rel['source']} --[{rel['relation']}]--> {rel['target']}[/dim]")

        # ── Bước 3: GT-Links → TreeNode ─────────────────────────
        candidate_node_ids: set[str] = set()
        for entity in related_entities:
            for nid in index.links.get_nodes(entity):
                candidate_node_ids.add(nid)

        console.print(f"  → {len(candidate_node_ids)} candidate nodes từ GT-Links")

        if not candidate_node_ids:
            console.print("  [yellow]Không có entity nào, fallback sang Selector[/yellow]")
            return Selector(self.embed_fn, self.top_k).run(query, index)

        # ── Bước 4: Rank candidate nodes theo semantic score ─────
        scored: list[tuple[float, TreeNode]] = []
        for node_id in candidate_node_ids:
            node = index.tree.get_node(node_id)
            if node is None or not node.content:
                continue
            if node.embedding is None:
                node.embedding = self.embed_fn(f"{node.title}\n{node.content}")
            score = cosine_similarity(query_vec, node.embedding)
            scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [n for _, n in scored[:self.top_k]]

        table = Table(title="Reasoner Results (Multi-hop)", box=box.SIMPLE)
        table.add_column("Node", style="dim", width=28)
        table.add_column("Title")
        table.add_column("Via entities", style="yellow")
        table.add_column("Score", style="green", width=7)
        for score, node in scored[:self.top_k]:
            entities_in_node = index.links.get_entities_in_node(node.node_id)
            relevant = [e for e in entities_in_node if e in related_entities]
            table.add_row(node.node_id, node.title[:40],
                          ", ".join(relevant[:3]), f"{score:.3f}")
        console.print(table)

        return selected


# ══════════════════════════════════════════════════════════════
# OPERATOR 3: SKYLINE RANKER
# ══════════════════════════════════════════════════════════════

class SkylineRanker:
    """
    Operator cho Global queries.

    Nhiệm vụ: Tìm các node "nổi bật" nhất toàn tài liệu theo hai chiều:
      1. Semantic relevance — node liên quan đến query
      2. Structural importance — node quan trọng trong cấu trúc tài liệu

    Một node được đưa vào kết quả nếu không có node nào khác
    vừa relevant hơn vừa important hơn nó (Skyline / Pareto frontier).

    Structural importance tính bằng:
      - Số lượng entities (GT-Links) trong node
      - Số lượng quan hệ của entities trong node (degree trong KG)
      - Vị trí trong cây (section quan trọng hơn chunk nhỏ)

    Ví dụ global query:
    "Hãy tóm tắt toàn bộ tác phẩm Truyện Kiều"
    → Cần lấy nodes từ nhiều chapter khác nhau, ưu tiên node overview
    """

    def __init__(self, embed_fn, top_k: int = 5):
        self.embed_fn = embed_fn
        self.top_k = top_k

    def run(self, query: str, index: BookIndex) -> list[TreeNode]:
        console.print(f"\n[cyan]→ Skyline Ranker[/cyan]: global ranking cho: \"{query[:60]}\"")

        query_vec = self.embed_fn(query)

        # ── Bước 1: Tính semantic score + structural score mọi node ──
        scored: list[tuple[float, float, TreeNode]] = []

        for node in index.tree.all_nodes():
            if node.level == 0 or not node.content:
                continue

            # Semantic score
            if node.embedding is None:
                node.embedding = self.embed_fn(f"{node.title}\n{node.content}")
            sem_score = cosine_similarity(query_vec, node.embedding)

            # Structural importance score
            struct_score = self._structural_importance(node, index)

            scored.append((sem_score, struct_score, node))

        # ── Bước 2: Skyline filtering (Pareto frontier) ───────────
        skyline = self._skyline_filter(scored)

        # ── Bước 3: Rank skyline nodes bằng combined score ────────
        # Combined = 0.6 * semantic + 0.4 * structural (normalize)
        max_struct = max((s for _, s, _ in scored), default=1.0)
        ranked = sorted(
            skyline,
            key=lambda x: 0.6 * x[0] + 0.4 * (x[1] / max(max_struct, 1e-9)),
            reverse=True
        )
        selected = [n for _, _, n in ranked[:self.top_k]]

        table = Table(title="Skyline Ranker Results (Global)", box=box.SIMPLE)
        table.add_column("Node", style="dim", width=25)
        table.add_column("Title")
        table.add_column("Semantic", style="green", width=9)
        table.add_column("Structural", style="blue", width=10)
        table.add_column("Combined", style="magenta", width=9)
        for sem, struct, node in ranked[:self.top_k]:
            combined = 0.6 * sem + 0.4 * (struct / max(max_struct, 1e-9))
            table.add_row(node.node_id, node.title[:38],
                          f"{sem:.3f}", f"{struct:.2f}", f"{combined:.3f}")
        console.print(table)

        return selected

    def _structural_importance(self, node: TreeNode, index: BookIndex) -> float:
        """
        Tính structural importance của một node:
        - Số entity trong node (GT-Links)
        - Tổng degree của entities trong KG
        - Level bonus: chapter > section > leaf
        """
        entities = index.links.get_entities_in_node(node.node_id)
        entity_count = len(entities)

        kg_degree = 0
        for entity in entities:
            if entity in index.graph.graph:
                kg_degree += index.graph.graph.degree(entity)

        level_bonus = {1: 3.0, 2: 2.0, 3: 1.0}.get(node.level, 1.0)

        return (entity_count * 2.0 + kg_degree * 0.5) * level_bonus

    def _skyline_filter(self, scored: list[tuple[float, float, TreeNode]]
                        ) -> list[tuple[float, float, TreeNode]]:
        """
        Lọc Pareto frontier: giữ lại node không bị node nào khác
        dominate trên cả hai chiều (semantic AND structural).
        """
        skyline = []
        for i, (sem_i, str_i, node_i) in enumerate(scored):
            dominated = False
            for j, (sem_j, str_j, _) in enumerate(scored):
                if i == j:
                    continue
                # j dominates i nếu j tốt hơn i ở cả hai chiều
                if sem_j >= sem_i and str_j >= str_i and (sem_j > sem_i or str_j > str_i):
                    dominated = True
                    break
            if not dominated:
                skyline.append((sem_i, str_i, node_i))
        return skyline
