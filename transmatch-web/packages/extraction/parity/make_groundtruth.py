# Runs the existing Python extraction pipeline headlessly over the sample PDFs
# and writes one JSON file per PDF, used as the reference for the TypeScript port.
import json
import logging
import os
import sys
import types

SRC = r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\Source_Code\TransMatch"
PDF_DIR = r"D:\CHIANWEILON\Software_Dev\TransMatch\Sample\Testing_PDF"
OUT_DIR = sys.argv[1]

sys.path.insert(0, SRC)
os.chdir(SRC)

# Stand-in logger so the app's own log folder is not written to.
fake_logger = types.ModuleType("logger")
fake_logger.logger = logging.getLogger("groundtruth")
fake_logger.logger.addHandler(logging.NullHandler())
fake_logger.logger.propagate = False
sys.modules["logger"] = fake_logger

# No GUI dialogs.
import tkinter.messagebox as mb  # noqa: E402
for name in ("showinfo", "showerror", "showwarning", "askyesno", "askokcancel"):
    setattr(mb, name, lambda *a, **k: None)

import pdfplumber  # noqa: E402
import pytesseract  # noqa: E402
from pdf2image import convert_from_path  # noqa: E402

import transaction.pdf_processor as pp  # noqa: E402
from transaction.pdf_extraction_method import pdf_extractor_engine as eng  # noqa: E402
from transaction.pdf_extraction_method import rhb_pdf_extraction, uob_pdf_extraction  # noqa: E402

for mod in (pp, rhb_pdf_extraction, uob_pdf_extraction):
    mod.output_rawdata = lambda text: None

os.makedirs(OUT_DIR, exist_ok=True)

for fname in sorted(os.listdir(PDF_DIR)):
    if not fname.lower().endswith(".pdf"):
        continue
    path = os.path.join(PDF_DIR, fname)
    out = {"file": fname}
    try:
        images = convert_from_path(path, first_page=1, last_page=1, poppler_path=pp.POPPLER_PATH)
        img = images[0]
        w, h = img.size
        out["ocr_text"] = pytesseract.image_to_string(img.crop((0, 0, w, int(h * 0.1))), config="--psm 6")
        out["page_px"] = [w, h]

        ident = pp.identify_bank(path)
        out["bank_id"] = ident["bank_id"]
        out["engine"] = ident["engine_mode"]

        if ident["bank_id"] < 90:
            pp.pdf_path_global = path
            first_text = eng.extract_text_by_engine(path, ident["engine_mode"], page_mode="first")
            all_text = eng.extract_text_by_engine(path, ident["engine_mode"], page_mode="all")
            out["first_text"] = first_text
            out["all_text"] = all_text
            out["doc"] = pp.extract_docInfo_TrxInfo(ident["bank_id"], first_text, "DOC")
            out["trx"] = pp.extract_docInfo_TrxInfo(ident["bank_id"], all_text, "TRN")

        if ident["engine_mode"].startswith("pdfplumber"):
            with pdfplumber.open(path) as pdf:
                out["plumber_words_p1"] = [
                    {"text": wd["text"], "x0": round(wd["x0"], 2), "x1": round(wd["x1"], 2),
                     "top": round(wd["top"], 2), "bottom": round(wd["bottom"], 2)}
                    for wd in pdf.pages[0].extract_words()
                ]
    except Exception as e:  # keep going; record the failure
        out["exception"] = f"{type(e).__name__}: {e}"

    with open(os.path.join(OUT_DIR, os.path.splitext(fname)[0] + ".json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    trx = out.get("trx")
    print(fname, "bank", out.get("bank_id"), out.get("engine"),
          "trx", len(trx) if isinstance(trx, list) else trx, out.get("exception", ""))
