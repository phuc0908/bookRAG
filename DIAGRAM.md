# Sơ Đồ & Giải Thích Thuật Ngữ — BookRAG

---

## SƠ ĐỒ 1 — Vấn Đề Của RAG Truyền Thống

```
╔══════════════════════════════════════════════════════════════════╗
║              RAG TRUYỀN THỐNG — flat chunking                    ║
╚══════════════════════════════════════════════════════════════════╝

  Light Novel gốc (có cấu trúc rõ ràng):

  ┌─────────────────────────────────────────────────────────────┐
  │  Chương 2: Nhân Vật                                         │
  │  ├── Ayanokoji: thiên tài ẩn, xuất thân từ Căn Phòng Trắng │
  │  ├── Horikita: lạnh lùng, mục tiêu lên lớp A               │
  │  └── Ryuuen: bạo chúa, phát hiện ra Ayanokoji              │
  │                                                             │
  │  Chương 3: Sự Kiện                                          │
  │  └── Ryuuen điều tra và tìm ra Ayanokoji là chỉ huy bí mật │
  └─────────────────────────────────────────────────────────────┘
              │
              │   Cắt thành chunk nhỏ
              ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ chunk_01 │ │ chunk_02 │ │ chunk_03 │ │ chunk_04 │ │ chunk_05 │
  │"Ayanokoji│ │"...thiên │ │"Horikita │ │"Ryuuen   │ │"...điều  │
  │là học    │ │tài ẩn,   │ │lạnh lùng │ │bạo chúa  │ │tra và tìm│
  │sinh lớp D│ │xuất thân │ │mục tiêu  │ │cai trị   │ │ra Ayano..│
  │năm nhất" │ │Phòng..." │ │lên lớp A"│ │lớp C..." │ │          │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘

  ❌ VẤN ĐỀ:
  • Quan hệ "Ryuuen phát hiện Ayanokoji" bị XÉ ĐÔI qua 2 chunk
  • Không biết chunk_04 (Ryuuen) và chunk_01 (Ayanokoji) có liên quan
  • Hỏi "Ai phát hiện Ayanokoji?" → có thể lấy sai chunk
```

---

## SƠ ĐỒ 2 — BookRAG Giải Quyết Thế Nào

```
╔══════════════════════════════════════════════════════════════════╗
║              BOOKRAG — giữ lại cấu trúc tài liệu                ║
╚══════════════════════════════════════════════════════════════════╝

  Thay vì 1 danh sách chunk, BookRAG xây 3 thứ cùng lúc:

  ┌─────────────────────────────────────────────────────────────────────┐
  │                         BOOK INDEX                                   │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
  │  │ Hierarchical     │  │  Knowledge       │  │   GT-Links        │  │
  │  │ Tree             │  │  Graph           │  │                   │  │
  │  │                  │  │                  │  │ "Ayanokoji"       │  │
  │  │ root             │  │  Ayanokoji       │  │   → [node_21,     │  │
  │  │  └ Chương 2      │  │   ↑DEFEATED      │  │      node_33]     │  │
  │  │     └ 2.1 Ayano  │  │  Ryuuen          │  │                   │  │
  │  │     └ 2.6 Ryuuen │  │   ↓DISCOVERED    │  │ "Ryuuen"          │  │
  │  │  └ Chương 3      │  │  Ayanokoji       │  │   → [node_26,     │  │
  │  │     └ 3.3 Điều   │  │                  │  │      node_33]     │  │
  │  │        tra       │  │  Kushida──HATES─►│  │                   │  │
  │  │                  │  │  Horikita        │  │ "Kushida"         │  │
  │  │  (CÂY PHÂN CẤP)  │  │  (ĐỒ THỊ        │  │   → [node_23,     │  │
  │  │                  │  │   QUAN HỆ)       │  │      node_34]     │  │
  │  └──────────────────┘  └──────────────────┘  └───────────────────┘  │
  │           │                     │                      │             │
  │           └─────────────────────┴──────────────────────┘             │
  │                           KẾT HỢP LẠI                               │
  └─────────────────────────────────────────────────────────────────────┘

  ✅ LỢI ÍCH:
  • Cây giữ nguyên cấu trúc chương/section
  • Đồ thị biết "Ryuuen PHÁT HIỆN Ayanokoji"
  • GT-Links biết: nói về "Ryuuen" → đọc node_26 và node_33
```

---

## SƠ ĐỒ 3 — Luồng Xử Lý Câu Hỏi (Query Pipeline)

```
╔══════════════════════════════════════════════════════════════════╗
║              3 LOẠI CÂU HỎI → 3 ĐƯỜNG XỬ LÝ KHÁC NHAU         ║
╚══════════════════════════════════════════════════════════════════╝

  Người dùng gõ câu hỏi
           │
           ▼
  ┌─────────────────────┐
  │   AGENT phân loại   │  ← Đọc từ khóa trong câu hỏi
  │   (classify_query)  │    để quyết định loại
  └──────┬──────┬───────┘
         │      │      │
    ┌────┘  ┌───┘  ┌───┘
    ▼       ▼      ▼
 [SINGLE] [MULTI] [GLOBAL]
  HOP      HOP
    │       │      │
    ▼       ▼      ▼
 ┌──────┐ ┌──────┐ ┌──────────┐
 │SELEC-│ │REASO-│ │SKYLINE   │
 │TOR   │ │NER   │ │RANKER    │
 └──┬───┘ └──┬───┘ └────┬─────┘
    │        │           │
    ▼        ▼           ▼
  Dùng     Duyệt      Tính 2
  GT-Links  đồ thị     điểm:
  để ưu    quan hệ     semantic
  tiên     (multi-     + tầm
  đúng     hop)        quan
  entity               trọng
    │        │           │
    └────────┴─────┬─────┘
                   │
                   ▼
           Các TreeNode
           liên quan nhất
                   │
                   ▼
          Ghép thành Context
          (kèm đường dẫn
           phân cấp)
                   │
                   ▼
          ┌──────────────┐
          │     LLM      │  ← GPT hoặc demo mode
          │  (GPT / demo)│
          └──────┬───────┘
                 │
                 ▼
          CÂU TRẢ LỜI ✅
```

---

## SƠ ĐỒ 4 — Ví Dụ Cụ Thể: Câu Hỏi Multi-hop

```
╔══════════════════════════════════════════════════════════════════╗
║  Ví dụ: "Ai đã phát hiện ra bí mật của Ayanokoji?"              ║
╚══════════════════════════════════════════════════════════════════╝

  BƯỚC 1 — Phân loại:
  ┌─────────────────────────────────────────────────────────────┐
  │ Từ khóa "ai đã" + entity "Ayanokoji" → MULTI_HOP           │
  │                              ↓ gọi Reasoner                 │
  └─────────────────────────────────────────────────────────────┘

  BƯỚC 2 — Tìm entity trong câu hỏi:
  ┌─────────────────────────────────────────────────────────────┐
  │ "Ayanokoji" tìm thấy → seed entity                         │
  └─────────────────────────────────────────────────────────────┘

  BƯỚC 3 — Duyệt Knowledge Graph (depth=2):
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │           Sakayanagi                                        │
  │          ╱ KNOWS_ABOUT                                      │
  │  Ayanokoji ─── CREATED_BY ──► Căn Phòng Trắng              │
  │          ╲ ◄── BLACKMAILS ─── Chabashira                   │
  │           ◄─── DISCOVERED ─── Ryuuen                        │
  │                                                             │
  │  → Related entities: {Sakayanagi, Căn Phòng Trắng,         │
  │                        Chabashira, Ryuuen, ...}             │
  └─────────────────────────────────────────────────────────────┘

  BƯỚC 4 — GT-Links map → TreeNode:
  ┌─────────────────────────────────────────────────────────────┐
  │  "Ryuuen"     → node "2.6 Ryuuen", node "3.3 Điều Tra"     │
  │  "Sakayanagi" → node "2.4 Sakayanagi", node "3.5 Tàu"      │
  │  "Chabashira" → node "2.8 Chabashira"                       │
  │  → Tổng: 6 candidate nodes                                  │
  └─────────────────────────────────────────────────────────────┘

  BƯỚC 5 — Rank theo similarity, lấy top-4:
  ┌─────────────────────────────────────────────────────────────┐
  │  #1  node "3.3 Ryuuen Điều Tra"    score: 0.84  ✅          │
  │  #2  node "2.8 Chabashira"         score: 0.79  ✅          │
  │  #3  node "2.4 Sakayanagi"         score: 0.76  ✅          │
  │  #4  node "2.6 Ryuuen Kakeru"      score: 0.71  ✅          │
  └─────────────────────────────────────────────────────────────┘

  BƯỚC 6 — Ghép context + gọi LLM:
  ┌─────────────────────────────────────────────────────────────┐
  │  [Nguồn 1: Chương 3 > 3.3 Ryuuen Điều Tra]                 │
  │  Ryuuen Kakeru tung gián điệp...                            │
  │                                                             │
  │  [Nguồn 2: Chương 2 > 2.8 Chabashira]                      │
  │  Chabashira biết Ayanokoji xuất thân từ Căn Phòng Trắng... │
  │  → GPT đọc → tổng hợp câu trả lời                          │
  └─────────────────────────────────────────────────────────────┘
```

---

## SƠ ĐỒ 5 — Selector Boost (Fix bug thực tế)

```
╔══════════════════════════════════════════════════════════════════╗
║  Ví dụ: "Kushida Kikyou là người như thế nào?"                  ║
╚══════════════════════════════════════════════════════════════════╝

  RAG THƯỜNG (chỉ dùng cosine similarity):
  ┌────────────────────────────────────────────────────────┐
  │  node "2.2 Horikita"   score: 0.72  ← lên đầu SAI!   │
  │  node "2.3 Kushida"    score: 0.69  ← đúng nhưng #2  │
  │  node "2.5 Ichinose"   score: 0.61                    │
  │  ❌ Model embedding không phân biệt tốt tên riêng     │
  └────────────────────────────────────────────────────────┘

  BOOKRAG (cosine + GT-Links boost):
  ┌────────────────────────────────────────────────────────┐
  │  Tìm entity "Kushida" trong câu hỏi                   │
  │  GT-Links["Kushida"] → [node "2.3 Kushida", ...]      │
  │                                                        │
  │  node "2.3 Kushida"   0.69 × 1.2(leaf) × 1.8(entity) │
  │                      = 1.49  ← lên đầu ĐÚNG! ✅       │
  │  node "2.2 Horikita"  0.72 × 1.2(leaf)                │
  │                      = 0.86                            │
  │  node "3.4 Bí Mật"    0.58 × 1.2 × 1.8(entity)       │
  │                      = 1.25  ← cũng boost vì Kushida  │
  └────────────────────────────────────────────────────────┘

           Leaf boost × 1.2        Entity boost × 1.8
                │                        │
                └────────────┬───────────┘
                             │
              Section cụ thể tốt hơn   Entity được hỏi
              chapter tổng quát         được ưu tiên
```

---

## GIẢI THÍCH THUẬT NGỮ TIẾNG ANH

### Thuật ngữ trong Paper BookRAG (arXiv 2512.03413)

| Thuật ngữ | Viết tắt | Ý nghĩa đơn giản |
|-----------|----------|------------------|
| **Retrieval-Augmented Generation** | RAG | "Tìm kiếm rồi mới sinh câu trả lời" — LLM không trả lời từ bộ nhớ mà đọc tài liệu trước rồi mới trả lời |
| **BookIndex** | — | Cấu trúc dữ liệu đặc biệt của BookRAG gồm 3 phần: cây + đồ thị + GT-Links |
| **Hierarchical Tree** | — | "Cây phân cấp" — biểu diễn cấu trúc mục lục của tài liệu (chương → section → đoạn) |
| **Knowledge Graph** | KG | "Đồ thị tri thức" — mạng lưới các nhân vật/khái niệm nối nhau bằng quan hệ có hướng |
| **Ground-Truth Links** | GT-Links | "Liên kết thật sự" — bảng tra cứu: entity này xuất hiện ở section nào trong cây |
| **Information Foraging Theory** | IFT | Lý thuyết từ sinh học: động vật tìm thức ăn theo "mùi" — agent tìm thông tin theo "độ liên quan" |
| **Single-hop query** | — | Câu hỏi một bước — chỉ cần đọc 1 section là đủ trả lời |
| **Multi-hop query** | — | Câu hỏi nhiều bước — cần kết hợp thông tin từ 2+ section qua quan hệ |
| **Global query** | — | Câu hỏi toàn tài liệu — cần tổng hợp từ nhiều chương |
| **Skyline / Pareto Frontier** | — | Lọc giữ lại những node "không bị ai beat cả hai chiều" — tránh bỏ sót node quan trọng |

---

### Thuật ngữ kỹ thuật trong code

| Thuật ngữ | Ý nghĩa đơn giản |
|-----------|------------------|
| **Embedding** | Chuyển text thành danh sách số thực (vector) để máy tính có thể so sánh. Ví dụ: "Ayanokoji" → `[0.12, -0.34, 0.89, ...]` (384 số) |
| **Vector** | Danh sách số thực đại diện cho ý nghĩa của một đoạn text |
| **Cosine Similarity** | Đo góc giữa 2 vector — góc nhỏ = 2 đoạn text có ý nghĩa gần nhau. Từ -1 đến 1, càng gần 1 càng giống |
| **Top-K** | Lấy K kết quả tốt nhất (ví dụ top-3 section liên quan nhất) |
| **Leaf node** | Node lá — node cuối cùng trong cây, không có node con, chứa nội dung chi tiết nhất |
| **Pickle** | Định dạng lưu trữ object Python xuống file (.pkl) để đọc lại sau mà không cần tính toán lại |
| **Operator** | "Công cụ" — mỗi loại query có một operator riêng (Selector/Reasoner/SkylineRanker) |
| **Seed entity** | Entity "hạt giống" — entity được tìm thấy trong câu hỏi, dùng làm điểm xuất phát duyệt đồ thị |
| **Graph traversal** | "Duyệt đồ thị" — đi qua các node trong đồ thị theo các cạnh quan hệ |
| **Depth (hop)** | Số bước nhảy trong đồ thị. depth=2 nghĩa là từ entity A, đi qua tối đa 2 cạnh |
| **Community detection** | Thuật toán tự động tìm nhóm entity liên quan nhau trong đồ thị (như "nhóm nhân vật lớp D") |
| **Pre-compute** | Tính toán trước và lưu lại — embedding được tính 1 lần khi build_index, không tính lại khi query |

---

### Thuật ngữ trong code project này

| Tên trong code | Ý nghĩa |
|---------------|---------|
| `TreeNode` | Một ô trong cây — đại diện cho một chương hoặc section |
| `HierarchicalTree` | Toàn bộ cây phân cấp của tài liệu |
| `KnowledgeGraph` | Đồ thị quan hệ giữa các nhân vật/khái niệm |
| `GTLinks` | Bảng tra: entity → các section chứa entity đó |
| `BookIndex` | Gói gồm Tree + KnowledgeGraph + GTLinks |
| `Selector` | Operator cho Single-hop: tìm section bằng similarity + GT-Links boost |
| `Reasoner` | Operator cho Multi-hop: duyệt đồ thị rồi map qua GT-Links |
| `SkylineRanker` | Operator cho Global: kết hợp semantic score + structural importance |
| `BookRAGAgent` | Bộ não điều phối: nhận câu hỏi → phân loại → gọi operator → trả lời |
| `classify_query()` | Hàm phân loại câu hỏi (Single/Multi/Global) dùng rule-based |
| `embed_fn` | Hàm chuyển text → vector (dùng sentence-transformers) |
| `bookindex.pkl` | File lưu BookIndex đã build sẵn xuống disk |
| `node.embedding` | Vector 384 chiều được tính sẵn cho mỗi section |
| `PREDEFINED_ENTITIES` | Danh sách nhân vật/địa điểm định nghĩa tay (trong thực tế dùng LLM tự động) |
| `PREDEFINED_RELATIONS` | Danh sách quan hệ giữa nhân vật định nghĩa tay |

---

### Các quan hệ trong Knowledge Graph của project

| Quan hệ | Ý nghĩa | Ví dụ |
|---------|---------|-------|
| `SECRETLY_LEADS` | Bí mật dẫn dắt | Ayanokoji → lớp D |
| `MANIPULATES` | Thao túng | Ayanokoji → Horikita |
| `RIVALS` | Đối thủ ngang tầm | Ayanokoji ↔ Sakayanagi |
| `DEFEATED` | Đánh bại | Ayanokoji → Ryuuen |
| `DISCOVERED` | Phát hiện ra | Ryuuen → Ayanokoji |
| `ALLIED_WITH` | Liên minh với | Ryuuen → Ayanokoji |
| `CREATED_BY` | Được tạo ra bởi | Ayanokoji → Căn Phòng Trắng |
| `ESCAPED_FROM` | Trốn thoát khỏi | Ayanokoji → Căn Phòng Trắng |
| `FOUNDED` | Sáng lập | Ayanokoji Touya → Căn Phòng Trắng |
| `KNOWS_ABOUT` | Biết về | Sakayanagi → Căn Phòng Trắng |
| `HATES` | Căm ghét | Kushida → Horikita |
| `KNOWS_SECRET_OF` | Biết bí mật của | Horikita → Kushida |
| `BETRAYED` | Phản bội | Kushida → lớp D |
| `BLACKMAILS` | Tống tiền/ép buộc | Chabashira → Ayanokoji |
| `WANTS_TO_DEFEAT` | Muốn đánh bại | Sakayanagi → Ayanokoji |
| `UNCONTROLLED_BY` | Không kiểm soát được | Koenji → Ayanokoji |

---

> **Tóm lại bằng 1 câu:**
> BookRAG = thay vì cắt sách thành mảnh vụn (RAG thường),
> hãy **giữ nguyên cấu trúc** (cây phân cấp) + **hiểu quan hệ** (đồ thị)
> + **biết entity ở đâu** (GT-Links) → tìm kiếm thông minh hơn nhiều.
