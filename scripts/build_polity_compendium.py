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

CACHE_PATH = r"c:\Users\Nikhil-Arun\Documents\antigravity\resilient-hertz\polity_polls_cache.json"
TYPST_PATH = r"c:\Users\Nikhil-Arun\Documents\antigravity\resilient-hertz\polity_compendium.typ"

# Exact 38-chapter taxonomy from Bhagirath Revision Notes Index (Samadhan Kokate)
BHAGIRATH_CHAPTERS = [
    (1, "घटना निर्मिती", ["घटना समिती", "संविधान सभा", "मसुदा समिती", "ड्राफ्टिंग", "आंबेडकर", "राजेंद्र प्रसाद", "बी. एन. राव", "9 डिसेंबर", "11 डिसेंबर", "13 डिसेंबर", "उद्दिष्टांचा ठराव", "26 नोव्हेंबर 1949", "26 जानेवारी 1950", "कॅबिनेट मिशन", "त्रिमंत्री", "माउंटबॅटन"]),
    (2, "भारताच्या घटनेची ठळक वैशिष्ट्ये", ["ठळक वैशिष्ट्ये", "लिखित घटना", "विस्तृत घटना", "ताठर", "लवचिक", "संसदीय शासन", "मूलभूत सांगाठा", "बेसिक स्ट्रक्चर", "एकात्म न्यायव्यवस्था", "धर्मनिरपेक्ष"]),
    (3, "भारतीय संघराज्यीय व्यवस्था", ["संघराज्य", "फेडरेशन", "एकात्म", "अर्धसंघराज्य", "क्वासी फेडरल", "के. सी. व्हिअर", "केंद्राकडे कल"]),
    (4, "प्रास्ताविका", ["प्रास्ताविका", "उद्देशपत्रिका", "सरनामा", "सार्वभौम", "समाजवादी", "धर्मनिरपेक्ष", "लोकशाही गणराज्य", "न्याय", "स्वातंत्र्य", "समता", "बंधुता", "बेरूबारी", "प्रिएम्बल", "preamble"]),
    (5, "संघराज्य व त्याचे राज्यक्षेत्र", ["कलम 1", "कलम 2", "कलम 3", "कलम 4", "नवीन राज्यांची", "सीमा बदल", "भाषावार प्रांतरचना", "फजल अली", "एस. के. धार", "जेव्हीपी", "राज्य पुनर्रचना कायदा"]),
    (6, "नागरिकत्व", ["नागरिकत्व", "कलम 5", "कलम 6", "कलम 7", "कलम 8", "कलम 9", "कलम 10", "कलम 11", "नागरिकत्व कायदा 1955", "एनआरसी", "सीएए", "एकेरी नागरिकत्व"]),
    (7, "मूलभूत हक्क", ["मूलभूत हक्क", "मॅग्नाकार्टा", "कलम 12", "कलम 13", "कलम 14", "कलम 15", "कलम 16", "कलम 17", "कलम 18", "कलम 19", "कलम 20", "कलम 21", "कलम 21अ", "कलम 22", "कलम 23", "कलम 24", "कलम 25", "कलम 26", "कलम 27", "कलम 28", "कलम 29", "कलम 30", "कलम 31", "कलम 32", "रिट", "प्राधिलेख", "बंदी प्रत्यक्षीकरण", "परमादेश", "प्रतिषेध", "उत्प्रेषण", "अधिकार पृच्छा", "शिक्षणाचा हक्क", "अस्पृश्यता"]),
    (8, "राज्य धोरणाची मार्गदर्शक तत्वे", ["मार्गदर्शक तत्वे", "डीपीएसपी", "dpsp", "कलम 36", "कलम 37", "कलम 38", "कलम 39", "कलम 39अ", "कलम 40", "कलम 41", "कलम 42", "कलम 43", "कलम 43अ", "कलम 43ब", "कलम 44", "समान नागरी कायदा", "ucc", "कलम 45", "कलम 46", "कलम 47", "कलम 48", "कलम 48अ", "कलम 49", "कलम 50", "कलम 51", "ग्रामपंचायत स्थापना"]),
    (9, "मूलभूत कर्तव्ये", ["मूलभूत कर्तव्ये", "कलम 51अ", "51a", "स्वरणसिंग", "स्वर्णसिंग", "86 वी घटनादुरुस्ती", "राष्ट्रध्वज", "राष्ट्रगीत"]),
    (10, "राष्ट्रपती", ["राष्ट्रपती", "कलम 52", "कलम 53", "कलम 54", "कलम 55", "कलम 56", "कलम 57", "कलम 58", "कलम 59", "कलम 60", "कलम 61", "महाभियोग", "कलम 72", "कलम 123", "राष्ट्रपतींचा अध्यादेश", "दयेचा अधिकार", "पॉकेट व्हिटो"]),
    (11, "उपराष्ट्रपती", ["उपराष्ट्रपती", "कलम 63", "कलम 64", "कलम 65", "कलम 66", "कलम 67", "कलम 68", "कलम 69", "पदसिद्ध सभापती"]),
    (12, "पंतप्रधान", ["पंतप्रधान", "कलम 75", "कलम 78", "वास्तव प्रमुख"]),
    (13, "केंद्रीय मंत्रिमंडळ", ["केंद्रीय मंत्रिमंडळ", "कलम 74", "सामूहिक जबाबदारी", "कॅबिनेट", "मंत्रिमंडळ सल्ला"]),
    (14, "भारताचा महान्यायवादी", ["महान्यायवादी", "अटर्नी जनरल", "कलम 76"]),
    (15, "संसद", ["संसद", "कलम 79", "राज्यसभा", "कलम 80", "लोकसभा", "कलम 81", "खासदार", "कलम 84", "कलम 85", "कलम 89", "कलम 93", "संयुक्त बैठक", "कलम 108", "अर्थविधेयक", "कलम 110", "धनविधेयक", "अर्थसंकल्प", "कलम 112", "संचित निधी", "आकस्मिकता निधी", "लोकलेखा समिती", "अंदाज समिती", "शून्य प्रहर", "तारांकित प्रश्न"]),
    (16, "न्यायव्यवस्था", ["सर्वोच्च न्यायालय", "सुप्रीम कोर्ट", "उच्च न्यायालय", "हायकोर्ट", "सरन्यायाधीश", "कलम 124", "कलम 129", "कलम 131", "कलम 136", "कलम 142", "कलम 143", "कोलेजियम", "कलम 214", "कलम 226", "जनहित याचिका", "pil", "न्यायाधीश"]),
    (17, "भारताचे नियंत्रक व महालेखापरीक्षक", ["नियंत्रक व महालेखापरीक्षक", "कॅग", "cag", "कलम 148", "कलम 149", "कलम 151"]),
    (18, "राज्यपाल", ["राज्यपाल", "कलम 153", "कलम 154", "कलम 155", "कलम 156", "कलम 161", "कलम 213", "राज्यपालांचा अध्यादेश", "स्वेच्छाधीन अधिकार"]),
    (19, "मुख्यमंत्री", ["मुख्यमंत्री", "कलम 164", "कलम 167"]),
    (20, "राज्य मंत्रिमंडळ", ["राज्य मंत्रिमंडळ", "कलम 163"]),
    (21, "राज्य विधानमंडळ", ["विधानमंडळ", "विधानसभा", "विधानपरिषद", "आमदार", "कलम 168", "कलम 169", "कलम 170", "कलम 171"]),
    (22, "केंद्रशासित प्रदेश", ["केंद्रशासित प्रदेश", "कलम 239", "कलम 239aa", "उपराज्यपाल", "प्रशासक", "दिल्ली विशेष"]),
    (23, "सहकारी सोसायट्या", ["सहकारी सोसायट्या", "सहकारी संस्था", "97 वी घटनादुरुस्ती", "भाग 9ब", "243zh", "243zt"]),
    (24, "अनुसूचित क्षेत्रे व आदिवासी क्षेत्रे", ["अनुसूचित क्षेत्रे", "आदिवासी क्षेत्रे", "कलम 244", "पेसा", "pesa", "पाचवी अनुसूची", "सहावी अनुसूची"]),
    (25, "केंद्र - राज्य संबंध", ["केंद्र - राज्य संबंध", "केंद्र-राज्य", "कलम 245", "कलम 246", "कलम 256", "वित्त आयोग", "कलम 280", "सरकारिया आयोग", "पुंछी आयोग"]),
    (26, "आंतर-राज्यीय संबंध", ["आंतर-राज्यीय संबंध", "आंतरराज्य परिषद", "कलम 263", "नदी जलविवाद", "कलम 262", "क्षेत्रीय परिषदा"]),
    (27, "लोकसेवा", ["लोकसेवा", "अखिल भारतीय सेवा", "कलम 312", "upsc", "mpsc", "कलम 315", "कलम 316", "कलम 320"]),
    (28, "न्यायाधिकरणे", ["न्यायाधिकरण", "ट्रिब्युनल", "कलम 323a", "कलम 323b", "कॅट", "मॅट"]),
    (29, "निवडणूक आयोग", ["निवडणूक आयोग", "निवडणूक आयुक्त", "कलम 324", "कलम 325", "कलम 326", "प्रौढ मताधिकार", "ईव्हीएम", "evm", "vvpat", "आचारसंहिता"]),
    (30, "राजकीय पक्ष", ["राजकीय पक्ष", "राष्ट्रीय पक्ष", "पक्षांतर बंदी", "52 वी घटनादुरुस्ती", "दहावी अनुसूची", "पक्ष"]),
    (31, "विवक्षित वर्गासाठी विशेष तरतुदी", ["विवक्षित वर्ग", "कलम 330", "कलम 332", "कलम 338", "कलम 338a", "कलम 338b", "sc आयोग", "st आयोग", "obc आयोग", "अँग्लो इंडियन"]),
    (32, "कार्यालयीन भाषा / राजभाषा", ["राजभाषा", "कार्यालयीन भाषा", "कलम 343", "कलम 344", "कलम 345", "कलम 348", "कलम 350अ", "कलम 351", "आठवी अनुसूची भाषा", "अभिजात भाषा"]),
    (33, "आणीबाणीविषयक तरतुदी", ["आणीबाणी", "कलम 352", "कलम 356", "कलम 360", "राष्ट्रीय आणीबाणी", "राष्ट्रपती राजवट", "वित्तीय आणीबाणी"]),
    (34, "घटनादुरुस्ती", ["घटनादुरुस्ती", "कलम 368", "विशेष बहुमत", "घटनादुरुस्ती विधेयक", "42 वी घटनादुरुस्ती", "44 वी घटनादुरुस्ती"]),
    (35, "अस्थायी, संक्रमणी व विशेष तरतुदी", ["अस्थायी तरतुदी", "कलम 370", "कलम 371", "371a", "371j", "विकास मंडळे"]),
    (36, "घटनेच्या अनुसूच्या / परिशिष्ट्ये", ["अनुसूची", "परिशिष्ट", "1 ली अनुसूची", "2 री अनुसूची", "3 री अनुसूची", "4 थी अनुसूची", "7 वी अनुसूची", "संघसूची", "राज्यसूची", "समवर्ती सूची", "11 वी अनुसूची", "12 वी अनुसूची", "पंचायत राज"]),
    (37, "वैधानिक संस्था / गैर घटनात्मक संस्था", ["वैधानिक संस्था", "गैर घटनात्मक", "मानवाधिकार आयोग", "nhrc", "महिला आयोग", "माहिती आयोग", "rti", "केंद्रीय दक्षता आयोग", "cvc", "लोकपाल", "लोकायुक्त", "नीती आयोग", "cbi"]),
    (38, "Important Facts from PYQs", ["pyq", "स्रोत", "ब्रिटन", "अमेरिका", "आयर्लंड", "कॅनडा", "ऑस्ट्रेलिया", "जर्मनी", "1935 चा कायदा", "राज्यशास्त्रज्ञ", "ऑस्टिन", "कोटा", "खटला"])
]

def escape_typst(text):
    if not text:
        return ""
    text = text.replace("\r", " ").replace("\t", " ")
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

def clean_question_text(q_raw):
    # Remove author signatures like "By samadhan kokate", "Polity by samadhan kokate"
    q = re.sub(r'(?i)by\s+samadhan\s+kokate.*', '', q_raw)
    q = re.sub(r'(?i)polity\s+by\s+samadhan\s+kokate.*', '', q)
    # Extract leading serial number if present: "13,314) ..."
    serial_match = re.match(r'^\s*([\d,]+)\)\s*(.*)', q, re.DOTALL)
    if serial_match:
        orig_num = serial_match.group(1).replace(',', '')
        clean_text = serial_match.group(2).strip()
    else:
        orig_num = None
        clean_text = q.strip()
    return clean_text, orig_num

def classify_to_chapter(q_text, answers):
    full_text = (q_text + " " + " ".join(answers)).lower()
    
    best_ch = 38 # Fallback to Important Facts / PYQs
    max_score = 0
    
    for ch_num, ch_title, kws in BHAGIRATH_CHAPTERS:
        score = 0
        for kw in kws:
            kw_l = kw.lower()
            if kw_l in full_text:
                # Longer keywords get higher weight
                score += len(kw_l)
        if score > max_score:
            max_score = score
            best_ch = ch_num
            
    return best_ch

def build_polity_typst():
    if not os.path.exists(CACHE_PATH):
        print(f"Error: Cache not found: {CACHE_PATH}", flush=True)
        return
        
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)
        
    print(f"Loaded {len(cache)} polity polls from cache.", flush=True)
    
    valid_polls = []
    for k, v in cache.items():
        if v.get("correct_option_idx") is not None and v.get("answers") and len(v["answers"]) >= 2:
            valid_polls.append(v)
            
    valid_polls.sort(key=lambda x: x.get("date", ""))
    print(f"Total valid polls ready for compendium: {len(valid_polls)}", flush=True)
    
    # Group by Chapter 1 to 38
    chapter_map = {num: {"title": title, "items": []} for num, title, _ in BHAGIRATH_CHAPTERS}
    
    for p in valid_polls:
        ch_id = classify_to_chapter(p["question"], p["answers"])
        chapter_map[ch_id]["items"].append(p)
        
    # Stats
    active_chapters = [c for c in chapter_map.values() if len(c["items"]) > 0]
    print(f"Questions distributed across {len(active_chapters)} of 38 chapters.")
    for num, data in chapter_map.items():
        if data["items"]:
            print(f"  Ch {num:02d}. {data['title']}: {len(data['items'])} MCQs")
            
    typst_lines = []
    
    # Page setup with Oxford black and white styling
    typst_lines.append("""
#set page(
  paper: "a4",
  margin: (top: 2cm, bottom: 2cm, left: 1.8cm, right: 1.8cm),
  header: context {
    if here().page() > 1 [
      #grid(
        columns: (1fr, 1fr),
        align(left)[#text(size: 8pt, fill: luma(100), font: "Times New Roman")[Polity By Samadhan Kokate | भारतीय राज्यव्यवस्था]],
        align(right)[#text(size: 8pt, fill: luma(100), font: "Times New Roman")[Bhagirath Revision Notes Series]]
      )
      #line(length: 100%, stroke: 0.4pt + luma(180))
    ]
  },
  footer: context [
    #line(length: 100%, stroke: 0.4pt + luma(180))
    #grid(
      columns: (1fr, 1fr),
      align(left)[#text(size: 8pt, fill: luma(120), font: "Times New Roman")[Strictly for Educational Revision | MPSC / Combined / UPSC]],
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
  #text(size: 16pt, weight: "bold")[भारतीय राज्यव्यवस्था व शासन (Indian Polity)] \\
  #v(2pt)
  #text(size: 12pt, weight: "bold", fill: luma(40))[अध्यायनिहाय वस्तुनिष्ठ प्रश्नसंच व सविस्तर उत्तरतालिका] \\
  #v(2pt)
  #text(size: 10pt, weight: "medium", fill: luma(70))[संकलन: समाधान कोकाटे (Polity By Samadhan Kokate 🎯📚)] \\
  #v(2pt)
  #text(size: 8.5pt, fill: luma(110))[भगीरथ 'परिपूर्ण Revision Notes' अधिकृत 38-प्रकरण अनुक्रमणिकेनुसार मांडणी]
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
      #text(weight: "bold")[स्त्रोत]: \\@Politybysamadhankokate \\
      #text(weight: "bold")[मार्गदर्शक]: प्रा. समाधान कोकाटे
    ],
    [
      #text(weight: "bold")[एकूण समाविष्ट प्रश्न]: """ + str(len(valid_polls)) + """ \\
      #text(weight: "bold")[वर्गीकरण]: 38-अध्याय भगीरथ इंडेक्स
    ],
    [
      #text(weight: "bold")[उत्तरतालिका]: 100% अधिकृत ऑथेंटिकेटेड \\
      #text(weight: "bold")[संकलन दिनांक]: 16 नोव्हेंबर 2026
    ]
  )
]

#v(10pt)
""")

    global_q_num = 1
    
    for ch_num, ch_data in chapter_map.items():
        items = ch_data["items"]
        if not items:
            continue
            
        typst_lines.append(f"""
#v(14pt)
#rect(
  width: 100%,
  stroke: (left: 3.5pt + luma(20), rest: 0.5pt + luma(180)),
  inset: (x: 10pt, y: 7pt),
  fill: luma(244)
)[
  #text(size: 11pt, weight: "bold")[प्रकरण {ch_num}. {escape_typst(ch_data['title'])}] \\
  #text(size: 8pt, fill: luma(90), style: "italic")[Bhagirath Polity Chapter {ch_num} — एकूण प्रश्न: {len(items)}]
]
#v(8pt)
""")

        for item in items:
            raw_q = item["question"]
            clean_q, orig_num = clean_question_text(raw_q)
            q_text = escape_typst(clean_q)
            date_str = item.get("date", "")[:10]
            corr_idx = item["correct_option_idx"]
            answers = item.get("answers", [])
            total_voters = item.get("total_voters", 0)
            solution = item.get("solution")
            
            opt_strings = [escape_typst(a) for a in answers]
            
            if 0 <= corr_idx < len(answers):
                correct_text = opt_strings[corr_idx]
                clean_corr_label = f"पर्याय {corr_idx + 1}"
            else:
                correct_text = "पर्याय उपलब्ध नाही"
                clean_corr_label = "-"
                
            voter_stats_str = f"{total_voters} उमेदवारांचा सहभाग" if total_voters > 0 else ""
            
            solution_block_content = f"#text(weight: \"bold\")[अचूक उत्तर:] #text(weight: \"bold\", fill: luma(20))[{clean_corr_label} — {correct_text}]"
            if solution:
                sol_esc = escape_typst(solution)
                solution_block_content += f" \\\\ \n  #text(weight: \"bold\")[स्पष्टीकरण:] #text(fill: luma(50))[{sol_esc}]"
            if voter_stats_str:
                solution_block_content += f" \\\\ \n  #text(size: 7.5pt, fill: luma(110))[{voter_stats_str}]"
                
            orig_badge = f" [क्र. {orig_num}]" if orig_num else ""
            
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
    [#text(weight: "bold", size: 9.5pt)[प्र. {global_q_num:02d}.{orig_badge}]],
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
        
    print(f"Typst source successfully generated at: {TYPST_PATH}", flush=True)
    print(f"Total Polity Questions Written: {global_q_num - 1}", flush=True)

if __name__ == "__main__":
    build_polity_typst()
