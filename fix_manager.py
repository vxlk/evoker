import sys
with open('evoker/src/evoker/manager.py', 'r') as f:
    content = f.read()
content = content.replace('sys.path.insert(1, str(site_packages))', 'sys.path.insert(1, str(site_packages))\n                    path_insertions.append(str(site_packages))')
content = content.replace('finally:\n            sys.path.pop(0)', 'finally:\n            for p in path_insertions:\n                if p in sys.path:\n                    sys.path.remove(p)')
with open('evoker/src/evoker/manager.py', 'w') as f:
    f.write(content)

