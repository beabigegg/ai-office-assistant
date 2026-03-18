"""
PANJIT Full_PKG_CODE Parser / Decoder
======================================

Decodes PANJIT's Full_PKG_CODE strings into structured information.

Full_PKG_CODE Structure (6 segments, dash-separated):
    XXXXXX - X  - XX - XX - XXXX - X
      |       |    |    |     |     |
      |       |    |    |     |     +-- Vendor Code (1 char)
      |       |    |    |     +-------- Compound Code (4 chars)
      |       |    |    +-------------- Wires Code (2 chars)
      |       |    +------------------- D/A Code (2 chars)
      |       +------------------------ LF Code (1 char)
      +-------------------------------- Package Code (6 chars)

Source: PANJIT Package code rev15 (F-RD0215), 2024-09-03
Built by: Toolsmith
Date: 2026-02-06

Usage:
    from shared.tools.parsers.pkg_code_parser import PkgCodeParser

    parser = PkgCodeParser()
    result = parser.parse("SOTU20-C-EP-CU-1702-7")
    print(result)

    valid, errors = parser.validate("SOTU20-C-EP-CU-1702-7")
    diff = parser.compare("SOTU20-C-EP-CU-1702-7", "SOTU20-C-EP-AU-1702-E")
"""

from typing import Dict, List, Tuple, Optional, Any
import re

# =============================================================================
# LOOKUP TABLES
# =============================================================================

# ---------------------------------------------------------------------------
# Package Code (6 chars) -- three parsing modes
# ---------------------------------------------------------------------------

# --- Mode A: SOT/SOD series ---
# Structure: XXX + X(position) + X(lead_forming) + X(lf_thickness)

SOTSOD_POSITION: Dict[str, str] = {
    "U": "Die up",
    "D": "Die down",
}

SOTSOD_LEAD_FORMING: Dict[str, str] = {
    "0": "Flat Lead",
    "1": "Flat Lead + Heat Sink",
    "2": "Gull Wing",
}

SOTSOD_LF_THICKNESS: Dict[str, str] = {
    "0": "0.10-0.25mm",
    "1": "0.26-0.30mm",
    "2": "0.31-0.60mm",
}

# Known SOT/SOD package code -> package name mapping
SOTSOD_PACKAGES: Dict[str, str] = {
    "SOTU20": "SOT-23/SOT-323/SOT-23 5L/6L",
    "SOTD20": "SOT-363/353/SOT-23 6L-1",
    "SOTU00": "SOT-523/543/553/563",
    "SODU20": "SOD-123",
    "SODU00": "SOD-123FL/SOD-323/SOD-523/SOD-923",
    "SODU10": "SOD-123HE/SOD-323HE",
}

# --- Mode B: DFN series ---
# Sub-mode B1: DFN + 3-digit body thickness code
# Sub-mode B2: DF + 4-digit independent code / DFN + 3-char code

DFN_BODY_THICKNESS: Dict[str, str] = {
    "030": "(T)<0.3mm",
    "050": "(T)0.3~0.5mm",
    "075": "(T)0.65~0.85mm",
}

# DF/DFN independent codes (6-char full code -> package name)
DFN_INDEPENDENT_CODES: Dict[str, str] = {
    "DF3333": "DFN3333-8L",
    "DF5060": "DFN5060-8L/DFN5060X-8L/DFN5060B-8L/DFN5060XC-8L",
    "DF8080": "DFN8x8-4L",
    "DFN33S": "DFN3333S-8L (WX Sawn type)",
    "DFN56S": "DFN5060S-8L (WX Sawn type)",
}

# Combined DFN package lookup (by thickness code)
DFN_PACKAGES: Dict[str, str] = {
    "DFN030": "DFN0603",
    "DFN050": "DFN 2L/3L/DFN2510/DFN5515",
    "DFN075": "DFN (T)0.65~0.85mm series",
}

# --- Mode C: SMA/SMB/SMC/SME series ---
# Structure: XXX + X(body_thickness) + X(lf_structure) + X(serial_no)

SMA_BODY_THICKNESS: Dict[str, str] = {
    "0": "Normal",
    "F": "Thinner",
}

SMA_LF_STRUCTURE: Dict[str, str] = {
    "0": "Two-piece (2-piece)",
    "1": "Three-piece (3-piece)",
}

# Known SMA-family package codes
SMA_PACKAGES: Dict[str, str] = {
    "SMA": "SMA",
    "SMB": "SMB",
    "SMC": "SMC",
    "SME": "SME",
}

# SMAF/SMBF are special (flat-lead versions)
SMAF_PACKAGES: Dict[str, str] = {
    "SMAF00": "SMAF",
    "SMBF00": "SMBF",
}

# --- Mode D: TO/DO/ITO and other independent codes ---
# These are 6-char codes that map directly to package names.

INDEPENDENT_PACKAGES: Dict[str, str] = {
    "TO0252": "TO-251AA/TO-252AA",
    "TO1252": "TO-252AA-2LD",
    "TO0220": "TO-220AB/TO-220AC",
    "TOL220": "TO-220AB-L",
    "TO03P0": "TO-3P",
    "TO0247": "TO-247AD-2LD/TO-247AD-3LD/TO-247-3L/TO-247AD-2LM",
    "TOP247": "TO-247PLUS-3L",
    "TO0263": "TO-263/TO-263-7L/TO-263AB/TO-263AB-L",
    "TO0277": "TO-277/TO-277C",
    "ITO220": "ITO-220AB/ITO-220AC",
    "FTO220": "ITO-220AB-F",
    "DO0218": "DO-218AC/DO-218AB",
    "SOP008": "SOP-8",
    "SOT223": "SOT-223",
    "SOT-89": "SOT-89",
    "DO0410": "DO-41",
    "DO0150": "DO-15",
    "DO0201": "DO-201AD/DO-201AE",
    "P00600": "P-600",
    "MDI000": "MDI",
    "SDI000": "SDIP",
    "TDI000": "TDI",
    "TOLL00": "TOLL (TO-Leadless Package)",
    "M40000": "M4 series",
    "M80000": "M8 series",
    "DXK000": "DXK series",
    "KBJ000": "KBJ-2",
    "GBU000": "GBU-2",
    "GBJ000": "GBJ-2",
    "GBL000": "GBL",
    "GBJS00": "GBJS",
}

# ---------------------------------------------------------------------------
# LF Code (Lead Frame, 1 char)
# ---------------------------------------------------------------------------

LF_CODES: Dict[str, Dict[str, str]] = {
    "C": {"material": "Cu", "note": "2023 年以前適用"},
    "A": {"material": "Alloy", "note": ""},
    "P": {"material": "Cu+Ni-Pd-Au", "note": ""},
    "B": {"material": "Bare Cu", "note": ""},
    "G": {"material": "Cu plating Ag", "note": ""},
    "H": {"material": "High Density (Cu)", "note": "高密度腳架，Cu 材質"},
}

# ---------------------------------------------------------------------------
# D/A Code (Die Attach, 2 chars)
# ---------------------------------------------------------------------------

DA_CODES: Dict[str, str] = {
    "EP": "Epoxy",
    "EU": "Eutectic",
    "SS": "Soft Solder",
    "SP": "Solder paste",
    "SF": "Solder flake",
}

# ---------------------------------------------------------------------------
# Wires Code (2 chars)
# ---------------------------------------------------------------------------

WIRE_CODES: Dict[str, str] = {
    "CU": "Cu wires",
    "AU": "Au wires",
    "CR": "Cu/Rid",
    "CA": "Cu/Al",
    "AL": "Al wires",
    "CJ": "Clip (jump)",
    "LW": "LeadWire",
    "AR": "Au/Rib",
    "AA": "Au/Al",
    "AG": "Ag wires",
    "PC": "PdAuCu wire",
    "AC": "Au/Clip",
}

# ---------------------------------------------------------------------------
# Compound Code (4 chars)
# ---------------------------------------------------------------------------

COMPOUND_CODES: Dict[str, str] = {
    "1702": "CEL-1702HF9",
    "1772": "CEL-1772HF9",
    "1700": "EK-1700G",
    "3600": "EK-3600GH(GT/GTM)",
    "5000": "CK5000",
    "8200": "SG-8200",
    "9240": "CEL-9240HF/10GEM(M1)/10-8L",
    "E500": "E500",
    "E590": "E590HT",
    "E110": "EME110G",
    "E115": "EME-115H",
    "E125": "EME125",
    "110G": "EME-E110G",
    "131Y": "NH-131YS",
    "100H": "ELER-8-100HFS",
    "300L": "GE300LCF",
    "500C": "500C/500C-S",
    "G100": "KL-G100S",
    "G260": "GR260",
    "G300": "GR300",
    "G310": "WH-G310",
    "G430": "TH-G430",
    "G510": "GR510",
    "G530": "GR530",
    "G590": "G590",
    "G600": "G600(FL/FB)",
    "G630": "EME-G630AY-H",
    "G660": "G660/G660BP-A",
    "G700": "G700",
    "G720": "EME-G720C",
    "G770": "EME-G770",
    "660P": "G660BP-A",
    "K200": "KHG200F",
}

# ---------------------------------------------------------------------------
# Vendor Code (1 char)
# ---------------------------------------------------------------------------

VENDOR_CODES: Dict[str, Dict[str, str]] = {
    "P": {"name": "PANJIT", "note": "2022 年以前適用"},
    "E": {"name": "GEM", "note": "捷敏電子"},
    "F": {"name": "FH", "note": "風華"},
    "T": {"name": "TSHT", "note": "天水華天"},
    "U": {"name": "Comchip", "note": "典琦"},
    "B": {"name": "力邁", "note": ""},
    "L": {"name": "ATEC", "note": ""},
    "K": {"name": "PPL", "note": "寶浦萊"},
    "S": {"name": "Carsem", "note": "嘉盛"},
    "8": {"name": "秀武", "note": ""},
    "M": {"name": "美林", "note": ""},
    "5": {"name": "PANJIT_MBU3", "note": "2023 年起"},
    "6": {"name": "PANJIT_MBU2", "note": "2023 年起"},
    "7": {"name": "PANJIT_MBU1", "note": "2023 年起, 岡山廠"},
    "X": {"name": "ATX", "note": "日月新半導體"},
    "V": {"name": "龍晶微", "note": "龍平微"},
    "A": {"name": "安美", "note": "未合格承認供應商"},
    "C": {"name": "合肥矽邁SMAT", "note": "未合格承認供應商"},
}

# ---------------------------------------------------------------------------
# Combined lookup for all known 6-char package codes (for quick search)
# ---------------------------------------------------------------------------

ALL_KNOWN_PACKAGE_CODES: Dict[str, str] = {}
ALL_KNOWN_PACKAGE_CODES.update(SOTSOD_PACKAGES)
ALL_KNOWN_PACKAGE_CODES.update(DFN_PACKAGES)
ALL_KNOWN_PACKAGE_CODES.update(DFN_INDEPENDENT_CODES)
ALL_KNOWN_PACKAGE_CODES.update(SMAF_PACKAGES)
ALL_KNOWN_PACKAGE_CODES.update(INDEPENDENT_PACKAGES)

# Series prefixes for classification
SOTSOD_PREFIXES = ("SOT", "SOD")
DFN_PREFIXES = ("DFN", "DF")
SMA_PREFIXES = ("SMA", "SMB", "SMC", "SME")


# =============================================================================
# PARSER CLASS
# =============================================================================

class PkgCodeParser:
    """
    PANJIT Full_PKG_CODE Parser.

    Parses 6-segment dash-separated package codes into structured dictionaries.

    Examples:
        >>> parser = PkgCodeParser()
        >>> result = parser.parse("SOTU20-C-EP-CU-1702-7")
        >>> result["package"]["packages"]
        'SOT-23/SOT-323/SOT-23 5L/6L'
        >>> result["vendor"]["name"]
        'PANJIT_MBU1'
    """

    # Regex for the standard Full_PKG_CODE format
    _PATTERN = re.compile(
        r"^([A-Za-z0-9\-]{5,6})"   # Segment 1: Package Code (5-6 chars)
        r"-([A-Za-z])"              # Segment 2: LF Code (1 char)
        r"-([A-Za-z]{2})"           # Segment 3: D/A Code (2 chars)
        r"-([A-Za-z]{2})"           # Segment 4: Wires Code (2 chars)
        r"-([A-Za-z0-9]{4})"        # Segment 5: Compound Code (4 chars)
        r"-([A-Za-z0-9])$"          # Segment 6: Vendor Code (1 char)
    )

    def parse(self, code_str: str) -> Dict[str, Any]:
        """
        Parse a single Full_PKG_CODE string into a structured dictionary.

        Args:
            code_str: The Full_PKG_CODE string, e.g. "SOTU20-C-EP-CU-1702-7"

        Returns:
            A dictionary with keys: raw_code, package, lead_frame, die_attach,
            wire, compound, vendor, _success, _errors.

        Examples:
            >>> parser = PkgCodeParser()
            >>> r = parser.parse("SOTU20-C-EP-CU-1702-7")
            >>> r["package"]["series"]
            'SOT'
            >>> r["vendor"]["name"]
            'PANJIT_MBU1'

            >>> r = parser.parse("DF5060-C-SS-CU-9240-E")
            >>> r["package"]["packages"]
            'DFN5060-8L/DFN5060X-8L/DFN5060B-8L/DFN5060XC-8L'
        """
        code_str = code_str.strip()
        result: Dict[str, Any] = {
            "raw_code": code_str,
            "package": {},
            "lead_frame": {},
            "die_attach": {},
            "wire": {},
            "compound": {},
            "vendor": {},
            "_success": True,
            "_errors": [],
        }

        m = self._PATTERN.match(code_str)
        if not m:
            result["_success"] = False
            result["_errors"].append(
                f"Format mismatch: expected 6 dash-separated segments, got '{code_str}'"
            )
            # Try to do best-effort split
            parts = code_str.split("-")
            if len(parts) >= 6:
                # Attempt partial parse even with format issues
                pkg_code = parts[0]
                lf_code = parts[1] if len(parts) > 1 else ""
                da_code = parts[2] if len(parts) > 2 else ""
                wire_code = parts[3] if len(parts) > 3 else ""
                compound_code = parts[4] if len(parts) > 4 else ""
                vendor_code = parts[5] if len(parts) > 5 else ""
            else:
                return result
        else:
            pkg_code = m.group(1)
            lf_code = m.group(2)
            da_code = m.group(3)
            wire_code = m.group(4)
            compound_code = m.group(5)
            vendor_code = m.group(6)

        # --- Decode Package Code ---
        result["package"] = self._decode_package(pkg_code)

        # --- Decode LF Code ---
        lf_upper = lf_code.upper()
        if lf_upper in LF_CODES:
            info = LF_CODES[lf_upper]
            result["lead_frame"] = {
                "code": lf_code,
                "material": info["material"],
                "note": info["note"],
            }
        else:
            result["lead_frame"] = {
                "code": lf_code,
                "material": f"UNKNOWN: {lf_code}",
                "note": "",
            }
            result["_errors"].append(f"Unknown LF code: {lf_code}")

        # --- Decode D/A Code ---
        da_upper = da_code.upper()
        if da_upper in DA_CODES:
            result["die_attach"] = {
                "code": da_code,
                "method": DA_CODES[da_upper],
            }
        else:
            result["die_attach"] = {
                "code": da_code,
                "method": f"UNKNOWN: {da_code}",
            }
            result["_errors"].append(f"Unknown D/A code: {da_code}")

        # --- Decode Wires Code ---
        wire_upper = wire_code.upper()
        if wire_upper in WIRE_CODES:
            result["wire"] = {
                "code": wire_code,
                "type": WIRE_CODES[wire_upper],
            }
        else:
            result["wire"] = {
                "code": wire_code,
                "type": f"UNKNOWN: {wire_code}",
            }
            result["_errors"].append(f"Unknown Wires code: {wire_code}")

        # --- Decode Compound Code ---
        compound_upper = compound_code.upper()
        if compound_upper in COMPOUND_CODES:
            result["compound"] = {
                "code": compound_code,
                "name": COMPOUND_CODES[compound_upper],
            }
        else:
            result["compound"] = {
                "code": compound_code,
                "name": f"UNKNOWN: {compound_code}",
            }
            result["_errors"].append(f"Unknown Compound code: {compound_code}")

        # --- Decode Vendor Code ---
        if vendor_code in VENDOR_CODES:
            info = VENDOR_CODES[vendor_code]
            result["vendor"] = {
                "code": vendor_code,
                "name": info["name"],
                "note": info["note"],
            }
        else:
            result["vendor"] = {
                "code": vendor_code,
                "name": f"UNKNOWN: {vendor_code}",
                "note": "",
            }
            result["_errors"].append(f"Unknown Vendor code: {vendor_code}")

        return result

    def _decode_package(self, pkg_code: str) -> Dict[str, Any]:
        """
        Decode the 6-char Package Code segment.

        Determines which mode (SOT/SOD, DFN, SMA, or independent) applies
        and extracts structural details accordingly.

        Args:
            pkg_code: The 6-char package code, e.g. "SOTU20", "DFN050", "DF5060"

        Returns:
            Dictionary with code, series, packages, and mode-specific fields.
        """
        result: Dict[str, Any] = {"code": pkg_code}
        upper = pkg_code.upper()

        # --- Check direct independent code lookup first (highest priority) ---
        if upper in ALL_KNOWN_PACKAGE_CODES:
            result["packages"] = ALL_KNOWN_PACKAGE_CODES[upper]

        # --- Mode A: SOT/SOD series ---
        if upper[:3] in SOTSOD_PREFIXES:
            result["series"] = upper[:3]
            result["_mode"] = "SOT/SOD"

            if len(upper) >= 6:
                pos_char = upper[3]   # U or D
                lf_char = upper[4]    # 0, 1, 2
                th_char = upper[5]    # 0, 1, 2

                result["die_position"] = SOTSOD_POSITION.get(
                    pos_char, f"UNKNOWN: {pos_char}"
                )
                result["lead_forming"] = SOTSOD_LEAD_FORMING.get(
                    lf_char, f"UNKNOWN: {lf_char}"
                )
                result["lf_thickness"] = SOTSOD_LF_THICKNESS.get(
                    th_char, f"UNKNOWN: {th_char}"
                )
            else:
                result["die_position"] = "UNKNOWN (code too short)"

            if "packages" not in result:
                result["packages"] = f"UNKNOWN SOT/SOD variant: {pkg_code}"

            return result

        # --- Mode B: DFN/DF series ---
        if upper[:3] == "DFN" or upper[:2] == "DF":
            result["_mode"] = "DFN"

            # Sub-mode B2: DF independent codes (DF3333, DF5060, DF8080)
            #              or DFN special codes (DFN33S, DFN56S)
            if upper in DFN_INDEPENDENT_CODES:
                result["series"] = upper[:2] if upper[:2] == "DF" else "DFN"
                result["packages"] = DFN_INDEPENDENT_CODES[upper]
                return result

            # Sub-mode B1: DFN + 3-digit body thickness
            if upper[:3] == "DFN":
                result["series"] = "DFN"
                thickness_code = upper[3:6]
                result["body_thickness_code"] = thickness_code
                result["body_thickness"] = DFN_BODY_THICKNESS.get(
                    thickness_code, f"UNKNOWN: {thickness_code}"
                )
                if "packages" not in result:
                    result["packages"] = DFN_PACKAGES.get(
                        upper, f"DFN series ({thickness_code})"
                    )
                return result

            # DF prefix but not in independent codes
            result["series"] = "DF"
            if "packages" not in result:
                result["packages"] = f"UNKNOWN DF variant: {pkg_code}"
            return result

        # --- SMAF/SMBF special cases ---
        if upper in SMAF_PACKAGES:
            result["series"] = upper[:4]  # SMAF or SMBF
            result["_mode"] = "SMAF/SMBF"
            result["packages"] = SMAF_PACKAGES[upper]
            return result

        # --- Mode C: SMA/SMB/SMC/SME series ---
        if upper[:3] in SMA_PREFIXES:
            result["series"] = upper[:3]
            result["_mode"] = "SMA/SMB/SMC/SME"

            if len(upper) >= 6:
                thick_char = upper[3]   # 0 or F
                lf_char = upper[4]      # 0 or 1
                serial_char = upper[5]  # 0, 1, ...

                result["body_thickness"] = SMA_BODY_THICKNESS.get(
                    thick_char, f"UNKNOWN: {thick_char}"
                )
                result["lf_structure"] = SMA_LF_STRUCTURE.get(
                    lf_char, f"UNKNOWN: {lf_char}"
                )
                result["serial_no"] = serial_char

            if "packages" not in result:
                result["packages"] = f"{upper[:3]} series"

            return result

        # --- Mode D: Independent codes (TO, DO, ITO, etc.) ---
        if upper in INDEPENDENT_PACKAGES:
            # Determine series from prefix
            series = upper[:2]
            for prefix_len in (3, 2):
                candidate = upper[:prefix_len]
                if candidate in ("TO0", "TO1", "TOL", "TOP", "ITO", "FTO",
                                 "DO0", "SOP", "SOT", "MDI", "SDI", "TDI",
                                 "TOL", "KBJ", "GBU", "GBJ", "GBL", "GBJ",
                                 "DXK", "M40", "M80", "P00"):
                    series = candidate
                    break
            result["series"] = series
            result["_mode"] = "independent"
            result["packages"] = INDEPENDENT_PACKAGES[upper]
            return result

        # --- Fallback: unknown package code ---
        result["series"] = "UNKNOWN"
        result["_mode"] = "unknown"
        result["packages"] = f"UNKNOWN: {pkg_code}"
        return result

    def parse_batch(self, code_list: List[str]) -> List[Dict[str, Any]]:
        """
        Parse a batch of Full_PKG_CODE strings.

        Args:
            code_list: List of Full_PKG_CODE strings.

        Returns:
            List of parsed result dictionaries.

        Examples:
            >>> parser = PkgCodeParser()
            >>> results = parser.parse_batch([
            ...     "SOTU20-C-EP-CU-1702-7",
            ...     "DF5060-C-SS-CU-9240-E",
            ... ])
            >>> len(results)
            2
        """
        return [self.parse(code) for code in code_list]

    def validate(self, code_str: str) -> Tuple[bool, List[str]]:
        """
        Validate a Full_PKG_CODE string format and content.

        Args:
            code_str: The Full_PKG_CODE string to validate.

        Returns:
            Tuple of (is_valid: bool, errors: list[str]).
            An empty errors list means the code is fully valid.

        Examples:
            >>> parser = PkgCodeParser()
            >>> valid, errors = parser.validate("SOTU20-C-EP-CU-1702-7")
            >>> valid
            True
            >>> errors
            []

            >>> valid, errors = parser.validate("BADCODE")
            >>> valid
            False
        """
        errors: List[str] = []
        code_str = code_str.strip()

        # Check overall format
        m = self._PATTERN.match(code_str)
        if not m:
            errors.append(
                f"Format error: expected XXXXXX-X-XX-XX-XXXX-X, got '{code_str}'"
            )
            parts = code_str.split("-")
            if len(parts) != 6:
                errors.append(
                    f"Segment count: expected 6, got {len(parts)}"
                )
            else:
                if len(parts[0]) < 5 or len(parts[0]) > 6:
                    errors.append(
                        f"Package code length: expected 5-6 chars, got {len(parts[0])}"
                    )
                if len(parts[1]) != 1:
                    errors.append(
                        f"LF code length: expected 1 char, got {len(parts[1])}"
                    )
                if len(parts[2]) != 2:
                    errors.append(
                        f"D/A code length: expected 2 chars, got {len(parts[2])}"
                    )
                if len(parts[3]) != 2:
                    errors.append(
                        f"Wires code length: expected 2 chars, got {len(parts[3])}"
                    )
                if len(parts[4]) != 4:
                    errors.append(
                        f"Compound code length: expected 4 chars, got {len(parts[4])}"
                    )
                if len(parts[5]) != 1:
                    errors.append(
                        f"Vendor code length: expected 1 char, got {len(parts[5])}"
                    )
            return False, errors

        # Check each segment against known codes
        pkg_code = m.group(1)
        lf_code = m.group(2).upper()
        da_code = m.group(3).upper()
        wire_code = m.group(4).upper()
        compound_code = m.group(5).upper()
        vendor_code = m.group(6)

        # Package code validation
        pkg_result = self._decode_package(pkg_code)
        if pkg_result.get("series") == "UNKNOWN":
            errors.append(f"Unknown package code: {pkg_code}")

        # LF code
        if lf_code not in LF_CODES:
            errors.append(f"Unknown LF code: {lf_code}")

        # D/A code
        if da_code not in DA_CODES:
            errors.append(f"Unknown D/A code: {da_code}")

        # Wires code
        if wire_code not in WIRE_CODES:
            errors.append(f"Unknown Wires code: {wire_code}")

        # Compound code
        if compound_code not in COMPOUND_CODES:
            errors.append(f"Unknown Compound code: {compound_code}")

        # Vendor code
        if vendor_code not in VENDOR_CODES:
            errors.append(f"Unknown Vendor code: {vendor_code}")

        return len(errors) == 0, errors

    def compare(self, code1: str, code2: str) -> Dict[str, Any]:
        """
        Compare two Full_PKG_CODE strings and report differences.

        Args:
            code1: First Full_PKG_CODE string.
            code2: Second Full_PKG_CODE string.

        Returns:
            Dictionary with keys: code1, code2, same, differences.
            Each difference entry includes segment name, code1_value, code2_value,
            and human-readable descriptions.

        Examples:
            >>> parser = PkgCodeParser()
            >>> diff = parser.compare(
            ...     "SOTU20-C-EP-CU-1702-7",
            ...     "SOTU20-C-EP-AU-1702-E"
            ... )
            >>> diff["same"]
            False
            >>> len(diff["differences"])
            2
        """
        r1 = self.parse(code1)
        r2 = self.parse(code2)

        differences: List[Dict[str, str]] = []

        # Compare package
        if r1["package"].get("code") != r2["package"].get("code"):
            differences.append({
                "segment": "package",
                "code1_code": r1["package"].get("code", ""),
                "code1_desc": r1["package"].get("packages", ""),
                "code2_code": r2["package"].get("code", ""),
                "code2_desc": r2["package"].get("packages", ""),
            })

        # Compare lead frame
        if r1["lead_frame"].get("code") != r2["lead_frame"].get("code"):
            differences.append({
                "segment": "lead_frame",
                "code1_code": r1["lead_frame"].get("code", ""),
                "code1_desc": r1["lead_frame"].get("material", ""),
                "code2_code": r2["lead_frame"].get("code", ""),
                "code2_desc": r2["lead_frame"].get("material", ""),
            })

        # Compare die attach
        if r1["die_attach"].get("code") != r2["die_attach"].get("code"):
            differences.append({
                "segment": "die_attach",
                "code1_code": r1["die_attach"].get("code", ""),
                "code1_desc": r1["die_attach"].get("method", ""),
                "code2_code": r2["die_attach"].get("code", ""),
                "code2_desc": r2["die_attach"].get("method", ""),
            })

        # Compare wire
        if r1["wire"].get("code") != r2["wire"].get("code"):
            differences.append({
                "segment": "wire",
                "code1_code": r1["wire"].get("code", ""),
                "code1_desc": r1["wire"].get("type", ""),
                "code2_code": r2["wire"].get("code", ""),
                "code2_desc": r2["wire"].get("type", ""),
            })

        # Compare compound
        if r1["compound"].get("code") != r2["compound"].get("code"):
            differences.append({
                "segment": "compound",
                "code1_code": r1["compound"].get("code", ""),
                "code1_desc": r1["compound"].get("name", ""),
                "code2_code": r2["compound"].get("code", ""),
                "code2_desc": r2["compound"].get("name", ""),
            })

        # Compare vendor
        if r1["vendor"].get("code") != r2["vendor"].get("code"):
            differences.append({
                "segment": "vendor",
                "code1_code": r1["vendor"].get("code", ""),
                "code1_desc": r1["vendor"].get("name", ""),
                "code2_code": r2["vendor"].get("code", ""),
                "code2_desc": r2["vendor"].get("name", ""),
            })

        return {
            "code1": code1,
            "code2": code2,
            "same": len(differences) == 0,
            "differences": differences,
            "parsed_code1": r1,
            "parsed_code2": r2,
        }

    def search(self, criteria: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Search known package codes by criteria.

        Searches through all known lookup tables to find matching entries.
        Criteria keys can be: series, package, lf_material, da_method,
        wire_type, compound, vendor.

        Args:
            criteria: Dictionary of search criteria. All specified criteria
                must match (AND logic). Values are matched case-insensitively
                as substrings.

        Returns:
            List of matching entries with their details.

        Examples:
            >>> parser = PkgCodeParser()
            >>> # Find all SOT packages
            >>> results = parser.search({"series": "SOT"})
            >>> len(results) > 0
            True

            >>> # Find all packages with Cu wire
            >>> results = parser.search({"wire_type": "Cu"})
        """
        results: List[Dict[str, Any]] = []

        # Search Package Codes
        if "series" in criteria or "package" in criteria:
            search_series = criteria.get("series", "").upper()
            search_pkg = criteria.get("package", "").upper()

            for code, packages in ALL_KNOWN_PACKAGE_CODES.items():
                code_upper = code.upper()
                pkg_upper = packages.upper()

                if search_series and search_series not in code_upper:
                    continue
                if search_pkg and search_pkg not in pkg_upper:
                    continue

                pkg_detail = self._decode_package(code)
                results.append({
                    "type": "package_code",
                    "code": code,
                    "detail": pkg_detail,
                })

        # Search LF Codes
        if "lf_material" in criteria:
            search_val = criteria["lf_material"].upper()
            for code, info in LF_CODES.items():
                if search_val in info["material"].upper():
                    results.append({
                        "type": "lf_code",
                        "code": code,
                        "material": info["material"],
                        "note": info["note"],
                    })

        # Search D/A Codes
        if "da_method" in criteria:
            search_val = criteria["da_method"].upper()
            for code, method in DA_CODES.items():
                if search_val in method.upper():
                    results.append({
                        "type": "da_code",
                        "code": code,
                        "method": method,
                    })

        # Search Wire Codes
        if "wire_type" in criteria:
            search_val = criteria["wire_type"].upper()
            for code, wire_type in WIRE_CODES.items():
                if search_val in wire_type.upper():
                    results.append({
                        "type": "wire_code",
                        "code": code,
                        "wire_type": wire_type,
                    })

        # Search Compound Codes
        if "compound" in criteria:
            search_val = criteria["compound"].upper()
            for code, name in COMPOUND_CODES.items():
                if search_val in code.upper() or search_val in name.upper():
                    results.append({
                        "type": "compound_code",
                        "code": code,
                        "name": name,
                    })

        # Search Vendor Codes
        if "vendor" in criteria:
            search_val = criteria["vendor"].upper()
            for code, info in VENDOR_CODES.items():
                if (search_val in code.upper()
                        or search_val in info["name"].upper()
                        or search_val in info["note"].upper()):
                    results.append({
                        "type": "vendor_code",
                        "code": code,
                        "name": info["name"],
                        "note": info["note"],
                    })

        return results

    def to_summary(self, parsed: Dict[str, Any]) -> str:
        """
        Convert a parsed result to a one-line human-readable summary.

        Args:
            parsed: The result dictionary from parse().

        Returns:
            A human-readable summary string.

        Examples:
            >>> parser = PkgCodeParser()
            >>> r = parser.parse("SOTU20-C-EP-CU-1702-7")
            >>> print(parser.to_summary(r))
            SOTU20-C-EP-CU-1702-7: SOT-23/SOT-323/SOT-23 5L/6L | Cu LF | Epoxy D/A | Cu wires | CEL-1702HF9 | PANJIT_MBU1
        """
        pkg = parsed.get("package", {}).get("packages", "?")
        lf = parsed.get("lead_frame", {}).get("material", "?")
        da = parsed.get("die_attach", {}).get("method", "?")
        wire = parsed.get("wire", {}).get("type", "?")
        compound = parsed.get("compound", {}).get("name", "?")
        vendor = parsed.get("vendor", {}).get("name", "?")

        return (
            f"{parsed.get('raw_code', '?')}: "
            f"{pkg} | {lf} LF | {da} D/A | {wire} | {compound} | {vendor}"
        )


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_DEFAULT_PARSER = PkgCodeParser()


def parse(code_str: str) -> Dict[str, Any]:
    """Parse a single Full_PKG_CODE string. Convenience wrapper."""
    return _DEFAULT_PARSER.parse(code_str)


def parse_batch(code_list: List[str]) -> List[Dict[str, Any]]:
    """Parse a batch of Full_PKG_CODE strings. Convenience wrapper."""
    return _DEFAULT_PARSER.parse_batch(code_list)


def validate(code_str: str) -> Tuple[bool, List[str]]:
    """Validate a Full_PKG_CODE string. Convenience wrapper."""
    return _DEFAULT_PARSER.validate(code_str)


def compare(code1: str, code2: str) -> Dict[str, Any]:
    """Compare two Full_PKG_CODE strings. Convenience wrapper."""
    return _DEFAULT_PARSER.compare(code1, code2)


def search(criteria: Dict[str, str]) -> List[Dict[str, Any]]:
    """Search known package codes by criteria. Convenience wrapper."""
    return _DEFAULT_PARSER.search(criteria)


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    import json

    parser = PkgCodeParser()

    print("=" * 70)
    print("PANJIT Full_PKG_CODE Parser -- Self Test")
    print("=" * 70)

    # --- Test 1: Parse various codes ---
    test_codes = [
        "SOTU20-C-EP-CU-1702-P",
        "SODU00-A-EU-AU-500C-7",
        "DF5060-C-SS-CU-9240-E",
        "DFN050-C-EP-AU-G600-T",
        "TO0252-C-SS-CA-9240-E",
        "SMAF00-C-SS-CJ-9240-7",
        "SOT223-C-EP-CU-1702-T",
        "SOTU20-C-EP-CU-1702-7",
        "DO0218-C-SS-AC-9240-6",
        "SMBF00-B-SS-CJ-G660-5",
    ]

    print("\n--- Test 1: Parse ---")
    for code in test_codes:
        result = parser.parse(code)
        summary = parser.to_summary(result)
        status = "OK" if result["_success"] else "WARN"
        errors = f"  errors: {result['_errors']}" if result["_errors"] else ""
        print(f"  [{status}] {summary}{errors}")

    # --- Test 2: Detailed parse ---
    print("\n--- Test 2: Detailed parse (SOTU20-C-EP-CU-1702-7) ---")
    detail = parser.parse("SOTU20-C-EP-CU-1702-7")
    # Print without _errors for cleanliness
    detail_clean = {k: v for k, v in detail.items() if k != "_errors" or v}
    print(json.dumps(detail_clean, indent=2, ensure_ascii=False))

    # --- Test 3: Validate ---
    print("\n--- Test 3: Validate ---")
    valid_codes = [
        "SOTU20-C-EP-CU-1702-7",
        "DF5060-C-SS-CU-9240-E",
    ]
    invalid_codes = [
        "BADFORMAT",
        "SOTU20-Z-EP-CU-1702-7",  # bad LF code
        "SOTU20-C-EP-CU-XXXX-7",  # bad compound
    ]
    for code in valid_codes + invalid_codes:
        is_valid, errors = parser.validate(code)
        status = "VALID" if is_valid else "INVALID"
        print(f"  [{status}] {code}")
        if errors:
            for e in errors:
                print(f"          - {e}")

    # --- Test 4: Compare ---
    print("\n--- Test 4: Compare ---")
    diff = parser.compare("SOTU20-C-EP-CU-1702-7", "SOTU20-C-EP-AU-1702-E")
    print(f"  Code 1: {diff['code1']}")
    print(f"  Code 2: {diff['code2']}")
    print(f"  Same: {diff['same']}")
    if diff["differences"]:
        print(f"  Differences ({len(diff['differences'])}):")
        for d in diff["differences"]:
            print(
                f"    {d['segment']}: "
                f"{d['code1_code']}({d['code1_desc']}) "
                f"-> {d['code2_code']}({d['code2_desc']})"
            )

    # --- Test 5: Search ---
    print("\n--- Test 5: Search ---")

    print("  Search: SOT packages")
    results = parser.search({"series": "SOT"})
    for r in results:
        print(f"    {r['code']}: {r['detail'].get('packages', '')}")

    print("  Search: Cu wire codes")
    results = parser.search({"wire_type": "Cu"})
    for r in results:
        print(f"    {r['code']}: {r['wire_type']}")

    print("  Search: PANJIT vendors")
    results = parser.search({"vendor": "PANJIT"})
    for r in results:
        print(f"    {r['code']}: {r['name']} ({r['note']})")

    # --- Test 6: Edge cases ---
    print("\n--- Test 6: Edge cases ---")
    edge_cases = [
        "",                        # empty
        "SOTU20",                 # incomplete (1 segment)
        "SOTU20-C-EP-CU-1702",   # 5 segments
        "SOTU20-C-EP-CU-1702-7-EXTRA",  # 7 segments
        "sotu20-c-ep-cu-1702-7", # lowercase
    ]
    for code in edge_cases:
        result = parser.parse(code)
        status = "OK" if result["_success"] else "FAIL"
        errors = result["_errors"]
        print(f"  [{status}] '{code}' -> {errors}")

    print("\n" + "=" * 70)
    print("Self-test complete.")
