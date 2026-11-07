#!/usr/bin/env python3
"""
Deduplicate defter claims across chunk files and CURUTULMUS.
Keeps first occurrence (in chunk files), moves second to 00_ARSIV/iddia-duplicates-<date>.md with annotation.
"""

import re
from datetime import datetime
from pathlib import Path

CHUNK_FILES = [
    Path("02_LITERATUR/iddia-defteri-0001-0500.md"),
    Path("02_LITERATUR/iddia-defteri-0501-1000.md"),
]
CURUTULMUS_FILE = Path("02_LITERATUR/iddia-defteri-CURUTULMUS.md")
ARCHIVE_DIR = Path("00_ARSIV")
DATE_STR = datetime.now().strftime("%Y-%m-%d")
DUPLICATES_FILE = ARCHIVE_DIR / f"iddia-duplicates-{DATE_STR}.md"

def parse_claims_from_file(filepath):
    """Parse all claim lines from a file, returning list of (claim_id, line, line_num)."""
    if not filepath.exists():
        return []
    lines = filepath.read_text(encoding='utf-8').splitlines(keepends=True)
    claims = []
    for i, line in enumerate(lines):
        match = re.match(r'^\|\s*\*\*(\d+)\*\*\s*\|', line)
        if match:
            claim_id = int(match.group(1))
            claims.append((claim_id, line, i))
    return claims

def get_all_lines(filepath):
    """Get all lines from a file."""
    if not filepath.exists():
        return []
    return filepath.read_text(encoding='utf-8').splitlines(keepends=True)

def write_lines(filepath, lines):
    """Write lines to a file."""
    filepath.write_text(''.join(lines), encoding='utf-8')

def main():
    # Ensure archive directory exists
    ARCHIVE_DIR.mkdir(exist_ok=True)
    
    # Parse claims from chunk files (first occurrence)
    chunk_claims = {}  # claim_id -> (filepath, line, line_num)
    chunk_all_lines = {}  # filepath -> all lines
    
    for cf in CHUNK_FILES:
        chunk_all_lines[cf] = get_all_lines(cf)
        for claim_id, line, line_num in parse_claims_from_file(cf):
            if claim_id not in chunk_claims:
                chunk_claims[claim_id] = (cf, line, line_num)
    
    # Parse claims from CURUTULMUS (potential duplicates)
    curutulmus_lines = get_all_lines(CURUTULMUS_FILE)
    curutulmus_claims = parse_claims_from_file(CURUTULMUS_FILE)
    
    # Find duplicates
    duplicates = []  # (claim_id, chunk_info, curutulmus_info)
    for claim_id, line, line_num in curutulmus_claims:
        if claim_id in chunk_claims:
            duplicates.append((claim_id, chunk_claims[claim_id], (CURUTULMUS_FILE, line, line_num)))
    
    print(f"Found {len(duplicates)} duplicate claim IDs")
    
    if not duplicates:
        print("No duplicates to process")
        return
    
    # Build duplicates archive content
    archive_lines = [
        f'# İDDİA DEFTERİ — MÜKERRER KAYITLAR (Arşiv: {DATE_STR})\n\n',
        f'> Bu dosya `deduplicate_defter.py` tarafından otomatik oluşturuldu.\n',
        f'> **Kural:** İlk oluşum (chunk dosyalarında) korunur, ikinci oluşum (CURUTULMUS) buraya taşınır.\n',
        f'> Orijinal satır numaraları ve dosya kaynakları not edilmiştir.\n\n',
        '## Mükerrer İddialar\n\n',
        '| İddia | Chunk Dosyası | Chunk Satır | CURUTULMUS Satır | Not |\n',
        '|-------|---------------|-------------|------------------|-----|\n',
    ]
    
    # Remove duplicates from CURUTULMUS (keep track of lines to remove)
    lines_to_remove = set()
    for claim_id, (chunk_file, chunk_line, chunk_line_num), (cur_file, cur_line, cur_line_num) in duplicates:
        lines_to_remove.add(cur_line_num)
        archive_lines.append(
            f'| {claim_id} | {chunk_file.name} | {chunk_line_num + 1} | {cur_line_num + 1} | '
            f'İlk oluşum chunk dosyasında; CURUTULMUS\'tan taşındı |\n'
        )
        # Also include the actual claim content for reference
        archive_lines.append(f'\n### İddia {claim_id} (CURUTULMUS\'tan taşınan satır)\n\n')
        archive_lines.append('```markdown\n')
        archive_lines.append(cur_line.rstrip() + '\n')
        archive_lines.append('```\n\n')
    
    # Write duplicates archive
    DUPLICATES_FILE.write_text(''.join(archive_lines), encoding='utf-8')
    print(f"Created duplicates archive: {DUPLICATES_FILE}")
    
    # Remove duplicate lines from CURUTULMUS
    new_curutulmus_lines = [line for i, line in enumerate(curutulmus_lines) if i not in lines_to_remove]
    write_lines(CURUTULMUS_FILE, new_curutulmus_lines)
    print(f"Removed {len(lines_to_remove)} duplicate lines from {CURUTULMUS_FILE}")
    
    # Verify no duplicates remain
    all_claims = {}
    for cf in CHUNK_FILES:
        for claim_id, line, line_num in parse_claims_from_file(cf):
            if claim_id in all_claims:
                print(f"WARNING: Duplicate still in chunks: {claim_id}")
            all_claims[claim_id] = (cf, line_num)
    
    for claim_id, line, line_num in parse_claims_from_file(CURUTULMUS_FILE):
        if claim_id in all_claims:
            print(f"WARNING: Duplicate still exists: {claim_id} in CURUTULMUS")
        all_claims[claim_id] = (CURUTULMUS_FILE, line_num)
    
    print(f"Total unique claims after deduplication: {len(all_claims)}")
    print("Deduplication complete!")

if __name__ == '__main__':
    main()