# PPT Tool v2

这是基于 `codex-ppt-skill` 改造的本地 PPT 制作工具层。底层保留参考项目的整页图片生成和 `assemble_ppt.py`，上层增加：

- 项目状态和审批闸门；
- 原生 PPTX / 整页图片 / 混合页面路由；
- GPT Image CLI 后端探测；
- 逐页样张和记录；
- image-to-editable-ppt 转换适配器；
- 统一的 QA 和失败报告。

## 命令

```powershell
python v2/ppt_tool/ppt_tool.py init v2/deck
python v2/ppt_tool/ppt_tool.py doctor
python v2/ppt_tool/ppt_tool.py validate v2/deck
python v2/ppt_tool/ppt_tool.py assemble v2/deck --name feature3_mps
python v2/ppt_tool/ppt_tool.py editable-export v2/deck --input feature3_mps.pptx
```

`generate-sample` 需要明确的 API/CLI 后端配置；工具不会假装已经调用了 GPT Image。无可用后端时，它会输出阻塞原因和需要配置的变量。

## 后端路由

`native`：python-pptx/PptxGenJS；`image`：GPT Image 整页生成；`hybrid`：按页面选择。image-to-editable 是后处理步骤，不能把每个生成图片可靠地恢复为真正的语义结构，因此必须把转换结果作为“候选可编辑版本”再人工验收。
