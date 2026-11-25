"""Verify protected hashes and token usage; never modify production assets."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
base=json.loads((root/'reports/gui_validation/protected_baseline.json').read_text())
protected={}
for key,value in base.items():
 p=Path(key);p=p if p.is_absolute() else root/p
 protected[key]=p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==value
violations=[]
for p in (root/'inspection-gui/src').rglob('*'):
 if not p.is_file() or p.name=='tokens.css' or 'fixtures' in p.parts:continue
 if p.suffix not in ('.ts','.tsx','.css'):continue
 for i,line in enumerate(p.read_text().splitlines(),1):
  if re.search(r'#[0-9a-fA-F]{3,8}\b|0x[0-9a-fA-F]{6}\b',line):violations.append({'file':str(p.relative_to(root)),'line':i})
changed=[]
source=json.loads((root/'reports/gui_validation/source_baseline.json').read_text())
paths=list((root/'inspection-gui').glob('*.ts'))+list((root/'inspection-gui/src').rglob('*'))+list((root/'app').glob('*.py'))+list((root/'scripts').glob('*'))+list((root/'tests').glob('test_*.py'))
for p in paths:
 if p.is_file() and p.suffix in ('.py','.ts','.tsx','.css','.sh','.mjs'):
  key=str(p.relative_to(root));digest=hashlib.sha256(p.read_bytes()).hexdigest()
  if source.get(key)!=digest:changed.append(key)
result={'protected_assets_unchanged':all(protected.values()),'protected_files':protected,'hardcoded_color_violations':violations,'changed_or_untracked_scope_files':sorted(set(changed)),'note':'Baseline covers pre-existing src/app/config and agent.py; scripts/tests listed without a baseline are not necessarily newly created. Git metadata unavailable.'}
(root/'reports/gui_validation/integrity.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
raise SystemExit(0 if all(protected.values()) and not violations else 1)
