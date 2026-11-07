#!/usr/bin/env python3
"""
Backfill script for claims 482-597.
Extracts "İddia XXX" references from tur-85 through tur-117 files
and creates skeleton entries in iddia-defteri.md.

Usage: python 08_ARACLAR/backfill_claims.py [--yes]
"""

import re
import sys
from pathlib import Path
from datetime import date

KOK = Path(__file__).resolve().parents[3] / "obezite-mekanizma-projesi"
SORULAR = KOK / "01_SORULAR"
DEFTER = KOK / "02_LITERATUR" / "iddia-defteri.md"

TUR_ARALIK = range(85, 118)

def mevcut_iddialar():
    if not DEFTER.exists():
        return set()
    icerik = DEFTER.read_text(encoding="utf-8")
    ids = set()
    for satir in icerik.splitlines():
        m = re.match(r'^\| \*\*(\d+)\*\*', satir)
        if m:
            ids.add(int(m.group(1)))
    return ids

def turdan_iddialar(tur_no):
    dosyalar = list(SORULAR.glob(f"tur-{tur_no}-*.md"))
    if not dosyalar:
        dosyalar = list((SORULAR / "KARANTINA").glob(f"tur-{tur_no}-*.md"))
    if not dosyalar:
        return []
    icerik = dosyalar[0].read_text(encoding="utf-8")
    ids = []
    for m in re.finditer(r'[İI]ddia\s+(\d+)', icerik):
        ids.append(int(m.group(1)))
    return sorted(set(ids))

def main():
    auto_yes = "--yes" in sys.argv
    
    print("=" * 60)
    print("BACKFILL SCRIPT: Claims 482-597")
    print("=" * 60)
    
    mevcut = mevcut_iddialar()
    print(f"Mevcut iddia sayisi: {len(mevcut)}")
    print(f"Max mevcut iddia: {max(mevcut) if mevcut else 0}")
    
    tum_iddialar = set()
    for tur_no in TUR_ARALIK:
        ids = turdan_iddialar(tur_no)
        if ids:
            print(f"  Tur {tur_no}: {len(ids)} iddia referansi -> {ids[:10]}{'...' if len(ids) > 10 else ''}")
            tum_iddialar.update(ids)
    
    print(f"\nToplam benzersiz iddia referansi (tur 85-117): {len(tum_iddialar)}")
    
    hedef_aralik = set(range(482, 598))
    eksik = sorted(hedef_aralik - mevcut)
    print(f"\n482-597 araliginda eksik olan: {len(eksik)} iddia")
    
    if not eksik:
        print("Eksik iddia yok, backfill gerekmiyor.")
        return
    
    print(f"Ilk 20 eksik: {eksik[:20]}")
    
    if not auto_yes:
        print("\nBu iddialar icin iskelet girisleri olusturulacak.")
        print("Her giris: D/E=?, K5=pending, backfill-gerektirir etiketiyle.")
        cevap = input("Devam etmek icin 'evet' yazin: ").strip().lower()
        if cevap != 'evet':
            print("Iptal edildi.")
            return
    
    defter_icerik = DEFTER.read_text(encoding="utf-8")
    
    yeni_satirlar = []
    bugun = date.today().isoformat()
    
    for id_no in eksik:
        kaynak_tur = None
        kaynak_dosya = None
        for tur_no in TUR_ARALIK:
            if id_no in turdan_iddialar(tur_no):
                kaynak_tur = tur_no
                dosyalar = list(SORULAR.glob(f"tur-{tur_no}-*.md"))
                if not dosyalar:
                    dosyalar = list((SORULAR / "KARANTINA").glob(f"tur-{tur_no}-*.md"))
                if dosyalar:
                    kaynak_dosya = dosyalar[0].name
                break
        
        if kaynak_dosya:
            tur_ref = f"[T{kaynak_tur}](../01_SORULAR/{kaynak_dosya})"
        elif kaynak_tur:
            tur_ref = f"[T{kaynak_tur}](../01_SORULAR/tur-{kaynak_tur}-...md)"
        else:
            tur_ref = "kaynak tur belirlenemedi"
        
        satir = f"| **{id_no}** | **BACKFILL GEREKTIRIR** -- Tur {kaynak_tur or '?'}-den 'İddia {id_no}' referansi bulundu; icerik henuz dogrulanmadi, deftere islenmedi. | L? | **D?/E?** -- backfill-gerektirir | ? | K5 aleyhte arama yapilmamis | **backfill-bekliyor** | {tur_ref} |"
        yeni_satirlar.append(satir)
    
    # Defterin sonuna ekle (aktif defter tablosunun sonundan önce, çürütülmüş bölümden önce)
        satirlar = defter_icerik.splitlines()
    
        # "ÇÜRÜTÜLMÜŞ" veya "curutulmus" başlığını bul
        curutulmus_indeksi = len(satirlar)
        for i, satir in enumerate(satirlar):
            if "ÇÜRÜTÜLMÜŞ" in satir.upper() or "CURUTULMUS" in satir.upper():
                curutulmus_indeksi = i
                break
    
        # Aktif defter tablosunun son satırını bul (çürütülmüş bölümden önce)
        ekleme_indeksi = curutulmus_indeksi
        for i in range(curutulmus_indeksi - 1, -1, -1):
            if satirlar[i].strip().startswith("|") and satirlar[i].strip().endswith("|"):
                ekleme_indeksi = i + 1
                break
    
        # Eğer çürütülmüş bölüm yoksa, dosya sonunu kullan
        if curutulmus_indeksi == len(satirlar):
            ekleme_indeksi = len(satirlar)
            for i in range(len(satirlar) - 1, -1, -1):
                if satirlar[i].strip().startswith("|") and satirlar[i].strip().endswith("|"):
                    ekleme_indeksi = i + 1
                    break
    
        yeni_icerik = satirlar[:ekleme_indeksi] + yeni_satirlar + satirlar[ekleme_indeksi:]
    
    yedek = DEFTER.with_suffix(f".md.backfill-{bugun}")
    DEFTER.write_text(defter_icerik, encoding="utf-8")
    print(f"\nYedek alindi: {yedek.name}")
    
    DEFTER.write_text("\n".join(yeni_icerik), encoding="utf-8")
    print(f"[OK] {len(yeni_satirlar)} iskelet giris eklendi.")
    print(f"Defter guncellendi: {DEFTER}")

if __name__ == "__main__":
    main()