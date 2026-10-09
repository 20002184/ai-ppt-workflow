# DSH 插件工作流

这个插件将 PPT 制作拆成可复现的阶段：

`主题与叙事 → 素材清单 → 页面任务 → 图像/图表生成 → 可编辑重建 → 备注 → 结构校验 → 视觉门控 → 人工交付确认`

## 本地开发预览

在 DeepSeek Harness 源码仓库中使用：

```powershell
pnpm dsh web --patch D:\PPT制作Agent\dsh-ppt-workflow\cordis.patch.yml
```

插件加载后，模型可以调用 `ppt_workflow`。默认工具根目录是 `<workspace>\v6`，也可以通过 `DSH_PPT_TOOL_ROOT` 或工具参数指定。

## 推荐调用顺序

```text
doctor
inspect(input=...)
prepare(input=..., backend=builtin-imagegen)
页面级重建与人工确认
validate(pptx=..., deck_manifest=...)
visual_gate(run_dir=...)
```

结构校验和视觉门控任何一个失败，都不能交付 PPTX。复杂医学图像可以保留为独立图片，但可读前景文字必须是原生 PowerPoint 文本。

## 产物漂移检查

`validate` 会同时比较 PPTX 页数、`deck_manifest.json` 页数、页面 manifest、备注页和备注哈希。如果 PPTX 被后续编辑成 15 页而 manifest 仍是 13 页，工具会明确返回失败；应先重新 `prepare`/记录页面，不能绕过这个门。

## 配置边界

插件包不携带 AtlasCloud、OpenAI、PaddleOCR 或其他密钥。API 凭据只应通过 Harness 的运行时环境或本机 `editppt` 配置注入。
