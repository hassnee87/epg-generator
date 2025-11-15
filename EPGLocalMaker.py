import os
import re

WORKFLOW_PATH = os.path.join('.github', 'workflows', 'epg.yml')
OUTPUT_BAT = 'CreateEPGs.bat'

def debug(msg):
    print(f"[DEBUG] {msg}")

def read_workflow():
    with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def extract_scripts(yaml_text):
    m = re.search(r"\$scripts\s*=\s*@\(\s*([\s\S]*?)\)\s", yaml_text)
    if not m:
        return []
    block = m.group(1)
    return re.findall(r"\"([^\"]+\.py)\"", block)

def generate_bat(scripts):
    lines = []
    lines.append('@echo off')
    lines.append('setlocal')
    lines.append('cd /d "%~dp0"')
    lines.append('echo Starting EPG generators...')
    lines.append('')
    for s in scripts:
        lines.append(f'IF EXIST "{s}" (')
        lines.append(f'  echo Running {s} ...')
        lines.append(f'  python "{s}"')
        lines.append(f'  IF ERRORLEVEL 1 echo FAILED {s}, continuing...')
        lines.append(') ELSE (')
        lines.append(f'  echo SKIPPED {s} (missing)')
        lines.append(')')
    lines.append('')
    lines.append('echo All done.')
    lines.append('endlocal')
    with open(OUTPUT_BAT, 'w', encoding='utf-8') as f:
        f.write("\r\n".join(lines))
    debug(f"Wrote {OUTPUT_BAT} with {len(scripts)} entries")

def main():
    yaml_text = read_workflow()
    scripts = extract_scripts(yaml_text)
    if not scripts:
        print('ERROR: Could not find scripts list in epg.yml')
        return 1
    generate_bat(scripts)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

