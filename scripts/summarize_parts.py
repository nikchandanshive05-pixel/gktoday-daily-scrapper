# -*- coding: utf-8 -*-
import json

with open('belonging_marathi/data/en/manifest.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

parts = []
curr_part = None

for it in items:
    fname = it['logical_file']
    if 'Part_' in fname:
        curr_part = {'part': fname, 'title': it['preview'], 'chapters': []}
        parts.append(curr_part)
    elif 'Chapter_' in fname or 'Epilogue' in fname:
        if curr_part is None:
            curr_part = {'part': 'Front', 'title': 'Front', 'chapters': []}
            parts.append(curr_part)
        curr_part['chapters'].append(it)

print(f"Total Parts: {len(parts)}")
for p in parts:
    part_words = sum(c['words'] for c in p['chapters'])
    print(f"\n=== {p['part']} ({len(p['chapters'])} chapters, {part_words} words) ===")
    for c in p['chapters']:
        print(f"   {c['logical_file']} : {c['words']} words")
