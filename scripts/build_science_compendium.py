import os
import sys
import json
import re

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CACHE_PATH = r"c:\Users\Nikhil-Arun\Documents\antigravity\resilient-hertz\science_polls_cache.json"
TYPST_PATH = r"c:\Users\Nikhil-Arun\Documents\antigravity\resilient-hertz\science_compendium.typ"

# Classification keyword rules
BIO_KEYWORDS = [
    "पेशी", "वनस्पती", "प्राणी", "उती", "वर्गीकरण", "प्रकाशसंश्लेषण", "उत्क्रांती", 
    "dna", "rna", "गुणसूत्र", "जीवाणू", "शैवाल", "बुरशी", "रुमीनन्ट", "सजीव",
    "मानवी", "पचन", "श्वसन", "रक्त", "हृदय", "मेंदू", "संप्रेरक", "ग्रंथी", 
    "मूत्रपिंड", "अस्थी", "स्नायू", "डोळा", "कान", "दांत", "जिवाणू", "अमिबा",
    "पॅरामेशियम", "हायड्रा", "फूल", "फळ", "पान", "मूळ", "क्लोरोप्लास्ट", "मायटोकॉन्ड्रिया",
    "रायबोझोम", "लायसोसोम", "सूक्ष्मजीव", "प्रोटिस्टा", "प्लँटी", "अ‍ॅनिमॅलिया", "कवक",
    "monera", "protista", "fungi", "plantae", "animalia", "cell", "tissue", "bacteria", "algae"
]

CHEM_KEYWORDS = [
    "मूलद्रव्य", "अणू", "रेणू", "आम्ल", "आम्लारी", "ph", "रासायनिक", "धातू", "अधातू", 
    "आवर्तसारणी", "गंज", "द्रावण", "ऑक्सिडीकरण", "क्षपण", "वायू", "आवर्त", "समस्थानिके", 
    "किरणोत्सार", "कार्बन", "संयुग", "मिश्रण", "हायड्रोजन", "ऑक्सिजन", "नायट्रोजन",
    "सोडियम", "पोटॅशियम", "कॅल्शियम", "लोह", "तांबे", "सल्फ्यूरिक", "हायड्रोक्लोरिक",
    "लिटमस", "उदासीनीकरण", "उत्प्रेरक", "संयुजा", "इलेक्ट्रॉन", "प्रोटॉन", "न्यूट्रॉन",
    "बॉण्ड", "अणुक्रमांक", "अणुवस्तुमानांक", "polymer", "acid", "base", "metal", "element"
]

PHYS_KEYWORDS = [
    "गती", "बल", "दाब", "कार्य", "ऊर्जा", "प्रकाश", "परावर्तन", "अपवर्तन", "भिंग", 
    "ध्वनी", "नाद", "कंपन", "विद्युत", "विद्युतधारा", "विभवांतर", "चुंबक", "रोध", 
    "उष्णता", "तापमान", "तरंग", "वारंवारता", "गुरुत्वाकर्षण", "वस्तुमान", "वजन",
    "न्यूटन", "ज्यूल", "वॅट", "व्होल्ट", "अँपिअर", "ओहम", "वेग", "त्वरण", "संवेग",
    "जडत्व", "प्लवमान", "प्रकाशाचा वेग", "विद्युतघट", "रोहित्र", "डायनॅमो", "लेन्स",
    "force", "motion", "energy", "work", "power", "light", "sound", "electricity", "heat"
]

APPLIED_KEYWORDS = [
    "रोग", "विषाणू", "रोगजंतू", "जीवनसत्त्व", "व्हिटॅमिन", "पोषण", "लस", "लसकरण", 
    "कुपोषण", "स्वच्छता", "पर्यावरण", "परिसंस्था", "प्रदूषण", "ओझोन", "हवामान", 
    "हरितगृह", "प्लास्टिक", "जैवतंत्रज्ञान", "शेती", "अन्न", "कॅन्सर", "एड्स", 
    "टीबी", "मलेरिया", "डेंग्यू", "कॉलरा", "टायफॉइड", "इन्फ्लुएन्झा", "कोरोना",
    "vitamin", "disease", "virus", "vaccine", "pollution", "ecology"
]

def escape_typst(text):
    if not text:
        return ""
    # Strip pymupdf / Devanagari decomposing anomalies if any
    text = text.replace("\r", " ").replace("\t", " ")
    # Characters that have special syntactic meaning in Typst markup
    replacements = [
        ('\\', '\\\\'),
        ('[', '\\['),
        (']', '\\]'),
        ('$', '\\$'),
        ('#', '\\#'),
        ('@', '\\@'),
        ('_', '\\_'),
        ('*', '\\*'),
        ('`', '\\`'),
        ('<', '\\<'),
        ('>', '\\>'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text.strip()

def classify_question(q_text, answers):
    full_text = (q_text + " " + " ".join(answers)).lower()
    
    score_bio = sum(1 for kw in BIO_KEYWORDS if kw in full_text)
    score_chem = sum(1 for kw in CHEM_KEYWORDS if kw in full_text)
    score_phys = sum(1 for kw in PHYS_KEYWORDS if kw in full_text)
    score_app = sum(1 for kw in APPLIED_KEYWORDS if kw in full_text)
    
    scores = [
        (score_bio, "Biology"),
        (score_chem, "Chemistry"),
        (score_phys, "Physics"),
        (score_app, "Applied")
    ]
    scores.sort(key=lambda x: x[0], reverse=True)
    if scores[0][0] > 0:
        return scores[0][1]
    return "General"

def build_typst_document():
    if not os.path.exists(CACHE_PATH):
        print(f"Error: Cache file not found: {CACHE_PATH}")
        return
        
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)
        
    print(f"Loaded {len(cache)} polls from cache.")
    
    # Filter valid polls
    valid_polls = []
    for k, v in cache.items():
        if v.get("correct_option_idx") is not None and v.get("answers") and len(v["answers"]) >= 2:
            valid_polls.append(v)
            
    # Sort chronologically
    valid_polls.sort(key=lambda x: x.get("date", ""))
    print(f"Total valid polls ready for compendium: {len(valid_polls)}")
    
    # Categorize
    categories = {
        "Biology": {
            "title_mr": "विभाग १: जीवशास्त्र (वनस्पतीशास्त्र, प्राणिशास्त्र व पेशीशास्त्र)",
            "title_en": "Section 1: Biology (Botany, Zoology & Cytology)",
            "items": []
        },
        "Chemistry": {
            "title_mr": "विभाग २: रसायनशास्त्र (मूलद्रव्ये, संयुगे व रासायनिक अभिक्रिया)",
            "title_en": "Section 2: Chemistry (Elements, Compounds & Reactions)",
            "items": []
        },
        "Physics": {
            "title_mr": "विभाग ३: भौतिकशास्त्र (गती, बल, प्रकाश, ध्वनी व विद्युत)",
            "title_en": "Section 3: Physics (Mechanics, Optics, Waves & Electricity)",
            "items": []
        },
        "Applied": {
            "title_mr": "विभाग ४: आरोग्यशास्त्र, पोषण व पर्यावरण विज्ञान",
            "title_en": "Section 4: Health Science, Diseases, Nutrition & Ecology",
            "items": []
        },
        "General": {
            "title_mr": "विभाग ५: सामान्य विज्ञान संमिश्र सराव प्रश्नसंच",
            "title_en": "Section 5: General Science Mixed Practice Set",
            "items": []
        }
    }
    
    for p in valid_polls:
        cat = classify_question(p["question"], p["answers"])
        categories[cat]["items"].append(p)
        
    print("Category Breakdown:")
    for cat_name, cat_data in categories.items():
        print(f"  - {cat_name}: {len(cat_data['items'])} questions")
        
    typst_lines = []
    
    # Header styling & setup
    typst_lines.append("""
#set page(
  paper: "a4",
  margin: (top: 2cm, bottom: 2cm, left: 1.8cm, right: 1.8cm),
  header: context {
    if here().page() > 1 [
      #grid(
        columns: (1fr, 1fr),
        align(left)[#text(size: 8pt, fill: luma(100), font: "Times New Roman")[Science By Rahul Deshmukh | वस्तुनिष्ठ सामान्य विज्ञान]],
        align(right)[#text(size: 8pt, fill: luma(100), font: "Times New Roman")[MPSC & Central Exam Q-Bank]]
      )
      #line(length: 100%, stroke: 0.4pt + luma(180))
    ]
  },
  footer: context [
    #line(length: 100%, stroke: 0.4pt + luma(180))
    #grid(
      columns: (1fr, 1fr),
      align(left)[#text(size: 8pt, fill: luma(120), font: "Times New Roman")[Strictly for Educational Revision | 2025–2026]],
      align(right)[#text(size: 8pt, fill: luma(120), font: "Times New Roman")[Page #counter(page).display()]]
    )
  ]
)

#set text(
  font: ("Times New Roman", "Nirmala UI", "Tiro Devanagari Marathi"),
  size: 9.5pt,
  lang: "mr"
)
#set par(justify: true, leading: 0.65em)

// Cover Header Block
#align(center)[
  #text(size: 16pt, weight: "bold")[स्पर्धा परीक्षा सामान्य विज्ञान प्रश्नसंच (2025–2026)] \\
  #v(2pt)
  #text(size: 11pt, weight: "medium", fill: luma(60))[संकलन: सायन्स बाय राहुल देशमुख (Science By Rahul Deshmukh)] \\
  #v(2pt)
  #text(size: 8.5pt, fill: luma(110))[MPSC राज्यसेवा / संयुक्त गट-ब व गट-क / CWC / SSC / Railway भरती परीक्षांसाठी विशेष उपयुक्त]
]

#v(8pt)
#line(length: 100%, stroke: 1pt + luma(40))
#v(6pt)

// Executive Metadata Box
#rect(
  width: 100%,
  stroke: 0.6pt + luma(160),
  radius: 3pt,
  inset: (x: 12pt, y: 8pt),
  fill: luma(250)
)[
  #grid(
    columns: (1.2fr, 1fr, 1fr),
    [
      #text(weight: "bold")[स्त्रोत]: \\@sciencebyrahuldeshmukh \\
      #text(weight: "bold")[कालावधी]: 2025–2026 Exam Cycle
    ],
    [
      #text(weight: "bold")[एकूण समाविष्ट प्रश्न]: """ + str(len(valid_polls)) + """ \\
      #text(weight: "bold")[प्रारूप]: वस्तुनिष्ठ प्रश्न (MCQ / Quiz)
    ],
    [
      #text(weight: "bold")[उत्तरतालिका]: अधिकृत ऑथेंटिकेटेड \\
      #text(weight: "bold")[संकलन दिनांक]: 16 नोव्हेंबर 2026
    ]
  )
]

#v(10pt)
""")

    global_q_num = 1
    
    for cat_name, cat_data in categories.items():
        if not cat_data["items"]:
            continue
            
        typst_lines.append(f"""
#v(14pt)
#rect(
  width: 100%,
  stroke: (left: 3.5pt + luma(20), rest: 0.5pt + luma(180)),
  inset: (x: 10pt, y: 7pt),
  fill: luma(244)
)[
  #text(size: 11pt, weight: "bold")[{escape_typst(cat_data["title_mr"])}] \\
  #text(size: 8pt, fill: luma(90), style: "italic")[{escape_typst(cat_data["title_en"])} — एकूण प्रश्न: {len(cat_data["items"])}]
]
#v(8pt)
""")

        for item in cat_data["items"]:
            q_text = escape_typst(item["question"])
            date_str = item.get("date", "")[:10]
            corr_idx = item["correct_option_idx"]
            answers = item.get("answers", [])
            total_voters = item.get("total_voters", 0)
            solution = item.get("solution")
            
            # Format options
            # If 4 options, format as a 2x2 grid or clean list
            opt_strings = [escape_typst(a) for a in answers]
            
            # Identify correct answer string
            if 0 <= corr_idx < len(answers):
                correct_text = opt_strings[corr_idx]
                # Extract clean option number if present, e.g. "1) ... "
                m = re.match(r"^(\d+\)?|\w\)?)\s*(.*)", correct_text)
                if m:
                    clean_corr_label = f"पर्याय {corr_idx + 1}"
                else:
                    clean_corr_label = f"पर्याय {corr_idx + 1}"
            else:
                correct_text = "पर्याय उपलब्ध नाही"
                clean_corr_label = "-"
                
            # Voters stats
            voter_stats_str = f"{total_voters} उमेदवारांचा सहभाग" if total_voters > 0 else ""
            
            solution_block_content = f"#text(weight: \"bold\")[अचूक उत्तर:] #text(weight: \"bold\", fill: luma(20))[{clean_corr_label} — {correct_text}]"
            if solution:
                sol_esc = escape_typst(solution)
                solution_block_content += f" \\\\ \n  #text(weight: \"bold\")[स्पष्टीकरण:] #text(fill: luma(50))[{sol_esc}]"
            if voter_stats_str:
                solution_block_content += f" \\\\ \n  #text(size: 7.5pt, fill: luma(110))[{voter_stats_str}]"
                
            # Build Question Block
            block_code = f"""
#block(
  width: 100%,
  breakable: false,
  stroke: 0.4pt + luma(210),
  radius: 2pt,
  inset: (x: 10pt, y: 8pt),
  fill: luma(255)
)[
  #grid(
    columns: (auto, 1fr, auto),
    [#text(weight: "bold", size: 9.5pt)[प्र. {global_q_num:02d}.]],
    [],
    [#text(size: 7.5pt, fill: luma(130))[दिनांक: {date_str} | ID: {item['msg_id']}]]
  )
  #v(2pt)
  #text(weight: "medium", size: 9.5pt)[{q_text}]
  
  #v(5pt)
  #grid(
    columns: (1fr, 1fr),
    gutter: 5pt,
"""
            for opt in opt_strings:
                block_code += f"    [#text(size: 8.5pt)[{opt}]],\n"
                
            block_code += f"""  )
  
  #v(5pt)
  #rect(
    width: 100%,
    stroke: (left: 2pt + luma(60), rest: none),
    fill: luma(248),
    inset: (x: 8pt, y: 5pt),
    radius: 0pt
  )[
    {solution_block_content}
  ]
]
#v(6pt)
"""
            typst_lines.append(block_code)
            global_q_num += 1
            
    with open(TYPST_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(typst_lines))
        
    print(f"Typst source successfully generated at: {TYPST_PATH}")
    print(f"Total Questions Written: {global_q_num - 1}")

if __name__ == "__main__":
    build_typst_document()
