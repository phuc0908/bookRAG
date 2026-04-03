# Giải Thích Chi Tiết Từng File — BookRAG

> Triển khai paper: **"BookRAG: A Hierarchical Structure-aware Index-based Approach for RAG on Complex Documents"** (arXiv 2512.03413)
> Tài liệu mẫu: **Lớp Học Đề Cao Thực Lực** (Classroom of the Elite)

---

## Mục Lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [data/classroom_elite.txt](#2-dataclassroom_elitetxt)
3. [src/book_index.py](#3-srcbook_indexpy)
4. [src/operators.py](#4-srcoperatorspy)
5. [src/agent.py](#5-srcagentpy)
6. [build_index.py](#6-build_indexpy)
7. [query.py](#7-querypy)
8. [Cách chạy](#8-cách-chạy)

---

## 1. Tổng Quan Hệ Thống

### Vấn đề BookRAG giải quyết

RAG truyền thống cắt tài liệu thành các đoạn nhỏ (chunk) rồi tìm kiếm theo độ giống nhau. Cách này có vấn đề lớn:

```
Tài liệu gốc (có cấu trúc):         RAG truyền thống (mất cấu trúc):

  Chương 2: Nhân Vật                 chunk_01: "...Ayanokoji là học sinh..."
    2.1 Ayanokoji        ──────►     chunk_02: "...lớp D năm nhất..."
    2.2 Horikita                     chunk_03: "...Horikita lạnh lùng..."
    2.6 Ryuuen                       chunk_04: "...Ryuuen cai trị lớp C..."

  Quan hệ "Ryuuen phát hiện Ayanokoji"  ← Quan hệ này BỊ MẤT trong chunk!
```

**BookRAG giữ lại cấu trúc** bằng cách xây dựng 3 thành phần song song:

```
                    ┌─────────────────────────────────┐
                    │          BOOK INDEX              │
                    │                                  │
  Tài liệu  ──────► │  HierarchicalTree  (cây phân cấp)│
                    │  KnowledgeGraph    (đồ thị quan hệ)│
                    │  GT-Links          (entity → node) │
                    └─────────────────────────────────┘
                                    │
                    ┌───────────────▼─────────────────┐
                    │         AGENT (IFT)              │
                    │  phân loại query → gọi operator  │
                    └──────┬────────────┬─────────────┘
                           │            │
               ┌───────────┼────────────┼───────────┐
               ▼           ▼            ▼
           Selector     Reasoner   SkylineRanker
          (1 section)  (multi-hop)  (toàn tài liệu)
```

### Luồng dữ liệu tổng thể

```
data/classroom_elite.txt
        │
        ▼
  build_index.py  ──►  src/book_index.py  ──►  bookindex.pkl
  (chạy 1 lần)         (xây Tree+KG+Links)      (lưu xuống disk)

  query.py        ──►  src/agent.py       ──►  src/operators.py  ──►  Câu trả lời
  (chạy nhiều lần)     (phân loại query)        (tìm đúng section)
```

---

## 2. `data/classroom_elite.txt`

**Vai trò:** Tài liệu đầu vào mẫu — tóm tắt có cấu trúc của light novel *Lớp Học Đề Cao Thực Lực*.

### Tại sao file này có dấu `#`, `##`, `###`?

Đây là cú pháp Markdown heading. Hệ thống dùng các dấu này để **phát hiện cấu trúc phân cấp** của tài liệu, giống như mục lục của một cuốn sách:

```
# LỚP HỌC ĐỀ CAO THỰC LỰC         ← Cấp 0: Tên tài liệu (root)

## Chương 1: Giới Thiệu             ← Cấp 1: Chương
### 1.1 Thông Tin Tác Phẩm          ← Cấp 2: Section (lá của cây)
Lớp Học Đề Cao Thực Lực là...      ← Nội dung của section

## Chương 2: Nhân Vật               ← Cấp 1: Chương tiếp theo
### 2.1 Ayanokoji Kiyotaka           ← Cấp 2: Section
Ayanokoji Kiyotaka là nhân vật...  ← Nội dung
```

> **Lưu ý quan trọng:** Trong light novel thật, không có `##` hay `###` — chỉ có text thuần và tiêu đề chương đơn giản. File này là **tóm tắt có cấu trúc nhân tạo** dùng cho demo. Trong thực tế, BookRAG dùng layout parser (PyMuPDF, Unstructured) + LLM để tự động trích xuất cấu trúc từ PDF/TXT thô bất kỳ.

---

## 3. `src/book_index.py`

**Vai trò:** Định nghĩa và xây dựng **BookIndex** — trái tim của toàn bộ hệ thống.

### 3.1 Class `TreeNode` — Một ô trong cây

Mỗi `TreeNode` đại diện cho một phần của tài liệu:

```python
@dataclass
class TreeNode:
    node_id:   str               # ID định danh, ví dụ: "L2_21_ayanokoji_kiyotaka"
    title:     str               # Tiêu đề, ví dụ: "2.1 Ayanokoji Kiyotaka – Nhân Vật Chính"
    level:     int               # 0=root, 1=chương, 2=section
    content:   str               # Nội dung text của section này
    parent:    TreeNode          # Node cha (trỏ lên trên trong cây)
    children:  list[TreeNode]    # Các node con (trỏ xuống dưới)
    embedding: list[float]       # Vector số thực (do embedding model tạo ra)
```

**Ví dụ cụ thể:**

```
node_id  = "L2_21_ayanokoji_kiyotaka__"
title    = "2.1 Ayanokoji Kiyotaka – Nhân Vật Chính"
level    = 2
content  = "Ayanokoji Kiyotaka là nhân vật trung tâm của tác phẩm..."
parent   = <TreeNode "Chương 2: Nhân Vật">
children = []   ← node lá, không có con
embedding= [0.12, -0.34, 0.89, ...]  ← 384 số thực
```

Hai method quan trọng:
- `path_from_root()` → `["LỚP HỌC ĐỀ CAO THỰC LỰC", "Chương 2", "2.1 Ayanokoji"]` — dùng để hiển thị nguồn trích dẫn
- `full_context()` → ghép nội dung node + tất cả node con — dùng khi cần đọc toàn bộ một chương

---

### 3.2 Class `HierarchicalTree` — Cây phân cấp

Lưu toàn bộ cấu trúc tài liệu dưới dạng cây có gốc (root):

```
root: "LỚP HỌC ĐỀ CAO THỰC LỰC"
├── [L1] Chương 1: Giới Thiệu
│   ├── [L2] 1.1 Thông Tin Tác Phẩm        ← leaf (node lá)
│   ├── [L2] 1.2 Bối Cảnh                  ← leaf
│   ├── [L2] 1.3 Hệ Thống Lớp Học          ← leaf
│   └── [L2] 1.4 Chủ Đề Chính              ← leaf
├── [L1] Chương 2: Nhân Vật
│   ├── [L2] 2.1 Ayanokoji Kiyotaka        ← leaf
│   ├── [L2] 2.2 Horikita Suzune           ← leaf
│   ├── [L2] 2.3 Kushida Kikyou            ← leaf
│   └── ...
└── [L1] Chương 5: Quan Hệ và Liên Minh
    └── ...
```

Method quan trọng:
- `add_node(parent_id, title, level)` — thêm node vào cây, tự tính ID từ tiêu đề
- `leaf_nodes()` — trả về tất cả node lá (section chi tiết nhất, không có con)
- `all_nodes(level=2)` — lọc node theo cấp
- `print_tree()` — in cây đẹp ra terminal

---

### 3.3 Class `KnowledgeGraph` — Đồ thị quan hệ

Lưu thực thể (entity) và quan hệ giữa chúng dưới dạng đồ thị có hướng:

```
Ayanokoji ──[SECRETLY_LEADS]──────► lớp D
Ayanokoji ──[RIVALS]───────────────► Sakayanagi
Ayanokoji ──[DEFEATED]─────────────► Ryuuen
Ryuuen    ──[DISCOVERED]───────────► Ayanokoji
Ryuuen    ──[ALLIED_WITH]──────────► Ayanokoji
Kushida   ──[HATES]────────────────► Horikita
Horikita  ──[KNOWS_SECRET_OF]──────► Kushida
Chabashira──[BLACKMAILS]───────────► Ayanokoji
```

**Tại sao cần đồ thị?**

Khi có câu hỏi: *"Ai biết bí mật thật của Ayanokoji?"*
- Tìm entity "Ayanokoji" trong đồ thị
- Duyệt ra: `Ayanokoji ←[KNOWS_ABOUT]── Sakayanagi`, `Chabashira ──[BLACKMAILS]──► Ayanokoji`
- Biết ngay phải đọc section về Sakayanagi và Chabashira

Nếu chỉ dùng chunk, thông tin này bị phân tán ở nhiều nơi khác nhau.

Method quan trọng:
- `add_entity(name, type)` — thêm nhân vật/địa điểm/khái niệm
- `add_relation(source, relation, target)` — thêm quan hệ có hướng
- `neighbors(entity, depth=2)` — tìm tất cả entity kết nối trong 2 bước (dùng cho multi-hop)
- `get_relations(entity)` — liệt kê quan hệ của một entity
- `community_detection()` — nhóm các entity liên quan thành cộng đồng

---

### 3.4 Class `GTLinks` — Cầu nối giữa Graph và Tree

GT-Links (Ground-Truth Links) là một **từ điển**: mỗi entity trỏ đến danh sách node trong cây chứa entity đó.

```python
# Bên trong GTLinks._links:
{
    "Ayanokoji": ["L2_21_ayanokoji_kiyotaka", "L1_chuong_3_su_kien", "L2_33_ryuuen_dieu_tra"],
    "Ryuuen":    ["L2_26_ryuuen_kakeru", "L2_33_ryuuen_dieu_tra", "L2_53_ayanokoji_va_ryuuen"],
    "Kushida":   ["L2_23_kushida_kikyou", "L2_34_bi_mat_cua_kushida"],
    ...
}
```

**Tại sao cần GT-Links?**

Khi `Reasoner` duyệt đồ thị và tìm được các entity liên quan đến câu hỏi, nó cần biết entity đó xuất hiện ở *section nào trong cây* để lấy đúng nội dung. GT-Links là cái cầu nối đó.

```
KnowledgeGraph              GT-Links                   HierarchicalTree
  "Ryuuen"      ────────► ["L2_26_ryuuen_kakeru"]  ──► node "2.6 Ryuuen Kakeru"
                                                         content: "Ryuuen Kakeru là..."
```

Method quan trọng:
- `add_link(entity, node_id)` — ghi nhận entity xuất hiện trong node nào
- `get_nodes(entity)` — trả về list node_id chứa entity
- `get_entities_in_node(node_id)` — chiều ngược lại: node này có những entity nào

---

### 3.5 Class `BookIndex` — Đóng gói tất cả

Chỉ là một dataclass gom 3 thành phần lại:

```python
@dataclass
class BookIndex:
    tree:  HierarchicalTree   # cây phân cấp
    graph: KnowledgeGraph     # đồ thị quan hệ
    links: GTLinks            # ánh xạ entity → node
```

Có 2 method quan trọng:
- `save("bookindex.pkl")` — lưu toàn bộ xuống disk bằng pickle
- `BookIndex.load("bookindex.pkl")` — đọc lại từ disk (không cần build lại)

---

### 3.6 Hàm `build_book_index(file_path)` — Xây dựng BookIndex

Đây là hàm chính, chạy 3 bước liên tiếp:

**Bước 1 — Xây HierarchicalTree:** Đọc file từng dòng, nhận diện `##` → chapter (level 1), `###` → section (level 2), text thường → nội dung. Dùng stack để theo dõi node cha đang mở.

**Bước 2 — Xây KnowledgeGraph:** Nạp danh sách entity và quan hệ từ `PREDEFINED_ENTITIES` và `PREDEFINED_RELATIONS` (nhân vật, địa điểm, khái niệm của Classroom of the Elite). Trong hệ thống thực: dùng LLM hoặc NER model để trích xuất tự động.

**Bước 3 — Xây GT-Links:** Duyệt qua từng node trong cây, kiểm tra xem entity nào xuất hiện trong `(title + content)`, rồi ghi nhận link.

---

## 4. `src/operators.py`

**Vai trò:** Ba "công cụ tìm kiếm" chuyên biệt cho 3 loại câu hỏi khác nhau.

### Hàm `cosine_similarity(a, b)`

Hàm tiện ích đo **độ giống nhau giữa hai vector**. Kết quả từ -1 đến 1, càng gần 1 càng giống nhau.

```
"Ayanokoji là ai?" → vector [0.2, 0.8, -0.3, ...]
"2.1 Ayanokoji – Nhân Vật Chính" → vector [0.19, 0.76, -0.28, ...]
cosine_similarity = 0.97  ← rất giống!

"Ayanokoji là ai?" → vector [0.2, 0.8, -0.3, ...]
"Hệ thống điểm S" → vector [-0.5, 0.1, 0.9, ...]
cosine_similarity = 0.31  ← khác nhau nhiều
```

---

### 4.1 Class `Selector` — Cho câu hỏi Single-hop

**Dùng khi:** Câu hỏi về một nhân vật/sự kiện cụ thể, chỉ cần tìm một section.

**Ví dụ:** *"Kushida Kikyou là người như thế nào?"*, *"Căn Phòng Trắng là gì?"*

**Cách hoạt động (4 bước):**

```
Bước 1: Tìm entity trong câu hỏi qua GT-Links
        "Kushida Kikyou là người như thế nào?"
        → Entity "Kushida" và "Kushida Kikyou" tìm thấy
        → GT-Links["Kushida"] = ["L2_23_kushida_kikyou", ...]
        → Đánh dấu các node đó để boost

Bước 2: Tính cosine similarity với tất cả nodes
        node "2.3 Kushida Kikyou" → score 0.74
        node "2.2 Horikita Suzune" → score 0.61
        node "3.4 Bí Mật Của Kushida" → score 0.58

Bước 3: Nhân hệ số boost
        Leaf node    → × 1.2
        Entity match → × 1.8
        node "2.3 Kushida" → 0.74 × 1.2 × 1.8 = 1.60  ← lên đầu!
        node "2.2 Horikita" → 0.61 × 1.2 = 0.73
        node "3.4 Bí Mật" → 0.58 × 1.2 × 1.8 = 1.25  ← cũng có entity match

Bước 4: Lấy top-3 nodes có score cao nhất
        Kết quả: [2.3 Kushida, 3.4 Bí Mật Của Kushida, 2.2 Horikita]  ✓
```

**Điểm khác biệt so với RAG thường:** Bước 1 và 3 — Selector kết hợp GT-Links để ưu tiên đúng entity được hỏi, không chỉ dùng similarity thuần.

---

### 4.2 Class `Reasoner` — Cho câu hỏi Multi-hop

**Dùng khi:** Câu hỏi cần kết hợp thông tin từ nhiều section qua quan hệ.

**Ví dụ:** *"Tại sao Ryuuen lại phát hiện ra Ayanokoji?"*

**Cách hoạt động (4 bước):**

```
Bước 1: Tìm entity "hạt giống" trong câu hỏi
        "Tại sao Ryuuen lại phát hiện ra Ayanokoji?"
        → Seed entities: "Ryuuen", "Ayanokoji"

Bước 2: Duyệt KnowledgeGraph (depth=2)
        Từ "Ryuuen": neighbors → [Ayanokoji, lớp C, lớp D]
        Từ "Ayanokoji": neighbors → [Horikita, Sakayanagi, Căn Phòng Trắng, ...]
        In ra quan hệ:
          Ryuuen --[DISCOVERED]--> Ayanokoji
          Ryuuen --[DEFEATED_BY]--> Ayanokoji
          Ryuuen --[ALLIED_WITH]--> Ayanokoji

Bước 3: Dùng GT-Links map entities → nodes
        GT-Links["Ryuuen"]    → ["L2_26_ryuuen", "L2_33_ryuuen_dieu_tra", "L2_53_..."]
        GT-Links["Ayanokoji"] → ["L2_21_ayanokoji", "L2_31_nam_nhat", ...]
        → Tổng hợp: 8 candidate nodes

Bước 4: Rank candidate nodes theo cosine similarity, lấy top-4
        Kết quả: [3.3 Ryuuen Điều Tra, 2.6 Ryuuen, 2.1 Ayanokoji, ...]  ✓
```

**Điểm mấu chốt:** Reasoner đi qua đồ thị quan hệ trước, rồi mới dùng GT-Links để xác định section cần đọc — đây là "multi-hop", vài bước nhảy qua graph.

---

### 4.3 Class `SkylineRanker` — Cho câu hỏi Global

**Dùng khi:** Câu hỏi cần tổng hợp toàn bộ tài liệu.

**Ví dụ:** *"Tóm tắt hệ thống lớp học"*, *"Các chủ đề chính của tác phẩm là gì?"*

**Cách hoạt động:**

Mỗi node được chấm 2 điểm:
- **Semantic score** — node liên quan đến câu hỏi đến mức nào (cosine similarity)
- **Structural importance** — node quan trọng trong tài liệu đến mức nào

```python
# Công thức tính structural importance:
structural = (số_entity_trong_node × 2.0 + tổng_degree_KG × 0.5) × level_bonus

# level_bonus: chương (3.0) > section (2.0) > node nhỏ (1.0)
# → node chứa nhiều nhân vật quan trọng và ở cấp cao sẽ có điểm structural cao
```

Sau đó lọc **Pareto Frontier (Skyline)**:
> Giữ lại node X nếu không có node nào khác vừa có semantic cao hơn X, vừa có structural cao hơn X cùng lúc.

```
Ví dụ với query "Tóm tắt hệ thống trường":
  Node "1.3 Hệ Thống Lớp Học": semantic=0.89, structural=6.0  ← GIỮ LẠI
  Node "2.1 Ayanokoji":         semantic=0.71, structural=8.0  ← GIỮ LẠI (struct cao hơn)
  Node "4.2 Hệ Thống Điểm S":  semantic=0.85, structural=4.0  ← GIỮ LẠI
  Node "2.8 Chabashira":        semantic=0.52, structural=3.0  ← BỎ (bị beat cả 2)
```

Cuối cùng rank skyline nodes bằng `0.6 × semantic + 0.4 × structural`.

---

## 5. `src/agent.py`

**Vai trò:** Bộ não điều phối — nhận câu hỏi, quyết định dùng operator nào, sinh câu trả lời.

### 5.1 `QueryType` — Enum 3 loại query

```python
class QueryType(Enum):
    SINGLE_HOP   # → Selector
    MULTI_HOP    # → Reasoner
    GLOBAL       # → SkylineRanker
```

### 5.2 Hàm `classify_query()` — Phân loại câu hỏi

Dùng rule-based (từ khóa) để phân loại, không cần API key:

```
Nếu có "tóm tắt", "toàn bộ", "chủ đề chính"... → GLOBAL
Nếu có "vì sao", "ai đã", "dẫn đến"... + nhắc entity → MULTI_HOP
Nếu có 2+ entity trong câu hỏi → MULTI_HOP
Còn lại → SINGLE_HOP (mặc định)
```

Ví dụ với Classroom of the Elite:
```
"Kushida là ai?"                      → SINGLE_HOP  (1 entity, không từ khóa đặc biệt)
"Vì sao Ryuuen thua Ayanokoji?"       → MULTI_HOP   ("vì sao" + 2 entity)
"Sakayanagi biết gì về Ayanokoji?"    → MULTI_HOP   (2 entity: Sakayanagi + Ayanokoji)
"Tóm tắt hệ thống điểm S"            → GLOBAL      ("tóm tắt")
```

> Trong paper gốc, bước này dùng LLM để phân loại chính xác hơn.

### 5.3 Hàm `generate_answer()` — Sinh câu trả lời

```python
def generate_answer(query, nodes, index):
    context = ghép nội dung các nodes lại (kèm đường dẫn phân cấp)

    if có OPENAI_API_KEY:
        gửi (context + query) đến GPT → nhận câu trả lời đầy đủ
    else:
        demo mode: hiển thị nội dung các section tìm được
```

Context được ghép kèm đường dẫn để LLM hiểu ngữ cảnh:

```
[Nguồn 1: LỚP HỌC ĐỀ CAO THỰC LỰC > Chương 3 > 3.3 Ryuuen Điều Tra]
Ryuuen Kakeru tung gián điệp và dùng nhiều thủ đoạn để truy tìm...

[Nguồn 2: LỚP HỌC ĐỀ CAO THỰC LỰC > Chương 2 > 2.6 Ryuuen Kakeru]
Ryuuen Kakeru là thủ lĩnh lớp C, cai trị bằng sức mạnh...
```

### 5.4 Class `BookRAGAgent` — Agent chính

```python
agent = BookRAGAgent(index, embed_fn)
result = agent.query("Tại sao Ryuuen phát hiện ra Ayanokoji?")
```

Pipeline bên trong `agent.query()`:

```
1. classify_query() → MULTI_HOP
2. reasoner.run()   → [node "3.3 Ryuuen Điều Tra", node "2.6 Ryuuen", ...]
3. build_context()  → ghép nội dung + đường dẫn phân cấp
4. generate_answer()→ gọi GPT hoặc demo mode
5. return { question, query_type, retrieved_nodes, answer }
```

---

## 6. `build_index.py`

**Vai trò:** Script chạy **một lần duy nhất** để chuẩn bị dữ liệu cho toàn bộ hệ thống.

### Các bước thực hiện

```
BƯỚC 1-3: build_book_index("data/classroom_elite.txt")
           → Xây HierarchicalTree + KnowledgeGraph + GTLinks
           → Trả về BookIndex

BƯỚC 4:   embed_all_nodes(index, embed_fn)
           → Load model "paraphrase-multilingual-MiniLM-L12-v2" (~500MB, lần đầu)
           → Với mỗi node có nội dung: tính embedding vector
           → Lưu vào node.embedding
           Tại sao tính trước? → Không phải tính lại mỗi lần query, tăng tốc đáng kể

BƯỚC 5:   index.save("bookindex.pkl")
           → Pickle toàn bộ BookIndex (tree + graph + links + embeddings) xuống disk
```

### Hàm `get_embed_fn()`

Trả về một hàm `embed(text) → list[float]`. Dùng model `paraphrase-multilingual-MiniLM-L12-v2` để chuyển text thành vector 384 chiều.

Model này:
- Hỗ trợ 50+ ngôn ngữ kể cả tiếng Nhật và tiếng Việt
- Chạy hoàn toàn local, không cần API key
- Tải về ~500MB lần đầu, lưu cache tự động

---

## 7. `query.py`

**Vai trò:** Giao diện tương tác với người dùng — load BookIndex đã build sẵn và trả lời câu hỏi.

### 4 chế độ chạy

**Chat tương tác** — gõ câu hỏi tự do:
```
run_query.bat
Bạn: Ayanokoji thực sự là ai?
Bạn: Tại sao Kushida ghét Horikita?
Bạn: thoát
```

**Hỏi 1 câu** — chạy rồi thoát:
```
run_query.bat -q "Căn Phòng Trắng là gì?"
```

**Demo tự động** — chạy 3 câu hỏi minh họa 3 loại query:
```
run_query.bat --demo
```
Lần lượt: single-hop ("Kushida là người như thế nào?"), multi-hop ("Ryuuen phát hiện Ayanokoji?"), global ("Tóm tắt hệ thống trường")

**So sánh với RAG thường:**
```
run_query.bat --compare
```
Chạy cùng 1 câu hỏi trên cả BookRAG và flat RAG để thấy rõ sự khác biệt.

### Hàm `run_compare()`

Đặc biệt hữu ích khi thuyết trình. Cho thấy:
- **Flat RAG**: chỉ dùng cosine similarity, có thể lấy sai section
- **BookRAG**: dùng agent + operator + GT-Links, lấy đúng section và có ngữ cảnh phân cấp

---

## 8. Cách Chạy

```
# Bước 1: Cài đặt môi trường venv (chỉ làm 1 lần)
setup.bat

# Bước 2: Xây BookIndex (chỉ làm 1 lần, hoặc khi đổi tài liệu)
run_build.bat

# Bước 3: Hỏi đáp (có thể chạy nhiều lần)
run_query.bat --demo       ← Xem demo 3 loại query
run_query.bat --compare    ← So sánh với flat RAG
run_query.bat              ← Chat tự do
```

### Ví dụ câu hỏi theo từng loại

| Loại | Câu hỏi mẫu | Operator dùng |
|------|-------------|---------------|
| Single-hop | `Kushida Kikyou là người như thế nào?` | Selector |
| Single-hop | `Căn Phòng Trắng là gì?` | Selector |
| Single-hop | `Sakayanagi Arisu có đặc điểm gì?` | Selector |
| Multi-hop | `Tại sao Ryuuen phát hiện ra Ayanokoji?` | Reasoner |
| Multi-hop | `Ai biết bí mật thật của Ayanokoji?` | Reasoner |
| Multi-hop | `Mối quan hệ giữa Ayanokoji và Sakayanagi?` | Reasoner |
| Global | `Tóm tắt hệ thống lớp học và điểm S` | SkylineRanker |
| Global | `Các chủ đề chính của tác phẩm là gì?` | SkylineRanker |

---

> **Tài liệu tham khảo:** Wang, S., Zhou, Y., & Fang, Y. (2025). *BookRAG: A Hierarchical Structure-aware Index-based Approach for Retrieval-Augmented Generation on Complex Documents*. arXiv:2512.03413
