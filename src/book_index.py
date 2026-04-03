"""
src/book_index.py

Triển khai BookIndex theo paper:
  "BookRAG: A Hierarchical Structure-aware Index-based Approach
   for Retrieval-Augmented Generation on Complex Documents"
  (arXiv 2512.03413)

BookIndex gồm 3 thành phần:
  1. HierarchicalTree  — cây phân cấp cấu trúc tài liệu (Table of Contents)
  2. KnowledgeGraph    — đồ thị thực thể và quan hệ
  3. GT-Links          — ánh xạ entity → node trong cây (Ground-Truth Links)
"""

from __future__ import annotations

import re
import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import networkx as nx
from rich.console import Console
from rich.tree import Tree as RichTree

console = Console()


# ══════════════════════════════════════════════════════════════
# 1. HIERARCHICAL TREE
# ══════════════════════════════════════════════════════════════

@dataclass
class TreeNode:
    """
    Một nút trong cây phân cấp tài liệu.

    level=0 → root (toàn bộ tài liệu)
    level=1 → chương  (## Chương...)
    level=2 → section (### 1.1 ...)
    level=3 → đoạn văn (chunk)
    """
    node_id:  str
    title:    str
    level:    int
    content:  str = ""
    parent:   Optional[TreeNode] = field(default=None, repr=False)
    children: list[TreeNode]     = field(default_factory=list, repr=False)

    # Embedding vector — điền vào sau khi embed
    embedding: Optional[list[float]] = field(default=None, repr=False)

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def path_from_root(self) -> list[str]:
        """Trả về đường dẫn từ root đến node này (để hiểu ngữ cảnh phân cấp)."""
        path = [self.title]
        node = self.parent
        while node is not None:
            path.append(node.title)
            node = node.parent
        return list(reversed(path))

    def full_context(self) -> str:
        """Ghép nội dung node + tất cả con cháu (dùng khi cần full context)."""
        texts = [f"[{self.title}]\n{self.content}"] if self.content else [f"[{self.title}]"]
        for child in self.children:
            texts.append(child.full_context())
        return "\n\n".join(t for t in texts if t.strip())


class HierarchicalTree:
    """
    Cây phân cấp tài liệu, xây dựng từ cấu trúc heading Markdown.

    Lý do cần cây thay vì flat chunks:
    - Flat chunks phá vỡ cấu trúc logic (một ý bị cắt giữa hai chunks)
    - Cây cho phép truy xuất theo mức độ chi tiết (chapter → section → đoạn)
    - Cho phép tổng hợp context từ nhiều node con của một chapter
    """

    def __init__(self, doc_title: str = "Document"):
        self.root = TreeNode(node_id="root", title=doc_title, level=0)
        self._node_map: dict[str, TreeNode] = {"root": self.root}

    def _make_id(self, level: int, title: str) -> str:
        slug = re.sub(r"[^\w\s]", "", title.lower()).strip().replace(" ", "_")[:30]
        return f"L{level}_{slug}"

    def add_node(self, parent_id: str, title: str, level: int, content: str = "") -> TreeNode:
        node_id = self._make_id(level, title)
        # Đảm bảo node_id unique
        base = node_id
        count = 1
        while node_id in self._node_map:
            node_id = f"{base}_{count}"
            count += 1

        parent = self._node_map[parent_id]
        node = TreeNode(node_id=node_id, title=title, level=level,
                        content=content, parent=parent)
        parent.children.append(node)
        self._node_map[node_id] = node
        return node

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        return self._node_map.get(node_id)

    def all_nodes(self, level: Optional[int] = None) -> list[TreeNode]:
        """Trả về tất cả node, có thể lọc theo level."""
        result = []
        def dfs(node: TreeNode):
            if level is None or node.level == level:
                result.append(node)
            for child in node.children:
                dfs(child)
        dfs(self.root)
        return result

    def leaf_nodes(self) -> list[TreeNode]:
        return [n for n in self.all_nodes() if n.is_leaf() and n.level > 0]

    def print_tree(self):
        """Hiển thị cây đẹp bằng rich."""
        def build_rich(node: TreeNode, rich_node):
            for child in node.children:
                label = f"[bold]{child.title}[/bold]" if child.level <= 2 else child.title
                sub = rich_node.add(f"[L{child.level}] {label} ({len(child.content)} chars)")
                build_rich(child, sub)

        rich_tree = RichTree(f"[bold magenta]{self.root.title}[/bold magenta]")
        build_rich(self.root, rich_tree)
        console.print(rich_tree)


# ══════════════════════════════════════════════════════════════
# 2. KNOWLEDGE GRAPH
# ══════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """
    Đồ thị thực thể-quan hệ được trích xuất từ tài liệu.

    Nodes: thực thể (nhân vật, địa điểm, khái niệm)
    Edges: quan hệ giữa các thực thể (LOVES, RELATED_TO, KILLS, ...)

    Tại sao cần Knowledge Graph?
    - Flat chunks không thể biểu diễn quan hệ giữa các thực thể
    - Graph cho phép multi-hop reasoning:
        "Ai là vợ của người đã bị Từ Hải cứu?"
        → Từ Hải → [RESCUED] → Thúy Kiều → [MARRIED_TO] → Kim Trọng
    - Community detection giúp tìm nhóm thực thể liên quan
    """

    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()

    def add_entity(self, name: str, entity_type: str, description: str = ""):
        """Thêm một thực thể vào graph."""
        self.graph.add_node(name, type=entity_type, description=description)

    def add_relation(self, source: str, relation: str, target: str, weight: float = 1.0):
        """Thêm quan hệ có hướng giữa hai thực thể."""
        if not self.graph.has_node(source):
            self.graph.add_node(source, type="UNKNOWN")
        if not self.graph.has_node(target):
            self.graph.add_node(target, type="UNKNOWN")
        self.graph.add_edge(source, target, relation=relation, weight=weight)

    def neighbors(self, entity: str, depth: int = 1) -> list[str]:
        """
        Tìm tất cả thực thể kết nối với entity trong vòng `depth` bước.
        Dùng cho multi-hop reasoning.
        """
        if entity not in self.graph:
            return []
        visited = {entity}
        frontier = {entity}
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                next_frontier |= set(self.graph.successors(node))
                next_frontier |= set(self.graph.predecessors(node))
            frontier = next_frontier - visited
            visited |= frontier
        visited.discard(entity)
        return list(visited)

    def get_relations(self, entity: str) -> list[dict]:
        """Lấy tất cả quan hệ của một entity."""
        relations = []
        for src, tgt, data in self.graph.edges(data=True):
            if src == entity or tgt == entity:
                relations.append({"source": src, "relation": data["relation"], "target": tgt})
        return relations

    def find_path(self, source: str, target: str) -> list[str]:
        """Tìm đường đi ngắn nhất giữa hai entity (multi-hop)."""
        try:
            path = nx.shortest_path(self.graph.to_undirected(), source, target)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def community_detection(self) -> dict[str, int]:
        """
        Phát hiện community (nhóm thực thể liên quan) bằng thuật toán Louvain.
        Paper gốc dùng Louvain; ở đây dùng greedy modularity (không cần thêm thư viện).
        """
        undirected = self.graph.to_undirected()
        if len(undirected.nodes) == 0:
            return {}
        communities = nx.community.greedy_modularity_communities(undirected)
        entity_community = {}
        for i, community in enumerate(communities):
            for entity in community:
                entity_community[entity] = i
        return entity_community

    def summary(self) -> str:
        return (f"KnowledgeGraph: {self.graph.number_of_nodes()} entities, "
                f"{self.graph.number_of_edges()} relations")


# ══════════════════════════════════════════════════════════════
# 3. GT-LINKS (Ground-Truth Links)
# ══════════════════════════════════════════════════════════════

class GTLinks:
    """
    Ánh xạ từ entity → danh sách TreeNode chứa entity đó.

    Đây là cầu nối giữa KnowledgeGraph và HierarchicalTree.

    Ví dụ:
      "Thúy Kiều" → [node "2.1 Thúy Kiều", node "3.1 Gặp gỡ", node "3.4 Đoàn tụ"]
      "Từ Hải"    → [node "2.3 Từ Hải", node "3.3 Báo ân báo oán"]

    Công dụng:
    - Khi tìm được entity liên quan qua graph traversal →
      ngay lập tức biết phải đọc section nào trong cây
    - Kết hợp semantic search + structural navigation
    """

    def __init__(self):
        # entity_name → [node_id, ...]
        self._links: dict[str, list[str]] = {}

    def add_link(self, entity: str, node_id: str):
        if entity not in self._links:
            self._links[entity] = []
        if node_id not in self._links[entity]:
            self._links[entity].append(node_id)

    def get_nodes(self, entity: str) -> list[str]:
        """Trả về danh sách node_id chứa entity này."""
        return self._links.get(entity, [])

    def get_entities_in_node(self, node_id: str) -> list[str]:
        """Trả về tất cả entity xuất hiện trong một node."""
        return [e for e, nodes in self._links.items() if node_id in nodes]

    def all_entities(self) -> list[str]:
        return list(self._links.keys())

    def summary(self) -> str:
        total_links = sum(len(v) for v in self._links.values())
        return f"GT-Links: {len(self._links)} entities → {total_links} links"


# ══════════════════════════════════════════════════════════════
# 4. BOOK INDEX — Thành phần thống nhất
# ══════════════════════════════════════════════════════════════

@dataclass
class BookIndex:
    """
    BookIndex = HierarchicalTree + KnowledgeGraph + GTLinks

    Đây là cấu trúc dữ liệu trung tâm của BookRAG, thay thế hoàn toàn
    flat chunk list của RAG truyền thống.
    """
    tree:   HierarchicalTree
    graph:  KnowledgeGraph
    links:  GTLinks

    def summary(self):
        console.print("\n[bold cyan]══ BookIndex Summary ══[/bold cyan]")
        console.print(f"  Tree nodes  : {len(self.tree.all_nodes())} nodes")
        console.print(f"  Leaf nodes  : {len(self.tree.leaf_nodes())} leaves")
        console.print(f"  {self.graph.summary()}")
        console.print(f"  {self.links.summary()}")

    def save(self, path: str):
        """Lưu BookIndex xuống disk."""
        with open(path, "wb") as f:
            pickle.dump(self, f)
        console.print(f"  ✓ BookIndex saved → [yellow]{path}[/yellow]")

    @staticmethod
    def load(path: str) -> BookIndex:
        """Load BookIndex từ disk."""
        with open(path, "rb") as f:
            return pickle.load(f)


# ══════════════════════════════════════════════════════════════
# 5. BUILDER — Xây dựng BookIndex từ tài liệu
# ══════════════════════════════════════════════════════════════

# Thực thể được định nghĩa sẵn cho tài liệu mẫu (Classroom of the Elite)
# Trong hệ thống thực: dùng LLM hoặc NER model để trích xuất tự động
PREDEFINED_ENTITIES = {
    # Nhân vật chính
    "Ayanokoji":        ("PERSON", "Nhân vật chính, thiên tài ẩn từ Căn Phòng Trắng"),
    "Ayanokoji Kiyotaka": ("PERSON", "Nhân vật chính, thiên tài ẩn từ Căn Phòng Trắng"),
    "Horikita":         ("PERSON", "Thủ lĩnh lớp D, mục tiêu lên lớp A"),
    "Horikita Suzune":  ("PERSON", "Thủ lĩnh lớp D, mục tiêu lên lớp A"),
    "Kushida":          ("PERSON", "Cô gái hai mặt, bí mật căm thù Horikita"),
    "Kushida Kikyou":   ("PERSON", "Cô gái hai mặt, bí mật căm thù Horikita"),
    "Sakayanagi":       ("PERSON", "Thủ lĩnh lớp A, đối thủ xứng tầm của Ayanokoji"),
    "Sakayanagi Arisu": ("PERSON", "Thủ lĩnh lớp A, đối thủ xứng tầm của Ayanokoji"),
    "Ichinose":         ("PERSON", "Thủ lĩnh lớp B, biểu tượng của lòng tốt"),
    "Ichinose Honami":  ("PERSON", "Thủ lĩnh lớp B, biểu tượng của lòng tốt"),
    "Ryuuen":           ("PERSON", "Bạo chúa lớp C, sau trở thành đồng minh của Ayanokoji"),
    "Ryuuen Kakeru":    ("PERSON", "Bạo chúa lớp C, sau trở thành đồng minh của Ayanokoji"),
    "Horikita Manabu":  ("PERSON", "Anh trai Horikita, Hội Trưởng Hội Học Sinh"),
    "Chabashira":       ("PERSON", "Giáo viên chủ nhiệm lớp D, biết bí mật Ayanokoji"),
    "Chabashira Sae":   ("PERSON", "Giáo viên chủ nhiệm lớp D, biết bí mật Ayanokoji"),
    "Ayanokoji Touya":  ("PERSON", "Cha Ayanokoji, người sáng lập Căn Phòng Trắng"),
    "Koenji":           ("PERSON", "Thiên tài ích kỷ lớp D, không thể kiểm soát"),
    "Koenji Rokusuke":  ("PERSON", "Thiên tài ích kỷ lớp D, không thể kiểm soát"),
    "Sudo Ken":         ("PERSON", "Học sinh lớp D hay gây rắc rối"),
    "Nagumo":           ("PERSON", "Hội Trưởng mới năm 2, tham vọng và nguy hiểm"),
    # Tổ chức / địa điểm
    "Căn Phòng Trắng":  ("CONCEPT", "Cơ sở huấn luyện bí mật tạo ra con người hoàn hảo"),
    "White Room":       ("CONCEPT", "Cơ sở huấn luyện bí mật, tên gốc tiếng Anh"),
    "lớp A":            ("CLASS", "Lớp ưu tú nhất trường"),
    "lớp B":            ("CLASS", "Lớp thứ hai, do Ichinose dẫn dắt"),
    "lớp C":            ("CLASS", "Lớp thứ ba, do Ryuuen cai trị"),
    "lớp D":            ("CLASS", "Lớp thấp nhất, nơi các nhân vật chính học"),
    "điểm S":           ("CONCEPT", "Tiền tệ ảo trong trường, thước đo thứ hạng"),
    "Hội Học Sinh":     ("ORG", "Tổ chức có quyền lực đặc biệt trong trường"),
    "kỳ thi đặc biệt":  ("CONCEPT", "Special Exam, thử thách định kỳ giữa các lớp"),
}

PREDEFINED_RELATIONS = [
    # Ayanokoji
    ("Ayanokoji",       "SECRETLY_LEADS",  "lớp D"),
    ("Ayanokoji",       "MANIPULATES",     "Horikita"),
    ("Ayanokoji",       "RIVALS",          "Sakayanagi"),
    ("Ayanokoji",       "DEFEATED",        "Ryuuen"),
    ("Ayanokoji",       "CREATED_BY",      "Căn Phòng Trắng"),
    ("Ayanokoji",       "ESCAPED_FROM",    "Căn Phòng Trắng"),
    ("Ayanokoji Touya", "FOUNDED",         "Căn Phòng Trắng"),
    ("Ayanokoji Touya", "FATHER_OF",       "Ayanokoji"),
    ("Ayanokoji Touya", "WANTS_BACK",      "Ayanokoji"),
    # Horikita
    ("Horikita",        "LEADS",           "lớp D"),
    ("Horikita",        "HATED_BY",        "Kushida"),
    ("Horikita",        "KNOWS_SECRET_OF", "Kushida"),
    ("Horikita Manabu", "BROTHER_OF",      "Horikita"),
    ("Horikita Manabu", "LEADS",           "Hội Học Sinh"),
    # Kushida
    ("Kushida",         "HATES",           "Horikita"),
    ("Kushida",         "PRETENDS_TO_BE",  "perfect student"),
    ("Kushida",         "BETRAYED",        "lớp D"),
    # Sakayanagi
    ("Sakayanagi",      "LEADS",           "lớp A"),
    ("Sakayanagi",      "KNOWS_ABOUT",     "Căn Phòng Trắng"),
    ("Sakayanagi",      "WANTS_TO_DEFEAT", "Ayanokoji"),
    ("Sakayanagi Arisu","DAUGHTER_OF",     "Sakayanagi Tomoya"),
    # Ryuuen
    ("Ryuuen",          "LEADS",           "lớp C"),
    ("Ryuuen",          "DISCOVERED",      "Ayanokoji"),
    ("Ryuuen",          "ALLIED_WITH",     "Ayanokoji"),
    # Ichinose
    ("Ichinose",        "LEADS",           "lớp B"),
    # Chabashira
    ("Chabashira",      "KNOWS_SECRET_OF", "Ayanokoji"),
    ("Chabashira",      "BLACKMAILS",      "Ayanokoji"),
    # Koenji
    ("Koenji",          "MEMBER_OF",       "lớp D"),
    ("Koenji",          "UNCONTROLLED_BY", "Ayanokoji"),
]


def build_book_index(file_path: str) -> BookIndex:
    """
    Xây dựng BookIndex từ file tài liệu có cấu trúc Markdown heading.

    Trong paper gốc, bước này dùng layout parser + LLM để tự động
    trích xuất cấu trúc từ PDF bất kỳ.
    Demo này dùng Markdown heading làm proxy cho cấu trúc phân cấp.
    """
    console.print("\n[bold cyan]══ Xây dựng BookIndex ══[/bold cyan]")

    text = Path(file_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    # ── 5.1 Xây dựng Hierarchical Tree ──────────────────────────
    console.print("\n[bold]BƯỚC 1:[/bold] Phân tích cấu trúc tài liệu → Hierarchical Tree")

    doc_title = "Truyện Kiều"
    for line in lines:
        if line.startswith("# "):
            doc_title = line[2:].strip()
            break

    tree = HierarchicalTree(doc_title)

    # Stack để theo dõi node cha hiện tại theo từng level
    # stack[i] = node_id của node level i đang mở
    stack: dict[int, str] = {0: "root"}
    current_content: list[str] = []
    current_node_id: Optional[str] = None

    def flush_content():
        """Lưu nội dung đang buffer vào node hiện tại."""
        nonlocal current_content, current_node_id
        if current_node_id and current_content:
            node = tree.get_node(current_node_id)
            if node:
                node.content = "\n".join(current_content).strip()
        current_content = []

    for line in lines:
        # Heading level 1 (# ) — title tài liệu, bỏ qua
        if re.match(r"^# ", line):
            continue
        # Heading level 2 (## ) → chapter (level=1)
        elif re.match(r"^## ", line):
            flush_content()
            title = line[3:].strip()
            parent_id = stack[0]
            node = tree.add_node(parent_id, title, level=1)
            stack[1] = node.node_id
            stack.pop(2, None)  # xóa level sâu hơn
            current_node_id = node.node_id
        # Heading level 3 (### ) → section (level=2)
        elif re.match(r"^### ", line):
            flush_content()
            title = line[4:].strip()
            parent_id = stack.get(1, "root")
            node = tree.add_node(parent_id, title, level=2)
            stack[2] = node.node_id
            current_node_id = node.node_id
        # Dấu phân cách ---
        elif line.strip() == "---":
            flush_content()
        # Dòng nội dung bình thường
        elif line.strip():
            current_content.append(line)

    flush_content()  # flush nội dung cuối cùng

    leaves = tree.leaf_nodes()
    console.print(f"  ✓ Tree: {len(tree.all_nodes())} nodes, {len(leaves)} leaf sections")
    tree.print_tree()

    # ── 5.2 Xây dựng Knowledge Graph ────────────────────────────
    console.print("\n[bold]BƯỚC 2:[/bold] Trích xuất thực thể → Knowledge Graph")

    graph = KnowledgeGraph()

    for name, (etype, desc) in PREDEFINED_ENTITIES.items():
        graph.add_entity(name, etype, desc)

    for src, rel, tgt in PREDEFINED_RELATIONS:
        graph.add_relation(src, rel, tgt)

    console.print(f"  ✓ {graph.summary()}")

    # Community detection
    communities = graph.community_detection()
    community_groups: dict[int, list[str]] = {}
    for entity, cid in communities.items():
        community_groups.setdefault(cid, []).append(entity)
    console.print(f"  ✓ {len(community_groups)} communities phát hiện:")
    for cid, members in community_groups.items():
        console.print(f"    Community {cid}: {', '.join(members[:5])}{'...' if len(members)>5 else ''}")

    # ── 5.3 Xây dựng GT-Links ────────────────────────────────────
    console.print("\n[bold]BƯỚC 3:[/bold] Xây dựng GT-Links (Entity → TreeNode)")

    links = GTLinks()

    for node in tree.all_nodes():
        if node.level == 0:
            continue
        text_lower = (node.title + " " + node.content).lower()
        for entity_name in PREDEFINED_ENTITIES:
            if entity_name.lower() in text_lower:
                links.add_link(entity_name, node.node_id)

    console.print(f"  ✓ {links.summary()}")

    # Hiển thị một số GT-Link ví dụ
    sample_entities = ["Thúy Kiều", "Từ Hải", "Mã Giám Sinh"]
    for ent in sample_entities:
        node_ids = links.get_nodes(ent)
        console.print(f"    [green]{ent}[/green] → {node_ids}")

    index = BookIndex(tree=tree, graph=graph, links=links)
    index.summary()
    return index
