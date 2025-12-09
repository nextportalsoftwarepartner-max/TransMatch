# flake8: noqa: E501
"""
Offline embedding-based NER for merchant / beneficiary name extraction.

- Uses a local sentence-transformers model (MiniLM).
- Generates candidate phrases from raw description text.
- Scores them against "ORG" vs "NOISE" prototypes.
- Returns the most organisation-like phrase, e.g. "JERRY DISTRIBUTORS SDN. B".

Dependencies:
    pip install sentence-transformers
"""

import math
import os
import re
from functools import lru_cache

import logger  # TransMatch logger
from sentence_transformers import SentenceTransformer
import numpy as np


# =========================
# 1. Model loading
# =========================

# You can change this to another local path or model name if desired.
# Common good options:
#   "all-MiniLM-L6-v2" (22MB, fast, good)
#   "all-MiniLM-L12-v2"
MODEL_NAME_OR_PATH = os.getenv("NER_EMBED_MODEL", "all-MiniLM-L6-v2")


def _get_model_path():
    """
    Get the path to the ML model, checking packaged location first.
    Returns the model path (local path if packaged, model name if not).
    """
    import sys
    
    # Check if we're in a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, "_internal")
        
        # Check _internal first (where we copy ml_libraries), then next to exe
        model_paths = [
            os.path.join(internal_dir, "ml_libraries", "models", MODEL_NAME_OR_PATH),  # _internal/ml_libraries/models/...
            os.path.join(exe_dir, "ml_libraries", "models", MODEL_NAME_OR_PATH),       # exe_dir/ml_libraries/models/...
        ]
        
        for packaged_model_path in model_paths:
            if os.path.exists(packaged_model_path):
                logger.logger.info(f"[ner_embeddings_offline] : Using packaged model from: {packaged_model_path}")
                return packaged_model_path
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        packaged_model_path = os.path.join(base_dir, "ml_libraries", "models", MODEL_NAME_OR_PATH)
        if os.path.exists(packaged_model_path):
            logger.logger.info(f"[ner_embeddings_offline] : Using packaged model from: {packaged_model_path}")
            return packaged_model_path
    
    # Fallback to model name (will download if not cached)
    logger.logger.info(f"[ner_embeddings_offline] : Using model name (will use cache or download): {MODEL_NAME_OR_PATH}")
    return MODEL_NAME_OR_PATH


@lru_cache(maxsize=1)
def get_model():
    """
    Lazy-load the sentence-transformers model.

    Checks for packaged model first, then falls back to model name
    (which will use Hugging Face cache if available).
    """
    model_path = _get_model_path()
    logger.logger.info(f"[ner_embeddings_offline] : Loading model -> {model_path}")
    model = SentenceTransformer(model_path)
    return model


# =========================
# 2. Cosine similarity
# =========================

def _cosine_similarity(a, b):
    if a is None or b is None:
        return 0.0
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return 0.0
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# =========================
# 3. Prototypes (ORG vs NOISE)
# =========================

ORG_PROTOTYPES = [
    "TNG DIGITAL SDN BHD",
    "JAYA GROCER SDN BHD",
    "MR DIY SDN BHD",
    "STARBUCKS COFFEE",
    "TESCO EXTRA",
    "JERRY DISTRIBUTORS SDN BHD",
    "GURUVAYURAPA ENTERPRISE",
    "LAZADA MALAYSIA",
    "SHOPEE PAY",
    "AEON BIG SDN BHD",
    "PET BOSS CENTRE",
    "MBB PET BOSS CENTRE CASH AND CARRY SDN BHD",
    "PASARAYA SEJATI TANJUNG GADING SDN BHD",
    # Add examples with PRIVATE P/L and CAPITAL patterns
    "EB VENTRA CAPITAL PRIVATE P/L",
    "VENTRA CAPITAL PRIVATE LIMITED",
    "ABC CAPITAL PRIVATE P/L",
    "XYZ VENTURE CAPITAL PRIVATE LIMITED",
    "DEF GROUP PRIVATE P/L",
]

# Separate person name prototypes for better matching
PERSON_PROTOTYPES = [
    # Malay names with markers
    "AHMAD BIN ALI",
    "SITI NURHALIZA BINTI TARUDIN",
    "FAUZIAH BINTI KAMARU",
    "MOHAMAD BIN HASSAN",
    "NOR AZIZAH BINTI ABDULLAH",
    "KESAVAN A/L GUNASEKAREN",
    "RAJESWARI A/P RAMASAMY",
    # Chinese names
    "CHIAN WEILON",
    "TAN AH QIONG",
    "LEE CHONG WEI",
    "LIM SIEW HONG",
    "WONG KAH MING",
    "CHEN WEI LING",
    # Indian names
    "KUMAR A/L MURUGAN",
    "PRIYA A/P DEVI",
    # Simple person names (2-3 words, no markers)
    "JOHN SMITH",
    "MARY TAN",
    "DAVID LEE",
    "SARAH LIM",
    "MICHAEL WONG",
    "LISA CHEN",
]


NOISE_PROTOTYPES = [
    "ONLINE TRANSFER 1234567890",
    "DUITNOW INSTANT TRF 1234567890123456",
    "DuitNow/Instant Trf",
    "DuitNow/Instant",
    "FPX PAYMENT REF 1234567890123456",
    "CARD NO 123456XXXXXX9876",
    "REFERENCE 1029384756",
    "REF 998877665544332211",
    "PAYMENT VIA MYDEBIT 123456",
    "FUND TRANSFER TO A/C 123456789012",
    "IBG 1234567890",
    "BALANCE FROM LAST STATEMENT",
    "CLOSING BALANCE IN THIS STATEMENT",
]


@lru_cache(maxsize=1)
def _get_prototype_embeddings():
    """
    Precompute and cache prototype embeddings.
    Returns: (org_embs, person_embs, noise_embs)
    """
    model = get_model()

    org_embs = model.encode(ORG_PROTOTYPES, convert_to_numpy=True, normalize_embeddings=True)
    person_embs = model.encode(PERSON_PROTOTYPES, convert_to_numpy=True, normalize_embeddings=True)
    noise_embs = model.encode(NOISE_PROTOTYPES, convert_to_numpy=True, normalize_embeddings=True)

    logger.logger.info(
        f"[ner_embeddings_offline] : Loaded {len(org_embs)} ORG, {len(person_embs)} PERSON, and {len(noise_embs)} NOISE prototypes."
    )
    return org_embs, person_embs, noise_embs


# =========================
# 4. Candidate generation
# =========================

ORG_KEYWORDS = {
    "SDN BHD", "SDN", "BHD", "BERHAD", "TRADING", "ENTERPRISE", "RESOURCES",
    "MARKETING", "SERVICES", "SERVICE", "HOLDINGS", "MANAGEMENT",
    "DISTRIBUTOR", "DISTRIBUTORS", "GLOBAL", "INDUSTRIES", "PLT",
    "SDN.", "BHD.", "BHD,", "SDN,", "CO.,LTD", "SUPPLIES",
    "PRIVATE", "P/L", "PRIVATE P/L", "PRIVATE LIMITED", "LTD", "LIMITED",
    "CAPITAL", "VENTURE", "GROUP", "CORPORATION", "CORP"
}

# New: person-name markers (Malay style etc.)
PERSON_MARKERS = {
    "BIN", "BINTI", "BT", "BTE", "A/L", "A/P"
}

EXCLUDE_KEYWORDS = {
    "DUITNOW", "INSTANT", "TRF", "TRANSFER", "PAYMENT", "GOODS", "QR",
    "ONLINE", "IBG", "FPX", "DEBIT", "CREDIT", "CARD", "VIA", "CASH",
    "REF", "REFERENCE", "NO", "NO.", "A/C", "ACCOUNT", "BALANCE",
    "STATEMENT", "DATE", "FROM", "TO", "MBB", "PBB", "CIMB", "OCBC",
    "UOB", "AFFIN", "RHB", "HLB", "BSN", "AMBANK", "AFFIN", "AMBG", "AGRO",
    # Generic transaction terms that should be excluded
    "MISC", "DR", "CR", "CDM", "CHEQUE", "DEPOSIT", "WITHDRAWAL",
    "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "JAN", "FEB", "MAR", "APR",
    "BULAN", "YEAR", "2024", "2023", "2025",
    "INV", "INVOICE", "BILL", "TRADE", "BILL TRANSFER",
    # Additional generic terms
    "DEP", "INSTANT", "TRF"
}

# Complete phrases that should be excluded (with special characters)
EXCLUDE_PHRASES = {
    "DUITNOW/INSTANT", "DUITNOW/INSTANT TRF", "DUITNOW INSTANT", "DUITNOW INSTANT TRF",
    "INSTANT TRF", "INSTANT TRANSFER", "GOODS PAYMENT",
    "TRADE BILL", "TRADE BILL TRANSFER", "CASH DEPOSIT", "CASH DEP",
    "CHEQUE DEPOSIT", "CDM CASH DEPOSIT"
}


def _extract_multiline_company_name(text: str):
    """
    Extract company names that span multiple lines.
    
    Example:
        MAY 2024 PAYMENT
        YOR406070377C01
        EB VENTRA CAPITAL
        PRIVATE P/L
    Expected: "EB VENTRA CAPITAL PRIVATE P/L"
    """
    if not text:
        return None
    
    # Normalize text
    text = text.replace("|", "\n")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    
    if len(lines) < 2:
        return None
    
    # Bank codes that should be removed from company names
    bank_codes = {"AMBG", "MBB", "PBB", "CIMB", "OCBC", "UOB", "AFFIN", "RHB", "HLB", "BSN", "AMBANK", "AGRO"}
    
    # Find lines that contain company keywords or look like company names
    company_lines = []
    for i, line in enumerate(lines):
        line_upper = line.upper()
        words = line_upper.split()
        
        # Skip lines that are mostly excluded keywords or numbers
        if all(w in EXCLUDE_KEYWORDS or _is_mostly_digits(w) for w in words):
            continue
        
        # Skip lines that start with excluded keywords (like "DUITNOW/INSTANT TRF GOODS PAYMENT")
        if words and words[0] in EXCLUDE_KEYWORDS:
            continue
        
        # Check if line contains company keywords or looks like part of a company name
        has_org_keyword = any(w in ORG_KEYWORDS for w in words)
        has_org_pattern = any(
            any(kw in w for kw in ["SDN", "BHD", "PRIVATE", "P/L", "LTD", "CAPITAL", "VENTURE", "GROUP", "ENTERPRISE"])
            for w in words
        )
        looks_like_company_part = (
            len(words) >= 2 and
            len(words) <= 6 and
            not any(w in EXCLUDE_KEYWORDS for w in words) and
            not _is_mostly_digits(line_upper)
        )
        
        if has_org_keyword or has_org_pattern or looks_like_company_part:
            # Filter out excluded keywords from the line before adding
            filtered_words = [w for w in words if w not in EXCLUDE_KEYWORDS and not _is_mostly_digits(w)]
            if filtered_words:
                filtered_line = " ".join(filtered_words)
                company_lines.append((i, filtered_line))
    
    if len(company_lines) < 1:
        return None
    
    # If we have consecutive company lines, join them
    if len(company_lines) >= 2:
        # Check if lines are consecutive or close together
        indices = [idx for idx, _ in company_lines]
        if max(indices) - min(indices) <= 3:  # Within 3 lines of each other
            # Join all company lines
            combined = " ".join([line for _, line in company_lines])
            
            # Clean up the result
            parts = combined.split()
            
            # Remove bank codes
            parts = [p for p in parts if p not in bank_codes]
            
            # Remove any trailing reference numbers
            while parts and _is_mostly_digits(parts[-1]):
                parts.pop()
            
            # Remove excluded keywords that might have slipped through
            parts = [p for p in parts if p not in EXCLUDE_KEYWORDS]
            
            # Deduplicate: remove consecutive repeated words/phrases
            if len(parts) >= 4:
                # Check for repeated patterns (e.g., "AMBG GURUVAYURAPA ENTERPRISE AMBG GURUVAYURAPA ENTERPRISE")
                deduplicated = []
                seen_phrases = set()
                for i in range(len(parts)):
                    # Check if this word starts a repeated phrase
                    is_repeat = False
                    for phrase_len in range(2, min(6, len(parts) - i + 1)):
                        phrase = " ".join(parts[i:i+phrase_len])
                        if phrase in seen_phrases:
                            is_repeat = True
                            break
                        # Check if this phrase appears later
                        if i + phrase_len < len(parts):
                            later_phrase = " ".join(parts[i+phrase_len:i+phrase_len*2])
                            if phrase == later_phrase:
                                is_repeat = True
                                seen_phrases.add(phrase)
                                break
                    if not is_repeat:
                        deduplicated.append(parts[i])
                    else:
                        # Skip the repeated part
                        break
                parts = deduplicated
            
            result = " ".join(parts).strip()
            
            # Final validation: reject if it contains too many excluded keywords
            result_words = result.split()
            excluded_count = sum(1 for w in result_words if w in EXCLUDE_KEYWORDS)
            if excluded_count >= len(result_words) * 0.3:  # More than 30% excluded keywords
                return None
            
            if len(result) >= 5:
                return result
    
    # If only one company line, but it's followed by a line with company keywords
    if len(company_lines) == 1:
        idx, line = company_lines[0]
        # Check next line
        if idx + 1 < len(lines):
            next_line = lines[idx + 1].strip().upper()
            next_words = next_line.split()
            # Filter excluded keywords
            next_words = [w for w in next_words if w not in EXCLUDE_KEYWORDS and not _is_mostly_digits(w)]
            if next_words:
                next_line_clean = " ".join(next_words)
                if any(w in ORG_KEYWORDS for w in next_words) or any(
                    any(kw in w for kw in ["PRIVATE", "P/L", "LTD", "ENTERPRISE"]) for w in next_words
                ):
                    combined = f"{line} {next_line_clean}".strip()
                    parts = combined.split()
                    # Remove bank codes
                    parts = [p for p in parts if p not in bank_codes]
                    # Remove trailing numbers
                    while parts and _is_mostly_digits(parts[-1]):
                        parts.pop()
                    result = " ".join(parts).strip()
                    if len(result) >= 5:
                        return result
    
    return None


def _clean_and_deduplicate_company_name(name: str) -> str:
    """
    Clean up and deduplicate a company name.
    
    Examples:
        "AMBG GURUVAYURAPA ENTERPRISE AMBG GURUVAYURAPA ENTERPRISE" 
        -> "GURUVAYURAPA ENTERPRISE"
        
        "GURUVAYURAPA ENTERPRISE GURUVAYURAP A ENTERPRISE"
        -> "GURUVAYURAPA ENTERPRISE"
        
        "DUITNOW/INSTANT" -> "" (rejected)
    """
    if not name:
        return name
    
    name_upper = name.upper().strip()
    
    # Reject if it's purely a generic transaction phrase
    if name_upper in EXCLUDE_PHRASES:
        return ""
    
    # Reject if it starts with or contains excluded phrases
    for phrase in EXCLUDE_PHRASES:
        if name_upper.startswith(phrase) or name_upper == phrase:
            return ""
        # Check if phrase appears in the name (with word boundaries)
        if phrase in name_upper:
            # If the name is mostly the excluded phrase, reject it
            if len(name_upper) <= len(phrase) + 5:  # Allow small variations
                return ""
    
    bank_codes = {"AMBG", "MBB", "PBB", "CIMB", "OCBC", "UOB", "AFFIN", "RHB", "HLB", "BSN", "AMBANK", "AGRO"}
    
    words = name_upper.split()
    
    # Remove bank codes
    words = [w for w in words if w not in bank_codes]
    
    # Remove excluded keywords
    words = [w for w in words if w not in EXCLUDE_KEYWORDS]
    
    # Remove words that are part of excluded phrases (handle "/" in phrases)
    filtered_words = []
    i = 0
    while i < len(words):
        # Check if current word(s) form an excluded phrase
        matched_phrase = False
        for phrase in EXCLUDE_PHRASES:
            phrase_words = phrase.replace("/", " ").split()
            if i + len(phrase_words) <= len(words):
                if words[i:i+len(phrase_words)] == phrase_words:
                    # Skip this phrase
                    i += len(phrase_words)
                    matched_phrase = True
                    break
        if not matched_phrase:
            # Also check for "/" patterns like "DUITNOW/INSTANT"
            if "/" in words[i] and words[i].upper() in ["DUITNOW/INSTANT", "DUITNOW/INSTANT/TRF"]:
                i += 1
                continue
            filtered_words.append(words[i])
            i += 1
    
    words = filtered_words
    
    # If nothing left after filtering, reject
    if not words:
        return ""
    
    # Deduplicate: find and remove repeated phrases
    if len(words) >= 4:
        # Try to find the longest unique company name
        # Look for patterns like "X Y X Y" or "X Y Z X Y Z"
        for pattern_len in range(min(4, len(words) // 2), 0, -1):
            if pattern_len * 2 > len(words):
                continue
            
            pattern1 = words[:pattern_len]
            pattern2 = words[pattern_len:pattern_len*2]
            
            if pattern1 == pattern2:
                # Found a repeat, return the first occurrence
                return " ".join(pattern1)
        
        # If no exact repeat, try to find common subsequences
        # Simple approach: if last few words match earlier words, remove the duplicate
        for suffix_len in range(1, min(5, len(words) // 2)):
            suffix = words[-suffix_len:]
            # Check if this suffix appears earlier
            for i in range(len(words) - suffix_len * 2):
                if words[i:i+suffix_len] == suffix:
                    # Found duplicate suffix, remove it
                    return " ".join(words[:-suffix_len])
    
    result = " ".join(words).strip()
    
    # Final check: reject if result is too short or is just generic terms
    if len(result) < 3:
        return ""
    
    # Reject if it's still an excluded phrase after cleaning
    if result.upper() in EXCLUDE_PHRASES:
        return ""
    
    return result


def _extract_repeated_org_name(text: str):
    """
    Rule-based extractor for repeated org names where the first block is noise or truncated,
    and the second block contains the full name.

    Example 1:
        PBB PET BOSS CENTRE CASH AND CARRY
        PBB PET BOSS CENTRE CASH AND CARRY SDN BHD
    Expected:
        PET BOSS CENTRE CASH AND CARRY SDN BHD

    Example 2:
        RHB TK MEDICAL SUPPLIES SDN BHD
        RHB TK MEDICAL SUPPLIES SDN BHD
    Expected:
        TK MEDICAL SUPPLIES SDN BHD
    """

    if not text:
        return None

    # Normalize text
    up = " ".join(text.upper().replace("|", " ").split())
    raw_tokens = [t.strip(",.") for t in up.split() if t.strip(",.")]
    if not raw_tokens:
        return None

    # Bank codes that should be removed
    bank_codes = {"AMBG", "MBB", "PBB", "CIMB", "OCBC", "UOB", "AFFIN", "RHB", "HLB", "BSN", "AMBANK", "AGRO"}
    
    # Remove noise (DuitNow, Instant, bank codes, ref numbers, month codes)
    cleaned = []
    for t in raw_tokens:
        if t in EXCLUDE_KEYWORDS:
            continue
        if t in bank_codes:  # Remove bank codes
            continue
        if any(ch.isdigit() for ch in t):    # numeric patterns like 20089765, MAY2024
            continue
        cleaned.append(t)

    if len(cleaned) < 4:
        return None

    n = len(cleaned)

    # Detect repeated org block
    # We want: [block][block][tail...]
    # And we should take the **SECOND block** because it is more complete.
    for k in range(n // 2, 1, -1):   # try larger blocks first
        if 2 * k > n:
            continue

        block1 = cleaned[0:k]
        block2 = cleaned[k:2 * k]

        if block1 == block2:
            # Pick the SECOND block (block2), not block1
            base = list(block2)

            # Look for SDN BHD in the tail
            tail = cleaned[2 * k:]
            if "SDN" in tail and "BHD" in tail:
                try:
                    idx_sdn = tail.index("SDN")
                    if idx_sdn + 1 < len(tail) and tail[idx_sdn + 1] == "BHD":
                        base += ["SDN", "BHD"]
                    else:
                        base += ["SDN", "BHD"]
                except ValueError:
                    base += ["SDN", "BHD"]

            # Basic sanity check: block must look like a real company
            if len(base) >= 3:
                result = " ".join(base)
                # Remove any bank codes that might have slipped through
                result_words = result.split()
                result_words = [w for w in result_words if w not in bank_codes]
                if len(result_words) >= 3:
                    return " ".join(result_words)

    return None


def _extract_person_marker_name(text):
    """
    Rule-based Malay person-name extractor.

    Looks for patterns like:
        ... FAUZIAH BINTI KAMARU ...
        ... AHMAD BIN ALI ...
        ... KESAVAN A/L GUNASEKAREN ...

    Returns 'FAUZIAH BINTI KAMARU', 'AHMAD BIN ALI', etc.
    """
    if not text:
        return None

    # Normalise text: uppercase, collapse spaces, remove '|' noise
    up = " ".join(text.upper().replace("|", " ").split())
    tokens = up.split()
    n = len(tokens)

    for idx, tok in enumerate(tokens):
        if tok not in PERSON_MARKERS:
            continue

        # Need a token before and after the marker
        if idx == 0 or idx + 1 >= n:
            continue

        before = tokens[idx - 1]
        after = tokens[idx + 1]

        # If the word before is a known noise word (e.g. AGRO),
        # try one more step back (so 'AGRO FAUZIAH BINTI KAMARU' -> 'FAUZIAH BINTI KAMARU')
        if before in EXCLUDE_KEYWORDS and idx - 2 >= 0:
            candidate_before = tokens[idx - 2]
            if candidate_before not in EXCLUDE_KEYWORDS:
                before = candidate_before

        # Basic sanity checks: avoid numeric/ref pieces
        if _is_mostly_digits(before) or _is_mostly_digits(after):
            continue

        name = f"{before} {tok} {after}".strip()
        if len(name) >= 5:
            return name

    return None


def _extract_simple_person_name(text):
    """
    Extract simple person names (2-4 words, no markers) that appear in clean contexts.
    
    Examples:
        "FUND TRANSFER JOHN SMITH 1234567890" -> "JOHN SMITH"
        "PAYMENT TO MARY TAN" -> "MARY TAN"
    """
    if not text:
        return None
    
    # Normalise text
    up = " ".join(text.upper().replace("|", " ").split())
    tokens = up.split()
    
    # Look for sequences of 2-4 words that look like person names
    for i in range(len(tokens) - 1):
        for length in [2, 3, 4]:
            if i + length > len(tokens):
                continue
            
            candidate_tokens = tokens[i:i+length]
            candidate = " ".join(candidate_tokens)
            
            # Check if it looks like a person name
            if looks_like_person_name(candidate):
                # Check context - should not be surrounded by noise words
                before = tokens[i-1] if i > 0 else ""
                after = tokens[i+length] if i+length < len(tokens) else ""
                
                # If surrounded by noise, skip
                if before in EXCLUDE_KEYWORDS or after in EXCLUDE_KEYWORDS:
                    continue
                
                # If before/after are numbers, might be a name
                if (not before or _is_mostly_digits(before) or before in ["TO", "FROM", "A/C", "A/", "FR"]) and \
                   (not after or _is_mostly_digits(after) or len(after) > 10):
                    return candidate
    
    return None


def looks_like_person_name(up: str) -> bool:
    """
    Rough heuristic for romanized person names, e.g.
    'CHIAN WEILON', 'TAN AH QIONG', 'LEE CHONG WEI'

    - 2–4 tokens
    - all alphabetic
    - no organisation / exclude keywords
    """
    tokens = up.split()
    if len(tokens) < 2 or len(tokens) > 4:
        return False

    # reject if contains org / exclude words
    if any(t in ORG_KEYWORDS or t in EXCLUDE_KEYWORDS for t in tokens):
        return False

    # reject if any token has digits
    if any(_is_mostly_digits(t) for t in tokens):
        return False

    # all tokens purely letters, length >= 2 (so 'A' or 'B' alone is unlikely)
    if not all(re.fullmatch(r"[A-Z]{2,}", t) for t in tokens):
        return False

    return True


def _is_mostly_digits(s: str) -> bool:
    s = s.replace(" ", "").replace("-", "").replace("/", "")
    return s.isdigit() or re.fullmatch(r"[0-9X]+", s) is not None


def _looks_like_amount_or_date(s: str) -> bool:
    s = s.strip()
    # Amount like 1,234.56
    if re.fullmatch(r"[\d,]+\.\d{2}", s):
        return True
    # Date like 01/06/2024 or 06-06-2024 etc
    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}([-/]\d{2,4})?", s):
        return True
    return False


def _prune_substring_candidates(candidates: set[str]) -> list[str]:
    """
    Drop candidates that are strict substrings of longer ones.
    e.g. keep 'KESAVAN A/L GUNASEKAREN' and drop 'L GUNASEKAREN'.
    """
    # cand_list = list(candidates)
    # keep: list[str] = []

    # for c in cand_list:
    #     cu = c.upper()
    #     words_c = cu.split()
    #     is_sub = False

    #     for other in cand_list:
    #         if other is c:
    #             continue
    #         ou = other.upper()
    #         words_o = ou.split()

    #         if len(words_o) > len(words_c) and cu in ou:
    #             # c is fully inside a strictly longer candidate
    #             is_sub = True
    #             break

    #     if not is_sub:
    #         keep.append(c)

    # return keep

    # Just return all unique candidates (case-insensitive)
    seen = set()
    out: list[str] = []
    for c in candidates:
        cu = c.upper().strip()
        if cu not in seen:
            seen.add(cu)
            out.append(c)
    return out


def generate_candidates(text: str):
    """
    Generate candidate phrases from raw description text.

    Strategy:
    - Normalise text (uppercase, '|' → newline).
    - Create line-based candidates.
    - Create sliding windows of 2–6 tokens skipping noise words.
    - Special handling for Malay person markers (BIN / BINTI / A/L / A/P).
    - Remove numeric / date / ref-only noise.
    - Prune shorter substrings (so we don't pick only 'PASSION' or 'KAMARU').
    - Heuristically pre-score before sending to the embedding model.
    """
    if not text:
        return []

    # Normalise text
    text = text.replace("|", "\n")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    candidates: set[str] = set()

    # -------- 1) Line-based raw candidates --------
    for line in lines:
        if len(line) < 3:
            continue
        if _is_mostly_digits(line):
            continue
        if _looks_like_amount_or_date(line):
            continue

        line_upper = line.upper().strip()
        
        # Skip if line is an excluded phrase
        if line_upper in EXCLUDE_PHRASES:
            continue
        
        # Skip if line starts with excluded phrase
        for phrase in EXCLUDE_PHRASES:
            if line_upper.startswith(phrase):
                continue

        words_up = [w.strip(",.()").upper() for w in line.split()]
        if words_up and all(w in EXCLUDE_KEYWORDS for w in words_up):
            continue

        # Skip lines that are purely generic transaction terms
        if len(words_up) <= 3 and all(w in EXCLUDE_KEYWORDS for w in words_up):
            continue

        parts = line.split()

        # Remove trailing numeric / reference-like tokens
        while parts and _is_mostly_digits(parts[-1]):
            parts.pop()

        cleaned_line = " ".join(parts).strip()
        
        # Skip if cleaned line is an excluded phrase
        if cleaned_line.upper() in EXCLUDE_PHRASES:
            continue
        
        if len(cleaned_line) >= 3:
            candidates.add(cleaned_line)
    
    # -------- 1B) Multi-line company name candidates --------
    # Join consecutive lines that look like company names (contain ORG keywords)
    for i in range(len(lines) - 1):
        line1 = lines[i].strip().upper()
        line2 = lines[i + 1].strip().upper()
        
        # Skip if lines are too short or contain only excluded keywords
        if len(line1) < 3 or len(line2) < 3:
            continue
        
        words1 = line1.split()
        words2 = line2.split()
        
        # Check if either line contains company keywords
        has_org_keyword = (
            any(w in ORG_KEYWORDS for w in words1) or
            any(w in ORG_KEYWORDS for w in words2) or
            any(any(org_kw in w for org_kw in ["SDN", "BHD", "PRIVATE", "P/L", "LTD", "CAPITAL"]) for w in words1 + words2)
        )
        
        # Check if lines don't contain only excluded keywords
        not_only_excluded = (
            not all(w in EXCLUDE_KEYWORDS or _is_mostly_digits(w) for w in words1) and
            not all(w in EXCLUDE_KEYWORDS or _is_mostly_digits(w) for w in words2)
        )
        
        if has_org_keyword and not_only_excluded:
            # Join the two lines
            combined = f"{line1} {line2}".strip()
            # Remove any reference numbers at the end
            combined_parts = combined.split()
            while combined_parts and _is_mostly_digits(combined_parts[-1]):
                combined_parts.pop()
            combined_clean = " ".join(combined_parts).strip()
            if len(combined_clean) >= 5:
                candidates.add(combined_clean)
        
        # Try 3 consecutive lines for longer company names
        if i + 2 < len(lines):
            line3 = lines[i + 2].strip().upper()
            if len(line3) >= 3:
                words3 = line3.split()
                has_org_keyword_3 = (
                    has_org_keyword or
                    any(w in ORG_KEYWORDS for w in words3) or
                    any(any(org_kw in w for org_kw in ["SDN", "BHD", "PRIVATE", "P/L", "LTD", "CAPITAL"]) for w in words3)
                )
                not_only_excluded_3 = (
                    not_only_excluded and
                    not all(w in EXCLUDE_KEYWORDS or _is_mostly_digits(w) for w in words3)
                )
                if has_org_keyword_3 and not_only_excluded_3:
                    combined = f"{line1} {line2} {line3}".strip()
                    combined_parts = combined.split()
                    while combined_parts and _is_mostly_digits(combined_parts[-1]):
                        combined_parts.pop()
                    combined_clean = " ".join(combined_parts).strip()
                    if len(combined_clean) >= 5:
                        candidates.add(combined_clean)

    # -------- 2) Token-based sliding windows (2–6 words) --------
    upper_text = " ".join(text.split()).upper()
    raw_tokens = upper_text.split()

    # Drop pure noise tokens (DUITNOW, INSTANT, TRF, etc.)
    tokens: list[str] = [
        t for t in raw_tokens
        if not _is_mostly_digits(t)
        and t not in EXCLUDE_KEYWORDS
    ]

    n = len(tokens)
    for i in range(n):
        for win_size in range(2, 7):  # 2..6 tokens
            j = i + win_size
            if j > n:
                break
            chunk_tokens = tokens[i:j]
            chunk = " ".join(chunk_tokens)
            if len(chunk) < 3:
                continue
            if _looks_like_amount_or_date(chunk):
                continue
            candidates.add(chunk)
            
            # Special handling: if chunk looks like a person name, also add it with higher priority
            if looks_like_person_name(chunk):
                candidates.add(chunk)  # Add again to increase its weight

    # -------- 3) Malay person-name join logic (BIN / BINTI / A/L / A/P) --------
    for i, line in enumerate(lines):
        up = line.strip().upper()
        if not up:
            continue

        tokens_line = up.split()
        has_person_marker = any(tok in PERSON_MARKERS for tok in tokens_line)
        if not has_person_marker:
            continue

        # Take up to 1 word before and 3 words after marker → full person name
        idxs = [idx for idx, tok in enumerate(tokens_line) if tok in PERSON_MARKERS]
        for idx in idxs:
            start = max(0, idx - 1)
            end = min(len(tokens_line), idx + 4)
            person_tokens = tokens_line[start:end]
            if len(person_tokens) >= 2:
                candidates.add(" ".join(person_tokens))

    # -------- 4) Chunk-based candidates from uppercase spans --------
    for m in re.finditer(r"([A-Z][A-Z0-9&\.\-/ ]{3,60})", upper_text):
        chunk = m.group(1).strip()

        # Skip if chunk is an excluded phrase
        if chunk.upper() in EXCLUDE_PHRASES:
            continue
        
        # Skip if chunk starts with excluded phrase
        for phrase in EXCLUDE_PHRASES:
            if chunk.upper().startswith(phrase):
                continue

        # Remove leading typical noise words repeatedly
        changed = True
        while changed:
            changed = False
            for kw in ["DUITNOW", "INSTANT", "TRF", "TRANSFER",
                       "PAYMENT", "GOODS", "ONLINE", "IBG", "FPX"]:
                if chunk.startswith(kw + " ") or chunk.startswith(kw + "/"):
                    chunk = chunk[len(kw) + 1:].strip()
                    changed = True
                    break
                # Also check for "DUITNOW/INSTANT" pattern
                if "/" in chunk and "DUITNOW" in chunk.upper() and "INSTANT" in chunk.upper():
                    # Extract part after "DUITNOW/INSTANT"
                    parts = re.split(r"DUITNOW[/\s]*INSTANT[/\s]*", chunk, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        chunk = parts[-1].strip()
                        changed = True
                        break

        if len(chunk) >= 3 and not _is_mostly_digits(chunk):
            # Final check: skip if cleaned chunk is an excluded phrase
            if chunk.upper() not in EXCLUDE_PHRASES:
                candidates.add(chunk)

    # -------- 5) Remove substring candidates --------
    pruned = _prune_substring_candidates(candidates)
    
    # -------- 5B) Filter out excluded phrases from candidates --------
    filtered_candidates = []
    for cand in pruned:
        cand_upper = cand.upper().strip()
        # Skip if candidate is an excluded phrase
        if cand_upper in EXCLUDE_PHRASES:
            continue
        # Skip if candidate starts with excluded phrase
        skip_candidate = False
        for phrase in EXCLUDE_PHRASES:
            if cand_upper.startswith(phrase) or cand_upper == phrase:
                skip_candidate = True
                break
        if not skip_candidate:
            filtered_candidates.append(cand)
    
    pruned = filtered_candidates

    # -------- 6) Heuristic pre-scoring to choose top ones for BERT --------
    scored = []
    for cand in pruned:
        up = cand.upper()
        words = up.split()
        score = 0

        # Very strong penalty if candidate starts with excluded keywords (generic transaction terms)
        if words and words[0] in EXCLUDE_KEYWORDS:
            score -= 15  # Heavily penalize candidates starting with "MISC", "DR", "MAY", etc.
        
        # Strong penalty if first 2 words are both excluded keywords
        if len(words) >= 2 and words[0] in EXCLUDE_KEYWORDS and words[1] in EXCLUDE_KEYWORDS:
            score -= 20  # Very heavy penalty for "MISC DR", "CHEQUE DEPOSIT", etc.

        # Strong penalty for single-word unless it clearly looks like a company
        if len(words) == 1:
            score -= 3

        # Boost for company/beneficiary keywords
        if any(w in ORG_KEYWORDS for w in words):
            score += 5  # Increased from 3 to prioritize company names
        
        # Strong boost if contains multiple company keywords (e.g., "PRIVATE P/L", "SDN BHD")
        org_keyword_count = sum(1 for w in words if w in ORG_KEYWORDS)
        if org_keyword_count >= 2:
            score += 3  # Extra boost for multiple company indicators

        # Strong boost for person markers (BIN / BINTI etc.)
        if any(w in PERSON_MARKERS for w in words):
            score += 4

        # Boost for romanised person names (Chinese / Malay style)
        if looks_like_person_name(up):
            score += 3

        # Strong penalty for excluded words (generic transaction terms)
        excluded_count = sum(1 for w in words if w in EXCLUDE_KEYWORDS)
        if excluded_count > 0:
            score -= excluded_count * 3  # Stronger penalty per excluded word
        
        # Very strong penalty if candidate is mostly excluded words
        if excluded_count >= len(words) / 2:
            score -= 10

        # Medium length (2–6 words) is ideal
        if 2 <= len(words) <= 6:
            score += 2

        # Too long → slight penalty
        if len(words) > 8:
            score -= 1

        # At least one vowel → looks like real name word
        if re.search(r"[AEIOU]", up):
            score += 1

        scored.append((score, cand))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Only keep candidates with non-negative score
    top_candidates = [c for s, c in scored if s >= 0][:10]

    logger.logger.info(
        f"[ner_embeddings_offline] : Generated {len(candidates)} raw candidates, "
        f"pruned to {len(pruned)}, using top {len(top_candidates)} for embeddings."
    )
    return top_candidates


# =========================
# 5. Main API
# =========================

def embedding_ner_extract(text: str):
    """
    Main offline embedding NER entry point.

    Input:
        text: full raw description (multi-line allowed)

    Output:
        Best guess organisation / merchant / person name, or None.
    """
    text = (text or "").strip()
    if not text:
        return None

    # ---- 0A) Strong rule-based override for multi-line company names ----
    multiline_org = _extract_multiline_company_name(text)
    if multiline_org:
        # Clean and deduplicate the result
        cleaned = _clean_and_deduplicate_company_name(multiline_org)
        logger.logger.info(
            f"[ner_embeddings_offline] : Multi-line company name rule matched -> '{multiline_org}' -> cleaned: '{cleaned}'"
        )
        if cleaned:  # Only return if cleaned result is not empty
            return cleaned
    
    # ---- 0B) Strong rule-based override for repeated org names (PET BOSS, TK MEDICAL, etc.) ----
    org_name = _extract_repeated_org_name(text)
    if org_name:
        # Clean and deduplicate the result
        cleaned = _clean_and_deduplicate_company_name(org_name)
        logger.logger.info(
            f"[ner_embeddings_offline] : Repeated-org rule matched -> '{org_name}' -> cleaned: '{cleaned}'"
        )
        if cleaned:  # Only return if cleaned result is not empty
            return cleaned

    # ---- 0C) Strong rule-based override for BIN/BINTI/A/L/A/P person names ----
    person_name = _extract_person_marker_name(text)
    if person_name:
        logger.logger.info(
            f"[ner_embeddings_offline] : Person-marker rule matched -> '{person_name}'"
        )
        return person_name
    
    # ---- 0D) Rule-based override for simple person names (2-4 words, no markers) ----
    simple_person_name = _extract_simple_person_name(text)
    if simple_person_name:
        logger.logger.info(
            f"[ner_embeddings_offline] : Simple person-name rule matched -> '{simple_person_name}'"
        )
        return simple_person_name

    # ---- 1) Normal embedding-based flow ----
    candidates = generate_candidates(text)
    if not candidates:
        return None

    model = get_model()
    org_embs, person_embs, noise_embs = _get_prototype_embeddings()

    # Encode candidates
    cand_embs = model.encode(candidates, convert_to_numpy=True, normalize_embeddings=True)

    best_candidate = None
    best_score = -999.0
    best_is_person = False

    for cand, emb in zip(candidates, cand_embs):
        cand_upper = cand.upper()
        words = cand_upper.split()
        
        # Check if candidate looks like a person name
        is_person_candidate = (
            any(w in PERSON_MARKERS for w in words) or
            looks_like_person_name(cand_upper) or
            (2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Z]{2,}", w) for w in words) and
             not any(w in ORG_KEYWORDS or w in EXCLUDE_KEYWORDS for w in words))
        )
        
        # Similarity to ORG prototypes (for companies)
        sim_org = float(np.mean([_cosine_similarity(emb, o) for o in org_embs])) if len(org_embs) > 0 else 0.0
        
        # Similarity to PERSON prototypes (for person names)
        sim_person = float(np.mean([_cosine_similarity(emb, p) for p in person_embs])) if len(person_embs) > 0 else 0.0

        # Similarity to NOISE prototypes
        sim_noise = float(np.mean([_cosine_similarity(emb, n) for n in noise_embs])) if len(noise_embs) > 0 else 0.0

        # Use person similarity if it's a person candidate, otherwise use org similarity
        if is_person_candidate:
            score = sim_person - sim_noise
            # Lower threshold for person names (they might not match as well)
            threshold = 0.01
        else:
            score = sim_org - sim_noise
            threshold = 0.02

        logger.logger.info(
            f"[ner_embeddings_offline] Candidate='{cand}' (person={is_person_candidate}) -> "
            f"sim_org={sim_org:.3f}, sim_person={sim_person:.3f}, sim_noise={sim_noise:.3f}, score={score:.3f}"
        )

        if score > best_score:
            best_score = score
            best_candidate = cand
            best_is_person = is_person_candidate

    # Use appropriate threshold based on whether it's a person or company
    threshold = 0.01 if best_is_person else 0.02
    
    if best_candidate and best_score > threshold:
        # Final check: reject if it's a generic transaction term
        best_upper = best_candidate.upper().strip()
        
        # Check if it's an excluded phrase
        if best_upper in EXCLUDE_PHRASES:
            logger.logger.info(
                f"[ner_embeddings_offline] : Rejected candidate (excluded phrase) -> '{best_candidate}'"
            )
            return None
        
        # Check if it starts with or contains excluded phrases
        for phrase in EXCLUDE_PHRASES:
            if best_upper.startswith(phrase) or best_upper == phrase:
                logger.logger.info(
                    f"[ner_embeddings_offline] : Rejected candidate (contains excluded phrase: {phrase}) -> '{best_candidate}'"
                )
                return None
        
        words = best_upper.split()
        
        # Check if it's a generic transaction term
        generic_terms = {"DR", "CR", "CDM", "CASH", "DEPOSIT", "DEP", "CHEQUE", 
                        "DUITNOW", "INSTANT", "TRF", "TRANSFER", "TRADE", "BILL",
                        "MISC", "PAYMENT", "GOODS"}
        
        # Reject if it starts with generic terms
        if words and words[0] in generic_terms:
            logger.logger.info(
                f"[ner_embeddings_offline] : Rejected candidate starting with generic term -> '{best_candidate}'"
            )
            return None
        
        # Reject if it's mostly generic terms
        generic_count = sum(1 for w in words if w in generic_terms)
        if len(words) > 0 and generic_count >= len(words) * 0.5:
            logger.logger.info(
                f"[ner_embeddings_offline] : Rejected candidate with too many generic terms -> '{best_candidate}'"
            )
            return None
        
        # Clean and deduplicate the result
        cleaned = _clean_and_deduplicate_company_name(best_candidate)
        if not cleaned:  # If cleaning resulted in empty string, reject it
            logger.logger.info(
                f"[ner_embeddings_offline] : Rejected candidate after cleaning (empty result) -> '{best_candidate}'"
            )
            return None
        logger.logger.info(
            f"[ner_embeddings_offline] : Selected '{best_candidate}' (person={best_is_person}) with score={best_score:.3f} -> cleaned: '{cleaned}'"
        )
        return cleaned.strip()

    logger.logger.info(f"[ner_embeddings_offline] : No candidate passed threshold (best_score={best_score:.3f}, threshold={threshold}); returning None")
    return None
