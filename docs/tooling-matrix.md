# 技能与工具边界

| 能力 | 推荐工具 / skill | 适合 | 不适合 |
|---|---|---|---|
| 内容抽取 | python-docx、PyMuPDF、Markdown parser | Word/PDF/论文结构化 | 代替事实核查 |
| 叙事规划 | GPT + `nature-paper2ppt` | 论点、页序、讲稿 | 自动决定临床结论 |
| 原生 PPTX | python-pptx、PptxGenJS | 可编辑文字、表格、流程、图表 | 复杂艺术版式 |
| 整页视觉 | `codex-ppt` 类图片式流程、imagegen | 封面、概念页、强统一风格 | 需要编辑每个文本框时 |
| 图片转可编辑 | `image-to-editable-ppt` / `editppt` | 从图片版页面恢复文字、简单形状、表格 | 不能保证复杂插画、视频、动画和所有图表可编辑 |
| 图像生成 | `imagegen` 或项目指定图像后端 | 概念插画、背景、非证据视觉 | 真实 CT、数据图、医学证据 |
| 数据图表 | Python matplotlib / seaborn / Plotly | 数值准确、可复现图表 | 需要自由手绘的概念图 |
| 结构图 | PPT 原生形状、SVG、Graphviz | 流程、架构、决策树 | 追求摄影级视觉 |
| 视频动画 | Remotion、Manim、FFmpeg、PPT 动画 | 时序、过程、动态解释 | 需要完全可编辑的逐帧 PPT |
| 预览 | LibreOffice/PowerPoint/WPS、截图 | 投影和字体替换检查 | 只看 PPTX 是否能打开 |
| 状态记录 | JSON + validate scripts | 可复现、可审计 | 只在聊天中口头确认 |

## 当前 v2 的后端策略

本任务不采用“整套页面全部由模型绘制”这一单一策略。对于技术汇报，默认采用混合模式：

- 封面和章节页：图片式或生成性视觉；
- 流程、公式、表格、病例数值：原生可编辑；
- 真实 CT 或论文图：原图插入并标注来源；
- 复杂解释图：先生成视觉草图，再决定是图片还是重绘为 SVG/PPT 原生；
- 动画：单独生成 MP4/GIF，先验证播放，再插入 PPT。

注意：`image-to-editable-ppt` 只能处理图片版输入。若原始 PPTX 已经含有原生文字和形状，应直接编辑原生 PPTX，而不是先送入转换器。

## 需要外部权限的工具

- 第三方生图 API：需要 API key、base URL 和模型配置；
- 外部素材下载：需确认版权和数据合规；
- PowerPoint/WPS GUI：适合人工验收，不应成为唯一自动化依赖；
- 多 agent：适用于逐页独立生成，但不能替代主控状态管理。
