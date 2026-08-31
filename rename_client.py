import os

def replace_in_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return
    
    new_content = content.replace("evoker_client.client", "evoker_client.client")
    new_content = new_content.replace("evoker_client.utils", "evoker_client.utils")
    new_content = new_content.replace("evoker_client._pyinstaller", "evoker_client._pyinstaller")
    new_content = new_content.replace("evoker_client", "evoker_client")
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {path}")

for root, dirs, files in os.walk('.'):
    if '.git' in root or 'node_modules' in root or 'build' in root or '__pycache__' in root or 'evoker_host.egg-info' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.md') or file.endswith('.rs') or file.endswith('.cpp') or file.endswith('.c') or file.endswith('.json') or file.endswith('.txt') or file.endswith('.toml'):
            replace_in_file(os.path.join(root, file))
