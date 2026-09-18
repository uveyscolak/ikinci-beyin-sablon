#!/usr/bin/env python3
"""Oturum başı bağlamını kurar ve Claude Code kancasının beklediği JSON'u basar.

Kurallar, Açık Konular ve Son Oturum CLAUDE.md'deki @ bağlarıyla tam yüklenir; bu kanca
onları basmaz. Kanca yalnız o an üretilen bilgiyi taşır ve toplamı beyin.json'daki
`kanca_acilis_karakter` sınırını (6.000) aşmaz. Claude Code 10.000 karakteri aşan kanca
çıktısını dosyaya atıp yalnız ilk 2.000 karakterini gösteriyor; pay bilerek büyük tutuldu.

Bloklar, sırasıyla:
  1. Beyin sağlığı (kısaltılmış)
  2. Boyut ve madde sayımı: yalnız sınırı aşan dosyalar, her biri tek satır
  3. Kod depoları ve vault: push durumu (yalnız sorun varsa; push artık makinenin işi)
  4. Bekleyenler: HAFIZA/Bekleyenler.md'den en fazla üç madde
  5. Hatırlatmalar: HAFIZA/Hatırlatmalar.md'de günü gelmiş satırlar
  6. Token: HAFIZA/Token Raporu.md'nin en son gün satırı, tek cümle
  7. Bağlanmamış iş dosyaları: saglik.py'nin bulduklarından en fazla üç tanesi
  8. Gece bakımı: son koşu düştüyse tek satır
  9. YouTube kuyruğu ve bugünün günlük kuyruğu

Bağlam özetlendiğinde (source=compact) ya da oturum sürdürüldüğünde (resume) hiçbir blok
basılmaz; yalnız tek satırlık bir not gider, çünkü bu dosyalar zaten o oturumda okundu.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from _sinirlar import ayar_oku, sinirlar  # noqa: E402

TAVAN = {
    "saglik": 600,
    "gunluk": 1_200,
    "youtube": 900,
}

# Kompakt ve sürdürme açılışında basılan tek satır. Proje ve alan blokları oturum izini
# pre-compact.sh sildiği için konu tekrar geçtiğinde kendiliğinden yeniden gelir.
KOMPAKT_NOT = "Bağlam özetlendi; proje ve alan blokları konu geçince yeniden gelecek."


def oku(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def kirp(metin: str, tavan: int, ad: str) -> str:
    metin = metin.strip()
    if len(metin) <= tavan:
        return metin
    not_ = f"[not: {ad} kırpıldı, tamamı için dosyayı aç]"
    return metin[: max(0, tavan - len(not_) - 1)].rstrip() + "\n" + not_


def _json_oku(path: Path) -> dict:
    try:
        veri = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}


def saglik(vault: Path) -> str:
    """saglik.py'nin yazdığı sonuç: sorun varsa veya haftalık bakım zamanıysa metin döner."""
    r = _json_oku(vault / ".claude" / "scripts" / ".state" / "saglik.json")
    if not r:
        return ""
    parca = []
    for s in (r.get("sorunlar") or [])[:4]:
        parca.append(f"- SORUN: {s}")
    for b in (r.get("bilgi") or [])[:3]:
        parca.append(f"- not: {b}")
    if r.get("haftalik"):
        son = r.get("haftalik_son") or "hiç"
        parca.append(
            f"- HAFTALIK BAKIM ZAMANI (son bakım: {son}). Kullanıcıya bugün bakım yapmayı teklif et;"
            " onay gelince `haftalik` skill'ini uygula."
        )
    if not parca:
        return ""
    parca.append("Sorunları kullanıcıya bir cümleyle söyle, düzeltmeyi teklif et.")
    return kirp("\n".join(parca), TAVAN["saglik"], "sağlık")


def sayim_blogu(vault: Path) -> str:
    """Boyut ve madde sayımı: yalnız sınırı aşan dosyalar, dosya başına tek satır.

    Sayıyı saglik.py --sayim üretir ve saglik.json'a yazar; burada yalnız basılır.
    Sayım yoksa (ilk koşu) dosya boyutundan tek başına uyarı verilir.
    """
    r = _json_oku(vault / ".claude" / "scripts" / ".state" / "saglik.json")
    sayim = r.get("sayim")
    sinir = sinirlar(vault)
    satirlar: list[str] = []
    if isinstance(sayim, dict) and sayim:
        for ad, deger in sayim.items():
            if not isinstance(deger, dict):
                continue
            if not deger.get("asiyor"):
                continue
            madde = deger.get("madde")
            madde_sinir = deger.get("madde_sinir")
            karakter = deger.get("karakter", 0)
            karakter_sinir = deger.get("karakter_sinir", 0)
            parcalar = []
            if isinstance(madde, int) and isinstance(madde_sinir, int) and madde_sinir:
                parcalar.append(f"{madde}/{madde_sinir} madde")
            parcalar.append(f"{karakter:,}/{karakter_sinir:,} karakter".replace(",", "."))
            satirlar.append(f"- {ad} {', '.join(parcalar)}")
    else:
        eslesme = {
            "HAFIZA/Kurallar.md": sinir["kurallar_karakter"],
            "HAFIZA/Açık Konular.md": sinir["acik_konular_karakter"],
            "HAFIZA/Son Oturum.md": sinir["son_oturum_karakter"],
        }
        for ad, tavan in eslesme.items():
            n = len(oku(vault / ad))
            if n > tavan:
                satirlar.append(f"- {ad} {n:,}/{tavan:,} karakter".replace(",", "."))
    if not satirlar:
        return ""
    satirlar.append("Sınırı aşan dosyayı sadeleştirmeyi kullanıcıya teklif et; hangi maddelerin birleşeceğini sen seç.")
    return "\n".join(satirlar)


def push_bekleyen(vault: Path) -> str:
    """Kod depoları ve vault'un push durumu: depo-push.py ve vault-push.py'nin yazdığı
    .state/push-durum.json'dan okunur. Push artık makinenin işi; burada
    yalnız sorun varsa tek satır basılır — doğrulama düşen depo, push hatası alan depo,
    uzak dalı olmayan depo. Her şey temizse blok hiç görünmez.
    """
    r = _json_oku(vault / ".claude" / "scripts" / ".state" / "push-durum.json")
    if not r:
        return ""
    satirlar: list[str] = []

    depolar = r.get("depolar")
    if isinstance(depolar, dict):
        for ad, kayit in sorted(depolar.items()):
            if not isinstance(kayit, dict):
                continue
            sonuc = kayit.get("sonuc")
            if sonuc == "push_edilmedi":
                dog = kayit.get("dogrulama") or {}
                satirlar.append(
                    f"- {ad}: doğrulama düştü ({dog.get('tur', '?')}), push edilmedi. "
                    f"{str(dog.get('ayrinti', ''))[:150]}"
                )
            elif sonuc == "push_hatasi":
                satirlar.append(f"- {ad}: push hatası — {str(kayit.get('push_ayrinti', ''))[:150]}")
            elif sonuc == "atlandi":
                satirlar.append(f"- {ad}: {kayit.get('ayrinti', 'uzak dal yok')}")

    vault_kaydi = r.get("vault")
    if isinstance(vault_kaydi, dict) and vault_kaydi.get("sonuc") == "hata":
        satirlar.append(f"- vault push hatası: {str(vault_kaydi.get('ayrinti', ''))[:150]}")

    if not satirlar:
        return ""
    parca = ["Push sorunları (push artık makinenin işi, yalnız sorun varsa görünür):"]
    parca.extend(satirlar[:5])
    return kirp("\n".join(parca), 400, "push durumu")


def bekleyenler(vault: Path, en_fazla: int) -> str:
    """HAFIZA/Bekleyenler.md: gece bakımının çıkardığı kural adayları ve öneriler.

    Dosya yoksa blok hiç basılmaz. En fazla `bekleyenler_en_fazla` madde gelir; gerisi
    dosyada durur ve kullanıcı isterse açılır.
    """
    metin = oku(vault / "HAFIZA" / "Bekleyenler.md")
    if not metin:
        return ""
    maddeler = [s.strip() for s in metin.splitlines() if s.lstrip().startswith("- ")]
    if not maddeler:
        return ""
    secilen = maddeler[:en_fazla]
    parca = list(secilen)
    if len(maddeler) > en_fazla:
        parca.append(f"  ... ve {len(maddeler) - en_fazla} madde daha (HAFIZA/Bekleyenler.md)")
    parca.append("Bunlar öneridir, kural değildir. Kullanıcıya sor; onaylananı Kurallar'a taşı, reddedileni sil.")
    return "\n".join(parca)


RE_HATIRLATMA = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+)$")


def hatirlatmalar(vault: Path) -> str:
    """HAFIZA/Hatırlatmalar.md: `- YYYY-AA-GG | cümle | link` satırları.

    Yalnız tarihi bugüne eşit ya da geçmiş satırlar basılır, hepsi basılır (sayı sınırı yok);
    günü gelmemiş satır hiç görünmez. Dosya yoksa blok basılmaz.
    """
    metin = oku(vault / "HAFIZA" / "Hatırlatmalar.md")
    if not metin:
        return ""
    bugun = dt.date.today()
    satirlar: list[str] = []
    for ham in metin.splitlines():
        eslesme = RE_HATIRLATMA.match(ham.strip())
        if not eslesme:
            continue
        try:
            gun = dt.date.fromisoformat(eslesme.group(1))
        except ValueError:
            continue
        if gun > bugun:
            continue
        satirlar.append(f"- [{gun.isoformat()}] {eslesme.group(2).strip()}")
    if not satirlar:
        return ""
    satirlar.append("Günü gelen işleri kullanıcıya hatırlat; bitenin satırını dosyadan sil.")
    return "\n".join(satirlar)


def token_satiri(vault: Path) -> str:
    """HAFIZA/Token Raporu.md tablosundaki en son gün satırından tek cümle.

    Tablo biçimi: | Gün | Oturum | Alt ajan kaydı | Girdi | ... | Toplam |
    En yeni gün en üstte olduğu için ayraçtan sonraki ilk veri satırı alınır.
    """
    metin = oku(vault / "HAFIZA" / "Token Raporu.md")
    if not metin:
        return ""
    ayrac_gecti = False
    for ham in metin.splitlines():
        s = ham.strip()
        if not s.startswith("|"):
            continue
        if re.match(r"^\|[\s:|-]+\|$", s):
            ayrac_gecti = True
            continue
        if not ayrac_gecti:
            continue
        hucre = [h.strip() for h in s.strip("|").split("|")]
        if len(hucre) < 3:
            return ""
        gun, oturum, toplam = hucre[0], hucre[1], hucre[-1]
        try:
            tarih = dt.date.fromisoformat(gun)
        except ValueError:
            return ""
        etiket = "Dün" if tarih == dt.date.today() - dt.timedelta(days=1) else gun
        sayi = toplam.replace(".", "").replace(",", "").strip()
        if sayi.isdigit():
            n = int(sayi)
            gosterim = f"{n / 1_000_000:.1f} milyon token".replace(".", ",") if n >= 1_000_000 \
                else f"{n:,} token".replace(",", ".")
        else:
            gosterim = f"{toplam} token"
        return f"{etiket}: {gosterim}, {oturum} oturum."
    return ""


def baglanmamis(vault: Path, en_fazla: int) -> str:
    """saglik.py'nin bulduğu bağlanmamış iş dosyaları: Kaynaklar listesinde geçmeyenler.

    Kullanıcının kendi eliyle yazdığı dosya hiçbir Durum'un Kaynaklar listesinde geçmiyorsa
    Claude onu hiç görmez. "İşaret etme, önüne koy" ilkesi gereği küçük dosyanın ilk
    satırları doğrudan basılır.
    """
    r = _json_oku(vault / ".claude" / "scripts" / ".state" / "saglik.json")
    kayitlar = r.get("baglanmamis")
    if not isinstance(kayitlar, list) or not kayitlar:
        return ""
    parca: list[str] = []
    for kayit in kayitlar[:en_fazla]:
        if not isinstance(kayit, dict):
            continue
        yol = kayit.get("yol")
        if not yol:
            continue
        bas = kayit.get("bas")
        if bas:
            parca.append(f"- {yol}\n  {bas}")
        else:
            parca.append(f"- {yol}")
    if not parca:
        return ""
    parca.append(
        "Bu dosyalar son yedi günde değişti ve hiçbir Durum dosyasının Kaynaklar listesinde geçmiyor."
        " İlgiliyse ait olduğu Durum'un Kaynaklar listesine ekle."
    )
    return "\n".join(parca)


def gece_bakim(vault: Path) -> str:
    """Gece bakımının son koşusu düştüyse tek satır; başarılıysa hiçbir şey basılmaz."""
    r = _json_oku(vault / ".claude" / "scripts" / ".state" / "gece-bakim.json")
    if not r or r.get("sonuc") != "basarisiz":
        return ""
    dusen = [ad for ad, d in (r.get("adimlar") or {}).items()
             if isinstance(d, dict) and d.get("sonuc") != "tamam"]
    zaman = r.get("bitis") or r.get("baslangic") or "?"
    liste = ", ".join(dusen[:4]) if dusen else "ayrıntı yok"
    return f"- Gece bakımı son koşuda düştü ({zaman}): {liste}. Kayıt: .claude/scripts/.state/gece-bakim.log"


def youtube_kuyruk(vault: Path) -> str:
    """EĞİTİMLER/YOUTUBE/KUYRUK.md: Sonnet'in notunu yazdığı, şef kontrolü bekleyen videolar."""
    parca: list[str] = []
    durum = _json_oku(vault / ".claude" / "scripts" / ".state" / "youtube-durum.json")
    if durum.get("hata"):
        parca.append(f"- izleyici son çalışmada hata verdi: {str(durum['hata'])[:120]}")
    metin = oku(vault / "EĞİTİMLER" / "YOUTUBE" / "KUYRUK.md")
    maddeler = [s for s in metin.splitlines() if s.lstrip().startswith("- ")]
    if maddeler:
        parca.extend(maddeler[:3])
        if len(maddeler) > 3:
            parca.append(f"  ... ve {len(maddeler) - 3} video daha (EĞİTİMLER/YOUTUBE/KUYRUK.md)")
        parca.append(
            "Notu Sonnet yazdı: `denetci` ajanına ham transkriptle karşılaştırt, düzelt,"
            " kaynak satırını 'şef kontrol etti <tarih>' yap, maddeyi KUYRUK.md'den sil."
        )
    if not parca:
        return ""
    return kirp("\n".join(parca), TAVAN["youtube"], "YouTube kuyruğu")


def gunluk(vault: Path) -> str:
    bugun = dt.date.today()
    for gun in (bugun, bugun - dt.timedelta(days=1)):
        p = vault / "GÜNLÜK" / f"{gun.isoformat()}.md"
        if p.exists():
            return "\n".join(oku(p).splitlines()[-20:])
    return ""


def kur(vault: Path) -> str:
    sinir = sinirlar(vault)
    toplam_tavan = sinir["kanca_acilis_karakter"]

    adaylar: list[tuple[str, str]] = []

    def ekle(etiket: str, metin: str) -> None:
        if metin and metin.strip():
            adaylar.append((etiket, metin.strip()))

    ekle("[Beyin sağlığı]", saglik(vault))
    ekle("[Boyut ve madde sayımı — sınırı aşanlar]", sayim_blogu(vault))
    ekle("[Kod depoları ve vault — push durumu]", push_bekleyen(vault))
    ekle("[Bekleyenler — gece bakımının önerileri]", bekleyenler(vault, sinir["bekleyenler_en_fazla"]))
    ekle("[Hatırlatmalar — günü gelenler]", hatirlatmalar(vault))
    ekle("[Token kullanımı]", token_satiri(vault))
    ekle("[Bağlanmamış iş dosyaları]", baglanmamis(vault, sinir["baglanmamis_en_fazla"]))
    ekle("[Gece bakımı]", gece_bakim(vault))
    ekle("[YouTube — Vault listesi]", youtube_kuyruk(vault))
    ekle("[Bugünün logu — kuyruk]", kirp(gunluk(vault), TAVAN["gunluk"], "günlük"))

    kapanis = (
        "[Hafıza] Kurallar, Açık Konular ve Son Oturum anayasanın parçası olarak zaten tam yüklü;"
        " üstlerine sormadan güncellemek senin sorumluluğun."
    )

    # Bütçe sırayla harcanır: yukarıdaki sıra önem sırasıdır, sığmayan blok atlanır.
    # Böylece sağlık ve sayım her zaman girer, günlük kuyruğu ilk düşen olur.
    parcalar: list[str] = []
    kullanilan = len(kapanis) + 80
    atlanan = 0
    for etiket, metin in adaylar:
        blok = f"{etiket}\n{metin}\n"
        if kullanilan + len(blok) > toplam_tavan:
            atlanan += 1
            continue
        parcalar.append(blok)
        kullanilan += len(blok)
    if atlanan:
        parcalar.append(f"[not: {atlanan} blok yer kalmadığı için atlandı]\n")
    parcalar.append(kapanis)
    metin = "\n".join(parcalar)
    if len(metin) > toplam_tavan:
        metin = metin[: toplam_tavan - 60].rstrip() + "\n[not: kanca çıktısı tavanda kesildi]"
    return metin + f"\n[Kanca çıktısı: {len(metin):,} karakter; tavan {toplam_tavan:,}]".replace(",", ".")


def kaynak_oku(argv: list[str]) -> str:
    """Kancanın stdin JSON'undaki `source` alanı: startup, resume, clear, compact, fork.

    Claude Code bu JSON'u stdin'den veriyor; session-start.sh onu dosyaya yazıp yolunu
    --girdi ile geçiyor. Dosya yoksa ya da alan okunamazsa normal açılış varsayılır.
    """
    for i, arg in enumerate(argv):
        if arg == "--girdi" and i + 1 < len(argv):
            try:
                veri = json.loads(Path(argv[i + 1]).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return ""
            if isinstance(veri, dict):
                kaynak = veri.get("source")
                return kaynak if isinstance(kaynak, str) else ""
    return ""


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    vault = Path(sys.argv[1])
    if not vault.is_dir():
        return 0
    kaynak = kaynak_oku(sys.argv)
    if kaynak in ("compact", "resume"):
        metin = KOMPAKT_NOT
    else:
        metin = kur(vault)
    if "--plain" in sys.argv:
        print(metin)
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                             "additionalContext": metin}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
