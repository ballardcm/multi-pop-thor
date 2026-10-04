import json,subprocess
from pathlib import Path
root=Path('/work/private/target-libs');result={}
for p in root.iterdir():
 if p.is_symlink() or not p.is_file():continue
 result[p.name]={'path':str(p),'symbols':subprocess.check_output(['readelf','--dyn-syms','--wide',str(p)],text=True),'versions':subprocess.check_output(['readelf','--version-info',str(p)],text=True)}
print(json.dumps(result))
