# v4 可编辑性审计

## 目标

v4 在 v3 的基础上补齐漏识别文字，并强制执行 `image-to-editable-ppt` 的文字对象规则：所有影响汇报含义的可读文字都必须进入原生 `text_boxes`，不能通过整页 PNG、隐藏文字或透明文字绕过。

## 识别与重建流程

1. 对每页运行 PaddleOCR-VL，保留正文、标题、页眉、页脚、标签、数字和英文行。
2. 与 v3 的提示结果做空间去重，补回 PaddleOCR 漏掉但原页面已有的文字。
3. 第 12 页 OCR 只返回标题，因此按源图逐项建立人工审计清单。
4. 对审计文字区域做局部背景清理，避免原图文字与原生文字重复。
5. 用确定性 manifest builder 生成原生 PowerPoint 文字框。
6. 用页面级验证和 deck-level 验证检查文字覆盖、缺失文字、资产来源和 PPTX 结构。

## 结果

- 页数：13
- 审计文字框：163
- 原生可编辑文字框：163
- 页面级验证：13/13 passed
- deck-level 验证：passed
- 演讲备注：13/13 保留

机器可读明细见：

`deck/editable_runs/20260923-152235-feature3_mps_v4_native_text/v4_text_coverage_audit.json`

## 当前边界

肺部插图、图标、流程节点和装饰性视觉目前保留为图片资产；它们不是文字对象，也没有被伪装成可编辑矢量。下一阶段若要求这些对象也可编辑，需要按参考 skill 的 foreground asset-sheet 流程逐页分离，再将结构性元素分别写入 `shapes`、`tables`、`images` 或公式资产。

## 交付文件

`deck/editable_runs/20260923-152235-feature3_mps_v4_native_text/final/feature3_mps_v4_native_text.pptx`

