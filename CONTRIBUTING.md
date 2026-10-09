# Contributing

1. Keep the core workflow deterministic and recordable.
2. Do not commit API keys, patient data, unpublished source files, generated PPTX files or large media.
3. Any new reconstruction rule must include a structural test and, where visual behavior changes, a source/preview QA fixture that is licensed for redistribution.
4. Preserve the distinction between native editable text, native simple geometry and independent raster assets.
5. Run the local checks before opening a pull request:

```powershell
python scripts/validate_project.py
```

For changes to `image-to-editable-ppt`, also run a real prepared run and both final gates on a local, non-sensitive fixture.
