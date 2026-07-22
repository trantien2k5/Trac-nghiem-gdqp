#!/usr/bin/env python3
"""
OCR văn bản thuần từ PDF ảnh (scan) và ảnh chụp, dùng Tesseract (không AI/LLM).
Ưu tiên xử lý được số lượng lớn file, không đặt nặng độ chính xác tuyệt đối.

Cài đặt (một lần):
  sudo apt-get install tesseract-ocr tesseract-ocr-vie   # engine OCR + gói tiếng Việt
  pip3 install -r tools/requirements.txt

Dùng:
  python3 tools/ocr.py <file_hoặc_thư_mục> [-o thư_mục_ra] [--lang vie+eng] [--dpi 200]

Ví dụ:
  python3 tools/ocr.py docs/de-moi.pdf
  python3 tools/ocr.py scans/ -o ocr_output --dpi 250
"""
import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF — render PDF thành ảnh, không cần cài poppler riêng
import pytesseract
from PIL import Image

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
SUPPORTED_EXTS = IMAGE_EXTS | {".pdf"}


def ocr_pdf(path, lang, dpi):
    doc = fitz.open(path)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    parts = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang=lang)
        parts.append(f"--- Trang {i + 1}/{len(doc)} ---\n{text}")
    doc.close()
    return "\n\n".join(parts)


def ocr_file(path, lang, dpi):
    ext = path.suffix.lower()
    if ext == ".pdf":
        return ocr_pdf(path, lang, dpi)
    return pytesseract.image_to_string(Image.open(path), lang=lang)


def collect_files(input_path):
    p = Path(input_path)
    if p.is_file():
        return [p]
    return sorted(f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED_EXTS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="File hoặc thư mục chứa PDF/ảnh cần OCR (thư mục sẽ quét đệ quy)")
    ap.add_argument("-o", "--outdir", default="ocr_output", help="Thư mục lưu file .txt kết quả (mặc định: ocr_output)")
    ap.add_argument("--lang", default="vie+eng", help="Ngôn ngữ OCR (mặc định: vie+eng)")
    ap.add_argument("--dpi", type=int, default=200, help="Độ phân giải render PDF — cao hơn = chính xác hơn nhưng chậm hơn (mặc định: 200)")
    args = ap.parse_args()

    files = collect_files(args.input)
    if not files:
        print("Không tìm thấy file PDF/ảnh nào.")
        sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Tìm thấy {len(files)} file. Bắt đầu OCR (lang={args.lang}, dpi={args.dpi})...\n")
    ok = 0
    failed = []
    for idx, f in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {f.name} ...", end=" ", flush=True)
        try:
            text = ocr_file(f, args.lang, args.dpi)
            out_path = outdir / (f.stem + ".txt")
            out_path.write_text(text, encoding="utf-8")
            ok += 1
            print(f"xong -> {out_path}")
        except Exception as e:
            failed.append((f.name, str(e)))
            print(f"LỖI: {e}")

    print(f"\nHoàn tất: {ok}/{len(files)} file OCR thành công. Kết quả trong: {outdir}/")
    if failed:
        print(f"{len(failed)} file lỗi:")
        for name, err in failed:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
