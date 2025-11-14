#!/usr/bin/env python3
"""
Standardize multi-country addresses into: Street, City, Postal Code, Country.

Features
--------
- Uses OpenAI GPT-5 with Structured Outputs (JSON Schema) for robust parsing.
- Preserves all original columns and appends standardized fields + flags.
- Two flags per row:
    * gpt_flag       : set by the model (e.g., ok, ambiguous, missing_fields, ...)
    * internal_flag  : set by this script if something looks off (bool) + details
- Gracefully handles extra components by keeping standardized columns strict
  and storing extras in 'unmapped_components' (JSON string) for audit.
- Retries with backoff on transient API errors.
- Falls back to a simple heuristic parser if OPENAI_API_KEY is not set
  (so you can still get a draft output).

Usage
-----
python standardize_addresses.py \
  --input "Address - Sheet1.csv" \
  --output "Address_Standardized.csv" \
  --model "gpt-5" \
  --rate-limit 3

Environment
-----------
export OPENAI_API_KEY="YOUR_KEY"

Notes
-----
- Postal codes are treated as strings to preserve leading zeros.
- 'Country' is returned as the English short name when possible.
- 'Street' should include house number + street name and unit/suite if present,
  but MUST NOT include city/region/postal/country.
"""

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Optional: tqdm for progress; fall back gracefully if not installed
try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(x, **kwargs):
        return x

# ---------------------------
# OpenAI client (lazy import)
# ---------------------------
def make_openai_client():
    """Import and construct the OpenAI client only if an API key is present."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI()
        return client
    except Exception as e:  # pragma: no cover
        print(f"[warn] Could not import OpenAI SDK: {e}", file=sys.stderr)
        return None


# ---------------------------
# JSON Schema for GPT-5
# ---------------------------
ADDRESS_PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "street": {
            "type": "string",
            "description": "Street line including house/building number and unit if present. Do NOT include city/region/postal/country."
        },
        "city": {
            "type": "string",
            "description": "City / Town / Municipality."
        },
        "postal_code": {
            "type": "string",
            "description": "Postal or ZIP code. Keep as string; preserve leading zeros."
        },
        "country": {
            "type": "string",
            "description": "Country name (English short name preferred)."
        },
        "extra": {
            "type": "object",
            "description": "Additional address components that do not map to the target columns.",
            "properties": {
                "state":   {"type": ["string", "null"]},
                "province":{"type": ["string", "null"]},
                "region":  {"type": ["string", "null"]},
                "county":  {"type": ["string", "null"]},
                "district":{"type": ["string", "null"]},
                "sublocality":{"type": ["string", "null"]},
                "building":{"type": ["string", "null"]},
                "unit":    {"type": ["string", "null"]},
                "landmark":{"type": ["string", "null"]},
                "po_box":  {"type": ["string", "null"]},
                "line2":   {"type": ["string", "null"]}
            },
            "required": [
                "state","province","region","county",
                "district","sublocality","building","unit",
                "landmark","po_box","line2"
            ],
            "additionalProperties": False
        },
        "confidence": {
            "type": "number",
            "description": "Model's confidence in [0.0, 1.0].",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "gpt_flag": {
            "type": "string",
            "description": "Model's assessment of parsing quality.",
            "enum": ["ok", "ambiguous", "missing_fields", "unmapped_extra", "low_confidence"]
        },
        "gpt_flag_reason": {
            "type": "string",
            "description": "Short reason for the flag."
        }
    },
    "required": [
        "street","city","postal_code","country",
        "extra","confidence","gpt_flag","gpt_flag_reason"
    ],
    "additionalProperties": False
}

SYSTEM_INSTRUCTIONS = (
    "You are an expert address normalizer. Extract the address into the schema fields. "
    "Rules:\n"
    "- street: include house/building number and unit/suite if present; do NOT include city/region/postal/country.\n"
    "- city: the appropriate city/town/municipality level. If multiple candidates, pick the most standard for mailing and set gpt_flag accordingly.\n"
    "- postal_code: keep as a string; preserve leading zeros; normalize spacing (e.g., 'SW1A 1AA').\n"
    "- country: English short name (ISO 3166 common name), e.g., 'United States', 'United Kingdom', 'Germany'.\n"
    "- extra: put any additional components here (state/province/region/county/district/sublocality/building/unit/landmark/po_box/line2). Use null for missing.\n"
    "- confidence: float [0,1].\n"
    "- gpt_flag: 'ok' if all core fields look correct; otherwise one of "
    "['ambiguous','missing_fields','unmapped_extra','low_confidence'].\n"
    "- gpt_flag_reason: concise explanation.\n"
    "If input is incompatible or unclear, leave unknowns empty (\"\") and set gpt_flag appropriately.\n"
    "Return ONLY valid JSON that matches the provided JSON Schema."
)

# ---------------------------
# Heuristic draft parser (fallback when no API key)
# ---------------------------
COUNTRY_MAP = {
    "us": "United States", "usa": "United States", "united states": "United States",
    "uk": "United Kingdom", "gb": "United Kingdom", "united kingdom": "United Kingdom",
    "canada": "Canada", "ca": "Canada", "australia": "Australia", "au": "Australia",
    "germany": "Germany", "de": "Germany", "france": "France", "fr": "France",
    "spain": "Spain", "es": "Spain", "italy": "Italy", "it": "Italy",
    "netherlands": "Netherlands", "nl": "Netherlands", "belgium": "Belgium", "be": "Belgium",
    "switzerland": "Switzerland", "ch": "Switzerland", "austria":"Austria","at":"Austria",
    "sweden":"Sweden","se":"Sweden","norway":"Norway","no":"Norway","denmark":"Denmark","dk":"Denmark",
    "finland":"Finland","fi":"Finland","ireland":"Ireland","ie":"Ireland",
    "new zealand":"New Zealand","nz":"New Zealand",
    "india":"India","in":"India","japan":"Japan","jp":"Japan","china":"China","cn":"China",
    "singapore":"Singapore","sg":"Singapore","hong kong":"Hong Kong","hk":"Hong Kong",
}

POSTAL_PATTERNS = [
    re.compile(r"\b\d{5}(?:-\d{4})?\b"),  # US
    re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][ -]?\d[ABCEGHJ-NPRSTV-Z]\d\b", re.I),  # CA
    re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.I),  # UK
    re.compile(r"\b\d{4,6}\b"),  # AU/EU generic
]

def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None

def _norm_country(s: Optional[str]) -> Optional[str]:
    s = _norm(s)
    if not s:
        return None
    key = s.lower()
    return COUNTRY_MAP.get(key, s)

def _extract_postal(text: str) -> Tuple[Optional[str], str]:
    for pat in POSTAL_PATTERNS:
        m = pat.search(text)
        if m:
            code = m.group(0).strip()
            rest = (text[:m.start()] + " " + text[m.end():]).strip()
            rest = re.sub(r"\s{2,}", " ", rest)
            return code, rest
    return None, text

def heuristic_parse(full: str, existing_country: Optional[str]) -> Dict[str, str]:
    st = city = postal = country = ""
    country = _norm_country(existing_country)

    if not country and full:
        parts = [p.strip() for p in full.split(",") if p.strip()]
        if parts:
            maybe_country = parts[-1]
            c2 = _norm_country(maybe_country)
            if c2 and c2 != maybe_country:
                country = c2

    if full:
        pc, rest = _extract_postal(full)
        if pc:
            postal = pc
            # guess city as last comma piece
            segs = [p.strip() for p in rest.split(",") if p.strip()]
            if segs:
                city = segs[-1]
            # street ~ everything before last 1-2 segments
            if len(segs) > 1:
                st = ", ".join(segs[:-1])
            else:
                st = rest
        else:
            # fallback: naive split
            segs = [p.strip() for p in full.split(",") if p.strip()]
            if len(segs) >= 3:
                st = ", ".join(segs[:-2])
                city = segs[-2]
                postal = ""  # unknown
            elif len(segs) == 2:
                st, city = segs
            elif len(segs) == 1:
                st = segs[0]

    return {
        "street": st,
        "city": city,
        "postal_code": postal,
        "country": country or ""
    }

# ---------------------------
# Column detection / assembly
# ---------------------------
def normalize_colname(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[\s\.\-_]+", "", s)
    return s

ALIASES = {
    "street": ["street","address","address1","addressline1","line1","addr1","streetaddress","addressline","addresslineone"],
    "street2": ["address2","addressline2","line2","addr2","unit","suite","apartment","addresslinetwo"],
    "city": ["city","town","locality","municipality"],
    "region": ["state","province","region","county","prefecture","district"],
    "postal": ["postalcode","postcode","zip","zipcode","pin","eircode"],
    "country": ["country","countryname","nation"]
}

def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    normalized_aliases = {a for a in aliases}
    for col in df.columns:
        if normalize_colname(col) in normalized_aliases:
            return col
    return None

def build_full_address(row: pd.Series, col_map: Dict[str, Optional[str]]) -> str:
    parts = []
    for key in ("street","street2","city","region","postal","country"):
        col = col_map.get(key)
        if col and pd.notna(row.get(col, None)) and str(row[col]).strip():
            parts.append(str(row[col]).strip())
    return ", ".join(parts)

# ---------------------------
# GPT call
# ---------------------------
def call_gpt_structured(client, model: str, raw_text: str) -> Optional[dict]:
    """Calls Responses API with JSON Schema format.

    Returns parsed dict or None on refusal.
    """
    # Prepare messages
    input_msgs = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": raw_text},
    ]
    try:
        # Prefer JSON-schema Structured Outputs
        response = client.responses.create(
            model=model,
            input=input_msgs,
            reasoning={"effort": "low"},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "address_parse",
                    "schema": ADDRESS_PARSE_SCHEMA,
                    "strict": True,
                },
                "verbosity": "low",
            },
            max_output_tokens=400,
        )

        # Handle refusals or incomplete
        status = getattr(response, "status", "completed")
        if status != "completed":
            # Could be content_filter or max_output_tokens, etc.
            return None

        # Successful structured output: parse JSON
        # New Responses API provides response.output_text with the JSON
        raw = response.output_text
        return json.loads(raw)

    except Exception:
        # As a fallback, try responses.parse() if available (Pydantic path).
        try:
            response = client.responses.parse(
                model=model,
                input=input_msgs,
                text_format=ADDRESS_PARSE_SCHEMA,  # some SDKs accept schema directly
            )
            return response.output_parsed  # already a dict
        except Exception:
            return None

# ---------------------------
# Backoff helper
# ---------------------------
def sleep_backoff(attempt: int, base: float = 1.0, cap: float = 10.0):
    time.sleep(min(cap, base * (2 ** attempt) * (1 + 0.1 * attempt)))

# ---------------------------
# Main processing
# ---------------------------
def process_file(
    input_path: str,
    output_path: str,
    model: str = "gpt-5",
    rate_limit: int = 3,
    preview_rows: Optional[int] = None,
) -> None:
    # Load CSV
    df = None
    for enc in ("utf-8-sig","utf-8","latin1"):
        try:
            df = pd.read_csv(input_path, encoding=enc)
            break
        except Exception:
            pass
    if df is None:
        raise RuntimeError(f"Could not read CSV: {input_path}")

    # Discover columns
    col_map = {
        key: find_column(df, [normalize_colname(a) for a in aliases])
        for key, aliases in ALIASES.items()
    }

    # Construct client (if key missing, we'll use heuristic fallback)
    client = make_openai_client()
    use_gpt = client is not None

    rows = df.iterrows()
    if preview_rows:
        rows = list(df.head(preview_rows).iterrows())

    output_records = []
    last_call_ts = 0.0
    min_spacing = 1.0 / max(rate_limit, 1)

    for idx, row in tqdm(rows, total=(len(rows) if isinstance(rows, list) else len(df))):
        # Build a raw, human-readable input for the model
        full_address = build_full_address(row, col_map)
        if not full_address:
            # as a fallback, join all non-null string-like values
            full_address = ", ".join(
                str(v).strip() for v in row.values if pd.notna(v) and isinstance(v, (str, int, float))
            )

        # Default result container
        result = {
            "street": "",
            "city": "",
            "postal_code": "",
            "country": "",
            "extra": {},
            "confidence": 0.0,
            "gpt_flag": "missing_fields",
            "gpt_flag_reason": "no data",
        }
        internal_flag = False
        internal_flag_details: List[str] = []
        unmapped_components: Dict[str, str] = {}

        if use_gpt:
            # Simple client-side rate limiting
            elapsed = time.time() - last_call_ts
            if elapsed < min_spacing:
                time.sleep(min_spacing - elapsed)

            # Call with retries
            payload = None
            for attempt in range(4):
                payload = call_gpt_structured(client, model, full_address)
                if payload is not None:
                    break
                sleep_backoff(attempt)
            last_call_ts = time.time()

            if payload is None:
                # Treat as refusal/failure
                internal_flag = True
                internal_flag_details.append("model_refusal_or_error")
            else:
                # Strictly trust the schema fields
                result.update({
                    "street": payload.get("street",""),
                    "city": payload.get("city",""),
                    "postal_code": payload.get("postal_code",""),
                    "country": payload.get("country",""),
                    "confidence": payload.get("confidence", 0.0),
                    "gpt_flag": payload.get("gpt_flag", "ok"),
                    "gpt_flag_reason": payload.get("gpt_flag_reason", ""),
                })
                extra = payload.get("extra", {}) or {}
                # If model provided extra components, we keep them but they are not mapped
                # into the standardized 4 columns (by design); we record for audit.
                # This also triggers the *internal* flag that there were unmapped extras.
                non_null_extras = {k: v for k, v in extra.items() if v}
                if non_null_extras:
                    unmapped_components.update(non_null_extras)
                    # The model should set gpt_flag=unmapped_extra, but we also mark internal.
                    internal_flag = True
                    internal_flag_details.append("unmapped_extra_components")

        else:
            # Heuristic fallback (no API key)
            country_val = row[col_map["country"]] if col_map["country"] else None
            parsed = heuristic_parse(full_address, country_val)
            result.update({
                "street": parsed["street"],
                "city": parsed["city"],
                "postal_code": parsed["postal_code"],
                "country": parsed["country"],
                "confidence": 0.25,
                "gpt_flag": "not_run",
                "gpt_flag_reason": "offline heuristic fallback",
            })
            internal_flag = True
            internal_flag_details.append("offline_heuristic_used")

        # Internal checks for missing core fields
        core_missing = any(not str(result[k]).strip() for k in ("street","city","postal_code","country"))
        if core_missing and result["gpt_flag"] == "ok":
            # Model said 'ok' but core fields are missing — override internal flag
            internal_flag = True
            internal_flag_details.append("core_fields_missing")

        output_records.append({
            **{c: row.get(c) for c in df.columns},  # preserve original
            "Street": result["street"] or "",
            "City": result["city"] or "",
            "Postal Code": result["postal_code"] or "",
            "Country": result["country"] or "",
            "gpt_flag": result["gpt_flag"],
            "gpt_flag_reason": result["gpt_flag_reason"],
            "internal_flag": bool(internal_flag),
            "internal_flag_details": "; ".join(sorted(set(internal_flag_details))) if internal_flag_details else "",
            "unmapped_components": json.dumps(unmapped_components, ensure_ascii=False) if unmapped_components else "",
            "confidence": result["confidence"],
            "raw_input_for_model": full_address,  # helpful audit column
        })

    out_df = pd.DataFrame(output_records)
    out_df.to_csv(output_path, index=False)
    # Optionally write an Excel too if user wants
    if output_path.lower().endswith(".xlsx"):
        out_df.to_excel(output_path, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True, help="Path to input CSV")
    ap.add_argument("--output", "-o", required=True, help="Path to output CSV or XLSX")
    ap.add_argument("--model", default="gpt-5", help="OpenAI model (default: gpt-5)")
    ap.add_argument("--rate-limit", type=int, default=3, help="Max requests per second (client-side throttle)")
    ap.add_argument("--preview-rows", type=int, default=None, help="Process only first N rows (debugging)")
    args = ap.parse_args()

    process_file(
        input_path=args.input,
        output_path=args.output,
        model=args.model,
        rate_limit=args.rate_limit,
        preview_rows=args.preview_rows,
    )


if __name__ == "__main__":
    main()
