# BookRAG — Triển khai Paper arXiv 2512.03413

> **"BookRAG: A Hierarchical Structure-aware Index-based Approach
> for Retrieval-Augmented Generation on Complex Documents"**
> Shu Wang, Yingli Zhou, Yixiang Fang — December 2025

Tài liệu mẫu: **Lớp Học Đề Cao Thực Lực** (Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e)

---

## Cài đặt & Chạy

```
# Bước 1: Cài đặt môi trường
setup.bat

# Bước 2: Xây dựng BookIndex
run_build.bat

# Bước 3: Hỏi đáp
run_query.bat --demo        ← 3 câu hỏi tự động (single/multi/global)
run_query.bat --compare     ← So sánh BookRAG vs flat RAG
run_query.bat               ← Chat tương tác
run_query.bat -q "Ayanokoji là ai?"
```

## Cấu trúc thư mục

```
bookrag/
├── data/
│   └── classroom_elite.txt   # Tài liệu mẫu (Lớp Học Đề Cao Thực Lực)
├── src/
│   ├── book_index.py         # BookIndex: Tree + KnowledgeGraph + GT-Links
│   ├── operators.py          # Selector / Reasoner / Skyline_Ranker
│   ├── agent.py              # BookRAG Agent + Query Classifier (IFT)
│   └── __init__.py
├── build_index.py            # Bước 1: xây dựng BookIndex → bookindex.pkl
├── query.py                  # Bước 2: hỏi đáp
├── setup.bat                 # Tạo venv + cài thư viện
├── run_build.bat             # Chạy build_index.py trong venv
├── run_query.bat             # Chạy query.py trong venv
├── requirements.txt
├── .env.example
├── README.md                 # File này
└── EXPLAINER.md              # Giải thích chi tiết từng file code
```

## Câu hỏi mẫu

| Loại | Câu hỏi | Operator |
|------|---------|----------|
| Single-hop | `Kushida Kikyou là người như thế nào?` | Selector |
| Single-hop | `Căn Phòng Trắng là gì?` | Selector |
| Single-hop | `Sakayanagi Arisu có đặc điểm gì?` | Selector |
| Multi-hop | `Tại sao Ryuuen lại phát hiện ra Ayanokoji?` | Reasoner |
| Multi-hop | `Ai biết bí mật thật của Ayanokoji?` | Reasoner |
| Multi-hop | `Mối quan hệ giữa Ayanokoji và Sakayanagi là gì?` | Reasoner |
| Global | `Tóm tắt hệ thống lớp học và điểm S` | SkylineRanker |
| Global | `Các chủ đề chính của tác phẩm là gì?` | SkylineRanker |

## Ghi chú về dữ liệu

File `data/classroom_elite.txt` là **tóm tắt có cấu trúc** dùng Markdown heading (`##`, `###`) để hệ thống phân tích cây phân cấp
