#!/usr/bin/env python3
"""
Create claim cross-reference index mapping claim → VA report, hipotez kartı, tur.
Reads from chunk files and CURUTULMUS, extracts the "Bağlı" column.
"""

import re
from pathlib import Path
from collections import defaultdict

CHUNK_FILES = [
    Path("02_LITERATUR/iddia-defteri-0001-0500.md"),
    Path("02_LITERATUR/iddia-defteri-0501-1000.md"),
]
CURUTULMUS_FILE = Path("02_LITERATUR/iddia-defteri-CURUTULMUS.md")
OUTPUT_FILE = Path("02_LITERATUR/claim-index.md")

def parse_claims_from_file(filepath):
    """Parse claims from a file, returning list of (claim_id, bağlı_col)."""
    if not filepath.exists():
        return []
    lines = filepath.read_text(encoding='utf-8').splitlines()
    claims = []
    for line in lines:
        # Match claim table rows: | **123** | ... | ... | ... | ... | ... | ... | S00.1 |
        match = re.match(r'^\|\s*\*\*(\d+)\*\*\s*\|(.+)\|$', line)
        if match:
            claim_id = int(match.group(1))
            # Split by | to get columns
            cols = match.group(2).split('|')
            if len(cols) >= 7:
                # Columns: İddia, Katman, Kanıt, Nedensellik, Aleyhte, Durum, Bağlı
                bagli = cols[6].strip()
                claims.append((claim_id, bagli))
    return claims

def categorize_reference(ref):
    """Categorize a reference string into type."""
    ref = ref.strip()
    if not ref or ref == '—':
        return []
    refs = []
    # Split by common separators
    parts = re.split(r'[,\s]+', ref)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith('VA-') or p.startswith('va-'):
            refs.append(('VA', p.upper()))
        elif p.startswith('S') and p[1:].replace('.', '').isdigit():
            refs.append(('SORU', p))
        elif p.startswith('Ç-') or p.startswith('C-'):
            refs.append(('ÇELİŞKİ', p))
        elif p.startswith('H') and p[1:].isdigit():
            refs.append(('HIPOTEZ', p))
        elif p.startswith('T') and p[1:].isdigit():
            refs.append(('TUR', p))
        elif p.startswith('G') and p[1:].isdigit():
            refs.append(('GÖZLEM', p))
        elif p.startswith('K') and p[1:].isdigit():
            refs.append(('KURAL', p))
        elif p.startswith('R') and p[1:].isdigit():
            refs.append(('KURAL', p))
        elif p.startswith('Z') and p[1:].isdigit():
            refs.append(('Z-SKOR', p))
        elif p.startswith('M-') or (p.startswith('M') and len(p) > 1 and p[1:].isdigit()):
            refs.append(('MODEL', p))
        elif p.startswith('D') and p[1:].isdigit():
            refs.append(('DERECE', p))
        elif p.startswith('E') and p[1:].isdigit():
            refs.append(('DERECE', p))
    return refs

def main():
    all_claims = {}
    
    # Parse all files
    for cf in CHUNK_FILES:
        for claim_id, bagli in parse_claims_from_file(cf):
            all_claims[claim_id] = bagli
    
    if CURUTULMUS_FILE.exists():
        for claim_id, bagli in parse_claims_from_file(CURUTULMUS_FILE):
            if claim_id not in all_claims:
                all_claims[claim_id] = bagli
    
    print(f"Total unique claims: {len(all_claims)}")
    
    # Build cross-reference index
    va_refs = defaultdict(list)
    hipotez_refs = defaultdict(list)
    tur_refs = defaultdict(list)
    soru_refs = defaultdict(list)
    celiski_refs = defaultdict(list)
    gozlem_refs = defaultdict(list)
    kural_refs = defaultdict(list)
    model_refs = defaultdict(list)
    derece_refs = defaultdict(list)
    zskor_refs = defaultdict(list)
    
    for claim_id, bagli in sorted(all_claims.items()):
        refs = categorize_reference(bagli)
        for ref_type, ref_val in refs:
            if ref_type == 'VA':
                va_refs[ref_val].append(claim_id)
            elif ref_type == 'HIPOTEZ':
                hipotez_refs[ref_val].append(claim_id)
            elif ref_type == 'TUR':
                tur_refs[ref_val].append(claim_id)
            elif ref_type == 'SORU':
                soru_refs[ref_val].append(claim_id)
            elif ref_type == 'ÇELİŞKİ':
                celiski_refs[ref_val].append(claim_id)
            elif ref_type == 'GÖZLEM':
                gozlem_refs[ref_val].append(claim_id)
            elif ref_type == 'KURAL':
                kural_refs[ref_val].append(claim_id)
            elif ref_type == 'MODEL':
                model_refs[ref_val].append(claim_id)
            elif ref_type == 'DERECE':
                derece_refs[ref_val].append(claim_id)
            elif ref_type == 'Z-SKOR':
                zskor_refs[ref_val].append(claim_id)
    
    # Write index file
    lines = [
        '# İDDİA ÇAPRAZ-ATIF İNDEKSİ\n\n',
        f'> Otomatik oluşturuldu: {len(all_claims)} benzersiz iddia\n',
        '> Kaynak: chunk dosyaları + CURUTULMUS\n\n',
        '## İstatistikler\n\n',
        f'- Toplam iddia: {len(all_claims)}\n',
        f'- VA raporu atıflı: {len(va_refs)}\n',
        f'- Hipotez kartı atıflı: {len(hipotez_refs)}\n',
        f'- Tur atıflı: {len(tur_refs)}\n',
        f'- Soru haritası atıflı: {len(soru_refs)}\n',
        f'- Çelişki atıflı: {len(celiski_refs)}\n',
        f'- Gözlem atıflı: {len(gozlem_refs)}\n',
        f'- Kural atıflı: {len(kural_refs)}\n',
        f'- Model atıflı: {len(model_refs)}\n',
        f'- Derece (D/E) atıflı: {len(derece_refs)}\n',
        f'- Z-skor atıflı: {len(zskor_refs)}\n\n',
    ]
    
    # VA Reports
    lines.append('## VA Raporlarına Göre İddialar\n\n')
    for va in sorted(va_refs.keys()):
        claims = sorted(va_refs[va])
        lines.append(f'### {va}\n\n')
        lines.append(f'İddialar: {", ".join(f"[{c}](#iddia-{c})" for c in claims)}\n\n')
    
    # Hipotez Kartları
    lines.append('## Hipotez Kartlarına Göre İddialar\n\n')
    for h in sorted(hipotez_refs.keys()):
        claims = sorted(hipotez_refs[h])
        lines.append(f'### {h}\n\n')
        lines.append(f'İddialar: {", ".join(f"[{c}](#iddia-{c})" for c in claims)}\n\n')
    
    # Turlar
    lines.append('## Turlara Göre İddialar\n\n')
    for t in sorted(tur_refs.keys(), key=lambda x: int(x[1:])):
        claims = sorted(tur_refs[t])
        lines.append(f'### {t}\n\n')
        lines.append(f'İddialar: {", ".join(f"[{c}](#iddia-{c})" for c in claims)}\n\n')
    
    # Soru Haritası
    lines.append('## Soru Haritasına Göre İddialar\n\n')
    for s in sorted(soru_refs.keys()):
        claims = sorted(soru_refs[s])
        lines.append(f'### {s}\n\n')
        lines.append(f'İddialar: {", ".join(f"[{c}](#iddia-{c})" for c in claims)}\n\n')
    
    # Çelişkiler
    lines.append('## Çelişkilerle Göre İddialar\n\n')
    for c in sorted(celiski_refs.keys()):
        claims = sorted(celiski_refs[c])
        lines.append(f'### {c}\n\n')
        lines.append(f'İddialar: {", ".join(f"[{c}](#iddia-{c})" for c in claims)}\n\n')
    
    # Full claim table
    lines.append('## Tam İddia Listesi (Bağlı Sütunu)\n\n')
    lines.append('| İddia | Bağlı |\n')
    lines.append('|-------|-------|\n')
    for claim_id in sorted(all_claims.keys()):
        bagli = all_claims[claim_id]
        lines.append(f'| {claim_id} | {bagli} |\n')
    
    OUTPUT_FILE.write_text(''.join(lines), encoding='utf-8')
    print(f"Created {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size/1024:.1f} KB)")

if __name__ == '__main__':
    main()