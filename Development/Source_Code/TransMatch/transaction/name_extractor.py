# flake8: noqa: E501

import re
from tkinter import messagebox

import dependency_manager
import logger


# Offline embedding-based NER (optional)
embedding_ner_extract = None  # populated lazily
_user_opted_out_ml = False
_manual_warning_shown = False


def reset_ml_warning_flag():
    """Reset the ML warning flag when a new PDF is selected."""
    global _manual_warning_shown
    _manual_warning_shown = False


def _load_embedding_engine() -> bool:
    """Ensure the embedding extractor is ready."""
    global embedding_ner_extract, _user_opted_out_ml
    if _user_opted_out_ml:
        return False
    if embedding_ner_extract is not None:
        return True
    
    # Check if ML library is available
    if not dependency_manager._has_sentence_transformers():
        # Show choice dialog if ML is not available
        try:
            result = dependency_manager.ensure_sentence_transformers(show_failure_message=False, show_choice_dialog=True)
            if result is None:
                # User cancelled, opt out of ML
                _user_opted_out_ml = True
                return False
            # result is False means user chose manual input or ML not available
            if not result:
                _user_opted_out_ml = True
                return False
        except Exception as e:
            logger.logger.exception(
                "[name_extractor] : Error showing ML choice dialog.", exc_info=e
            )
            _user_opted_out_ml = True
            return False
    
    try:
        from transaction.ner_embeddings_offline import embedding_ner_extract as _embedding_fn
        embedding_ner_extract = _embedding_fn
        return True
    except ImportError as exc:
        if "sentence_transformers" in str(exc):
            result = dependency_manager.ensure_sentence_transformers(show_failure_message=False)
            if result is None:
                # User cancelled
                _user_opted_out_ml = True
                return False
            if result:
                return _load_embedding_engine()
            _user_opted_out_ml = True
            return False
        logger.logger.info(
            "[name_extractor] : sentence-transformers unavailable; embedding NER disabled."
        )
        return False
    except Exception as exc:
        logger.logger.exception(
            "[name_extractor] : Unexpected error loading embedding NER.", exc_info=exc
        )
        _user_opted_out_ml = True
        return False

# ================== Regex-based extractors ==================

def NER_extract_name(text):
    # logger.logger.info("[name_extractor] : Formatting the text parameter for named entity recognition(NER) features")

    text = text.upper()  # normalize to uppercase
    # final_text_clean = " ".join(text.split())
    # logger.logger.info(f"[name_extractor] : Original text = {final_text_clean}")

    # DuitNow
    duitnow_match = re.search(r'DR \d+ ([A-Z &\.]+) FROM', text)
    if duitnow_match:
        return duitnow_match.group(1).strip()

    # A/C pattern
    ac_match = re.search(r'A/C ([A-Z &\.]+)', text)
    if ac_match:
        return ac_match.group(1).strip()

    # FR A/ pattern with number+* before name
    fr_a_after_number_match = re.search(
        r'FR\s+A/\s*\S+\s*\*?\s+([A-Z &\.]+)', text)
    if fr_a_after_number_match:
        return fr_a_after_number_match.group(1).strip()

    # FPX PAYMENT FR A/ pattern
    fpx_match = re.search(
        r'FPX PAYMENT\s+FR\s+A/\s*\S+\s*\*?\s+([A-Z][A-Z &\.]+(?:\s+[A-Z][A-Z &\.]+)*)', text)
    if fpx_match:
        return fpx_match.group(1).strip()

    # PAYMENT VIA MYDEBIT pattern
    mydebit_match = re.search(
        r'PAYMENT VIA MYDEBIT\s+([A-Z0-9 ()\-]+?)(?=\*|PAYMENT VIA)', text)
    if mydebit_match:
        return mydebit_match.group(1).strip()

    # DEBIT ADVICE pattern
    debit_advice_match = re.search(
        r'DEBIT ADVICE\s+([A-Z0-9 &\.\-]+)\s*\*', text)
    if debit_advice_match:
        return debit_advice_match.group(1).strip()

    # FUND TRANSFER TO A/ pattern
    fund_transfer_match = re.search(
        r'FUND TRANSFER TO A/\s+([A-Z ]+?)\s*\*', text)
    if fund_transfer_match:
        return fund_transfer_match.group(1).strip()

    # SALE DEBIT pattern
    sale_debit_match = re.search(r'SALE DEBIT\s+([A-Z0-9 \-]+?)\s*\*', text)
    if sale_debit_match:
        return sale_debit_match.group(1).strip()

    # After masked XXXXXX pattern
    masked_match = re.search(r'XXXXXX\s*([A-Z &\.]+)', text)
    if masked_match:
        return masked_match.group(1).strip()

    # After card number pattern
    card_match = re.search(r'\d{10,}\&*\s*([A-Z &\.]+)', text)
    if card_match:
        return card_match.group(1).strip()

    # Last fallback: after last number block
    generic_match = re.search(r'(?:\d{4,}\s+)?([A-Z][A-Z &\.]{3,})$', text)
    if generic_match:
        return generic_match.group(1).strip()

    # Generic fallback: capture likely company name before long reference ID
    fallback_match = re.search(
        r'([A-Z0-9 &\.\(\)\-]{5,})\s+[A-Z0-9]{10,}', text)
    if fallback_match:
        return fallback_match.group(1).strip()

    return None


def extract_from_duitnow_1(text):
    match = re.search(r'DR\s+\d+\s+([A-Z &\.]+)\s+FROM', text)
    return match.group(1).strip() if match else None


def extract_from_duitnow_2(text):
    text = text.upper()
    if "DUITNOW QR" in text:
        match = re.search(r'DUITNOW QR QR PAYMENT\s+([A-Z ]{3,40})', text)
        if match:
            return match.group(1).strip()

        match = re.search(r'DUITNOW QR\s+([A-Z ]{3,40})\s+\d{20,}', text)
        if match:
            return match.group(1).strip()

        match = re.search(r'DUITNOW QR\s+([A-Z ]{3,40})', text)
        if match:
            return match.group(1).strip()

def extract_from_duitnow_3(text):
    """
    Handle generic DuitNow Instant Transfer blocks where name appears
    on a clean line (often capitalized company name).
    Example:
        DuitNow/Instant Trf
        Goods Payment
        Guruvayurapa Enterprise
        AMBG GURUVAYURAPA
    → Extracts 'Guruvayurapa Enterprise'
    """
    text = text.upper().replace("|", " ")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    for i, line in enumerate(lines):
        # Match DuitNow/Instant Trf in any variation
        if re.search(r"DUITNOW[\s/\-]*INSTANT\s*TRF", line):
            # Scan forward up to 6 lines after this point
            forward_lines = lines[i + 1:i + 7]
            buffer = []
            for ln in forward_lines:
                if re.match(r"^[A-Z0-9 ()./-]+$", ln) and len(ln) >= 3:
                    buffer.append(ln)
            merged = " ".join(buffer)

            # Look for company-style pattern in the combined block
            match = re.search(
                r"([A-Z][A-Z0-9 &\.']{2,}?\s+(?:SDN\.?\s*BHD?|ENTERPRISE|TRADING|SERVICES|RESOURCES|PLT))",
                merged
            )
            if match:
                return match.group(1).title()

    return None

def extract_from_ac_format(text):
    match = re.search(r'A/C\s+([A-Z &\.]+)', text)
    return match.group(1).strip() if match else None


def extract_from_fr_a(text):
    match = re.search(r'FR\s+A/\s*\S+\s*\*?\s+([A-Z &\.]+)', text)
    return match.group(1).strip() if match else None


def extract_from_fpx(text):
    match = re.search(
        r'FPX PAYMENT\s+FR\s+A/\s*\S+\s*\*?\s+([A-Z][A-Z &\.]+(?:\s+[A-Z][A-Z &\.]+)*)', text)
    return match.group(1).strip() if match else None


def extract_from_mydebit_1(text):
    match = re.search(
        r'PAYMENT VIA MYDEBIT\s+([A-Z0-9 ()\-]+?)(?=\*|PAYMENT VIA)', text)
    return match.group(1).strip() if match else None


def extract_from_mydebit_2(text):
    # Capture merchant name appearing after amount lines for MyDebit
    match = re.search(r'MYDEBIT.*?(?:\n|\s+)([A-Z0-9\- ]{3,40}\(?[A-Z0-9\- ]*\(?)', text)
    if match:
        return match.group(1).strip()

    match = re.search(r'MYDEBIT\s+[\d,.]+\s+[\d,.]+\s+([A-Z0-9\- ]{3,40})', text)
    if match:
        return match.group(1).strip()


def extract_from_debit_advice(text):
    match = re.search(r'DEBIT ADVICE\s+([A-Z0-9 &\.\-]+)\s*\*', text)
    return match.group(1).strip() if match else None


def extract_from_fund_transfer(text):
    text = text.upper()
    if "FUND TRANSFER" in text:
        match = re.search(r'FUND TRANSFER TO A/\s+([A-Z ]+?)\s*\*', text)
        if match:
            return match.group(1).strip()

        match = re.search(r'FUND TRANSFER\s+([A-Z ]{3,40})\s+\d{8}[A-Z]{8,}', text)
        if match:
            return match.group(1).strip()
        match = re.search(r'FUND TRANSFER\s+([A-Z ]{3,40})\s+[A-Z0-9]{20,}', text)
        if match:
            return match.group(1).strip()

        match = re.search(r'FUND TRANSFER\s+[A-Z0-9]{8,}\s+([A-Z ]{2,})\s*(?=\d{8}[A-Z0-9]{10,})', text)
        if match:
            return match.group(1).strip()

        text2 = text.upper().replace("\n", " ")
        match = re.search(r'FUND TRANSFER\s+([A-Z ]{3,40})\s+(?:[A-Z0-9_ ]{5,40})?\s+([0-9]{8}[A-Z]{8,})', text2)
        if match:
            return match.group(1).strip()

        match = re.search(r'FUND TRANSFER\s+[A-Z0-9]{8,}\s+([A-Z&. ]{5,60})\s+\d{8}[A-Z0-9]{10,}', text)
        if match:
            return match.group(1).strip()

    return None


def extract_from_sale_debit(text):
    match = re.search(r'SALE DEBIT\s+([A-Z0-9 \-]+?)\s*\*', text)
    return match.group(1).strip() if match else None


def extract_from_masked(text):
    match = re.search(r'XXXXXX\s*([A-Z &\.]+)', text)
    return match.group(1).strip() if match else None


def extract_from_card_number(text):
    match = re.search(r'\d{10,}\&*\s*([A-Z &\.]+)', text)
    return match.group(1).strip() if match else None


def extract_from_instant_transf(text):
    text = text.upper()
    if "INSTANT TRANSFER AT KLM" in text:
        text = text.upper()

        match = re.search(
            r'INSTANT TRANSFER AT KLM(?:\s+\d+\.\d{2}){0,2}\s+(?![A-Z0-9]*\d)([A-Z ]{3,60})(?=\d{8}[A-Z0-9]{10,})',
            text
        )
        if match:
            return match.group(1).strip()

        match = re.search(r'\b[A-Z0-9]{8,}\s+([A-Z ]{3,40})\s+\d{8}[A-Z0-9]{10,}', text)
        if match:
            return match.group(1).strip()

        match = re.search(
            r'DUITNOW QR\s+.+?\s+([A-Z &\.]{3,60})(?=\s*\d{8}[A-Z0-9]{10,})',
            text)
        if match:
            return match.group(1).strip()

        match = re.search(
            r'INSTANT TRANSFER AT KLM(?:\s+[A-Z0-9_\.]{3,})*?\s+((?:[A-Z]+(?:\s+|$)){2,})(?=\d{8}[A-Z0-9]{10,})',
            text
        )
        if match:
            return match.group(1).strip()

        return None


def extract_generic(text):
    match = re.search(r'(?:\d{4,}\s+)?([A-Z][A-Z &\.]{3,})$', text)
    return match.group(1).strip() if match else None


def extract_fallback(text):
    match = re.search(r'([A-Z0-9 &\.\(\)\-]{5,})\s+[A-Z0-9]{10,}', text)
    return match.group(1).strip() if match else None


# Generic transaction terms that should NEVER be extracted as Target Audience
GENERIC_TRANSACTION_TERMS = {
    "DR", "CR", "CDM", "CASH DEPOSIT", "CASH DEP", "CHEQUE DEPOSIT", "CHEQUE",
    "DUITNOW", "INSTANT TRF", "DUITNOW/INSTANT TRF", "DUITNOW/INSTANT",
    "TRADE BILL", "TRADE BILL TRANSFER", "BILL TRANSFER",
    "TRANSFER", "PAYMENT", "DEPOSIT", "WITHDRAWAL",
    "MISC DR", "MISC CR", "MISC",
    "IBG", "FPX", "MYDEBIT", "ONLINE TRANSFER",
    "GOODS PAYMENT", "INSTANT TRANSFER"
}


def _is_generic_transaction_term(result: str) -> bool:
    """
    Check if the extracted result is a generic transaction term that should be rejected.
    """
    if not result:
        return True
    
    result_upper = result.upper().strip()
    
    # Check exact matches
    if result_upper in GENERIC_TRANSACTION_TERMS:
        return True
    
    # Check if result starts with generic terms
    for term in GENERIC_TRANSACTION_TERMS:
        if result_upper.startswith(term + " ") or result_upper == term:
            return True
    
    # Check if result is mostly generic terms (e.g., "DR 252BA103127 TRADE BILL TRANSFER")
    words = result_upper.split()
    generic_word_count = sum(1 for w in words if w in GENERIC_TRANSACTION_TERMS or w in ["DR", "CR", "TRANSFER", "BILL", "TRADE"])
    
    # If more than 50% of words are generic terms, reject it
    if len(words) > 0 and generic_word_count >= len(words) * 0.5:
        return True
    
    # Check for patterns like "DR 252BA103127" or "CDM CASH DEPOSIT"
    if re.match(r'^(DR|CR|CDM|MISC)\s+', result_upper):
        return True
    
    if re.search(r'\b(TRADE\s+BILL|CASH\s+DEPOSIT|CASH\s+DEP|CHEQUE\s+DEPOSIT)\b', result_upper):
        return True
    
    # Check if it's just a reference number pattern (e.g., "252BA103127")
    if re.match(r'^[A-Z0-9]{8,}$', result_upper.replace(" ", "")):
        return True
    
    return False


def NER_extraction(text):
    text = text.upper().strip()

    extractors = [
        extract_from_duitnow_1,
        extract_from_duitnow_2,
        extract_from_duitnow_3,
        extract_from_ac_format,
        extract_from_fr_a,
        extract_from_fpx,
        extract_from_mydebit_1,
        extract_from_mydebit_2,
        extract_from_debit_advice,
        extract_from_fund_transfer,
        extract_from_sale_debit,
        extract_from_masked,
        extract_from_card_number,
        extract_from_instant_transf,
        extract_generic,
        extract_fallback
    ]

    for extractor in extractors:
        result = extractor(text)
        if result:
            # Filter out generic transaction terms
            if _is_generic_transaction_term(result):
                logger.logger.info(
                    f"[name_extractor] : Rejected generic transaction term from {extractor.__name__} -> '{result}'"
                )
                continue
            # logger.logger.info(f"[name_extractor] : Extracted name using {extractor.__name__} -> {result}")
            return result

    # logger.logger.info("[name_extractor] : No match found for NER")
    return None


# ================== Public APIs ==================

def NER_extraction_ML(text: str):
    global _manual_warning_shown

    # --- Step 1: offline embedding-based extraction ---
    if embedding_ner_extract is None and not _load_embedding_engine():
        # Show message when ML is needed but not available (downloading or not downloaded)
        if not _manual_warning_shown:
            try:
                messagebox.showinfo(
                    "TransMatch",
                    "Optional ML components were not downloaded. "
                    "Target Audience (NER) values will remain blank until you download them.",
                )
            except Exception:
                logger.logger.info(
                    "[name_extractor] : Unable to show NER warning message to user."
                )
            _manual_warning_shown = True
        # Fallback to regex-based extraction if ML is not available
        logger.logger.info("[name_extractor] : ML not available, falling back to regex-based extraction")
        return NER_extraction(text)

    if embedding_ner_extract is not None:
        try:
            emb_res = embedding_ner_extract(text)
            if emb_res:
                logger.logger.info(
                    f"[name_extractor] : Embedding-based NER result -> {emb_res}"
                )
                return emb_res.strip()
        except Exception as e:
            logger.logger.info(f"[name_extractor] : Embedding NER failed -> {str(e)}")

    # --- Final fallback to regex-based extraction ---
    logger.logger.info("[name_extractor] : ML extraction returned None, falling back to regex-based extraction")
    regex_res = NER_extraction(text)
    if regex_res:
        logger.logger.info(
            f"[name_extractor] : Regex-based NER result -> {regex_res}"
        )
        return regex_res.strip()
    
    logger.logger.info("[name_extractor] : No match found (regex + offline embeddings)")
    return None