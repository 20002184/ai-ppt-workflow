# dsh-ppt-workflow

一个面向 DeepSeek Harness 的 PPT 制作插件，将现有的高质量学术 PPT 流程封装为模型可调用的 `ppt_workflow` 工具。

## 能力

- `doctor`：检查工作区、Python 和 v6 工具链。
- `inspect`：统计 PPT 页数、备注页、原生文本形状和图片对象。
- `prepare`：调用 `editppt prepare`，生成逐页可编辑重建任务。
- `validate`：校验 PPTX、页面 manifest、备注页和页数契约。
- `visual_gate`：运行逐页源图/清理底图/预览一致性门控。
- `run_v6`：运行当前 MPS 示例的 v6 重建脚本。

## 安装方式

这是 DeepSeek Harness bundle，不是 Codex `.codex-plugin` 包。把本目录作为本地 bundle 安装，或在 Harness 源码环境中使用：

```powershell
pnpm dsh web --patch D:\PPT制作Agent\dsh-ppt-workflow\cordis.patch.yml
```

插件默认从 `<workspace>\v6` 读取现有工具链，也可设置 `DSH_PPT_WORKSPACE`、`DSH_PPT_TOOL_ROOT` 和 `DSH_PPT_PYTHON`。

## 重要边界

插件只编排本地工作流，不在包内携带 AtlasCloud、OpenAI、PaddleOCR 或其他密钥。图像/ OCR 后端仍由 Harness 运行时或 `editppt` 本地配置提供。

`validate` 是硬门：如果 PPTX 已被后续编辑但 `deck_manifest.json` 没有同步，工具必须拒绝交付，而不是“按当前页数猜测通过”。

调用 `visual_gate` 时也建议传入最终 `pptx`；插件会先检查它与 `deck_manifest.page_count` 是否一致，再进入像素级门控。
