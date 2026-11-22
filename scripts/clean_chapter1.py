# -*- coding: utf-8 -*-
import re

with open('belonging_marathi/data/mr/chapter1.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Find all brackets
brackets = re.findall(r'\([^)]*[A-Za-z]+[^)]*\)', text)
print(f"Total English brackets found: {len(brackets)}")
for b in brackets:
    print(" -", b)

# Clean replacements
replacements = [
    (r"\s*\('द व्हर्सिटी'\s*\|\s*The Varsity\)", ""),
    (r"\s*\(The Varsity\)", ""),
    (r"\s*\(Cambridge\)", ""),
    (r"\s*\(Jarrett School of English\)", ""),
    (r"\s*\(High Tea\)", ""),
    (r"\s*\(bacon\)", ""),
    (r"\s*\(baked beans\)", ""),
    (r"\s*\(tinned spaghetti on toast\)", ""),
    (r"\s*\(delicatessen\)", ""),
    (r"\s*\(San Daniele ham\)", ""),
    (r"\s*\(Gorgonzola\)", ""),
    (r"\s*\(Fontina\)", ""),
    (r"\s*\(Luigi\)", ""),
    (r"\s*\(Charlie\)", ""),
    (r"\s*\(Neapolitan\)", ""),
    (r"\s*\(Sicilian\)", ""),
    (r"\s*\(Spanish\)", ""),
    (r"\s*\(Tiepolo\)", ""),
    (r"\s*\(Milan\)", ""),
    (r"\s*\(Christian von Stieglitz\)", ""),
    (r"\s*\(Ruth\)", ""),
    (r"\s*\(un colpo di fulmine - प्रेमाची वीज पडणे\)", ""),
    (r"\s*\(un colpo di fulmine\)", ""),
    (r"\s*\(Ely Cathedral\)", ""),
    (r"\s*\(Trinity College\)", ""),
    (r"\s*\(Non fidarti di nessuno, soprattutto degli uomini - 'कोणावरही विश्वास ठेवू नकोस, विशेषतः पुरुषांवर तर मुळीच नाही!'\)", "—म्हणजे 'कोणावरही विश्वास ठेवू नकोस, विशेषतः पुरुषांवर तर मुळीच नाही!'"),
    (r"\s*\(chicken\)", ""),
    (r"\s*\(kitchen\)", ""),
    (r"\s*\(apple crumble\)", ""),
    (r"\s*\(apple scrumble\)", ""),
    (r"\s*\(brainwave\)", ""),
    (r"\s*\(wavebrain\)", ""),
    (r"\s*\(St\. Valentine's Day\)", ""),
    (r"\s*\(The Whim\)", ""),
    (r"\s*\(clotted cream\)", ""),
    (r"\s*\(scones\)", ""),
    (r"\s*\(Pink Geranium\)", ""),
    (r"\s*\(Tickell Arms\)", ""),
    (r"\s*\(Heffers\)", ""),
    (r"\s*\(Kimberley Road\)", ""),
    (r"\s*\(VW Beetle\)", ""),
    (r"\s*\(windscreen\)", ""),
    (r"\s*\(coup de foudre - प्रेमाची वीज कोसळणे\)", ""),
    (r"\s*\(Non uscire di sera - 'रात्री घराबाहेर पडू नकोस!'\)", "—म्हणजे 'रात्री घराबाहेर पडू नकोस!'"),
    (r"\s*\(Non uscire mai sola di sera\.\.\. - 'रात्री कधीही एकटी बाहेर पडू नकोस, नेहमी मित्रमैत्रिणींच्या घोळक्यातच राहा!'\)", "—म्हणजे 'रात्री कधीही एकटी बाहेर पडू नकोस, नेहमी मित्रमैत्रिणींच्या घोळक्यातच राहा!'"),
    (r"\s*\(Non accettare mai bibite\.\.\. - 'ज्याला तू नीट ओळखत नाहीस, त्याच्याकडून कधीही पेय घेऊ नकोस!'\)", "—म्हणजे 'ज्याला तू नीट ओळखत नाहीस, त्याच्याकडून कधीही पेय घेऊ नकोस!'"),
    (r"\s*\(Vedrai quando torni a casa! - 'घरी परत येशील तेव्हा बघतोच तुला!'\)", "—म्हणजे 'घरी परत येशील तेव्हा बघतोच तुला!'"),
    (r"\s*\(Easter break\)", ""),
    (r"\s*\(Ninetta\)", ""),
    (r"\s*\(nonnas and nonnos\)", ""),
    (r"\s*\(zios and zias\)", ""),
    (r"\s*\(cugini\)", ""),
    (r"\s*\(cellar\)", ""),
    (r"\s*\(Bambini, state fermi! - 'मुलांनो, शांत बसा!'\)", "—म्हणजे 'मुलांनो, शांत बसा!'"),
    (r"\s*\(antipasti - स्टार्टर्स\)", ""),
    (r"\s*\(grappa - इटालियन मद्य\)", ""),
    (r"\s*\(Stefano and Paolina Maino\)", ""),
    (r"\s*\(Torino/Turin\)", ""),
    (r"\s*\(Orbassano\)", ""),
    (r"\s*\(Vicenza\)", ""),
    (r"\s*\(Asiago\)", ""),
    (r"\s*\(Lusiana\)", ""),
    (r"\s*\(Gomarolo\)", ""),
    (r"\s*\(Fiat\)", ""),
    (r"\s*\(Giovanni\)", ""),
    (r"\s*\(Sangano\)", ""),
    (r"\s*\(Nadia\)", ""),
    (r"\s*\(sulla parola - विश्वासावर दिलेला केवळ तोंडी शब्द\)", " म्हणजे विश्वासावर दिलेला तोंडी शब्द"),
    (r"\s*\(Signor Maino\)", ""),
    (r"\s*\(minestrone\)", ""),
    (r"\s*\(buona volontà di lavorare - काम करण्याची मनापासूनची तयारी\)", " म्हणजे काम करण्याची मनापासूनची तयारी"),
    (r"\s*\(pagnotta\)", ""),
    (r"\s*\(al dente - योग्य प्रमाणात शिजलेला, किंचित कडक\)", ""),
    (r"\s*\(Dovresti vergognarti\.\.\. - 'लाज वाटली पाहिजे तुला, जगात कित्येक निष्पाप मुलांना खायला अन्न मिळत नाही!'\)", "—म्हणजे 'लाज वाटली पाहिजे तुला, जगात कित्येक निष्पाप मुलांना खायला अन्न मिळत नाही!'"),
    (r"\s*\(gnocchi - चीज वा टोमॅटो सॉससोबत खाल्ला जाणारा पदार्थ\)", ""),
    (r"\s*\(tagliatelle\)", ""),
    (r"\s*\(Pino\)", ""),
    (r"\s*\(biscotti\)", ""),
    (r"\s*\(nougat किंवा almond croccante\)", ""),
    (r"\s*\(bumper cars\)", ""),
    (r"\s*\(Anouchka\)", ""),
    (r"\s*\(Domenico Modugno\)", ""),
    (r"\s*\(Piemonte\)", ""),
    (r"\s*\(Alps\)", ""),
    (r"\s*\(Nonno Marco\)", ""),
    (r"\s*\(Zio Mario - मारिओ काकांच्या\)", ""),
    (r"\s*\(Giardinetta Fiat\)", ""),
    (r"\s*\(Sestriere\)", ""),
    (r"\s*\(Agnelli\)", ""),
    (r"\s*\(Bersaglieri\)", ""),
    (r"\s*\(sergente maggiore\)", ""),
    (r"\s*\(Ritirata - माघार\)", " म्हणजे माघार"),
    (r"\s*\(General Winter\)", ""),
    (r"\s*\(compagnia\)", ""),
    (r"\s*\(Maino il Leone - 'सिंह माईनो'\)", " म्हणजेच 'सिंह माईनो'"),
    (r"\s*\(Christmas\)", ""),
    (r"\s*\(Cavaglia\)", ""),
    (r"\s*\(Dnepropetrovsk / Dnipro\)", ""),
    (r"\s*\(parish priest\)", ""),
    (r"\s*\(Alessandra\)", ""),
    (r"\s*\(Antonia\)", ""),
    (r"\s*\(Nadia Maria\)", "")
]

cleaned = text
for pattern, repl in replacements:
    cleaned = re.sub(pattern, repl, cleaned)

# Check remaining brackets
remaining = re.findall(r'\([^)]*[A-Za-z]+[^)]*\)', cleaned)
print(f"Remaining English brackets: {len(remaining)}")
for r in remaining:
    print("  Remaining:", r)

with open('belonging_marathi/data/mr/chapter1.txt', 'w', encoding='utf-8') as f:
    f.write(cleaned)

print("Saved clean Chapter 1 successfully.")
