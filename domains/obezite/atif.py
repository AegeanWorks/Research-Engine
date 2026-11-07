# -*- coding: utf-8 -*-
"""İddia atıfı çıkarıcı — künye gürültüsünü ayıklayarak.

NEDEN: ilk sürüm `\\b([1-9]\\d{1,2})\\b` kullandı ve SAYFA NUMARALARINI iddia atfı sandı:
  74 -> "90"  : Endocrinology. 1976;98(1):84-90
  120 -> "448": Nature. 2020;578(7795):444-448
  76 -> "476" : Metabolism. 1999;48(4):472-476
Eyleme dönük kümede %100 yanlış pozitif. Bu modül, künye desenlerini ÖNCE siler.
"""
import re

_TEMIZLE = [
    (re.compile(r'\[[^\]]*\]\([^)]*\)'), ' '),            # markdown link
    (re.compile(r'PMID[:\s]*\d+', re.I), ' '),
    (re.compile(r'PMC\d+', re.I), ' '),
    (re.compile(r'NCT\d+', re.I), ' '),
    (re.compile(r'doi[^\s·|]*', re.I), ' '),
    (re.compile(r'10\.\d{4,}/[^\s·|)]*'), ' '),      # DOI govdesi: 10.1038/s41586-...
    (re.compile(r'10\.\d+'), ' '),                   # artik DOI onu
    (re.compile(r'\d{4}\s*;\s*\d+\s*(\([^)]*\))?\s*:\s*[\dEe\-–]+'), ' '),  # 2020;578(7795):444-448
    (re.compile(r'\b(19|20)\d{2}\b'), ' '),               # yıl
    (re.compile(r'\b\d+\s*[-–]\s*\d+\b'), ' '),           # sayfa/aralık
    (re.compile(r'\bv?\d+\s*\(\d+\)'), ' '),              # cilt(sayı)
    (re.compile(r'[A-ZÇĞİÖŞÜ][\w\.\-]*\s+(ve\s+ark\.|et\s+al\.?)'), ' '),   # yazar
    (re.compile(r'(VA|Ç|K|T|H|G|Z|D|E|L)\-?\d+', re.I), ' '),               # proje kodlari
]

def atiflar(bagli_sutun):
    """Bağlı sütunundan iddia numaralarını çıkar (künye gürültüsü ayıklanmış)."""
    s = bagli_sutun
    for rx, yerine in _TEMIZLE:
        s = rx.sub(yerine, s)
    # Kalan: virgul/orta-nokta ile ayrilmis yalin sayilar
    return sorted({int(x) for x in re.findall(r'(?<![\w\-])([1-9]\d{0,2})(?![\w\-])', s)})
