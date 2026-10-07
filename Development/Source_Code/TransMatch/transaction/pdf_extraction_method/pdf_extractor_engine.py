# flake8: noqa: E501
"""
pdf_extractor_engine.py
Centralized extractor backend routing for PDF text extraction
"""

import fitz
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
import logger
import cv2
import numpy as np
import tempfile
import ocrmypdf
import os
import sys
import re
import json
from typing import List, Dict, Tuple


IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    # When bundled by PyInstaller, look for external folders in _internal first,
    # then next to the executable (for onedir mode)
    exe_dir = os.path.dirname(sys.executable)
    internal_dir = os.path.join(exe_dir, "_internal")
    
    # Try multiple possible poppler paths (check _internal first, then exe_dir)
    poppler_paths = [
        os.path.join(internal_dir, "poppler", "Library", "bin"),  # _internal/poppler/Library/bin
        os.path.join(exe_dir, "poppler", "Library", "bin"),       # exe_dir/poppler/Library/bin
        os.path.join(internal_dir, "poppler", "bin"),             # _internal/poppler/bin
        os.path.join(exe_dir, "poppler", "bin"),                  # exe_dir/poppler/bin
        os.path.join(internal_dir, "poppler"),                     # _internal/poppler
        os.path.join(exe_dir, "poppler"),                          # exe_dir/poppler
    ]
    POPPLER_PATH = None
    for path in poppler_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, "pdftoppm.exe")):
            POPPLER_PATH = path
            break
    # If not found, use first expected path for error message (but validation will catch it)
    if POPPLER_PATH is None:
        POPPLER_PATH = poppler_paths[0]  # _internal/poppler/Library/bin
    
    # Add Poppler directories to PATH so DLLs can be found
    # This is critical for poppler executables to find their required DLLs
    # Poppler may need DLLs from both bin and parent Library directories
    if POPPLER_PATH and os.path.exists(POPPLER_PATH):
        current_path = os.environ.get("PATH", "")
        paths_to_add = [POPPLER_PATH]
        
        # Also add parent Library directory if it exists (for additional DLLs)
        parent_library = os.path.dirname(POPPLER_PATH)  # Should be Library
        if parent_library and os.path.exists(parent_library):
            paths_to_add.append(parent_library)
        
        # Add grandparent poppler directory (in case DLLs are there)
        grandparent_poppler = os.path.dirname(parent_library) if parent_library else None
        if grandparent_poppler and os.path.exists(grandparent_poppler):
            paths_to_add.append(grandparent_poppler)
        
        # Add paths that aren't already in PATH
        new_paths = [p for p in paths_to_add if p and p not in current_path]
        if new_paths:
            os.environ["PATH"] = os.pathsep.join(new_paths) + os.pathsep + current_path
            logger.logger.info(f"[pdf_extractor_engine] : Added Poppler paths to PATH: {new_paths}")
    
    # Try tesseract in _internal first, then next to exe
    tesseract_paths = [
        os.path.join(internal_dir, "tesseract", "tesseract.exe"),  # _internal/tesseract/tesseract.exe
        os.path.join(exe_dir, "tesseract", "tesseract.exe"),      # exe_dir/tesseract/tesseract.exe
    ]
    TESSERACT_PATH = None
    for path in tesseract_paths:
        if os.path.exists(path):
            TESSERACT_PATH = path
            break
    # If not found, use first expected path for error message (but validation will catch it)
    if TESSERACT_PATH is None:
        TESSERACT_PATH = tesseract_paths[0]  # _internal/tesseract/tesseract.exe
    
    # Help Tesseract locate language files - check _internal first
    tessdata_paths = [
        os.path.join(internal_dir, "tesseract", "tessdata"),  # _internal/tesseract/tessdata
        os.path.join(exe_dir, "tesseract", "tessdata"),          # exe_dir/tesseract/tessdata
    ]
    for path in tessdata_paths:
        if os.path.exists(path):
            os.environ["TESSDATA_PREFIX"] = path
            break
    
    # Add Tesseract directory to PATH so DLLs can be found
    # This is critical for tesseract.exe to find its required DLLs
    if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
        tesseract_dir = os.path.dirname(TESSERACT_PATH)  # Directory containing tesseract.exe
        current_path = os.environ.get("PATH", "")
        if tesseract_dir and tesseract_dir not in current_path:
            os.environ["PATH"] = tesseract_dir + os.pathsep + current_path
            logger.logger.info(f"[pdf_extractor_engine] : Added Tesseract to PATH: {tesseract_dir}")
else:
    # In dev: allow .env overrides, else fall back to conventional locations
    POPPLER_PATH   = os.getenv("POPPLER_PATH")   or r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0\Library\bin"
    TESSERACT_PATH = os.getenv("TESSERACT_PATH") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ===================== FITZ =====================
def extract_with_fitz(pdf_path: str) -> str:
    logger.logger.info(f"[pdf_extractor_engine] Using FITZ for text extraction: {pdf_path}")
    text_content = []
    doc = fitz.open(pdf_path)
    for page in doc:
        text_content.append(page.get_text("text"))
    doc.close()
    # Combine pages:
    # - "\n" ensures readable flow
    # - "\fPage" (or "\fPage:{n}") marks actual page separation
    return "\n".join(text_content)

# ===================== FITZ 2 =====================
def extract_with_fitz2(pdf_path: str) -> str:
    logger.logger.info(f"[pdf_extractor_engine] Using FITZ for text extraction: {pdf_path}")
    text_content = []
    doc = fitz.open(pdf_path)
    for page in doc:
        page_text = page.get_text("text")
        if not isinstance(page_text, str):
            page_text = str(page_text)

        # Replace empty columns or missing words with 'no data'
        lines = []
        for line in page_text.splitlines():
            clean_line = line.strip()
            # If the line is blank or only spaces/tabs, mark as 'no data'
            if not clean_line:
                lines.append("no data")
            else:
                lines.append(clean_line)
        text_content.append("\n".join(lines))
    doc.close()
    # Combine pages with clear separator
    return "\n".join(text_content)

# ===================== PDFPLUMBER =====================
def extract_with_pdfplumber(pdf_path: str) -> str:
    logger.logger.info(f"[pdf_extractor_engine] Using PDFPLUMBER for text extraction: {pdf_path}")
    text_content = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_content.append(page_text)
    # Combine pages:
    # - "\n" ensures readable flow
    # - "\fPage" (or "\fPage:{n}") marks actual page separation
    return "\n".join(text_content)

# ===================== PDFPLUMBER - RHB (SPECIAL) =====================
def extract_rhb_pdf_lines(pdf_path: str) -> str:
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            rows = {}
            for w in words:
                y = round(w['top'] / 3) * 3   # bucket by y
                rows.setdefault(y, []).append((w['x'], w['text']))
            for y in sorted(rows):
                row_text = " ".join(t for _, t in sorted(rows[y]))
                lines.append(row_text)
    # Combine pages:
    # - "\n" ensures readable flow
    # - "\fPage" (or "\fPage:{n}") marks actual page separation
    return "\n".join(lines)  

# ===================== PDFPLUMBER x & y - RHB TRN =====================
def extract_with_pdfplumber_xy_rhb_trn(pdf_path):
    logger.logger.info(f"[rhb_xy_extraction] Processing: {pdf_path}")

    column_boxes = {
        "Date": (10, 58),
        "Branch": (59, 85),
        "Description": (86, 130),
        "Sender": (135, 185),
        "Ref1": (191, 245),
        "Ref2": (246, 305),
        "RefNum": (306, 350),
        "AmountDR": (351, 435),
        "AmountCR": (436, 515),
        "Balance": (516, 585),
    }

    Y_TOLERANCE = 30        # ✅ merge all words within ±25 pt vertically
    DATE_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{4}$")  # 06-06-2024 etc.
    all_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            if not words:
                continue

            # Sort words top to bottom
            words.sort(key=lambda w: w["top"])
            groups, current_group, current_y = [], [], None

            # Group by Y proximity
            for w in words:
                if current_y is None:
                    current_y = w["top"]
                    current_group.append(w)
                    continue

                if abs(w["top"] - current_y) <= Y_TOLERANCE:
                    current_group.append(w)
                else:
                    groups.append(current_group)
                    current_group = [w]
                    current_y = w["top"]
            if current_group:
                groups.append(current_group)

            # Convert grouped words into structured rows
            for group in groups:
                row_data = {}
                for col, (xmin, xmax) in column_boxes.items():
                    cell_words = [w["text"] for w in group if xmin <= w["x0"] < xmax]
                    row_data[col] = " ".join(cell_words).strip()

                # Skip blank or invalid
                if not any(row_data.values()):
                    continue
                if row_data["Date"].lower() in ("date", "beginning"):
                    continue
                if not DATE_PATTERN.match(row_data["Date"]):
                    logger.logger.debug(f"[rhb_xy_extraction] Skipped invalid date: {row_data['Date']}")
                    continue

                all_rows.append(row_data)

    # ✅ Convert list of dicts to JSON string
    json_output = json.dumps(all_rows, indent=4, ensure_ascii=False)

    logger.logger.info(f"[rhb_xy_extraction] Total valid transactions extracted: {len(all_rows)}")
    return json_output

# ===================== PDFPLUMBER x & y - RHB DOC =====================
def extract_with_pdfplumber_xy_rhb_doc(pdf_path):
    logger.logger.info(f"[rhb_xy_extraction][extract_with_pdfplumber_xy_rhb_doc] Processing: {pdf_path}")

    # Define coordinate zones + default fallback for each field
    coord_boxes = {
        "Bank Name": {
            "coords": (0, 0, 0, 0),
            "default": "RHB Bank Berhad"
        },
        "Bank Registration No": {
            "coords": (0, 0, 0, 0),
            "default": "NA"
        },
        "Bank Address": {
            "coords": (0, 0, 0, 0),
            "default": "NA"
        },
        "Customer Name": {
            "coords": (10, 300, 60, 72),
            "default": "Unknown Customer"
        },
        "Customer Address": {
            "coords": (10, 300, 73, 130),
            "default": "NA"
        },
        "Statement Date": {
            "coords": (320, 375, 150, 160),
            "default": "NA"
        },
        "Account Number": {
            "coords": (10, 200, 180, 195),
            "default": "NA"
        },
    }

    doc_info = {key: val["default"] for key, val in coord_boxes.items()}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return json.dumps(doc_info)

            page = pdf.pages[0]
            words = page.extract_words()
            if not words:
                return json.dumps(doc_info)

            # Loop through each field: extract if text found, else keep default
            for field, cfg in coord_boxes.items():
                xmin, xmax, ymin, ymax = cfg["coords"]
                found_words = [
                    w["text"] for w in words
                    if xmin <= w["x0"] < xmax and ymin <= w["top"] < ymax
                ]
                if found_words:
                    doc_info[field] = " ".join(found_words).strip()

    except Exception as e:
        logger.logger.exception(f"[rhb_xy_extraction][extract_with_pdfplumber_xy_rhb_doc][ERROR]: {e}")

    return json.dumps(doc_info, indent=4, ensure_ascii=False)

# ===================== PDFPLUMBER x & y - RHB CURRENT ACCOUNT TRN =====================
def extract_with_pdfplumber_xy_rhbcurr_trn(pdf_path):
    """
    Extract RHB Current Account transactions.
    Uses fixed X-column coordinates and dynamically detects Y-ranges between blue horizontal lines.
    Returns JSON string.
    """
    logger.logger.info(f"[rhb_xy_extraction][extract_with_pdfplumber_xy_rhbcurr_trn] Processing: {pdf_path}")

    # Define X-column ranges (you can fine-tune later)
    column_boxes = {
        "Date": (40, 90),
        "Description": (95, 330),
        "Cheque": (335, 400),
        "Debit": (405, 460),
        "Credit": (465, 520),
        "Balance": (525, 590),
    }

    all_rows = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                words = page.extract_words()
                lines = page.lines

                # 🧩 Step 1: detect horizontal blue lines (transaction separators)
                horizontal_lines = [
                    ln["y0"] for ln in lines if abs(ln["x1"] - ln["x0"]) > 200
                ]
                horizontal_lines = sorted(set(horizontal_lines), reverse=True)

                if len(horizontal_lines) < 2:
                    logger.logger.warning(f"[rhb_xy_extraction] Page {page_index}: no blue lines found.")
                    continue

                # 🧩 Step 2: iterate between each pair of blue lines
                for i in range(len(horizontal_lines) - 1):
                    top_y = horizontal_lines[i]
                    bottom_y = horizontal_lines[i + 1]

                    # collect all words between the two lines
                    row_words = [w for w in words if bottom_y < w["top"] < top_y]
                    if not row_words:
                        continue

                    # 🧩 Step 3: group into columns using X-ranges
                    record = {}
                    for col, (xmin, xmax) in column_boxes.items():
                        cell_words = [w["text"] for w in row_words if xmin <= w["x0"] < xmax]
                        record[col] = " ".join(cell_words).strip()

                    # skip empty or header lines
                    if not any(record.values()):
                        continue
                    if record["Date"].lower() in ("date", "tarikh"):
                        continue

                    all_rows.append(record)

                logger.logger.info(f"[rhb_xy_extraction] Page {page_index}: extracted {len(all_rows)} transactions.")

    except Exception as e:
        logger.logger.exception(f"[rhb_xy_extraction][extract_with_pdfplumber_xy_rhbcurr_trn][ERROR]: {e}")

    # ✅ return as JSON for downstream processing
    return json.dumps(all_rows, indent=4, ensure_ascii=False)

# ===================== PDFPLUMBER x & y - RHB CURRENT ACCOUNT DOC =====================
def extract_with_pdfplumber_xy_rhbcurr_doc(pdf_path):
    logger.logger.info(f"[rhb_xy_extraction][extract_with_pdfplumber_xy_rhb_doc] Processing: {pdf_path}")

    # Define coordinate zones + default fallback for each field
    coord_boxes = {
        "Bank Name": {
            "coords": (0, 0, 0, 0),
            "default": "RHB Bank Berhad"
        },
        "Bank Registration No": {
            "coords": (0, 0, 0, 0),
            "default": "NA"
        },
        "Bank Address": {
            "coords": (0, 0, 0, 0),
            "default": "NA"
        },
        "Customer Name": {
            "coords": (35, 200, 135, 145),
            "default": "Unknown Customer"
        },
        "Customer Address": {
            "coords": (35, 200, 146, 190),
            "default": "NA"
        },
        "Statement Date": {
            "coords": (475, 560, 55, 70),
            "default": "NA"
        },
        "Account Number": {
            "coords": (160, 225, 280, 295),
            "default": "NA"
        },
    }

    doc_info = {key: val["default"] for key, val in coord_boxes.items()}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return json.dumps(doc_info)

            page = pdf.pages[0]
            words = page.extract_words()
            if not words:
                return json.dumps(doc_info)

            # Loop through each field: extract if text found, else keep default
            for field, cfg in coord_boxes.items():
                xmin, xmax, ymin, ymax = cfg["coords"]
                found_words = [
                    w["text"] for w in words
                    if xmin <= w["x0"] < xmax and ymin <= w["top"] < ymax
                ]
                if found_words:
                    doc_info[field] = " ".join(found_words).strip()

    except Exception as e:
        logger.logger.exception(f"[rhb_xy_extraction][extract_with_pdfplumber_xy_rhb_doc][ERROR]: {e}")

    return json.dumps(doc_info, indent=4, ensure_ascii=False)


# ===================== PDF2IMAGE + TESSERACT =====================
def extract_with_pdf2image(pdf_path: str) -> str:
    """Extract PDF text by converting to image (supports row/column layout)."""

    pages = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
    all_text = []

    for page in pages:
        # Convert PIL image to OpenCV format
        img = np.array(page)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Optional: adaptive threshold for clarity
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 31, 2)

        # Use OCR with layout info (bbox)
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

        # Reconstruct text line by line (group by 'block_num' and 'line_num')
        rows = {}
        for i, text in enumerate(data["text"]):
            if text.strip():
                y = data["top"][i]
                line_id = data["block_num"][i] * 1000 + data["line_num"][i]
                rows.setdefault(line_id, []).append((data["left"][i], text))

        # Sort by Y coordinate and X coordinate within each row
        for _, items in sorted(rows.items()):
            line_text = " ".join([w for _, w in sorted(items, key=lambda x: x[0])])
            all_text.append(line_text)

    return "\n".join(all_text)


# ===================== OCRMYPDF =====================
def extract_with_ocrmypdf(pdf_path: str) -> str:
    """Run OCRmyPDF to make PDF searchable, then extract text via FITZ."""
    temp_output = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
    ocrmypdf.ocr(pdf_path, temp_output, force_ocr=True, skip_text=True)

    doc = fitz.open(temp_output)
    text_list: list[str] = []
    for p in doc:
        page_text = p.get_text("text")
        if isinstance(page_text, str):
            text_list.append(page_text)

    text = "\n".join(text_list)
    doc.close()
    return text


# ===================== TrOCR =====================
def extract_with_trocr(pdf_path: str) -> str:
    logger.logger.info(f"[pdf_extractor_engine] Placeholder for TrOCR extraction: {pdf_path}")
    return ""  # TODO: implement later


# ===================== Dispatcher (Final Modular Version) =====================
def extract_text_by_engine(pdf_path: str, engine: str = "fitz", page_mode: str = "all") -> str:
    """
    Unified dispatcher for text extraction.

    engine: fitz, pdfplumber, pdf2image, ocrmypdf, trocr
    page_mode: "first" for first page only, "all" for full document
    """
    engine = engine.lower().strip()
    page_mode = page_mode.lower().strip()
    logger.logger.info(f"[pdf_extractor_engine] Extracting PDF ({page_mode}-page) using engine = {engine}")

    try:
        # === Call Independent Extractor ===
        if engine == "fitz":
            full_text = extract_with_fitz(pdf_path)
        elif engine == "fitz2":
            full_text = extract_with_fitz2(pdf_path)
        elif engine == "pdfplumber":
            full_text = extract_with_pdfplumber(pdf_path)

            # RHB - Reflx
        elif engine == "pdfplumberxy_rhb" and page_mode == "first":
            full_text = extract_with_pdfplumber_xy_rhb_doc(pdf_path)
        elif engine == "pdfplumberxy_rhb" and page_mode == "all":
            full_text = extract_with_pdfplumber_xy_rhb_trn(pdf_path)
             # RHB - Current Account
        elif engine == "pdfplumberxy_rhbcc" and page_mode == "first":
            full_text = extract_with_pdfplumber_xy_rhbcurr_doc(pdf_path)
        elif engine == "pdfplumberxy_rhbcc" and page_mode == "all":
            full_text = extract_with_pdfplumber_xy_rhbcurr_trn(pdf_path)

            

        elif engine == "pdf2image":
            full_text = extract_with_pdf2image(pdf_path)
        elif engine == "ocrmypdf":
            full_text = extract_with_ocrmypdf(pdf_path)
        elif engine == "trocr":
            full_text = extract_with_trocr(pdf_path)
        elif engine == "pdfplumberRHB":
            full_text = extract_rhb_pdf_lines(pdf_path)
        else:
            logger.logger.warning(f"[pdf_extractor_engine] Unknown engine '{engine}', defaulting to FITZ.")
            full_text = extract_with_fitz(pdf_path)

    except Exception as e:
        logger.logger.exception(f"[pdf_extractor_engine] Error using {engine}: {str(e)}. Falling back to FITZ.")
        full_text = extract_with_fitz(pdf_path)

    # === Page mode handling (common across engines) ===
    # Note: Not all engines produce page delimiters (e.g., \f).
    # This logic ensures you can still extract "first page only" text consistently.
    if page_mode == "first":
        # Prefer form feed delimiter if present
        if "\fPage" in full_text:
            return full_text.split("\fPage")[0]
        # Otherwise, just take the first ~10% of text as proxy for first page
        text_length = len(full_text)
        approx_first_page = full_text[: max(3000, int(text_length * 0.1))]
        return approx_first_page
    else:
        return full_text
