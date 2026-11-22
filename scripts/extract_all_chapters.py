# -*- coding: utf-8 -*-
import zipfile, os, json
from bs4 import BeautifulSoup

epub_path = r'C:\Users\Nikhil-Arun\Downloads\Telegram Desktop\Belonging_A_Journey_of_Love_Sonia_Gandhi_z_library_sk,_1lib_sk,.epub'
out_dir = r'belonging_marathi/data/en'
os.makedirs(out_dir, exist_ok=True)

with zipfile.ZipFile(epub_path, 'r') as z:
    # Get spine
    opf_name = [f for f in z.namelist() if f.endswith('.opf')][0]
    soup_opf = BeautifulSoup(z.read(opf_name), 'xml')
    spine = [item['idref'] for item in soup_opf.find_all('itemref')]
    manifest = {item['id']: item['href'] for item in soup_opf.find_all('item')}
    
    chapter_map = []
    
    for s in spine:
        href = manifest.get(s, '')
        full_path = 'OEBPS/' + href if not href.startswith('OEBPS/') else href
        if not full_path.endswith('.xhtml') or full_path not in z.namelist():
            continue
        
        soup = BeautifulSoup(z.read(full_path), 'html.parser')
        
        # Clean text
        paras = []
        for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'blockquote']):
            t = p.get_text().strip()
            if t:
                paras.append(t)
        
        base = os.path.basename(full_path)
        word_count = sum(len(p.split()) for p in paras)
        
        # Determine logical name
        logical_name = base.replace('.xhtml', '.txt')
        out_path = os.path.join(out_dir, logical_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(paras))
        
        chapter_map.append({
            'source_file': full_path,
            'logical_file': logical_name,
            'paragraphs': len(paras),
            'words': word_count,
            'preview': paras[0][:60] if paras else ''
        })

with open('belonging_marathi/data/en/manifest.json', 'w', encoding='utf-8') as f:
    json.dump(chapter_map, f, ensure_ascii=False, indent=2)

print(f"Extracted {len(chapter_map)} sections successfully.")
for c in chapter_map[:15]:
    print(f" - {c['logical_file']} ({c['words']} words): {c['preview']}")
