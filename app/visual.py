"""Minimal visual compliance checker (no AI needed, works offline).

Checks an uploaded image + its alt text and returns findings in the same shape
as the text pipeline, so the evidence validator, decisions, approvals and the
dashboard all work unchanged.

Rule IDs (must exist in the `rules` table - see schema_round3.sql):
  AC-001  image has alt text                (already in Round 2 rules)
  AC-002  alt text is meaningful            (new)
  AC-003  text/background contrast >= 4.5:1 (new)
  VC-001  dominant colours match brand palette (new)
"""
from __future__ import annotations

import io
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
GENERIC_ALT = {"image", "photo", "picture", "banner", "poster", "graphic", "img", "logo", "pic", "screenshot"}
_PALETTE_PATH = os.path.join(os.path.dirname(__file__), "brand_palette.json")


class VisualError(ValueError):
    """Raised for bad uploads; the message is safe to show the user."""


def load_palette() -> Dict[str, Any]:
    with open(_PALETTE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _hex(rgb: Tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def _from_hex(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lin(c: int) -> float:
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _distance(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _is_neutral(rgb) -> bool:
    return max(rgb) - min(rgb) < 28  # black, white and greys are always allowed


def dominant_colours(img: Image.Image, n: int = 8) -> List[Dict[str, Any]]:
    small = img.convert("RGB").resize((160, 160))
    q = small.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    total = 160 * 160
    out = []
    for count, idx in sorted(q.getcolors(), reverse=True):
        rgb = (pal[idx * 3], pal[idx * 3 + 1], pal[idx * 3 + 2])
        out.append({"rgb": rgb, "hex": _hex(rgb), "share": round(100.0 * count / total, 1)})
    return out


def check_alt_text(alt: str) -> Optional[Dict[str, Any]]:
    alt = (alt or "").strip()
    if not alt:
        return {
            "rule": "AC-001", "severity": "medium", "category": "accessibility", "confidence": 0.99,
            "excerpt": "(no alt text provided)",
            "explanation": "The image has no alt text, so screen-reader users cannot understand it.",
            "fix_1": "Add a short description, e.g. \"AstraPay app showing a UPI payment confirmation screen\".",
            "fix_2": "If the image is purely decorative, mark it decorative and say so in the post notes.",
        }
    words = re.findall(r"[A-Za-z0-9']+", alt)
    looks_like_file = bool(re.search(r"\.(png|jpe?g|webp|gif)$", alt, re.I)) or bool(re.fullmatch(r"(img|image|dsc|screenshot)[-_ ]?\d+", alt, re.I))
    if len(alt) < 12 or len(words) < 3 or alt.lower() in GENERIC_ALT or looks_like_file:
        return {
            "rule": "AC-002", "severity": "low", "category": "accessibility", "confidence": 0.9,
            "excerpt": alt[:200],
            "explanation": "The alt text is too short or generic to describe what the image shows or why it is there.",
            "fix_1": "Describe the content and purpose in one sentence of at least 5 words.",
            "fix_2": "Include any text that appears inside the image, e.g. the offer line or headline.",
        }
    return None


def check_contrast(colours: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
    """Best-case contrast between the main background and any other significant colour."""
    if len(colours) < 2:
        return None, None
    bg = colours[0]
    fg = [c for c in colours[1:] if c["share"] >= 1.0]
    if not fg:
        return None, None
    best = max(fg, key=lambda c: contrast_ratio(bg["rgb"], c["rgb"]))
    ratio = round(contrast_ratio(bg["rgb"], best["rgb"]), 2)
    if ratio >= 4.5:
        return None, ratio
    return {
        "rule": "AC-003", "severity": "medium", "category": "accessibility", "confidence": 0.7,
        "needs_human": True,
        "excerpt": f"Background {bg['hex']} vs strongest foreground {best['hex']}: {ratio}:1",
        "explanation": f"Even the strongest foreground colour in the image has only {ratio}:1 contrast against the background; WCAG 2.2 requires 4.5:1 for normal text. This is estimated from dominant colours, so please confirm by eye.",
        "fix_1": "Darken the text or lighten the background until text reaches at least 4.5:1 contrast.",
        "fix_2": "Place text on a solid brand-colour panel (e.g. white text on AstraPay Green) instead of on the busy area.",
    }, ratio


def check_brand_colours(colours: List[Dict[str, Any]], palette: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    brand = {name: _from_hex(h) for name, h in palette["colours"].items()}
    limit = float(palette.get("max_distance", 70))
    min_share = float(palette.get("min_share_percent", 10))
    off = []
    for c in colours:
        if c["share"] < min_share or _is_neutral(c["rgb"]):
            continue
        name, dist = min(((n, _distance(c["rgb"], rgb)) for n, rgb in brand.items()), key=lambda t: t[1])
        if dist > limit:
            off.append((c, name, round(dist)))
    if not off:
        return None
    c, name, _ = max(off, key=lambda t: t[0]["share"])
    return {
        "rule": "VC-001", "severity": "medium", "category": "visual_brand", "confidence": 0.8,
        "excerpt": f"{c['hex']} covers {c['share']}% of the image",
        "explanation": f"A large part of the image uses {c['hex']}, which is not close to any approved brand colour (nearest: {name}).",
        "fix_1": f"Recolour the dominant area using {name} ({palette['colours'][name]}) or another approved brand colour.",
        "fix_2": "Keep the photo but add a brand-colour frame or overlay so brand colours lead the design.",
    }


def analyze_image(data: bytes, alt_text: str, palette: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Returns {'findings': [...], 'metrics': {...}}. Raises VisualError for unusable files."""
    if not data:
        raise VisualError("Please choose an image file.")
    if len(data) > MAX_BYTES:
        raise VisualError("Image is too large (max 5 MB).")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            raise VisualError("Only PNG, JPEG or WebP images are supported.")
        img.load()
    except VisualError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise VisualError("That file could not be read as an image.")
    palette = palette or load_palette()
    colours = dominant_colours(img)

    findings: List[Dict[str, Any]] = []
    alt = check_alt_text(alt_text)
    if alt:
        findings.append(alt)
    contrast, ratio = check_contrast(colours)
    if contrast:
        findings.append(contrast)
    brand = check_brand_colours(colours, palette)
    if brand:
        findings.append(brand)

    metrics = {
        "format": fmt, "width": img.width, "height": img.height,
        "dominant_colours": [{"hex": c["hex"], "share": c["share"]} for c in colours[:5]],
        "best_contrast": ratio,
    }
    return {"findings": findings, "metrics": metrics}


def describe_for_record(filename: str, alt_text: str, metrics: Dict[str, Any]) -> str:
    """Text stored as the submission 'body' so the normal history/approval screens work."""
    cols = ", ".join(f"{c['hex']} ({c['share']}%)" for c in metrics["dominant_colours"][:3])
    return (f"[IMAGE ASSET] {filename[:80]} - {metrics['width']}x{metrics['height']} {metrics['format']}\n"
            f"Alt text: {alt_text.strip() or '(none)'}\n"
            f"Dominant colours: {cols}\n"
            f"Best contrast estimate: {metrics['best_contrast']}")
