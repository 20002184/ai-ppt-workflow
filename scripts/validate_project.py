from __future__ import annotations

import json
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    package = json.loads((ROOT / "src/dsh-ppt-workflow/package.json").read_text(encoding="utf-8"))
    assert package["dsh"]["bundle"]["patch"] == "./cordis.patch.yml"
    assert (ROOT / "src/dsh-ppt-workflow/cordis.patch.yml").exists()
    assert (ROOT / "src/dsh-ppt-workflow/index.js").exists()
    assert (ROOT / "src/ppt_tool/image-to-editable-ppt/SKILL.md").exists()
    assert (ROOT / "src/visual_fidelity_gate.py").exists()
    for path in [ROOT / "src/dsh-ppt-workflow/scripts/ppt_pipeline.py", ROOT / "src/visual_fidelity_gate.py"]:
        py_compile.compile(str(path), doraise=True)
    for path in [ROOT / "src/dsh-ppt-workflow/locale/en.json", ROOT / "src/dsh-ppt-workflow/locale/zh.json", ROOT / "examples/page_job.example.json"]:
        json.loads(path.read_text(encoding="utf-8"))
    forbidden = {".pptx", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".mp4"}
    tracked_candidate_media = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in forbidden and ".git" not in p.parts]
    if tracked_candidate_media:
        raise AssertionError(f"Generated or source media found in release tree: {tracked_candidate_media[:3]}")
    print("Project validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
