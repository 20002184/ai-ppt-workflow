---
name: dsh-ppt-workflow
description: Build high-quality Chinese academic PowerPoint decks from documents, papers, slide images, or existing PPTX files using staged story design, asset provenance, native text reconstruction, speaker notes, and hard visual-fidelity gates.
---

# DSH PPT Workflow

This plugin turns the repository's v6 process into a DeepSeek Harness capability. The model should treat a deck as a reproducible build, not a single image-generation call.

## Required stages

1. **Brief and story**: identify audience, decision, claim hierarchy, page count, visual language, and human approval points. Save the outline and page contracts.
2. **Material inventory**: record source documents, figures, images, citations, licenses, and generated asset prompts. Do not invent scientific results.
3. **Build**: create page-local tasks. Use image generation only for visual assets; keep readable foreground text out of generated raster backgrounds when it must be editable.
4. **Editable reconstruction**: use `image-to-editable-ppt` page manifests. Readable text becomes native text boxes; simple geometry can become native PowerPoint shapes; complex medical imagery remains an independent image asset.
5. **Notes**: preserve or write speaker notes for every page.
6. **Gates**: run structural validation and `visual_fidelity_gate.py`. Both must pass before delivery.

## Hard visual gate

For every readable text object compare source and preview pixels. Preserve the measured source box, glyph height, font family, weight, color, alignment, line spacing, and mixed-style hierarchy. Never let automatic fitting silently reduce a measured size. Split formulas, status labels, metric cards, and mixed-color phrases into native runs or separate text boxes.

## Human intervention

The model may automate extraction, layout proposals, asset generation, reconstruction, and deterministic QA. A human must approve the story direction, externally sourced or generated scientific visuals, ambiguous OCR/text boxes, claims that affect medical interpretation, and the final side-by-side visual review.

## Tool entry point

Use the registered `ppt_workflow` tool with one of these actions:

- `doctor`: verify the workspace and v6 toolchain.
- `inspect`: count slides, notes, native text shapes, and pictures in an existing PPTX.
- `prepare`: normalize an input into an `editppt` run directory.
- `validate`: run deterministic PPTX/manifest validation.
- `visual_gate`: compare source, cleaned background, and preview for every audited text box; when `pptx` is supplied, also reject PPTX/manifest page-count drift.
- `run_v6`: run the repository's v6 reconstruction script when working with the current MPS deck.

The tool never accepts or stores API keys. Configure image/OCR providers through the runtime environment or the local `editppt` configuration.
