#!/usr/bin/env python3
"""Small DSH-facing adapter around the repository's v6 PPT toolchain."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok", True) else 1


def run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def parse_json_output(text: str) -> dict:
    """Parse a pretty-printed JSON object emitted by a validation command."""
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(text[start : end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    return {"stdout": text}


def inspect_pptx(pptx: Path) -> dict:
    slides = []
    with zipfile.ZipFile(pptx) as archive:
        names = sorted(
            (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
            key=lambda name: int(re.search(r"slide(\d+)", name).group(1)),
        )
        for name in names:
            root = ET.fromstring(archive.read(name))
            texts = [
                "".join(node.text or "" for node in shape.findall(".//a:t", NS)).strip()
                for shape in root.findall(".//p:sp", NS)
            ]
            slides.append({
                "slide": name,
                "native_text_shapes": sum(bool(text) for text in texts),
                "pictures": len(root.findall(".//p:pic", NS)),
            })
        notes = len([name for name in archive.namelist() if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml")])
    return {"slides": len(slides), "notes": notes, "native_text_shapes": sum(item["native_text_shapes"] for item in slides), "pictures": sum(item["pictures"] for item in slides), "per_slide": slides}


def resolve(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    workspace = Path(args.workspace).resolve()
    tool_root = Path(args.tool_root).resolve()
    cli = tool_root / "ppt_tool" / "image-to-editable-ppt" / "cli" / "editppt" / "cli.py"
    validate = tool_root / "ppt_tool" / "image-to-editable-ppt" / "cli" / "editppt" / "runtime" / "validate_pptx.py"
    gate = tool_root / "visual_fidelity_gate.py"
    for required in (cli, validate, gate):
        if not required.exists():
            raise FileNotFoundError(f"Missing v6 toolchain file: {required}")
    return workspace, cli, validate, gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=["doctor", "inspect", "prepare", "validate", "visual_gate", "run_v6"])
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--tool-root", required=True)
    parser.add_argument("--input")
    parser.add_argument("--pptx")
    parser.add_argument("--run-dir")
    parser.add_argument("--deck-manifest")
    parser.add_argument("--report")
    parser.add_argument("--backend", default="builtin-imagegen")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()

    try:
        workspace, cli, validate, gate = resolve(args)
        python = sys.executable
        if args.action == "doctor":
            return emit({"ok": True, "workspace": str(workspace), "tool_root": str(Path(args.tool_root).resolve()), "python": python, "cli": str(cli), "gate": str(gate)})
        if args.action == "inspect":
            target = Path(args.input or args.pptx).resolve()
            if not target.exists():
                return emit({"ok": False, "error": f"Input not found: {target}"})
            return emit({"ok": True, "input": str(target), **inspect_pptx(target)})
        if args.action == "prepare":
            target = Path(args.input).resolve()
            if not target.exists():
                return emit({"ok": False, "error": f"Input not found: {target}"})
            code, stdout, stderr = run([python, str(cli), "prepare", str(target), "--image-backend", args.backend], workspace)
            return emit({"ok": code == 0, "command": "prepare", "exit_code": code, "stdout": stdout[-12000:], "stderr": stderr[-12000:]})
        if args.action == "validate":
            pptx = Path(args.pptx).resolve()
            report = Path(args.report).resolve() if args.report else None
            cmd = [python, str(validate), str(pptx)]
            if args.deck_manifest:
                cmd += ["--deck-manifest", str(Path(args.deck_manifest).resolve())]
            if report:
                cmd += ["--report", str(report)]
            code, stdout, stderr = run(cmd, workspace)
            payload = parse_json_output(stdout)
            return emit({"ok": code == 0 and payload.get("passed", False), "command": "validate", "result": payload, "stderr": stderr[-12000:]})
        if args.action == "visual_gate":
            run_dir = Path(args.run_dir).resolve()
            report = Path(args.report).resolve() if args.report else run_dir / "final" / "visual_fidelity_gate.json"
            if args.pptx:
                pptx = Path(args.pptx).resolve()
                manifest_path = run_dir / "deck_manifest.json"
                manifest_pages = None
                if manifest_path.exists():
                    manifest_pages = json.loads(manifest_path.read_text(encoding="utf-8")).get("page_count")
                actual_pages = inspect_pptx(pptx).get("slides") if pptx.exists() else None
                if manifest_pages is not None and actual_pages != manifest_pages:
                    drift = {
                        "ok": False,
                        "command": "visual_gate",
                        "artifact_drift": {
                            "pptx": str(pptx),
                            "manifest_page_count": manifest_pages,
                            "pptx_slide_count": actual_pages,
                        },
                        "error": "PPTX slide count does not match deck_manifest.page_count; rebuild or re-record pages before visual QA.",
                    }
                    report.parent.mkdir(parents=True, exist_ok=True)
                    report.write_text(json.dumps(drift, ensure_ascii=False, indent=2), encoding="utf-8")
                    return emit(drift)
            code, stdout, stderr = run([python, str(gate), "--run", str(run_dir), "--report", str(report)], workspace)
            payload = parse_json_output(stdout)
            return emit({"ok": code == 0 and payload.get("passed", False), "command": "visual_gate", "result": payload, "stderr": stderr[-12000:]})
        if args.action == "run_v6":
            script = Path(args.tool_root).resolve() / "rebuild_v6_textcomplete.py"
            code, stdout, stderr = run([python, str(script)], workspace)
            return emit({"ok": code == 0, "command": "run_v6", "exit_code": code, "stdout": stdout[-12000:], "stderr": stderr[-12000:]})
    except Exception as exc:
        return emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return emit({"ok": False, "error": "unreachable action"})


if __name__ == "__main__":
    raise SystemExit(main())
