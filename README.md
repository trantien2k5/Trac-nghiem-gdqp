# Ôn Tập Trắc Nghiệm GDQP

Ứng dụng web (single-page, không cần build) để ôn tập trắc nghiệm Giáo dục quốc phòng và an ninh — có chế độ Luyện tập (tự động lặp lại câu sai, ưu tiên câu chưa thuộc), Thi thử (tính giờ), Ôn câu sai và Luyện tập thông minh (chọn câu theo thuật toán lặp lại ngắt quãng). Có tab Thống kê tổng quan, chế độ sáng/tối.

📘 **Muốn hiểu/tái sử dụng thuật toán độ thuộc, lặp lại ngắt quãng, chọn câu thông minh, thống kê...** xem chi tiết ở [`docs/THUAT-TOAN.md`](docs/THUAT-TOAN.md).

## Cấu trúc thư mục

```
index.html      Toàn bộ giao diện + logic app (SPA thuần HTML/CSS/JS, không phụ thuộc ngoài)
data/           Dữ liệu câu hỏi app dùng khi chạy
  hp1.js          Học phần 1 — mảng QUESTIONS_HP1
  hp2.js          Học phần 2 — mảng QUESTIONS_HP2
docs/           Tài liệu PDF gốc (tham khảo/trích xuất) + tài liệu thuật toán
  THUAT-TOAN.md   Mô tả chi tiết các thuật toán & mô hình dữ liệu dùng trong app
```

## Thêm học phần mới

1. Tạo `data/hp3.js` theo đúng khuôn của `data/hp1.js` (mảng các object `{id, q, options, answer}`).
2. Thêm `<script src="data/hp3.js"></script>` vào `index.html` cạnh 2 dòng script hiện có.
3. Thêm một dòng vào `HP_LIST` trong `index.html`: `{ id: 'hp3', name: 'Học phần 3', questions: QUESTIONS_HP3, setSize: 25 }`.

## Chạy thử

Không cần cài đặt gì — mở trực tiếp `index.html` bằng trình duyệt, hoặc chạy một static server bất kỳ (`python3 -m http.server`) rồi mở `index.html`.
