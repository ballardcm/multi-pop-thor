import json,subprocess,os,re,tarfile,sys,glob
names=['libfreeimage.so.3','libSDL2-2.0.so.0','libfreetype.so.6','libSDL2_mixer-2.0.so.0','libcurl.so.4','libvlc.so.5','libudev.so.1','libpulse.so.0','libGLESv2.so.2','libEGL.so.1','libstdc++.so.6','libm.so.6','libgcc_s.so.1','libc.so.6','libpthread.so.0','libdl.so.2','librt.so.1','libz.so.1','ld-linux-aarch64.so.1']
paths={}
while names:
 name=names.pop(0)
 if name in paths:continue
 candidates=['/usr/lib/'+name,'/lib/'+name]+glob.glob('/usr/lib/*/'+name)
 path=next((p for p in candidates if os.path.exists(p)),None)
 if path is None:raise RuntimeError('Missing target dependency: '+name)
 paths[name]=path
 dynamic=subprocess.check_output(['readelf','-d',path],text=True)
 names.extend(x for x in re.findall(r'NEEDED.*?\[([^]]+)\]',dynamic) if x not in paths)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',dereference=True) as tar:
 for name,path in paths.items():tar.add(path,arcname=name,recursive=False)
