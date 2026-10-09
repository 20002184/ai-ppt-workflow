#!/usr/bin/env python3
"""Own orchestration layer for the v2 PPT production workflow."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REF = ROOT / 'scripts'
EDITPPT = ROOT / 'image-to-editable-ppt' / 'cli' / 'editppt' / 'cli.py'

def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def save_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def init_project(project: Path):
    project = project.resolve()
    for name in ('origin_image', 'prompts', 'assets', 'qa'):
        (project / name).mkdir(parents=True, exist_ok=True)
    state = project / 'slide_run_state.json'
    if not state.exists():
        save_json(state, {'phase':'source_and_outline', 'backend':None, 'sample_generation_method':None, 'slides':{}, 'blockers':[]})
    jobs = project / 'slide_jobs.json'
    if not jobs.exists():
        save_json(jobs, {'approval':{'outline':'pending','style':'pending','backend':'pending','sample':'pending'},'jobs':[]})
    print(f'project ready: {project}')

def doctor():
    print('PPT Tool v2 doctor')
    print('python:', sys.executable)
    print('reference image_gen.py:', (REF / 'image_gen.py').exists())
    print('reference assemble_ppt.py:', (REF / 'assemble_ppt.py').exists())
    print('OPENAI_API_KEY:', 'present' if os.environ.get('OPENAI_API_KEY') else 'missing')
    print('OPENAI_BASE_URL:', os.environ.get('OPENAI_BASE_URL') or 'default')
    print('CODEX_PPT_IMAGE_MODEL:', os.environ.get('CODEX_PPT_IMAGE_MODEL') or 'gpt-image-2.5-flare (reference default)')
    converter = os.environ.get('IMAGE_TO_EDITABLE_PPT_HOME')
    print('IMAGE_TO_EDITABLE_PPT_HOME:', converter or 'not configured')
    print('built-in image_gen: unavailable as a callable local command; use configured CLI/API backend when approved')

def validate(project: Path):
    project = project.resolve()
    required = ['deck_spec.json', 'slide_jobs.json', 'slide_run_state.json']
    missing = [x for x in required if not (project / x).exists()]
    if missing:
        raise SystemExit('missing required state files: ' + ', '.join(missing))
    spec = load_json(project / 'deck_spec.json')
    jobs = load_json(project / 'slide_jobs.json')
    state = load_json(project / 'slide_run_state.json')
    assert spec.get('slide_count') == len(spec.get('slides', []))
    assert jobs.get('sample_slide') in {s['id'] for s in spec['slides']}
    print('state: OK')
    print('phase:', state.get('phase'))
    print('approval:', jobs.get('approval'))
    print('expected slides:', spec.get('slide_count'))
    images = sorted((project / 'origin_image').glob('slide_*.png')) if (project / 'origin_image').exists() else []
    print('final images:', len(images))

def generate_sample(project: Path, prompt: Path):
    project = project.resolve(); prompt = prompt.resolve()
    jobs = load_json(project / 'slide_jobs.json')
    if jobs.get('approval', {}).get('outline') != 'approved':
        raise SystemExit('blocked: approve outline before sample generation')
    if jobs.get('approval', {}).get('style') != 'approved':
        raise SystemExit('blocked: approve style before sample generation')
    if jobs.get('approval', {}).get('backend') != 'approved':
        raise SystemExit('blocked: approve image backend before sample generation')
    if not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('blocked: CLI/API backend selected but OPENAI_API_KEY is missing; configure locally before generation')
    out = project / 'origin_image' / 'sample_slide.png'
    cmd = [sys.executable, str(REF / 'image_gen.py'), 'generate', '--prompt-file', str(prompt), '--out', str(out)]
    print('running:', ' '.join(cmd))
    subprocess.run(cmd, check=True)

def assemble(project: Path, name: str):
    project = project.resolve()
    jobs = load_json(project / 'slide_jobs.json')
    pending = [j['slide_id'] for j in jobs.get('jobs', []) if j.get('status') not in {'recorded', 'accepted'}]
    if pending:
        raise SystemExit('blocked: slides not recorded: ' + ', '.join(pending))
    base = project.parent
    cmd = [sys.executable, str(REF / 'assemble_ppt.py'), str(base), name + '.pptx', '--aspect-ratio', '16:9']
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    subprocess.run(cmd, check=True, env=env)

def editable_export(project: Path, input_name: str):
    project = project.resolve()
    source = project / input_name
    if not source.exists():
        raise SystemExit(f'input PPTX not found: {source}')
    if EDITPPT.exists():
        out_root = project / 'editable_runs'
        out_root.mkdir(parents=True, exist_ok=True)
        backend = 'editppt-image-cli' if os.environ.get('OPENAI_API_KEY') else 'builtin-imagegen'
        cmd = [sys.executable, str(EDITPPT), 'prepare', str(source), '--out-root', str(out_root), '--image-backend', backend]
        print('preparing image-to-editable run:', ' '.join(cmd))
        subprocess.run(cmd, check=True)
        print('next: inspect editable_runs/*/page_jobs.json, dispatch page workers, then run finalize')
        return
    converter = os.environ.get('IMAGE_TO_EDITABLE_PPT_HOME')
    if not converter:
        raise SystemExit('blocked: image-to-editable CLI is unavailable and IMAGE_TO_EDITABLE_PPT_HOME is not configured')
    command = Path(converter) / 'convert.py'
    if not command.exists():
        raise SystemExit(f'blocked: converter entrypoint not found: {command}')
    out = project / (source.stem + '_editable.pptx')
    subprocess.run([sys.executable, str(command), str(source), str(out)], check=True)
    print('editable candidate:', out)

def editable_finalize(run_dir: Path):
    if not EDITPPT.exists():
        raise SystemExit('blocked: local image-to-editable CLI is unavailable')
    cmd = [sys.executable, str(EDITPPT), 'run', 'finalize', str(run_dir)]
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description='PPT Tool v2')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('init'); p.add_argument('project', type=Path)
    sub.add_parser('doctor')
    p = sub.add_parser('validate'); p.add_argument('project', type=Path)
    p = sub.add_parser('generate-sample'); p.add_argument('project', type=Path); p.add_argument('prompt', type=Path)
    p = sub.add_parser('assemble'); p.add_argument('project', type=Path); p.add_argument('--name', default='presentation')
    p = sub.add_parser('editable-export'); p.add_argument('project', type=Path); p.add_argument('--input', required=True)
    p = sub.add_parser('editable-finalize'); p.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    if args.command == 'init': init_project(args.project)
    elif args.command == 'doctor': doctor()
    elif args.command == 'validate': validate(args.project)
    elif args.command == 'generate-sample': generate_sample(args.project, args.prompt)
    elif args.command == 'assemble': assemble(args.project, args.name)
    elif args.command == 'editable-export': editable_export(args.project, args.input)
    elif args.command == 'editable-finalize': editable_finalize(args.run_dir)

if __name__ == '__main__':
    main()
