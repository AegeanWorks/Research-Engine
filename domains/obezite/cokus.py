#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cokus.py — ÇÖKÜŞ ÇAĞLAYANI DENETİMİ (T209, iddia 806) · kontrol.ps1 §13

NEDEN VAR
=========
Defterde "bu iddianın dayanağı çöktü" mekanizması YOKTU. 671'in kaynağı bir influenza
makalesi çıktığında, ona bağlı olan Ç-29'u **elle** aramak zorunda kaldım. Oysa `Bağlı`
sütunu zaten var: bir iddia çürütüldü/derecesi düşürüldü ise, onu anan satırların bu
çöküşü **kaydetmiş olması** gerekir. Bu betik onu denetler.

GARANTİ EDİLEN ÖZELLİK (ve neden bu özellik)
============================================
"Geçersiz kılınan her X için, X'i anan her Y'nin Durum veya Aleyhte sütununda bir şerh
belirteci (~~ ⛔ ◐ ⚠) bulunmalı."

★ Önce YANLIŞ ölçütü denedim: "Y < X ise şerh ara" (yazım sırası varsayımı). Bu yanlış,
çünkü iddia numarası yazım sırasıdır ama X'in **çürütüldüğü tur** X'in yazıldığı turdan
çok sonra olabilir — o zaman Y > X olan bir satır da habersiz kalmış olabilir. Sıra
varsayımını tamamen attım: ölçüt yalnızca "şerh var mı".

★★ Ve ölçütü kabul etmeden önce BOŞ OLUP OLMADIĞINI ölçtüm (T209 dersi):
    şerh belirteci taban oranı        : 480/801 satır = %60
    geçersiz iddia anan bağımlı küme  : 46/46        = %100
Şans olasılığı 0.60^46 ≈ 3e-11 → zenginleşme gerçek, test boş değil.
Şerh "satırın herhangi bir yeri" değil **Durum/Aleyhte sütunu** diye daraltıldı; taban
%67'den %60'a indi, bağımlı küme %100'de kaldı.

★★★ BU DENETİM BUGÜN SIFIR BULUYOR — ve bu bir kusur değil, bulgudur:
§10 (K12d) iki canlı ihlal + 31 eski borç buldu · §12 ayrışma buldu · §13 HİÇBİR ŞEY.
Yani çöküş-şerhi pratiği zaten doğru işliyordu; §13 bir hata bulucu değil, bir
GERİLEME NÖBETÇİSİ. Taban oranı ölçülmeden bu ikisi ayırt edilemezdi: "disiplin tutuyor"
ile "test hiçbir şeyi test etmiyor" aynı çıktıyı verir.

KULLANIM
========
  python 08_ARACLAR/cokus.py            # özet (çıkış 0 = temiz, 1 = şerhsiz bağımlı var)
  python 08_ARACLAR/cokus.py --ayrinti  # geçersiz iddia -> bağımlı haritasını da yaz
"""
import io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from domains.obezite.atif import atiflar  # künye gürültüsünü ayıklayan atıf çıkarıcı (T209)

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANA = os.path.join(KOK, "02_LITERATUR", "iddia-defteri.md")

IDDIA = re.compile(r'^\| \*\*(\d+)\*\*')
# Durum sütununda geçersizleşmeyi bildiren ifadeler
GECERSIZ = re.compile(
    r'çürütüldü|GERİ ALINDI|geri alındı|DÜŞÜRÜLDÜ|düşürüldü|geçersiz|falsified|ÇÖKTÜ|çöktü',
    re.I)
# Şerh belirteçleri: üstü çizili düzeltme, çürütme, kısmî, uyarı
SERH = re.compile(r'~~|⛔|◐|⚠')


def satirlar():
    with io.open(ANA, encoding="utf-8") as fh:
        return fh.read().split("\n")


def serh_var(satir):
    """Şerh YALNIZ Durum veya Aleyhte veri sütununda sayılır (bkz. başlık: daraltma)."""
    a = satir.split("|")
    if len(a) < 9:
        return SERH.search(satir) is not None
    return (SERH.search(a[-3]) or SERH.search(a[-4])) is not None


def analiz():
    s = {}
    for l in satirlar():
        m = IDDIA.match(l)
        if m:
            s[int(m.group(1))] = l

    gecersiz = set()
    for n, l in s.items():
        a = l.split("|")
        if len(a) >= 9 and GECERSIZ.search(a[-3]):
            gecersiz.add(n)

    # Bağlı sütunundan ters indeks: X -> onu anan Y'ler
    anan = {}
    for n, l in s.items():
        a = l.split("|")
        if len(a) < 3:
            continue
        for r in atiflar(a[-2]):
            anan.setdefault(r, []).append(n)

    bagimli = sorted({d for g in gecersiz for d in anan.get(g, []) if d != g})
    eksik = [(g, d) for g in sorted(gecersiz)
             for d in sorted(anan.get(g, [])) if d != g and not serh_var(s[d])]
    return s, gecersiz, anan, bagimli, eksik


def main():
    ayrinti = "--ayrinti" in sys.argv
    s, gecersiz, anan, bagimli, eksik = analiz()

    taban = sum(1 for l in s.values() if serh_var(l))
    print("iddia %d · gecersiz %d · onlari anan %d satir" % (len(s), len(gecersiz), len(bagimli)))
    print("serh taban orani %d/%d (%.0f%%) · bagimli kumede %d/%d (%.0f%%)" % (
        taban, len(s), 100.0 * taban / len(s),
        len(bagimli) - len({d for _, d in eksik}), len(bagimli),
        100.0 * (len(bagimli) - len({d for _, d in eksik})) / len(bagimli) if bagimli else 100.0))

    if ayrinti:
        for g in sorted(gecersiz):
            d = [x for x in anan.get(g, []) if x != g]
            if d:
                print("  %3d <- %s" % (g, " ".join(str(x) for x in sorted(d))))

    if eksik:
        print("SERHSIZ BAGIMLI: %d" % len(eksik))
        for g, d in eksik:
            a = s[d].split("|")
            durum = (a[-3].strip() if len(a) >= 9 else "?")[:60]
            print("  %3d gecersiz -> %3d serhsiz | durum: %s" % (g, d, durum))
        return 1

    print("TEMIZ: gecersiz iddia anan her satir serh tasiyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
