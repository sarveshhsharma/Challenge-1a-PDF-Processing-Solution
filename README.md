# Challenge-1a-PDF-Processing-Solution
## Adobe India Hackathon:
This project extracts structured headings from PDF documents using visual and textual features like font size, style, alignment, and spacing. The output is a clean JSON with the document's title and an outline of its section hierarchy (e.g., H1, H2, H3).

---

## Features

- Extracts **title** and **headings** (H1, H2, ...) from PDFs.
- Detects **bold**, **italic**, and **large-font** styled lines.
- Ignores content inside **tables** using `pdfplumber`.
- Uses **line spacing**, **font size**, and **alignment** for accurate detection.
- Outputs clean structured **JSON**.

---

## Libraries Used

- [PyMuPDF (`fitz`)]
- [pdfplumber]
- `collections`, `json`, `re`
