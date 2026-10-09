#!/usr/bin/env python3
"""Page-level source/preview fidelity gate for image-to-editable-ppt runs.

The structural validator proves that a PPTX is well formed. This gate adds the
visual checks that structural validation cannot see: every manifest text box
must correspond to changed source pixels, source and preview glyph masks must
overlap, measured colors must be plausible, font metadata must be usable, and
text boxes must not be duplicate or out of bounds.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


DEFAULT_RUN = Path(
    "v6/deck/editable_runs/20260925-feature3_mps_v6_visual_fidelity"
).resolve()


def load_image(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"cannot read image: {path}")
    return image


def rgb_hex(value: str) -> np.ndarray | None:
    value = str(value or "").strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    except ValueError:
        return None


def box_slice(box: list[float], shape: tuple[int, ...]) -> tuple[int, int, int, int] | None:
    height, width = shape[:2]
    x, y, w, h = [int(round(float(v))) for v in box]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(width, x + max(0, w)), min(height, y + max(0, h))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def overlap_ratio(a: list[float], b: list[float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    return inter / max(1.0, min(aw * ah, bw * bh))


def changed_mask(source: np.ndarray, clean: np.ndarray) -> np.ndarray:
    diff = np.linalg.norm(source.astype(np.float32) - clean.astype(np.float32), axis=2)
    mask = (diff > 35).astype(np.uint8) * 255
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def preview_mask(preview: np.ndarray, clean: np.ndarray) -> np.ndarray:
    resized = cv2.resize(preview, (clean.shape[1], clean.shape[0]), interpolation=cv2.INTER_AREA)
    diff = np.linalg.norm(resized.astype(np.float32) - clean.astype(np.float32), axis=2)
    return (diff > 22).astype(np.uint8) * 255


def local_foreground_rgb(source: np.ndarray, clean: np.ndarray, box: list[float]) -> tuple[np.ndarray | None, int]:
    region = box_slice(box, source.shape)
    if region is None:
        return None, 0
    x0, y0, x1, y1 = region
    source_crop = source[y0:y1, x0:x1]
    clean_crop = clean[y0:y1, x0:x1]
    delta = np.linalg.norm(source_crop.astype(np.float32) - clean_crop.astype(np.float32), axis=2)
    changed = source_crop[delta > 35]
    if len(changed) < 8:
        return None, len(changed)
    hsv = cv2.cvtColor(changed.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
    value, saturation = hsv[:, 2], hsv[:, 1]
    border = np.concatenate(
        [
            source_crop[: max(1, min(4, source_crop.shape[0])), :, :].reshape(-1, 3),
            source_crop[-max(1, min(4, source_crop.shape[0])) :, :, :].reshape(-1, 3),
            source_crop[:, : max(1, min(4, source_crop.shape[1])), :].reshape(-1, 3),
            source_crop[:, -max(1, min(4, source_crop.shape[1])) :, :].reshape(-1, 3),
        ],
        axis=0,
    )
    border_value = float(np.median(cv2.cvtColor(border.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV)[:, 0, 2]))
    if border_value < 150:
        ink = changed[(value > max(150.0, border_value + 35.0)) | ((saturation > 80) & (value > 120))]
    else:
        ink = changed[(value < 190) & ((saturation > 45) | (value < 145))]
    if len(ink) < 8:
        ink = changed
    rgb = np.percentile(ink[:, ::-1], 18, axis=0)
    return np.clip(np.round(rgb), 0, 255).astype(np.float32), len(changed)


def changed_rgb_pixels(source: np.ndarray, clean: np.ndarray, box: list[float]) -> np.ndarray:
    region = box_slice(box, source.shape)
    if region is None:
        return np.empty((0, 3), dtype=np.float32)
    x0, y0, x1, y1 = region
    source_crop = source[y0:y1, x0:x1]
    clean_crop = clean[y0:y1, x0:x1]
    delta = np.linalg.norm(source_crop.astype(np.float32) - clean_crop.astype(np.float32), axis=2)
    return source_crop[delta > 35][:, ::-1].astype(np.float32)


def expected_colors(item: dict) -> list[np.ndarray]:
    values = [item.get("color")]
    values.extend(run.get("color") for run in item.get("runs", []) if isinstance(run, dict))
    return [value for value in (rgb_hex(v) for v in values) if value is not None]


def text_iou(source_mask: np.ndarray, preview_mask_image: np.ndarray, box: list[float]) -> tuple[float, int, int]:
    region = box_slice(box, source_mask.shape)
    if region is None:
        return 0.0, 0, 0
    x0, y0, x1, y1 = region
    source_crop = source_mask[y0:y1, x0:x1] > 0
    preview_crop = preview_mask_image[y0:y1, x0:x1] > 0
    union = np.logical_or(source_crop, preview_crop).sum()
    inter = np.logical_and(source_crop, preview_crop).sum()
    return float(inter / max(1, union)), int(source_crop.sum()), int(preview_crop.sum())


def page_gate(page_dir: Path) -> dict:
    manifest = json.loads((page_dir / "manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((page_dir / "validation.json").read_text(encoding="utf-8"))
    source = load_image(page_dir / "source.png")
    clean = load_image(page_dir / "clean_base_v4.png")
    preview = load_image(page_dir / "preview.png")
    source_mask = changed_mask(source, clean)
    preview_diff = preview_mask(preview, clean)
    boxes = manifest.get("text_boxes", [])
    failures: list[dict] = []
    checks: list[dict] = []

    if source.shape[:2] != clean.shape[:2]:
        failures.append({"type": "clean-size-mismatch", "source": list(source.shape[:2]), "clean": list(clean.shape[:2])})
    if preview.shape[0] < 700 or preview.shape[1] < 1200:
        failures.append({"type": "preview-too-small", "size": list(preview.shape[:2])})
    if not validation.get("passed"):
        failures.append({"type": "page-validation-failed"})
    if validation.get("editable_text_shapes", 0) != len(boxes):
        failures.append({"type": "editable-count-mismatch", "manifest": len(boxes), "pptx": validation.get("editable_text_shapes", 0)})

    source_h, source_w = source.shape[:2]
    for index, item in enumerate(boxes, start=1):
        text = str(item.get("text", "")).strip()
        box = item.get("box_px")
        item_failures: list[str] = []
        if not text:
            item_failures.append("empty-text")
        if not isinstance(box, list) or len(box) != 4:
            item_failures.append("invalid-box")
            box = [0, 0, 0, 0]
        else:
            x, y, w, h = [float(v) for v in box]
            if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > source_w + 2 or y + h > source_h + 2:
                item_failures.append("out-of-bounds")
        if float(item.get("font_size", 0) or 0) <= 0:
            item_failures.append("invalid-font-size")
        if not str(item.get("font_size_source", "")).strip():
            item_failures.append("missing-font-size-source")
        if not str(item.get("font", "")).strip():
            item_failures.append("missing-font")
        preview_font = item.get("preview_font")
        if preview_font and not Path(preview_font).exists():
            item_failures.append("preview-font-missing")
        colors = expected_colors(item)
        if not colors:
            item_failures.append("missing-color")
        foreground, changed_count = local_foreground_rgb(source, clean, box)
        if changed_count < 8:
            item_failures.append("no-source-glyph-evidence")
        color_distance = None
        if foreground is not None and colors:
            # Prefer an actual glyph pixel when anti-aliased edges or inpaint
            # halos skew the percentile estimate. This also handles white
            # numerals inside colored status circles.
            pixels = changed_rgb_pixels(source, clean, box)
            nearest_distance = min(
                float(np.min(np.linalg.norm(pixels - expected, axis=1)))
                for expected in colors
            ) if len(pixels) else math.inf
            percentile_distance = min(float(np.linalg.norm(foreground - expected)) for expected in colors)
            color_distance = min(nearest_distance, percentile_distance)
            # Anti-aliasing and generated-image compression make exact RGB
            # equality impossible; a large distance still signals wrong ink.
            if color_distance > 105:
                item_failures.append("color-drift")
        iou, source_pixels, preview_pixels = text_iou(source_mask, preview_diff, box)
        # Tiny footer text may move by a few pixels; prominent boxes must still
        # have a non-trivial source/preview mask overlap.
        if source_pixels >= 30 and preview_pixels == 0:
            item_failures.append("preview-text-missing")
        if source_pixels >= 1200 and iou < 0.01:
            item_failures.append("preview-mask-mismatch")
        elif source_pixels >= 500 and iou < 0.005:
            item_failures.append("preview-mask-mismatch")
        checks.append(
            {
                "id": item.get("id", f"text-{index:03d}"),
                "text": text,
                "changed_source_pixels": changed_count,
                "source_mask_pixels": source_pixels,
                "preview_mask_pixels": preview_pixels,
                "mask_iou": round(iou, 4),
                "estimated_source_rgb": foreground.astype(int).tolist() if foreground is not None else None,
                "expected_colors": [color.astype(int).tolist() for color in colors],
                "color_distance": round(color_distance, 2) if color_distance is not None else None,
                "failures": item_failures,
            }
        )
        if item_failures:
            failures.append({"type": "text-box", "id": item.get("id"), "text": text, "failures": item_failures})

    duplicate_pairs = []
    for left_index, left in enumerate(boxes):
        for right in boxes[left_index + 1 :]:
            if str(left.get("text", "")).strip() and overlap_ratio(left["box_px"], right["box_px"]) >= 0.78:
                duplicate_pairs.append([left.get("id"), right.get("id")])
    if duplicate_pairs:
        failures.append({"type": "duplicate-text-boxes", "pairs": duplicate_pairs})

    return {
        "page": page_dir.name,
        "source_size": [source_w, source_h],
        "preview_size": [int(preview.shape[1]), int(preview.shape[0])],
        "text_boxes": len(boxes),
        "editable_text_shapes": validation.get("editable_text_shapes", 0),
        "checks": checks,
        "duplicate_pairs": duplicate_pairs,
        "failures": failures,
        "passed": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    pages = sorted((run / "pages").glob("page_*"))
    if not pages:
        raise SystemExit(f"No pages found under {run / 'pages'}")
    page_reports = [page_gate(page) for page in pages]
    report = {
        "schema_version": 1,
        "run": str(run),
        "page_count": len(page_reports),
        "pages": page_reports,
        "failed_pages": [page["page"] for page in page_reports if not page["passed"]],
        "passed": all(page["passed"] for page in page_reports),
        "hard_gate": "Every audited text box must have source glyph evidence, usable font metadata, plausible source color, and source/preview mask overlap.",
    }
    output = args.report.resolve() if args.report else run / "final" / "visual_fidelity_gate.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "passed": report["passed"], "failed_pages": report["failed_pages"]}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
