# BookRAG — Sơ Đồ 3 Thành Phần Chi Tiết
> Dữ liệu thực tế từ `data/classroom_elite.txt` + `src/book_index.py`

---

## Tổng Quan: BookIndex = 3 Thành Phần Kết Hợp

```
┌─────────────────────────────────────────────────────────────────────┐
│                          B O O K I N D E X                          │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ HierarchicalTree │◄───│    GT-Links       │───►│KnowledgeGraph │  │
│  │                  │    │                  │    │               │  │
│  │  Cây phân cấp    │    │ Entity → Node ID │    │ Entity + Quan │  │
│  │  tài liệu        │    │ (cầu nối 2 bên)  │    │ hệ có hướng   │  │
│  │  (26 nodes)      │    │ (29 entities)    │    │ (29 nodes,    │  │
│  └──────────────────┘    └──────────────────┘    │  29 edges)    │  │
│                                                   └───────────────┘  │
│                                                                      │
│  Khi query đến:                                                      │
│    query ──► KnowledgeGraph (tìm entity liên quan)                   │
│           ──► GT-Links (entity → node_id)                            │
│           ──► HierarchicalTree (lấy nội dung section)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

# SƠ ĐỒ 1: HIERARCHICAL TREE
> Cây phân cấp cấu trúc tài liệu. Xây từ Markdown heading: `##` = chapter (level 1), `###` = section (level 2).

```
[ROOT] LỚP HỌC ĐỀ CAO THỰC LỰC  (level=0)
│
├── [CH1] Chương 1: Giới Thiệu Tác Phẩm  (level=1)
│   ├── [1.1] 1.1 Thông Tin Tác Phẩm  (level=2) ─── 475 chars
│   │         "Lớp Học Đề Cao Thực Lực (ようこそ実力至上主義の教室へ) là bộ light
│   │          novel của Kinugasa Shougo, minh họa Tomose Shunsaku, xuất bản
│   │          2015. Anime 2017, manga. Một trong LN ăn khách nhất Nhật Bản."
│   │
│   ├── [1.2] 1.2 Bối Cảnh  (level=2) ─── 406 chars
│   │         "Trường Trung Học Nuôi Dưỡng Cấp Cao Tokyo. Nội trú đặc biệt do
│   │          chính phủ tài trợ. Tỷ lệ vào đại học ~100%. Khuôn viên như
│   │          thành phố thu nhỏ."
│   │
│   ├── [1.3] 1.3 Hệ Thống Lớp Học và Điểm S  (level=2) ─── 461 chars
│   │         "4 lớp: A (ưu tú) → B → C → D (thấp nhất). Điểm S (Class Points)
│   │          = tiền tệ ảo để đổi đặc quyền và đo thứ hạng. Private Points
│   │          cho mua sắm cá nhân."
│   │
│   └── [1.4] 1.4 Chủ Đề Chính  (level=2) ─── 354 chars
│             "Triết lý 'Thực lực là tất cả'. Quy tắc bề ngoài công bằng nhưng
│              thực chất thử thách cực hạn. Câu hỏi: Thực lực thật sự là gì?"
│
├── [CH2] Chương 2: Nhân Vật  (level=1)
│   ├── [2.1] 2.1 Ayanokoji Kiyotaka – Nhân Vật Chính  (level=2) ─── 642 chars
│   │         "Học sinh lớp D. Cố ý để điểm 50/môn. Sản phẩm của Căn Phòng
│   │          Trắng do cha Ayanokoji Touya tạo. Trí tuệ vượt trội, phân tích
│   │          tâm lý tinh vi, thể chất đỉnh cao. Bí mật dẫn dắt lớp D."
│   │
│   ├── [2.2] 2.2 Horikita Suzune – Thủ Lĩnh Lớp D  (level=2) ─── 601 chars
│   │         "Lớp D. Lạnh lùng, kiêu ngạo. Mục tiêu lên lớp A để chứng tỏ
│   │          với anh Horikita Manabu. Dần trở thành thủ lĩnh thực sự.
│   │          Không biết Ayanokoji đang hỗ trợ cô."
│   │
│   ├── [2.3] 2.3 Kushida Kikyou – Mặt Nạ Hoàn Hảo  (level=2) ─── 529 chars
│   │         "Được yêu thích nhất trường. Nhưng thực ra lạnh lùng, toan tính.
│   │          Căm thù Horikita vì bí mật trường cũ. Sẵn sàng phản bội để
│   │          bảo vệ hình ảnh."
│   │
│   ├── [2.4] 2.4 Sakayanagi Arisu – Nữ Hoàng Lớp A  (level=2) ─── 581 chars
│   │         "Lớp A. Bệnh tim, phải chống gậy. Trí tuệ sắc bén nhất trường.
│   │          Biết về Căn Phòng Trắng. Xem Ayanokoji là đối thủ duy nhất
│   │          xứng tầm. Cha: Sakayanagi Tomoya (Chủ Tịch HĐQT)."
│   │
│   ├── [2.5] 2.5 Ichinose Honami – Biểu Tượng Lớp B  (level=2) ─── 462 chars
│   │         "Lớp B. Tốt bụng, lãnh đạo xuất sắc. Xây dựng lớp B theo niềm
│   │          tin và hỗ trợ lẫn nhau. Mang bí mật đau lòng từ quá khứ."
│   │
│   ├── [2.6] 2.6 Ryuuen Kakeru – Bạo Chúa Lớp C  (level=2) ─── 633 chars
│   │         "Lớp C. Cai trị bằng sức mạnh và đe dọa. Hệ thống gián điệp
│   │          dày đặc. Tìm ra Ayanokoji là chỉ huy bí ẩn. Sau khi thua,
│   │          trở thành đồng minh bất ngờ."
│   │
│   ├── [2.7] 2.7 Horikita Manabu – Anh Trai Hội Trưởng  (level=2) ─── 376 chars
│   │         "Anh trai Horikita. Hội Trưởng Hội Học Sinh. Lạnh lùng, giữ
│   │          khoảng cách với em để thúc đẩy. Nhận ra tiềm năng Ayanokoji
│   │          sớm nhất."
│   │
│   ├── [2.8] 2.8 Chabashira Sae – Giáo Viên Chủ Nhiệm Lớp D  (level=2) ─── 394 chars
│   │         "GVCN lớp D. Biết Ayanokoji từ Căn Phòng Trắng. Dùng bí mật
│   │          để ép anh giúp lớp D đạt điểm S cao. Có mục tiêu riêng:
│   │          đưa lớp D lên A."
│   │
│   ├── [2.9] 2.9 Ayanokoji Touya – Người Tạo Ra Căn Phòng Trắng  (level=2) ─── 452 chars
│   │         "Cha Ayanokoji. Sáng lập Căn Phòng Trắng. Nhà giáo dục cực đoan.
│   │          Tối ưu hóa con người từ sơ sinh. Kiyotaka là 'sản phẩm thành
│   │          công nhất' rồi trốn thoát."
│   │
│   └── [2.10] 2.10 Koenji Rokusuke – Thiên Tài Ích Kỷ  (level=2) ─── 449 chars
│              "Lớp D. Điển trai, tự cao. Không quan tâm thứ hạng. Tài năng
│               xuất chúng: thể chất đỉnh, trí nhớ phi thường. Ngay cả
│               Ayanokoji cũng không kiểm soát được."
│
├── [CH3] Chương 3: Sự Kiện Chính  (level=1)
│   ├── [3.1] 3.1 Năm Nhất – Sự Thức Tỉnh Của Lớp D  (level=2) ─── 580 chars
│   │         "Lớp D nhận 100.000 điểm S rồi tiêu hết → bài học đầu tiên.
│   │          Ayanokoji: ngăn Sudo Ken bị đuổi học, giúp lớp D qua Special
│   │          Exams, dẫn dắt qua Horikita như con rối."
│   │
│   ├── [3.2] 3.2 Kỳ Thi Đảo Hoang (Island Exam)  (level=2) ─── 345 chars
│   │         "Sinh tồn trên đảo. Ryuuen bắt đầu nghi ngờ có 'bộ não ẩn' sau
│   │          lớp D. Ayanokoji phối hợp chiến lược với Horikita từ xa."
│   │
│   ├── [3.3] 3.3 Ryuuen Điều Tra Và Phát Hiện Ayanokoji  (level=2) ─── 464 chars
│   │         "Ryuuen tung gián điệp, kết luận Ayanokoji là chỉ huy bí ẩn.
│   │          Thách thức trực tiếp → Ayanokoji bộc lộ thực lực lần đầu.
│   │          Đánh bại Ryuuen → Ryuuen chuyển sang hỗ trợ."
│   │
│   ├── [3.4] 3.4 Bí Mật Của Kushida Bị Đe Dọa  (level=2) ─── 440 chars
│   │         "Kushida phá hoại Horikita liên tục. Hợp tác lớp khác, rò rỉ
│   │          thông tin lớp D. Ayanokoji giữ Kushida vì 'có ích hơn khi
│   │          còn trong lớp D'."
│   │
│   ├── [3.5] 3.5 Kỳ Thi Tàu Thuyền và Liên Minh Bất Ngờ  (level=2) ─── 393 chars
│   │         "Hợp tác + cạnh tranh đồng thời. Ayanokoji tiếp cận Sakayanagi
│   │          và Ichinose để đọc chiến lược. Sakayanagi xác nhận biết về
│   │          Căn Phòng Trắng."
│   │
│   └── [3.6] 3.6 Căn Phòng Trắng Và Mối Đe Dọa Từ Cha  (level=2) ─── 352 chars
│             "Ayanokoji Touya cử 'sản phẩm' khác đến thách thức Kiyotaka.
│              Cuộc đối đầu bộc lộ thực lực thật sự của Ayanokoji."
│
├── [CH4] Chương 4: Hệ Thống và Cơ Chế  (level=1)
│   ├── [4.1] 4.1 Kỳ Thi Đặc Biệt (Special Exams)  (level=2) ─── 456 chars
│   │         "Định kỳ, không chỉ học lực mà còn trí tuệ xã hội, đàm phán,
│   │          chiến lược nhóm. Ảnh hưởng điểm S. Có thể loại học sinh hoặc
│   │          chuyển lớp. Gồm: đảo hoang, tàu thuyền, bỏ phiếu loại trừ."
│   │
│   ├── [4.2] 4.2 Hệ Thống Điểm S và Quyền Mua Đặc Quyền  (level=2) ─── 409 chars
│   │         "Điểm S lớp (thứ hạng, chuyển nhượng) + điểm S cá nhân (mua
│   │          đồ, phiếu bảo vệ). Phản ánh thế giới thực: tài nguyên và
│   │          quyền lực có thể mua được."
│   │
│   ├── [4.3] 4.3 Hội Học Sinh và Quyền Lực Ngầm  (level=2) ─── 411 chars
│   │         "Hội Học Sinh có quyền đặc biệt, ít ràng buộc. Horikita Manabu
│   │          (Hội Trưởng) → tốt nghiệp → Nagumo Miyabi lên nắm quyền,
│   │          tạo mối đe dọa mới."
│   │
│   └── [4.4] 4.4 Căn Phòng Trắng (White Room)  (level=2) ─── 431 chars
│             "Cơ sở bí mật do Ayanokoji Touya thành lập. Trẻ em huấn luyện
│              khắc nghiệt: không tình cảm, không bạn bè. Kiyotaka: điểm
│              tuyệt đối mọi hạng mục → trốn thoát. Giải thích nguồn gốc."
│
└── [CH5] Chương 5: Quan Hệ và Liên Minh  (level=1)
    ├── [5.1] 5.1 Ayanokoji và Horikita  (level=2) ─── 445 chars
    │         "Ayanokoji dùng Horikita như 'người tiền tuyến', thiết kế tình
    │          huống để cô thành công. Horikita không biết. Dần trở nên
    │          chân thật hơn."
    │
    ├── [5.2] 5.2 Ayanokoji và Sakayanagi  (level=2) ─── 381 chars
    │         "Sakayanagi nhìn thấu Ayanokoji ngay từ đầu. Đối kháng + tôn
    │          trọng. Cuộc đối đầu giữa 2 thiên tài cùng đẳng cấp."
    │
    ├── [5.3] 5.3 Ayanokoji và Ryuuen  (level=2) ─── 374 chars
    │         "Sau thất bại, Ryuuen chọn im lặng quan sát. Người duy nhất
    │          biết Ayanokoji là ai mà vẫn hành động độc lập."
    │
    └── [5.4] 5.4 Kushida và Horikita  (level=2) ─── 399 chars
              "Kushida căm thù vì Horikita biết bí mật trường cũ (bùng phát
               thịnh nộ thật). Horikita giữ bí mật vì Ayanokoji thuyết phục.
               Sự căng thẳng như vũ khí 2 lưỡi."
```

**Thống kê cây:**
- Tổng nodes: 31 (1 root + 5 chapter + 24 section + 1 root)
- Nodes level 0 (root): 1
- Nodes level 1 (chapter): 5
- Nodes level 2 (section): 24 ← đây là các leaf nodes
- Nội dung: ~10,000 chars tổng cộng

---

# SƠ ĐỒ 2: KNOWLEDGE GRAPH
> Đồ thị thực thể và quan hệ. Nodes = thực thể, Edges = quan hệ có hướng.

## 2A. Danh Sách Tất Cả Thực Thể (29 nodes)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE GRAPH — NODES                             │
├────────────────────────┬──────────┬────────────────────────────────────┤
│ Tên Entity             │ Loại     │ Mô tả                              │
├────────────────────────┼──────────┼────────────────────────────────────┤
│ Ayanokoji              │ PERSON   │ Nhân vật chính, thiên tài ẩn       │
│ Ayanokoji Kiyotaka     │ PERSON   │ Tên đầy đủ (= Ayanokoji)           │
│ Horikita               │ PERSON   │ Thủ lĩnh lớp D                     │
│ Horikita Suzune        │ PERSON   │ Tên đầy đủ (= Horikita)            │
│ Kushida                │ PERSON   │ Cô gái hai mặt                     │
│ Kushida Kikyou         │ PERSON   │ Tên đầy đủ (= Kushida)             │
│ Sakayanagi             │ PERSON   │ Thủ lĩnh lớp A                     │
│ Sakayanagi Arisu       │ PERSON   │ Tên đầy đủ (= Sakayanagi)          │
│ Ichinose               │ PERSON   │ Thủ lĩnh lớp B                     │
│ Ichinose Honami        │ PERSON   │ Tên đầy đủ (= Ichinose)            │
│ Ryuuen                 │ PERSON   │ Bạo chúa lớp C → đồng minh         │
│ Ryuuen Kakeru          │ PERSON   │ Tên đầy đủ (= Ryuuen)              │
│ Horikita Manabu        │ PERSON   │ Anh trai, Hội Trưởng               │
│ Chabashira             │ PERSON   │ GVCN lớp D                         │
│ Chabashira Sae         │ PERSON   │ Tên đầy đủ (= Chabashira)          │
│ Ayanokoji Touya        │ PERSON   │ Cha Ayanokoji, sáng lập White Room │
│ Koenji                 │ PERSON   │ Thiên tài ích kỷ lớp D             │
│ Koenji Rokusuke        │ PERSON   │ Tên đầy đủ (= Koenji)              │
│ Sudo Ken               │ PERSON   │ Học sinh lớp D hay gây rắc rối     │
│ Nagumo                 │ PERSON   │ Hội Trưởng mới năm 2               │
├────────────────────────┼──────────┼────────────────────────────────────┤
│ Căn Phòng Trắng        │ CONCEPT  │ Cơ sở huấn luyện bí mật            │
│ White Room             │ CONCEPT  │ Tên gốc tiếng Anh                  │
│ điểm S                 │ CONCEPT  │ Tiền tệ ảo trong trường            │
│ kỳ thi đặc biệt        │ CONCEPT  │ Special Exam định kỳ               │
├────────────────────────┼──────────┼────────────────────────────────────┤
│ lớp A                  │ CLASS    │ Lớp ưu tú nhất                     │
│ lớp B                  │ CLASS    │ Lớp 2, Ichinose dẫn đầu            │
│ lớp C                  │ CLASS    │ Lớp 3, Ryuuen cai trị              │
│ lớp D                  │ CLASS    │ Lớp thấp nhất, nhân vật chính      │
├────────────────────────┼──────────┼────────────────────────────────────┤
│ Hội Học Sinh           │ ORG      │ Tổ chức quyền lực đặc biệt         │
└────────────────────────┴──────────┴────────────────────────────────────┘
  ↑ 20 PERSON + 4 CONCEPT + 4 CLASS + 1 ORG = 29 nodes
  + "perfect student" + "Sakayanagi Tomoya" (tự động thêm bởi UNKNOWN)
```

## 2B. Tất Cả Quan Hệ (29 edges có hướng)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE GRAPH — EDGES                             │
├────┬──────────────────────┬─────────────────────┬──────────────────────┤
│ #  │ SOURCE               │ RELATION             │ TARGET               │
├────┼──────────────────────┼─────────────────────┼──────────────────────┤
│ 01 │ Ayanokoji            │ SECRETLY_LEADS      │ lớp D                │
│ 02 │ Ayanokoji            │ MANIPULATES         │ Horikita             │
│ 03 │ Ayanokoji            │ RIVALS              │ Sakayanagi           │
│ 04 │ Ayanokoji            │ DEFEATED            │ Ryuuen               │
│ 05 │ Ayanokoji            │ CREATED_BY          │ Căn Phòng Trắng      │
│ 06 │ Ayanokoji            │ ESCAPED_FROM        │ Căn Phòng Trắng      │
│ 07 │ Ayanokoji Touya      │ FOUNDED             │ Căn Phòng Trắng      │
│ 08 │ Ayanokoji Touya      │ FATHER_OF           │ Ayanokoji            │
│ 09 │ Ayanokoji Touya      │ WANTS_BACK          │ Ayanokoji            │
│ 10 │ Horikita             │ LEADS               │ lớp D                │
│ 11 │ Horikita             │ HATED_BY            │ Kushida              │
│ 12 │ Horikita             │ KNOWS_SECRET_OF     │ Kushida              │
│ 13 │ Horikita Manabu      │ BROTHER_OF          │ Horikita             │
│ 14 │ Horikita Manabu      │ LEADS               │ Hội Học Sinh         │
│ 15 │ Kushida              │ HATES               │ Horikita             │
│ 16 │ Kushida              │ PRETENDS_TO_BE      │ perfect student      │
│ 17 │ Kushida              │ BETRAYED            │ lớp D                │
│ 18 │ Sakayanagi           │ LEADS               │ lớp A                │
│ 19 │ Sakayanagi           │ KNOWS_ABOUT         │ Căn Phòng Trắng      │
│ 20 │ Sakayanagi           │ WANTS_TO_DEFEAT     │ Ayanokoji            │
│ 21 │ Sakayanagi Arisu     │ DAUGHTER_OF         │ Sakayanagi Tomoya    │
│ 22 │ Ryuuen               │ LEADS               │ lớp C                │
│ 23 │ Ryuuen               │ DISCOVERED          │ Ayanokoji            │
│ 24 │ Ryuuen               │ ALLIED_WITH         │ Ayanokoji            │
│ 25 │ Ichinose             │ LEADS               │ lớp B                │
│ 26 │ Chabashira           │ KNOWS_SECRET_OF     │ Ayanokoji            │
│ 27 │ Chabashira           │ BLACKMAILS          │ Ayanokoji            │
│ 28 │ Koenji               │ MEMBER_OF           │ lớp D                │
│ 29 │ Koenji               │ UNCONTROLLED_BY     │ Ayanokoji            │
└────┴──────────────────────┴─────────────────────┴──────────────────────┘
```

## 2C. Sơ Đồ Graph Trực Quan (ASCII)

```
                          ┌──────────────────┐
                          │ Ayanokoji Touya  │
                          └──────────────────┘
                           │ FATHER_OF │ FOUNDED  │ WANTS_BACK
                           ▼           ▼           ▼
          ┌────────────────────┐   ┌──────────────────────┐
          │    AYANOKOJI       │   │   Căn Phòng Trắng    │
          │  (Kiyotaka)        │   │   / White Room        │
          └────────────────────┘   └──────────────────────┘
           │   │   │   │   │   │           ▲
           │   │   │   │   │   └─CREATED_BY┘
           │   │   │   │   └─ESCAPED_FROM──┘
           │   │   │   │
           │   │   │   └─SECRETLY_LEADS──────────────►[ lớp D ]◄──LEADS─────[ Horikita ]
           │   │   │                                       │                       │
           │   │   └─MANIPULATES────────────────────►[ Horikita ]                 │
           │   │                                      │   │                        │
           │   │                               LEADS  │   │ HATED_BY  KNOWS_SECRET │
           │   │                                  ▼   │   ▼               ▼        │
           │   │                              [lớp D] │ [Kushida]────HATES─────────┘
           │   │                                      │     │
           │   │                              KNOWS_SECRET  └─BETRAYED──►[ lớp D ]
           │   │                              _OF Kushida   └─PRETENDS──►[perfect student]
           │   │
           │   └─RIVALS──────────────────────────────►[ Sakayanagi ]──LEADS──►[ lớp A ]
           │                                                │
           │                                        KNOWS_ABOUT──►[Căn Phòng Trắng]
           │                                        WANTS_TO_DEFEAT──►[Ayanokoji]◄┐
           │                                                                        │
           └─DEFEATED──────────────────────────────►[ Ryuuen ]──LEADS──►[ lớp C ] │
                                                      │                             │
                                               DISCOVERED──►[Ayanokoji]            │
                                               ALLIED_WITH──►[Ayanokoji]◄──────────┘


[ Ichinose ]──LEADS──►[ lớp B ]

[ Horikita Manabu ]──BROTHER_OF──►[ Horikita ]
                    └─LEADS──────►[ Hội Học Sinh ]

[ Chabashira ]──KNOWS_SECRET_OF──►[ Ayanokoji ]
              └─BLACKMAILS──────►[ Ayanokoji ]

[ Koenji ]──MEMBER_OF──────►[ lớp D ]
          └─UNCONTROLLED_BY──►[ Ayanokoji ]

[ Sakayanagi Arisu ]──DAUGHTER_OF──►[ Sakayanagi Tomoya ]
```

## 2D. Multi-hop Reasoning — Ví Dụ Truy Vết Quan Hệ

```
Q: "Ai đã tạo ra người biết bí mật của Ayanokoji?"

Bước 1: Tìm node "Ayanokoji"
Bước 2: Duyệt cạnh vào (predecessors):
  → Chabashira ──KNOWS_SECRET_OF──► Ayanokoji
  → Ryuuen     ──DISCOVERED──────► Ayanokoji
  → Sakayanagi ──WANTS_TO_DEFEAT──► Ayanokoji  (cô biết về White Room)

Bước 3 (multi-hop): Ai tạo ra Ayanokoji?
  → Ayanokoji Touya ──FATHER_OF──► Ayanokoji
  → Căn Phòng Trắng ──[CREATED]──► Ayanokoji (qua CREATED_BY ngược lại)
  → Ayanokoji Touya ──FOUNDED──►  Căn Phòng Trắng

Kết luận path: Ayanokoji Touya → FOUNDED → Căn Phòng Trắng → CREATED → Ayanokoji
```

---

# SƠ ĐỒ 3: GT-LINKS (Ground-Truth Links)
> Ánh xạ Entity → danh sách Node ID trong HierarchicalTree.
> Đây là "cầu nối" giữa KnowledgeGraph và HierarchicalTree.

## 3A. Bảng Đầy Đủ Entity → Nodes

```
┌────────────────────────┬──────────────────────────────────────────────────────────┐
│ Entity                 │ Xuất hiện trong Nodes                                    │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ayanokoji              │ [2.1][2.2][2.4][2.6][2.7][2.8][2.10]                    │
│                        │ [3.1][3.2][3.3][3.4][3.5][3.6]                          │
│                        │ [5.1][5.2][5.3][5.4]                                    │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ayanokoji Kiyotaka     │ [2.1][3.6][4.4]                                         │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Horikita               │ [2.2][2.3][2.7]                                         │
│                        │ [3.1][3.2][3.4]                                         │
│                        │ [5.1][5.4]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Horikita Suzune        │ [2.2][5.1]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Kushida                │ [2.3][3.4][5.4]                                         │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Kushida Kikyou         │ [2.3]                                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Sakayanagi             │ [2.4][3.5][5.2]                                         │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Sakayanagi Arisu       │ [2.4][5.2]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ichinose               │ [2.5][3.5]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ichinose Honami        │ [2.5]                                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ryuuen                 │ [2.6][3.2][3.3][5.3]                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ryuuen Kakeru          │ [2.6][3.3]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Horikita Manabu        │ [2.7][4.3]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Chabashira             │ [2.8]                                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Chabashira Sae         │ [2.8]                                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ayanokoji Touya        │ [2.9][3.6][4.4]                                         │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Koenji                 │ [2.10]                                                  │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Koenji Rokusuke        │ [2.10]                                                  │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Sudo Ken               │ [3.1]                                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Nagumo                 │ [4.3]                                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Căn Phòng Trắng        │ [2.1][2.4][2.9][3.5][3.6][4.4][5.2]                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ White Room             │ [4.4]                                                   │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ lớp A                  │ [1.3][2.2][2.4]                                         │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ lớp B                  │ [1.3][2.5]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ lớp C                  │ [1.3][2.6]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ lớp D                  │ [1.3][2.1][2.2][2.6][2.8][2.10]                        │
│                        │ [3.1][3.2][3.3][3.4][5.1]                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ điểm S                 │ [1.3][4.2]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ Hội Học Sinh           │ [2.7][4.3]                                              │
├────────────────────────┼──────────────────────────────────────────────────────────┤
│ kỳ thi đặc biệt        │ [3.1][4.1]                                              │
└────────────────────────┴──────────────────────────────────────────────────────────┘
  Tổng: 29 entities × trung bình ~3 nodes = ~87 links
```

## 3B. Sơ Đồ GT-Links — Nhìn Từ Node (Node nào chứa Entity nào)

```
[1.3] Hệ Thống Lớp Học và Điểm S
  └── entities: lớp A, lớp B, lớp C, lớp D, điểm S

[2.1] Ayanokoji Kiyotaka – Nhân Vật Chính
  └── entities: Ayanokoji, Ayanokoji Kiyotaka, Căn Phòng Trắng, lớp D

[2.2] Horikita Suzune – Thủ Lĩnh Lớp D
  └── entities: Horikita, Horikita Suzune, Ayanokoji, lớp A, lớp D

[2.3] Kushida Kikyou – Mặt Nạ Hoàn Hảo
  └── entities: Kushida, Kushida Kikyou, Horikita

[2.4] Sakayanagi Arisu – Nữ Hoàng Lớp A
  └── entities: Sakayanagi, Sakayanagi Arisu, Ayanokoji, Căn Phòng Trắng, lớp A

[2.5] Ichinose Honami – Biểu Tượng Lớp B
  └── entities: Ichinose, Ichinose Honami, lớp B

[2.6] Ryuuen Kakeru – Bạo Chúa Lớp C
  └── entities: Ryuuen, Ryuuen Kakeru, Ayanokoji, lớp C, lớp D

[2.7] Horikita Manabu – Anh Trai Hội Trưởng
  └── entities: Horikita Manabu, Horikita, Ayanokoji, Hội Học Sinh

[2.8] Chabashira Sae – Giáo Viên Chủ Nhiệm Lớp D
  └── entities: Chabashira, Chabashira Sae, Ayanokoji, lớp D

[2.9] Ayanokoji Touya – Người Tạo Ra Căn Phòng Trắng
  └── entities: Ayanokoji Touya, Căn Phòng Trắng

[2.10] Koenji Rokusuke – Thiên Tài Ích Kỷ
  └── entities: Koenji, Koenji Rokusuke, Ayanokoji, lớp D

[3.1] Năm Nhất – Sự Thức Tỉnh Của Lớp D
  └── entities: Ayanokoji, Horikita, Sudo Ken, lớp D, kỳ thi đặc biệt

[3.2] Kỳ Thi Đảo Hoang
  └── entities: Ayanokoji, Horikita, Ryuuen, lớp D

[3.3] Ryuuen Điều Tra Và Phát Hiện Ayanokoji
  └── entities: Ayanokoji, Ryuuen, Ryuuen Kakeru, lớp D

[3.4] Bí Mật Của Kushida Bị Đe Dọa
  └── entities: Ayanokoji, Kushida, Horikita, lớp D

[3.5] Kỳ Thi Tàu Thuyền và Liên Minh Bất Ngờ
  └── entities: Ayanokoji, Sakayanagi, Ichinose, Căn Phòng Trắng

[3.6] Căn Phòng Trắng Và Mối Đe Dọa Từ Cha
  └── entities: Ayanokoji Touya, Ayanokoji Kiyotaka, Căn Phòng Trắng

[4.1] Kỳ Thi Đặc Biệt (Special Exams)
  └── entities: kỳ thi đặc biệt

[4.2] Hệ Thống Điểm S và Quyền Mua Đặc Quyền
  └── entities: điểm S

[4.3] Hội Học Sinh và Quyền Lực Ngầm
  └── entities: Hội Học Sinh, Horikita Manabu, Nagumo

[4.4] Căn Phòng Trắng (White Room)
  └── entities: Căn Phòng Trắng, White Room, Ayanokoji Touya, Ayanokoji Kiyotaka

[5.1] Ayanokoji và Horikita
  └── entities: Ayanokoji, Horikita, Horikita Suzune, lớp D

[5.2] Ayanokoji và Sakayanagi
  └── entities: Ayanokoji, Sakayanagi, Sakayanagi Arisu, Căn Phòng Trắng

[5.3] Ayanokoji và Ryuuen
  └── entities: Ayanokoji, Ryuuen

[5.4] Kushida và Horikita
  └── entities: Ayanokoji, Kushida, Horikita
```

---

# SƠ ĐỒ 4: BA THÀNH PHẦN PHỐI HỢP — Ví Dụ Query Thực Tế

```
══════════════════════════════════════════════════════════════════════
 QUERY: "Ai là người tìm ra Ayanokoji là chỉ huy bí ẩn của lớp D?"
══════════════════════════════════════════════════════════════════════

BƯỚC 1 — CLASSIFY (agent.py)
  → Có "ai" + entity "Ayanokoji" + "lớp D" → MULTI-HOP
  → Gọi Reasoner

BƯỚC 2 — REASONER dùng KnowledgeGraph
  Entity seed: "Ayanokoji", "lớp D"
  Duyệt graph hop=1:
    "Ayanokoji" predecessors:
      ← Ryuuen ──DISCOVERED──► Ayanokoji  ✓ liên quan!
      ← Chabashira ──KNOWS_SECRET_OF──► Ayanokoji
      ← Sakayanagi ──WANTS_TO_DEFEAT──► Ayanokoji
    "lớp D" predecessors:
      ← Horikita ──LEADS──► lớp D
      ← Ayanokoji ──SECRETLY_LEADS──► lớp D
      ← Koenji ──MEMBER_OF──► lớp D

  Entities liên quan nhất: {Ryuuen, Chabashira, lớp D, Ayanokoji}

BƯỚC 3 — GT-Links → tìm Node IDs
  "Ryuuen"     → [2.6][3.2][3.3][5.3]
  "Ayanokoji"  → [2.1][3.3][3.2]...
  "lớp D"      → [3.3][3.1]...
  Giao nhau nổi bật: [3.3] = "Ryuuen Điều Tra Và Phát Hiện Ayanokoji" ← chính xác!

BƯỚC 4 — HierarchicalTree → lấy content [3.3]
  "Ryuuen Kakeru tung gián điệp và dùng nhiều thủ đoạn để truy tìm
   'chỉ huy bí ẩn' của lớp D. Sau nhiều cuộc điều tra, anh ta kết luận
   đó là Ayanokoji..."

BƯỚC 5 — LLM generate answer
  → "Ryuuen Kakeru là người phát hiện ra Ayanokoji là chỉ huy bí ẩn..."

══════════════════════════════════════════════════════════════════════
```

---

# Tóm Tắt 3 Thành Phần

| Thành phần | Câu hỏi trả lời | Cấu trúc | Số lượng |
|---|---|---|---|
| **HierarchicalTree** | "Nội dung section X là gì?" | Cây (root→chapter→section) | 31 nodes |
| **KnowledgeGraph** | "Entity A quan hệ thế nào với B?" | Đồ thị có hướng | 29 nodes, 29 edges |
| **GT-Links** | "Entity X xuất hiện ở section nào?" | Dict[entity → [node_ids]] | 29 entities, ~87 links |
