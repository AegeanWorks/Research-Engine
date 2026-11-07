#!/usr/bin/env python3
"""
Split iddia-defteri.md by claim range (500 claims per file).
Creates:
- 02_LITERATUR/iddia-defteri-index.md (master index)
- 02_LITERATUR/iddia-defteri-0001-0500.md (claims 1-500)
- 02_LITERATUR/iddia-defteri-0501-1000.md (claims 501-1000)
"""

import re
from pathlib import Path

SOURCE_FILE = Path("02_LITERATUR/iddia-defteri.md")
INDEX_FILE = Path("02_LITERATUR/iddia-defteri-index.md")
CHUNK_1_FILE = Path("02_LITERATUR/iddia-defteri-0001-0500.md")
CHUNK_2_FILE = Path("02_LITERATUR/iddia-defteri-0501-1000.md")

def parse_claims(lines):
    """Parse claims from the markdown table lines."""
    claims = []
    in_table = False
    for i, line in enumerate(lines):
        if line.strip().startswith('| # | İddia'):
            in_table = True
            continue
        if in_table and line.strip().startswith('|---'):
            continue
        if in_table:
            match = re.match(r'^\|\s*\*\*(\d+)\*\*\s*\|', line)
            if match:
                claim_id = int(match.group(1))
                claims.append((claim_id, i, line))
            elif line.strip() and not line.strip().startswith('|'):
                # End of table
                break
    return claims

def main():
    lines = SOURCE_FILE.read_text(encoding='utf-8').splitlines(keepends=True)
    
    # Find the header (everything before the first table)
    header_end = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('| # | İddia'):
            header_end = i
            break
    
    header = lines[:header_end]
    
    # Parse all claims
    claims = parse_claims(lines)
    print(f"Found {len(claims)} claims")
    
    # Split claims into chunks
    chunk1_claims = [c for c in claims if 1 <= c[0] <= 500]
    chunk2_claims = [c for c in claims if 501 <= c[0] <= 1000]
    
    print(f"Chunk 1 (1-500): {len(chunk1_claims)} claims")
    print(f"Chunk 2 (501-1000): {len(chunk2_claims)} claims")
    
    # Find the end of the main claims table (before ÇELİŞKİLER section)
    main_table_end = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith('### ★ YENİ ÇELİŞKİLER'):
            main_table_end = i
            break
    
    # Get the sections after the main table
    post_table = lines[main_table_end:]
    
    # Build chunk 1: header + claims 1-500
    chunk1_lines = header[:]
    chunk1_lines.append('## A. AKTİF İDDİALAR (1-500)\n\n')
    chunk1_lines.append('| # | İddia (nicel, model sistemi ile) | Katman | En güçlü kanıt (D/E) | Nedensellik (K6) | Aleyhte veri | Durum | Bağlı |\n')
    chunk1_lines.append('|---|---|---|---|---|---|---|---|\n')
    for claim_id, _, line in chunk1_claims:
        chunk1_lines.append(line)
    chunk1_lines.append('\n')
    # Add a note about continuation
    chunk1_lines.append('> **Not:** İddialar 501-1000 için bkz. [iddia-defteri-0501-1000.md](iddia-defteri-0501-1000.md)\n')
    chunk1_lines.append('> **Ana indeks:** [iddia-defteri-index.md](iddia-defteri-index.md)\n')
    
    # Build chunk 2: header + claims 501-1000 + post-table sections
    chunk2_lines = header[:]
    chunk2_lines.append('## A. AKTİF İDDİALAR (501-1000)\n\n')
    chunk2_lines.append('| # | İddia (nicel, model sistemi ile) | Katman | En güçlü kanıt (D/E) | Nedensellik (K6) | Aleyhte veri | Durum | Bağlı |\n')
    chunk2_lines.append('|---|---|---|---|---|---|---|---|\n')
    for claim_id, _, line in chunk2_claims:
        chunk2_lines.append(line)
    chunk2_lines.append('\n')
    # Add post-table sections
    chunk2_lines.extend(post_table)
    chunk2_lines.append('\n')
    chunk2_lines.append('> **Not:** İddialar 1-500 için bkz. [iddia-defteri-0001-0500.md](iddia-defteri-0001-0500.md)\n')
    chunk2_lines.append('> **Ana indeks:** [iddia-defteri-index.md](iddia-defteri-index.md)\n')
    
    # Build index file
    index_lines = [
        '# İDDİA DEFTERİ — ANA İNDEKS\n\n',
        '> Bu dosya, iddia defterinin parçalanmış dosyalarını haritalar.\n',
        '> Her chunk dosyası bağımsız okunabilir; kontrol.ps1 bunları birleştirir.\n\n',
        '## Chunk Haritası\n\n',
        '| Dosya | Aralık | İddia Sayısı | Açıklama |\n',
        '|-------|--------|--------------|----------|\n',
        f'| [iddia-defteri-0001-0500.md](iddia-defteri-0001-0500.md) | 1-500 | {len(chunk1_claims)} | İlk 500 iddia (temel epidemioloji, VA-01/02/03/04/05) |\n',
        f'| [iddia-defteri-0501-1000.md](iddia-defteri-0501-1000.md) | 501-1000 | {len(chunk2_claims)} | İddialar 501+ (mekanizma, farmakoloji, çelişkiler, çürütülmüş) |\n',
        '\n',
        '## Kullanım\n\n',
        '- **Tam defter için:** `kontrol.ps1` otomatik olarak chunk dosyalarını birleştirir\n',
        '- **Hızlı arama için:** İlgili chunk dosyasını doğrudan açın\n',
        '- **Çapraz atıf:** İddia numaraları chunk sınırlarını aşabilir (ör. 499 → 501 atıfı)\n\n',
        '## Notlar\n\n',
        '- Aralık 482-597 **boş** (yapısal boşluk, DÜZELTME-2026-10-09 belgesine bakın)\n',
        '- Çürütülmüş iddialar ayrı dosyada: `iddia-defteri-CURUTULMUS.md`\n',
        '- Mükerrer iddialar (27 adet) `00_ARSIV/iddia-duplicates-<date>.md` taşındı\n',
    ]
    
    # Write files
    CHUNK_1_FILE.write_text(''.join(chunk1_lines), encoding='utf-8')
    CHUNK_2_FILE.write_text(''.join(chunk2_lines), encoding='utf-8')
    INDEX_FILE.write_text(''.join(index_lines), encoding='utf-8')
    
    print(f"Created {CHUNK_1_FILE} ({CHUNK_1_FILE.stat().st_size/1024:.1f} KB)")
    print(f"Created {CHUNK_2_FILE} ({CHUNK_2_FILE.stat().st_size/1024:.1f} KB)")
    print(f"Created {INDEX_FILE} ({INDEX_FILE.stat().st_size/1024:.1f} KB)")

if __name__ == '__main__':
    main()