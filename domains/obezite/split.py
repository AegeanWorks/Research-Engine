import re
import os

source_file = r'02_LITERATUR\iddia-defteri.md'
active_file = r'02_LITERATUR\iddia-defteri-AKTIF.md'
quarantine_file = r'02_LITERATUR\iddia-defteri-CURUTULMUS.md'

with open(source_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

active_lines = []
quarantine_lines = []

# Keywords that indicate a claim is falsified or retracted
# Looking specifically in the "Derece" or "Hüküm" columns, but a global row match is usually safe enough if it's explicitly marked.
quarantine_keywords = [
    'falsified', 
    'GERİ ÇEKİLDİ', 
    'geçersiz', 
    'çürütüldü', 
    'yanlışlandı',
    'replike edilemedi'
]

claim_pattern = re.compile(r'^\|\s*\*\*\d+\*\*\s*\|')

for line in lines:
    if claim_pattern.match(line):
        # It's a claim row
        is_quarantined = any(kw.lower() in line.lower() for kw in quarantine_keywords)
        
        # Exception: if it says "falsifikasyon" in the claim title but the claim itself is "kanıtlı", it shouldn't be quarantined.
        # Let's be more precise: check if the 'Derece' or 'Hüküm' contains the keywords.
        # A claim row has columns separated by '|'. 
        # Format: | ID | İddia | Sınıf | Kanıt Derecesi | Sentez Yönü | Hüküm | Kaynaklar |
        # Columns: 1:ID, 2:İddia, 3:Sınıf, 4:Kanıt, 5:Yön, 6:Hüküm, 7:Kaynaklar
        cols = line.split('|')
        if len(cols) >= 7:
            hukum_col = cols[6].lower()
            yon_col = cols[5].lower()
            if any(kw.lower() in hukum_col for kw in quarantine_keywords) or any(kw.lower() in yon_col for kw in quarantine_keywords):
                quarantine_lines.append(line)
            else:
                active_lines.append(line)
        else:
            # Fallback
            active_lines.append(line)
    else:
        # Non-claim row (headers, empty lines, section titles)
        active_lines.append(line)
        quarantine_lines.append(line)

with open(active_file, 'w', encoding='utf-8') as f:
    f.writelines(active_lines)

with open(quarantine_file, 'w', encoding='utf-8') as f:
    f.writelines(quarantine_lines)

print(f"Total lines: {len(lines)}")
print(f"Active claims/lines: {len(active_lines)}")
print(f"Quarantined claims/lines: {len(quarantine_lines)}")
