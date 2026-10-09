# AI PPT Workflow

面向科研、医学和技术汇报的可复现 PPT 制作工作流，目标是同时解决三件事：

1. 先建立可信的主题、叙事和素材清单；
2. 在整页视觉稿与原生 PowerPoint 对象之间做可控的混合重建；
3. 在交付前强制检查文字可编辑性、备注、页数契约和视觉一致性。

项目包含一个 DeepSeek Harness `dsh-plugin`，以及可脱离 Harness 使用的 Python/PPT 工具层。它不是一个“把整页图片塞进 PPT”的脚本：可读前景文字会尽量还原为原生文本框，简单几何会按页面决策恢复为形状，复杂医学图像则保留为独立图片资产并记录来源。

## 项目结构

```text
src/
  dsh-ppt-workflow/          # DeepSeek Harness bundle，注册 ppt_workflow 工具
  ppt_tool/                  # editppt 运行时、图片转可编辑 PPT、素材和页面工具
  visual_fidelity_gate.py    # 逐页源图/预览视觉门控
docs/                        # 工作流、质量评分、人工介入和工具边界
examples/                    # 最小配置和页面任务示例
scripts/                     # 项目级验证脚本
```

## 快速开始

### 1. 安装 Python 依赖

建议使用 Python 3.11 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r src/ppt_tool/requirements.txt
```

如果要运行视觉门控，还需要：

```powershell
python -m pip install opencv-python numpy
```

### 2. 准备图片/PDF/PPTX 输入

```powershell
python src/ppt_tool/image-to-editable-ppt/cli/editppt/cli.py prepare input.pptx `
  --out-root runs `
  --image-backend builtin-imagegen
```

`prepare` 会建立逐页任务、页面源图、文本提示、备注清单和 manifest。页面重建遵循 `src/ppt_tool/image-to-editable-ppt/SKILL.md` 与 `references/` 中的契约。

### 3. 交付前运行双重 QA

结构校验：

```powershell
python src/ppt_tool/image-to-editable-ppt/cli/editppt/runtime/validate_pptx.py `
  runs/<run>/final/deck.pptx `
  --deck-manifest runs/<run>/deck_manifest.json `
  --report runs/<run>/final/validation.json
```

视觉门控：

```powershell
python src/visual_fidelity_gate.py `
  --run runs/<run> `
  --report runs/<run>/final/visual_fidelity_gate.json
```

只有两个报告都包含 `passed: true` 且失败页为空时才允许交付。

## DeepSeek Harness 插件

插件目录：`src/dsh-ppt-workflow`。

在 DeepSeek Harness 源码环境中加载：

```powershell
pnpm dsh web --patch D:\path\to\AI-PPT-Workflow\src\dsh-ppt-workflow\cordis.patch.yml
```

插件注册 `ppt_workflow` 工具，支持：

- `doctor`：检查运行时和 v6 工具链；
- `inspect`：统计页数、备注、原生文本框和图片；
- `prepare`：创建 `editppt` 逐页运行；
- `validate`：检查 PPTX 与 manifest、备注和页数契约；
- `visual_gate`：运行像素级文字视觉门控，并可检查 PPTX/manifest 页数漂移；
- `run_v6`：运行当前 MPS 示例的历史重建脚本（仅用于兼容性复现）。

工具根目录默认是 `<workspace>\\v6`。发布项目中建议显式设置：

```powershell
$env:DSH_PPT_WORKSPACE = 'D:\PPT制作Agent'
$env:DSH_PPT_TOOL_ROOT = 'D:\PPT制作Agent\v6'
$env:DSH_PPT_PYTHON = 'python'
```

插件包不会携带任何 API key。AtlasCloud、OpenAI、PaddleOCR 等服务必须通过运行时环境或本机 `editppt` 配置注入。

## 推荐生产流程

`输入清点 → 主题/叙事确认 → 素材和版权清单 → 风格样张 → 页面任务 → 生成/重建 → 备注 → 结构 QA → 视觉门控 → 人工浏览 → 交付`

人工确认不能省略：大纲与页数、医学/科研结论、外部素材版权、OCR 争议文字、复杂图片是否保留为 raster，以及最终投影可读性都需要人审。

## 已知边界

- 复杂插图、CT、气道树、照片和图标不会被虚假宣称为可编辑矢量；
- 图片转 PPT 不能可靠恢复所有动画、视频、复杂图表和逐帧结构；
- 原生 PPTX 已含文本和形状时，应优先直接编辑原生对象，不要先栅格化再 OCR；
- `validate` 会拒绝 PPTX 页数与 `deck_manifest.page_count` 不一致的产物；
- 生图模型只用于概念视觉和背景，不用于篡改真实医学证据或数据图。

## 安全与隐私

不要将 API key、患者数据、未公开论文、原始 CT 或带个人信息的 PPTX 提交到 Git。仓库 `.gitignore` 默认排除运行目录、媒体、PPTX、DOCX、token 配置和缓存。外部 OCR/生图服务前应确认数据合规和版权授权。

## 许可证

本项目代码采用 MIT License。第三方组件和参考项目的许可边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
