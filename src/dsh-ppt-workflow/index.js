import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'dsh-ppt-workflow'
export const inject = ['tools']

const PACKAGE_DIR = path.dirname(fileURLToPath(import.meta.url))

function runProcess(command, args, { cwd, signal } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, windowsHide: true })
    let stdout = ''
    let stderr = ''
    const abort = () => child.kill()
    if (signal) {
      if (signal.aborted) {
        child.kill()
        reject(new Error('PPT workflow cancelled before process start'))
        return
      }
      signal.addEventListener('abort', abort, { once: true })
    }
    child.stdout?.on('data', (chunk) => { stdout += chunk.toString() })
    child.stderr?.on('data', (chunk) => { stderr += chunk.toString() })
    child.on('error', reject)
    child.on('close', (code, closeSignal) => {
      signal?.removeEventListener('abort', abort)
      resolve({ code: code ?? 1, signal: closeSignal ?? null, stdout, stderr })
    })
  })
}

function lastJson(text) {
  const lines = text.trim().split(/\r?\n/).reverse()
  for (const line of lines) {
    try { return JSON.parse(line) } catch {}
  }
  return null
}

export function apply(ctx) {
  ctx.tools.register(defineTool({
    name: 'ppt_workflow',
    description: 'Run a staged, traceable PPT workflow: inspect an input deck, prepare an image-to-editable run, validate a reconstructed PPTX, or execute the v6 visual-fidelity gate. Use this tool for PPT production tasks instead of ad-hoc slide edits.',
    parameters: {
      action: { type: 'string', required: true, description: 'One of: doctor, inspect, prepare, validate, visual_gate, run_v6.' },
      input: { type: 'string', description: 'Absolute input image, PDF, PPTX, or source document path for inspect/prepare.' },
      pptx: { type: 'string', description: 'Final PPTX path for validate, inspect, or visual_gate artifact-drift checking.' },
      run_dir: { type: 'string', description: 'Absolute editppt run directory for visual_gate or run_v6.' },
      deck_manifest: { type: 'string', description: 'Optional deck_manifest.json path for validate.' },
      report: { type: 'string', description: 'Optional output JSON report path.' },
      workspace: { type: 'string', description: 'Workspace root. Defaults to DSH_PPT_WORKSPACE or the current working directory.' },
      tool_root: { type: 'string', description: 'Root containing the v6 toolchain. Defaults to DSH_PPT_TOOL_ROOT or workspace/v6.' },
      backend: { type: 'string', description: 'Image backend for prepare: builtin-imagegen or editppt-image-cli.' }
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }]
    },
    async execute(args, exec) {
      const workspace = path.resolve(args.workspace || process.env.DSH_PPT_WORKSPACE || process.cwd())
      const toolRoot = path.resolve(args.tool_root || process.env.DSH_PPT_TOOL_ROOT || path.join(workspace, 'v6'))
      const python = process.env.DSH_PPT_PYTHON || 'python'
      const script = path.join(PACKAGE_DIR, 'scripts', 'ppt_pipeline.py')
      const commandArgs = [script, '--action', args.action, '--workspace', workspace, '--tool-root', toolRoot]
      for (const [key, value] of Object.entries({ input: args.input, pptx: args.pptx, run_dir: args.run_dir, deck_manifest: args.deck_manifest, report: args.report, backend: args.backend })) {
        if (value) commandArgs.push(`--${key.replaceAll('_', '-')}`, value)
      }
      const result = await runProcess(python, commandArgs, { cwd: workspace, signal: exec.signal })
      const payload = lastJson(result.stdout) || { stdout: result.stdout }
      return {
        ok: result.code === 0 && payload.ok !== false,
        action: args.action,
        ...payload,
        exit_code: result.code,
        stderr: result.stderr.trim() || undefined
      }
    }
  }))
}
