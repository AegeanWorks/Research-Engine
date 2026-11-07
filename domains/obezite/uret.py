#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
uret.py — TÜRETİLMİŞ DOSYA ÜRETİCİSİ (T209, iddia 804)

NEDEN VAR
=========
T207'de chunk bölme hatası bulundu: **iddia 600-608 chunk'lardan düşmüştü** ve
`kontrol.ps1` yalnız chunk'ları okuduğu için hatayı GÖREMEDİ ("785 satır, temiz" dedi;
ana defterde 794 vardı). Düşenler projenin en yük taşıyanlarıydı (600, 606, 607, 608).

Kök neden: türetilmiş veri ELLE bakılıyordu. T150-T208'in ölçülmüş dersi:
  · metne yazılan her kural ihlal edildi (K12b-k, K-T6, K-T7)
  · kontrol.ps1'e konan her denetim tuttu (§1b, §10, §11)
→ Bu betik, "iki kaynak" desenini kökten kapatır: türetilmiş dosyalar artık
  bir İKİNCİ KAYNAK değil, ana defterin bir PROJEKSİYONUDUR.

KANONİK KAYNAK: 02_LITERATUR/iddia-defteri.md  (yalnız buraya yazılır)
ÜRETİLENLER:
  · iddia-defteri-0001-0500.md, -0501-1000.md, ...   (okuma ekonomisi için chunk)
  · iddia-defteri-index.md                            (chunk haritası)
  · claim-index.md                                    (iddia → chunk + Bağlı çapraz atıf)

KULLANIM
========
  python 08_ARACLAR/uret.py            # üret (diske yaz)
  python 08_ARACLAR/uret.py --kontrol  # ÜRETME, yalnız diskteki ile karşılaştır
                                       # (çıkış 0 = eşit, 1 = ayrışma) -> kontrol.ps1 §12

TASARIM İLKESİ — KAYIPSIZ BÖLME
================================
Ana defter yalnız iddia satırı içermez: 10 başlık, 170 blockquote, 52 başka tablo
satırı, 75 düz metin var (T209 ölçümü). Naif bir "iddia satırlarını topla" üretimi
bunları YOK EDER. Bu yüzden bölme şöyle çalışır: her satır, kendisinden önce gelen
son iddia numarasının chunk'ına yazılır. Böylece Ç-28/Ç-29 gibi bölüm metinleri
ilgili iddiaların yanında kalır ve HİÇBİR SATIR KAYBOLMAZ.
DOĞRULANAN ÖZELLİK — ve bu bir tasarım kararıdır
=================================================
İlk sürüm "chunk gövdelerinin birleşimi ana defteri BİREBİR yeniden üretmeli" diye test
etti ve **BAŞARISIZ OLDU** (üretim doğru biçimde iptal edildi). Neden: ana defterin
fiziksel sırası sayısal DEĞİL — tarihsel bir artefakt olarak şöyle dizilmiş:
    satır 1-489  : iddia 1-500
    satır 490-586: iddia 501-597  (backfill satırları)
    satır 587-879: iddia 215-481  ← numarası küçük ama DOSYADA SONRA
    satır 888+   : iddia 600-803
Yani sayı-tabanlı bölme hiçbir zaman "bitişik dilim" olamaz; sıra 500 sınırını 3 kez aşıyor.

→ Doğru doğrulama özelliği "birleşim = orijinal" DEĞİL, **"hiçbir satır kaybolmaz veya
çoğalmaz"**dır (çok-küme/multiset korunumu). Çünkü chunk'lar bir ARAMA KOLAYLIĞIDIR;
kanonik dosya ana defterdir ve sıra orada korunur. İddia düzeyindeki garanti ise
`kontrol.ps1` §1b'nin küme karşılaştırmasıyla ayrıca sağlanır.
★ Ders: nöbetçiyi yazarken önce "hangi özelliği garanti etmem gerekiyor?" diye sor —
yanlış özelliği test etmek, test etmemekten daha yanıltıcıdır.
"""
import io, os, re, sys, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from domains.obezite.atif import atiflar  # T209: kunye gurultusu ayiklayan atif cikarici

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
ANA = os.path.join(KOK, "02_LITERATUR", "iddia-defteri.md")
CHUNK_BOY = 500

IDDIA = re.compile(r'^\| \*\*(\d+)\*\*')


def oku(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read().split("\n")


def chunk_adi(n):
    bas = ((n - 1) // CHUNK_BOY) * CHUNK_BOY + 1
    return "iddia-defteri-%04d-%04d.md" % (bas, bas + CHUNK_BOY - 1), bas, bas + CHUNK_BOY - 1


def bol(satirlar):
    """Kayıpsız bölme: her satır, önceki son iddia numarasının chunk'ına gider.
    İlk iddiadan önceki satırlar 'onsoz' olur (chunk 1'e girer)."""
    onsoz, kutular, sira = [], {}, []
    akt = None
    for s in satirlar:
        m = IDDIA.match(s)
        if m:
            ad, a, b = chunk_adi(int(m.group(1)))
            if ad not in kutular:
                kutular[ad] = {"satir": [], "alt": a, "ust": b, "ids": []}
                sira.append(ad)
            akt = ad
            kutular[ad]["ids"].append(int(m.group(1)))
        if akt is None:
            onsoz.append(s)
        else:
            kutular[akt]["satir"].append(s)
    return onsoz, kutular, sira


def banner(ad, alt, ust, adet):
    return [
        "# İDDİA DEFTERİ — chunk %d-%d" % (alt, ust),
        "",
        "> ## ⛔ BU DOSYA ÜRETİLMİŞTİR — ELLE DÜZENLEME",
        ">",
        "> **Kanonik kaynak:** [`iddia-defteri.md`](iddia-defteri.md). Bu dosya ondan",
        "> `08_ARACLAR/uret.py` ile üretilir ve **her tur `kontrol.ps1` §12 tarafından",
        "> yeniden üretilip karşılaştırılır** — ayrışma varsa SORUN verir.",
        ">",
        "> **Yeni iddia buraya YAZILMAZ**, ana deftere yazılır; sonra `uret.py` çalıştırılır.",
        ">",
        "> **Niçin bu bant var (iddia 797):** T207'de elle yapılan bölmede **iddia 600-608",
        "> düşmüştü** — aralarında 600 (SGLT2i %72 silinme), 606 (Z1'i geçen tek maruziyet),",
        "> 607 (akı ≠ stok), 608 (potasyum mimarisi) vardı. Ve `kontrol.ps1` o zaman yalnız",
        "> chunk'ları okuduğu için hatayı **göremedi**. Bu dosya artık bir ikinci kaynak",
        "> değil, ana defterin bir **projeksiyonudur**.",
        "",
        "**Bu chunk'ta %d iddia var.**" % adet,
        "",
        "---",
        "",
    ]


def uret(satirlar):
    """Üretilecek dosyaları {ad: metin} olarak döndür."""
    onsoz, kutular, sira = bol(satirlar)
    cikti = {}

    for i, ad in enumerate(sira):
        k = kutular[ad]
        govde = (onsoz + k["satir"]) if i == 0 else k["satir"]
        cikti[ad] = "\n".join(banner(ad, k["alt"], k["ust"], len(k["ids"])) + govde)

    # chunk haritası
    h = [
        "# İDDİA DEFTERİ — CHUNK HARİTASI",
        "",
        "> ⛔ **ÜRETİLMİŞTİR** — `08_ARACLAR/uret.py`. Kanonik kaynak: `iddia-defteri.md`.",
        "",
        "| Dosya | Aralık | İddia sayısı |",
        "|---|---|---|",
    ]
    for ad in sira:
        k = kutular[ad]
        h.append("| [%s](%s) | %d-%d | **%d** |" % (ad, ad, k["alt"], k["ust"], len(k["ids"])))
    toplam = sum(len(kutular[a]["ids"]) for a in sira)
    h += [
        "",
        "**Toplam: %d iddia** · max: **%d**" % (toplam, max(max(kutular[a]["ids"]) for a in sira)),
        "",
        "## Kullanım",
        "",
        "- **Yeni iddia:** `iddia-defteri.md`'ye yaz, sonra `python 08_ARACLAR/uret.py`",
        "- **Okuma:** hedef aralığı belirle, yalnız o chunk'ı aç (token ekonomisi)",
        "- **Doğrulama:** `kontrol.ps1` §12 her tur üretimi diskle karşılaştırır",
        "",
    ]
    cikti["iddia-defteri-index.md"] = "\n".join(h)

    # çapraz atıf indeksi: iddia -> chunk + Bağlı sütunu
    ci = [
        "# İDDİA ÇAPRAZ-ATIF İNDEKSİ",
        "",
        "> ⛔ **ÜRETİLMİŞTİR** — `08_ARACLAR/uret.py`. Kanonik kaynak: `iddia-defteri.md`.",
        "> **Toplam %d iddia.** 'Bağlı' sütunu, satırın son alanından alınan iddia numaralarıdır." % toplam,
        "",
        "| İddia | Chunk | Bağlı |",
        "|---|---|---|",
    ]
    for ad in sira:
        for s in kutular[ad]["satir"]:
            m = IDDIA.match(s)
            if not m:
                continue
            alan = s.split("|")
            bagli = ""
            if len(alan) >= 3:
                # T209: duz regex SAYFA NUMARALARINI atif saniyordu (74->90, 120->448,
                # 76->476 -- hepsi kunye sayfa araligiydi). atif.py kunyeyi ayikliyor.
                bagli = " ".join(str(x) for x in atiflar(alan[-2]))
            ci.append("| **%s** | %s | %s |" % (m.group(1), ad, bagli[:120]))
    cikti["claim-index.md"] = "\n".join(ci)
    return cikti, kutular, sira, onsoz


def govde_dogrula(satirlar, kutular, sira, onsoz):
    """KAYIPSIZLIK TESTİ — çok-küme korunumu (bkz. modül başlığı: neden 'birebir' değil).
    Her satır chunk'lar arasında TAM BİR KEZ görünmeli: ne kayıp ne çoğalma."""
    from collections import Counter
    yeniden = Counter(onsoz)
    for ad in sira:
        yeniden.update(kutular[ad]["satir"])
    asil = Counter(satirlar)
    kayip = asil - yeniden
    fazla = yeniden - asil
    if kayip or fazla:
        print("  KAYIP satir : %d" % sum(kayip.values()))
        print("  FAZLA satir : %d" % sum(fazla.values()))
        for s in list(kayip)[:3]:
            print("    kayip ornek: %s" % s[:90])
        return False
    return True


def main():
    kontrol = "--kontrol" in sys.argv
    satirlar = oku(ANA)
    cikti, kutular, sira, onsoz = uret(satirlar)

    tamam = govde_dogrula(satirlar, kutular, sira, onsoz)
    print("KAYIPSIZLIK TESTI: %s (%d satir)" % ("GECTI" if tamam else "BASARISIZ", len(satirlar)))
    if not tamam:
        print("  -> URETIM IPTAL: bolme kayipsiz degil")
        return 2

    ids = sorted(set(i for a in sira for i in kutular[a]["ids"]))
    print("iddia: %d tekil, max %d, chunk %d" % (len(ids), max(ids), len(sira)))

    ayrisan = []
    for ad, metin in sorted(cikti.items()):
        yol = os.path.join(LIT, ad)
        if os.path.exists(yol):
            with io.open(yol, encoding="utf-8") as fh:
                var = fh.read()
        else:
            var = None
        esit = (var == metin)
        if not esit:
            ayrisan.append(ad)
        if kontrol:
            print("  %-34s %s" % (ad, "ayni" if esit else "AYRISMIS"))
        else:
            with io.open(yol, "w", encoding="utf-8") as fh:
                fh.write(metin)
            print("  %-34s %s" % (ad, "degismedi" if esit else "YAZILDI"))

    if kontrol and ayrisan:
        print("\nAYRISMA: %d dosya -> 'python 08_ARACLAR/uret.py' calistir" % len(ayrisan))
        return 1
    print("\nTAMAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
