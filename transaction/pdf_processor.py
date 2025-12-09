# flake8: noqa: E501

from tkinter import messagebox
import fitz  # type: ignore # PyMuPDF
import re
import os
import sys
import traceback
import pytesseract
import logger
import importlib
from transaction.name_extractor import NER_extract_name, NER_extraction
from transaction.pdf_extraction_method.pdf_extractor_engine import extract_text_by_engine
from pdf2image import convert_from_path
from datetime import datetime
import pdfplumber
import fitz

# === Paths for Poppler & Tesseract (dev + packaged) ===
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent           # .../TransMatch/transaction
ROOT_DIR = BASE_DIR.parent                           # .../TransMatch

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
    # If not found, use first expected path for error message (but _check_deps will validate)
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
            logger.logger.info(f"[pdf_processor] : Added Poppler paths to PATH: {new_paths}")
    
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
    # If not found, use first expected path for error message (but _check_deps will validate)
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
            logger.logger.info(f"[pdf_processor] : Added Tesseract to PATH: {tesseract_dir}")
else:
    # In dev: allow .env overrides, else fall back to conventional locations
    POPPLER_PATH   = os.getenv("POPPLER_PATH")   or r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0\Library\bin"
    TESSERACT_PATH = os.getenv("TESSERACT_PATH") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Point pytesseract at the binary
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Optional but useful: sanity check + friendly error if missing
def _check_deps():
    missing = []
    if not os.path.exists(TESSERACT_PATH):
        missing.append(f"Tesseract not found: {TESSERACT_PATH}")
    if not os.path.exists(os.path.join(POPPLER_PATH, "pdftoppm.exe")):
        missing.append(f"pdftoppm.exe not found in: {POPPLER_PATH}")
    if not os.path.exists(os.path.join(POPPLER_PATH, "pdfinfo.exe")):
        missing.append(f"pdfinfo.exe not found in: {POPPLER_PATH}")

    logger.logger.info(f"[pdf_processor] : POPPLER_PATH = {POPPLER_PATH}")
    logger.logger.info(f"[pdf_processor] : POPPLER_PATH exists? {os.path.exists(POPPLER_PATH)}")
    logger.logger.info(f"[pdf_processor] : TESSERACT_PATH = {TESSERACT_PATH}")
    logger.logger.info(f"[pdf_processor] : TESSERACT_PATH exists? {os.path.exists(TESSERACT_PATH)}")

    if missing:
        msg = "\n".join(missing) + \
              "\n\nHint: set POPPLER_PATH/TESSERACT_PATH in .env " \
              "or ensure 'poppler' and 'tesseract' folders are copied to _internal directory " \
              f"({internal_dir}) during build."
        try:
            messagebox.showerror("Missing dependencies", msg)
        except Exception:
            pass  # if no Tk context yet
        raise RuntimeError(msg)

_check_deps()


# Map bank IDs to module file names
BANK_MODULES = {
    1: "pbb_pdf_extraction",       # Public Islamic Bank
    2: "pbb_pdf_extraction",       # Public Bank
    3: "mbb_pdf_extraction",       # Maybank Islamic
    4: "mbb_pdf_extraction",       # Maybank
    5: "cimb_pdf_extraction",      # CIMB Islamic
    6: "cimb_pdf_extraction",      # CIMB Bank
    7: "rhb_pdf_extraction",       # RHB Islamic
    8: "rhb_pdf_extraction",       # RHB Reflex
    9: "rhb_pdf_extraction",       # RHB Bank Berhad
    10: "hlb_pdf_extraction",      # Hong Leong Islamic
    11: "hlb_pdf_extraction",      # Hong Leong Bank
    12: "amb_pdf_extraction",      # AmBank Islamic
    13: "amb_pdf_extraction",      # AmBank
    14: "uob_pdf_extraction",      # UOB Islamic
    15: "uob_pdf_extraction",      # UOB Bank
    16: "aeon_pdf_extraction",     # AEON Bank Islamic
    17: "aeon_pdf_extraction",     # AEON Bank
    18: "affin_pdf_extraction",    # Affin Bank Islamic
    19: "affin_pdf_extraction",    # Affin Bank
    20: "bsn_pdf_extraction",      # BSN Bank Islamic
    21: "bsn_pdf_extraction",      # BSN Bank
    22: "muamalat_pdf_extraction"  # Muamalat Bank Islamic
}


def identify_bank(pdf_path):
    """Detect bank name by extracting text from the top half of the first page"""
    logger.logger.info(f"[pdf_processor][identify_bank()] : Executing the BANK IDENTIFY operation, from the file path = {pdf_path}")

    # ✅ Convert the first page to an image
    try:
        logger.logger.info(f"[pdf_processor][identify_bank()] : Using POPPLER_PATH = {POPPLER_PATH}")
        logger.logger.info(f"[pdf_processor][identify_bank()] : POPPLER_PATH exists = {os.path.exists(POPPLER_PATH)}")
        if POPPLER_PATH:
            pdftoppm_exe = os.path.join(POPPLER_PATH, "pdftoppm.exe")
            logger.logger.info(f"[pdf_processor][identify_bank()] : pdftoppm.exe exists = {os.path.exists(pdftoppm_exe)}")
        
        images = convert_from_path(
            pdf_path, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
    except Exception as e:
        error_msg = f"{datetime.now()} - [pdf_processor][identify_bank()][ERROR] : {e}"
        print(error_msg)
        logger.logger.error(error_msg)
        logger.logger.exception("Full traceback:")
        traceback.print_exc()

    if not images:
        print(f"{datetime.now()} - [pdf_processor][identify_bank()][DEBUG] : ❌ Error: No images extracted from the PDF.")
        return {"bank_id": 98, "engine_mode": "-"}

    # ✅ Define crop area for the **top half of the page**
    img = images[0]
    width, height = img.size  # Get image dimensions

    # Crop top 10% of the page
    crop_area = (0, 0, width, int(height * 0.1))
    top_half_img = img.crop(crop_area)

    # ✅ Perform OCR on the cropped top-half image
    extracted_text = pytesseract.image_to_string(
        top_half_img, config="--psm 6")

    # ✅ Convert extracted text to lowercase for case-insensitive matching
    extracted_text_lower = extracted_text.lower()
    extracted_text_lower_clean = " ".join(extracted_text_lower.split())
    logger.logger.info(f"[pdf_processor][identify_bank()] : Extracted bank name(Crop top 10% of the page only) = {extracted_text_lower_clean}")


    # Engine Mode Option: fitz, pdfplumber, pdf2image, ocrmypdf, trocr
    # ✅ Public Bank
    if "public islamic bank" in extracted_text_lower:
        bank_id, engine_mode = 1, "fitz"
    elif "public bank" in extracted_text_lower:
        bank_id, engine_mode = 2, "fitz"

    # ✅ Maybank
    elif "maybank islamic berhad" in extracted_text_lower:
        bank_id, engine_mode = 3, "fitz"
    elif "malayan banking berhad" in extracted_text_lower:
        bank_id, engine_mode = 4, "fitz"

    # ✅ CIMB
    elif "cimb islamic bank berhad" in extracted_text_lower:
        bank_id, engine_mode = 5, "fitz"
    elif "cimb cdcks" in extracted_text_lower:
        bank_id, engine_mode = 6, "fitz"

    # ✅ RHB
    elif "rhb islamic bank berhad" in extracted_text_lower:
        bank_id, engine_mode = 7, "fitz"
    elif "rbs" in extracted_text_lower and "reflex" in extracted_text_lower:
        bank_id, engine_mode = 8, "pdfplumberxy_rhb"
    elif "rhb bank berhad" in extracted_text_lower:
        bank_id, engine_mode = 9, "fitz"

    # ✅ Hong Leong
    elif "hongleong islamic bank" in extracted_text_lower:
        bank_id, engine_mode = 10, "fitz"
    elif "hongleong bank" in extracted_text_lower:
        bank_id, engine_mode = 11, "fitz"

    # ✅ AmBank
    elif "ambank islamic berhad" in extracted_text_lower:
        bank_id, engine_mode = 12, "fitz"
    elif "ambank" in extracted_text_lower:
        bank_id, engine_mode = 13, "fitz"

    # ✅ UOB
    elif "itt uob islamic berhad" in extracted_text_lower:
        bank_id, engine_mode = 14, "fitz"
    elif "itt uob" in extracted_text_lower:
        bank_id, engine_mode = 15, "fitz"

    # ✅ AEON
    elif "aeon islamic berhad bank" in extracted_text_lower:
        bank_id, engine_mode = 16, "fitz"
    elif "aeon bank" in extracted_text_lower:
        bank_id, engine_mode = 17, "fitz"

    # ✅ Affin
    elif "affin islamic berhad bank" in extracted_text_lower:
        bank_id, engine_mode = 18, "fitz"
    elif "affin bank" in extracted_text_lower:
        bank_id, engine_mode = 19, "fitz"

    # ✅ BSN
    elif "bsn islamic" in extracted_text_lower:
        bank_id, engine_mode = 20, "fitz"
    elif "bsn" in extracted_text_lower or "bsn" in extracted_text_lower:
        bank_id, engine_mode = 21, "fitz"

    # ✅ Muamalat
    elif "bank muamalat" in extracted_text_lower:
        bank_id, engine_mode = 22, "fitz"
    else:
        bank_id, engine_mode = 99, "-"

    logger.logger.info(f"[identify_bank()] → Detected bank_id={bank_id}, engine={engine_mode}")
    return {"bank_id": bank_id, "engine_mode": engine_mode}
    


def extract_docInfo_TrxInfo(identified_bank, page_text, purpose):
    """
    Dispatch extraction dynamically based on bank ID.
    """
    logger.logger.info(f"[pdf_processor][extract_docInfo_TrxInfo()] : Dispatching extraction for bank_id={identified_bank}, purpose={purpose}")

    module_name = BANK_MODULES.get(identified_bank)
    if not module_name:
        logger.logger.info("[pdf_processor][extract_docInfo_TrxInfo()] : Error code [98] - Bank undefined from the uploaded PDF")
        return {"error": 98}
        
    if module_name == 99:
        logger.logger.info("[pdf_processor][extract_docInfo_TrxInfo()] : Bank not supported")
        return {"error": 99}

    try:
        # Load the module dynamically from transaction/pdf_extraction_method
        module = importlib.import_module(f"transaction.pdf_extraction_method.{module_name}")

        if purpose == "DOC":
            return module.extract_docInfo(page_text, identified_bank, pdf_path_global)
        elif purpose == "TRN":
            return module.extract_trxInfo(page_text, identified_bank, pdf_path_global)
        else:
            logger.logger.info("[pdf_processor][extract_docInfo_TrxInfo()] : Invalid purpose parameter")
            return {"error": 97}

    except Exception as e:
        logger.logger.exception(f"[pdf_processor][extract_docInfo_TrxInfo()][ERROR] : Failed to load module {module_name} → {e}")
        return {"error": 97}


def output_rawdata(text):
    # # To output the raw data from "text"
    output_path = r"D:\CHIANWEILON\Software_Dev\TransMatch\Sample\OUTPUT_TEXT\OUTPUT_TEXT_.txt"
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(text)


# def pdf_data_extraction_main(pdf_path):
#     logger.logger.info("[pdf_processor][pdf_data_extraction_main()] : Extract transactions from a given PDF file and save the output as JSON")
#     global pdf_path_global
#     pdf_path_global = pdf_path

#     # """Extract transactions from a given PDF file and save the output as JSON."""
#     doc = fitz.open(pdf_path)  # Open the PDF
#     total_pages = len(doc)  # Get the total number of pages

#     all_transactions = []
#     document_info = {}

#     identified_bank = identify_bank(pdf_path)
#     logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : Detect bank seq = {str(identified_bank)}")

#     # === Error Message prompt handling session -----------------------------------------------------------
#     if identified_bank == 99:
#         logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : {str(identified_bank)} - Bank Not Supported")
#         messagebox.showerror(
#             "Bank Not Supported",
#             "The uploaded bank statement is currently **not supported**.\n"
#             "Please contact the IT department to request template enhancement for this bank."
#         )
#     elif identified_bank == 98:
#         logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : {str(identified_bank)} - Bank Undefined")
#         messagebox.showerror(
#             "Bank Undefined",
#             "Error Code: [98]\n"
#             "The uploaded PDF could not be identified as a known bank.\n"
#             "Please ensure you have uploaded the correct document.\n"
#             "For further assistance, contact the IT department."
#         )
#     elif identified_bank > 90:  # error code start from 90
#         logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : {str(identified_bank)} - Unknown Error Code")
#         messagebox.showerror(
#             "Unknown Error Code",
#             "For further assistance, contact the IT department."
#         )
#     else:
#         logger.logger.info("[pdf_processor][pdf_data_extraction_main()] : Start for the main process - Loop each line from the PDF")
#         # Main Process - Loop each line from the PDF ----------------------------------------------------------
#         all_page_text = ""  # Initialize variable before the loop, to store all page text

#         logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : Total page of the uploaded PDF = {total_pages}")
#         for page_num in range(total_pages):
#             page_text = doc[page_num].get_text("text") # pyright: ignore[reportAttributeAccessIssue]

#             if page_num == 0:
#                 all_page_text += page_text + "\n"  # append to all_page_text
#                 document_info = extract_docInfo_TrxInfo(
#                     identified_bank, all_page_text, "DOC")
#             elif page_num == total_pages - 1:
#                 # Extract transactions from all pages
#                 all_page_text += page_text + "\n"  # append to all_page_text
#                 page_transactions = extract_docInfo_TrxInfo(identified_bank, all_page_text, "TRN")
#                 all_transactions.extend(page_transactions)
#             else:
#                 # Append current page text
#                 all_page_text += page_text + "\n"

#     # Close the PDF file
#     doc.close()

#     return {"Document Info": document_info, "Transactions": all_transactions}


def pdf_data_extraction_main(pdf_path):
    """
    New extraction handler that allows dynamic selection of PDF extraction method.
    Supported engines: 'fitz', 'pdfplumber', 'pdf2image', 'ocrmypdf', 'trocr'
    """
    logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : Start process")

    global pdf_path_global
    pdf_path_global = pdf_path

    # Step 1: Identify bank
    result = identify_bank(pdf_path)
    identified_bank = result["bank_id"]
    engine = result["engine_mode"]  # override engine from config

    logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : Detected bank seq = {identified_bank}, engine = {engine}")

    #     # === Error Message prompt handling session -----------------------------------------------------------
    if identified_bank == 99:
        logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : {str(identified_bank)} - Bank Not Supported")
        messagebox.showerror(
            "Bank Not Supported",
            "The uploaded bank statement is currently **not supported**.\n"
            "Please contact the IT department to request template enhancement for this bank."
        )
    elif identified_bank == 98:
        logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : {str(identified_bank)} - Bank Undefined")
        messagebox.showerror(
            "Bank Undefined",
            "Error Code: [98]\n"
            "The uploaded PDF could not be identified as a known bank.\n"
            "Please ensure you have uploaded the correct document.\n"
            "For further assistance, contact the IT department."
        )
    elif identified_bank > 90:  # error code start from 90
        logger.logger.info(f"[pdf_processor][pdf_data_extraction_main()] : {str(identified_bank)} - Unknown Error Code")
        messagebox.showerror(
            "Unknown Error Code",
            "For further assistance, contact the IT department."
        )
    else:
        # Step 2: Extract text (first page for DOC, all pages for TRN)
        first_page_text = extract_text_by_engine(pdf_path, engine, page_mode="first")
        all_text = extract_text_by_engine(pdf_path, engine, page_mode="all")
        # output_rawdata(all_text)

        # Step 3: Pass text to bank-specific extraction modules
        doc_info = extract_docInfo_TrxInfo(identified_bank, first_page_text, "DOC")
        trx_info = extract_docInfo_TrxInfo(identified_bank, all_text, "TRN")

    return {"Document Info": doc_info, "Transactions": trx_info}