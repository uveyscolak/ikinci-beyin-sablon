#!/usr/bin/env python3
"""Yeni proje ya da yeni çalışma alanı kurulumu.

Proje = kodu olan iş. Vault'ta PROJELER/<Ad>/ (Proje.md, PRD.md, Kararlar.md, Context.md),
kod klasöründe git deposu + CLAUDE.md işaretçisi.
Alan  = kodu olmayan çalışma alanı. Vault'ta verilen klasörün içine
        Alan.md (tetik kelimeleriyle ve `ad:` frontmatter'ıyla), Context.md, Kararlar.md.

Kullanım:
  python3 proje-kur.py --ad "Ad" [--amac "tek cümle"] [--klasor /yol] [--kod-yok] [--kuru]
  python3 proje-kur.py --alan "İŞ/ALT KLASÖR" --ad "Ad" [--amac "..."] [--tetik "a,b,c"] [--kuru]

Kurallar:
  - Kod dışarıda (beyin.json "projeler" kökü altında), akıl vault'ta PROJELER/<Ad>/ altında.
  - Vault klasörü zaten varsa durur; kod klasörü varsa koda dokunmaz, sadece eksik
    CLAUDE.md ve .gitignore satırını tamamlar.
  - Alan modunda klasör zaten varsa dolduruluyor, var olan dosyanın üstüne yazılmıyor.
  - Sırlar vault'a girmez; anahtarlar GİZLİ/ altında tutulur.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
BUGUN = datetime.date.today().isoformat()


def beyin_ayar():
    p = VAULT / ".claude" / "beyin.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------- şablonlar ----------

def t_claude_md(ad):
    return f"""# {ad}

Bu projenin kuralları burada tutulmuyor.

**Ortak anayasa:** {VAULT}/CLAUDE.md
**Proje beyni:** {VAULT}/PROJELER/{ad}/ — sayfa, yönerge (varsa), PRD, Kararlar, Context

Claude her zaman {VAULT} klasöründen çalıştırılır. Bir projenin adı geçtiğinde o projenin
yönergesi ve `Context.md` dosyası oturuma otomatik enjekte edilir.

Bu klasörde yalnız kod durur. `brain/` açılmaz; akıl vault'tadır.

> Kuruluş tarihi: {BUGUN}
"""


def t_gitignore():
    return ".DS_Store\n.env\n.env.*\nbrain/\n"


def t_sayfa(ad, amac, klasor, proje_rel):
    return f"""# {ad} — Proje

**Ne:** {amac or '<tek cümle>'}
**Neden var:** <hangi ihtiyaçtan doğdu>
**Hangi işe hizmet ediyor:** <iç araç mı, satılacak ürün mü, kişisel mi>

## Nerede duruyor
- **Kod:** {klasor or 'kod yok'}
- **Git:** <url> — <özel | açık>
- **Yönerge:** yok (gerekirse `Yönerge.md` açılır)
- **Beyin:** [[{proje_rel}/PRD|PRD]] · [[{proje_rel}/Kararlar|Kararlar]] · [[{proje_rel}/Context|Context]]

## Son bilinen hal
Kuruldu ({BUGUN}). Canlı durum [[{proje_rel}/Context|Context]] sayfasında; bu sayfa onu tekrarlamaz.

## Bağlantılar
[[Projeler]]
"""


def t_prd(ad, amac, proje_rel):
    return f"""# {ad} — PRD

**Yazıldı:** {BUGUN} · **Mod:** <hızlı | tam> · **Bağlı:** [[{proje_rel}/Context|Context]]

## Problem
{amac or '<Kullanıcının yaşadığı problem, onun gözünden.>'}

## Çözüm
<Önerilen çözüm, kullanıcının gözünden.>

## Kullanıcı Hikayeleri (tam mod)
1. Bir <aktör> olarak <özellik> istiyorum, böylece <fayda>.

## Uygulama Kararları
<Modüller, mimari, teknoloji, şema, API sözleşmeleri. Her karar Kararlar'a da tarihli girer.>

## Kabul Kriterleri
- [ ] <Somut, ölçülebilir, çıktıyla kanıtlanabilir.>

## Kapsam Dışı
<Bilinçli olarak yapılmayacaklar. Kapsam bekçiliği buradan.>

## Notlar
<Sorulamadan varsayılanlar, tek tek.>

## Değişiklik Notları
> Yalnız eklenir: `[YYYY-AA-GG] ne değişti — bkz. Kararlar [tarih]`.

---
[[{proje_rel}/Context|Context]] — ana hub
"""


def t_context(ad, klasor, proje_rel):
    return f"""# {ad} — Context

**Durum:** 🟡 kurulum
**Son güncelleme:** {BUGUN}
**Kod:** {klasor or 'yok'} · **Repo:** <url> · **Stack:** <stack> · **Deploy:** <deploy>

## Şu An Nerede
- Proje kuruldu, PRD henüz konuşulmadı.

## Sıradaki Adım
1. PRD'yi sohbetle doldur (problem, kapsam, kabul kriterleri, kapsam dışı).

## Bitiş Çizgisi
- [ ] <PRD kabul kriterlerinin özeti; detay [[{proje_rel}/PRD|PRD]].>

## Açık Sorular
- <Karara bağlanmamış şeyler, tarihiyle.>

## Alt Sayfalar
- [[{proje_rel}/PRD|PRD]] — hedef, kapsam, kabul kriterleri
- [[{proje_rel}/Kararlar|Kararlar]] — neden öyle yapıldığı
- [[{proje_rel}/Proje|Proje]] — projenin vault sayfası
"""


def t_kararlar(ad):
    return f"""# {ad} — Karar Günlüğü

> NEDEN'in tek evi. Yalnız eklenir. Her karar: tarih, ne, neden, varsa "denedik olmadı".

## [{BUGUN}] Proje kuruldu
**Ne:** Vault'ta `PROJELER/{ad}/` açıldı; kod ayrı klasörde.
**Neden:** Kod git'te, akıl vault'ta; anayasanın "Projelerde çalışma düzeni" bölümü.
"""


def t_alan_sayfa(ad, amac, tetikler, klasor):
    ust = "---\ntetik: [" + ", ".join(tetikler) + f"]\nad: {ad}\n---\n" if tetikler else f"---\nad: {ad}\n---\n"
    return f"""{ust}# {ad} — Alan

**Ne:** {amac or '<tek cümle>'}
**Neden var:** <hangi ihtiyaçtan doğdu>
**Tür:** çalışma alanı — kodu yok. Kod doğarsa ayrı bir proje olarak kurulur.

## Nerede duruyor
- **Klasör:** {klasor}
- **Yönerge:** yok (gerekirse `Yönerge.md` açılır)
- **Beyin:** [[{klasor}/Kararlar|Kararlar]] · [[{klasor}/Context|Context]]

## Tetik kelimeleri
Yukarıdaki `tetik:` satırındaki kelimelerden biri sohbette geçtiğinde bu alanın yönergesi
ve Context'i oturuma otomatik yüklenir. Listeyi değiştirmek için o satırı düzenle;
burada tekrarlama.

## Son bilinen hal
Kuruldu ({BUGUN}). Canlı durum [[{klasor}/Context|Context]] sayfasında; bu sayfa onu tekrarlamaz.

## Bağlantılar
[[Projeler]]
"""


def t_alan_context(ad, klasor):
    return f"""# {ad} — Context

**Durum:** 🟡 kurulum
**Son güncelleme:** {BUGUN}
**Klasör:** {klasor}

## Şu An Nerede
- Alan kuruldu, ilk oturum bekleniyor.

## Sıradaki Adım
1. <İlk somut adım.>

## Bitiş Çizgisi
- [ ] <Bu alanda "iyi" neye benziyor.>

## Açık Sorular
- <Karara bağlanmamış şeyler, tarihiyle.>

## Alt Sayfalar
- [[{klasor}/Kararlar|Kararlar]] — neden öyle yapıldığı
- [[{klasor}/Alan|Alan]] — alanın vault sayfası
"""


def t_alan_kararlar(ad, klasor):
    return f"""# {ad} — Karar Günlüğü

> NEDEN'in tek evi. Yalnız eklenir. Her karar: tarih, ne, neden, varsa "denedik olmadı".

## [{BUGUN}] Alan kuruldu
**Ne:** `{klasor}` altında alan sayfası, Context ve Kararlar açıldı.
**Neden:** Kodu olmayan işin de yönergesi ve canlı durumu olmalı; anayasanın "Projelerde çalışma düzeni" bölümü.
"""


# ---------- işler ----------

def hub_basliklar(satir):
    return [h.strip().lower() for h in satir.strip().strip("|").split("|")]


def hub_satiri(basliklar, degerler):
    """Sütun sayısını tablo başlığından okur; bilinmeyen sütuna tire koyar."""
    return "| " + " | ".join(degerler.get(b) or "—" for b in basliklar) + " |"


def hub_ekle(link, degerler, kuru, tablo_onek, bolum=None, yeni_tablo=None):
    hub = VAULT / "PROJELER" / "Projeler.md"
    if not hub.exists():
        print(f"  ! Hub yok: {hub} — satır eklenmedi")
        return
    satirlar = hub.read_text(encoding="utf-8").splitlines()
    if any(link in s for s in satirlar):
        print("  = Hub'da satır zaten var")
        return

    bas, bit = 0, len(satirlar)
    if bolum:
        yeri = next((i for i, s in enumerate(satirlar) if s.strip().lower() == bolum.lower()), None)
        if yeri is None:
            if yeni_tablo is None:
                print(f"  ! Hub'da '{bolum}' bölümü yok — satır eklenmedi")
                return
            yeni = hub_satiri(hub_basliklar(yeni_tablo[0]), degerler)
            satirlar += ["", bolum, ""] + list(yeni_tablo) + [yeni]
            if not kuru:
                hub.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
            print(f"  + Hub'a '{bolum}' bölümü açıldı")
            print(f"  + Hub satırı: {yeni}")
            return
        bas = yeri
        bit = next((i for i in range(bas + 1, len(satirlar)) if satirlar[i].startswith("## ")),
                   len(satirlar))

    tablo = next((i for i in range(bas, bit) if satirlar[i].startswith(tablo_onek)), None)
    if tablo is None:
        print(f"  ! Hub'da '{tablo_onek}' tablosu bulunamadı — satır eklenmedi")
        return
    basliklar = hub_basliklar(satirlar[tablo])
    son = tablo
    while son + 1 < bit and satirlar[son + 1].startswith("|"):
        son += 1
    yeni = hub_satiri(basliklar, degerler)
    satirlar.insert(son + 1, yeni)
    if not kuru:
        hub.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print(f"  + Hub satırı: {yeni}")


def hub_proje_satiri(ad, amac, kuru):
    hub_ekle(
        f"[[{ad} — Proje]]",
        {
            "proje": f"[[{ad} — Proje]]",
            "ne": amac,
            "son bilinen hal": f"Kuruldu ({BUGUN})",
            "yönerge": "—",
        },
        kuru,
        "| Proje",
    )


def hub_alan_satiri(ad, amac, klasor, kuru):
    hub_ekle(
        f"[[{ad} — Alan]]",
        {
            "alan": f"[[{ad} — Alan]]",
            "ne": amac,
            "klasör": klasor,
            "son bilinen hal": f"Kuruldu ({BUGUN})",
            "yönerge": "—",
        },
        kuru,
        "| Alan",
        bolum="## Alanlar",
        yeni_tablo=("| Alan | Ne | Klasör |", "|---|---|---|"),
    )


def kod_kur(ad, klasor: Path, kuru):
    if klasor.exists():
        print(f"  = Kod klasörü var, koda dokunulmadı: {klasor}")
    else:
        print(f"  + Kod klasörü: {klasor} (git init)")
        if not kuru:
            klasor.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=klasor, check=False)
    gi = klasor / ".gitignore"
    if gi.exists():
        icerik = gi.read_text(encoding="utf-8")
        if not re.search(r"^/?brain/?$", icerik, re.M):
            print("  + .gitignore: brain/ satırı eklendi")
            if not kuru:
                gi.write_text(icerik.rstrip("\n") + "\nbrain/\n", encoding="utf-8")
    else:
        print("  + .gitignore")
        if not kuru:
            gi.write_text(t_gitignore(), encoding="utf-8")
    cm = next((p for p in klasor.glob("*") if p.name.lower() == "claude.md"), None) if klasor.exists() else None
    if cm:
        print(f"  = {cm.name} zaten var, dokunulmadı")
    else:
        print("  + CLAUDE.md işaretçisi")
        if not kuru:
            (klasor / "CLAUDE.md").write_text(t_claude_md(ad), encoding="utf-8")


def vault_kur(ad, amac, klasor, kuru):
    hedef = VAULT / "PROJELER" / ad
    if hedef.exists():
        sys.exit(f"HATA: {hedef} zaten var. Var olan projeyi yeniden kurma.")
    proje_rel = f"PROJELER/{ad}"
    dosyalar = {
        "Proje.md": t_sayfa(ad, amac, klasor, proje_rel),
        "PRD.md": t_prd(ad, amac, proje_rel),
        "Kararlar.md": t_kararlar(ad),
        "Context.md": t_context(ad, klasor, proje_rel),
    }
    print(f"  + {hedef.relative_to(VAULT)}/")
    for isim, icerik in dosyalar.items():
        print(f"      {isim}")
        if not kuru:
            hedef.mkdir(parents=True, exist_ok=True)
            (hedef / isim).write_text(icerik, encoding="utf-8")


def alan_kur(ad, amac, tetikler, klasor_rel, kuru):
    hedef = VAULT / klasor_rel
    try:
        hedef.resolve().relative_to(VAULT.resolve())
    except (ValueError, OSError):
        sys.exit(f"HATA: alan klasörü vault dışında: {klasor_rel}")
    dosyalar = {
        "Alan.md": t_alan_sayfa(ad, amac, tetikler, klasor_rel),
        "Context.md": t_alan_context(ad, klasor_rel),
        "Kararlar.md": t_alan_kararlar(ad, klasor_rel),
    }
    print(f"  + {klasor_rel}/")
    for isim, icerik in dosyalar.items():
        if (hedef / isim).exists():
            print(f"      = {isim} (var, dokunulmadı)")
            continue
        print(f"      {isim}")
        if not kuru:
            hedef.mkdir(parents=True, exist_ok=True)
            (hedef / isim).write_text(icerik, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ad", required=True, help="Proje ya da alan adı (dosya öneki olur)")
    ap.add_argument("--amac", default="", help="Tek cümle: proje ne")
    ap.add_argument("--klasor", help="Kod klasörü (varsayılan: beyin.json projeler kökü / Ad)")
    ap.add_argument("--kod-yok", action="store_true", help="Kod klasörü açma (yalnız vault)")
    ap.add_argument("--alan", help="Alan modu: vault'a göreli klasör (ör. \"İŞ/VİDEO EDİT\")")
    ap.add_argument("--tetik", default="", help="Alan tetik kelimeleri, virgülle ayrık")
    ap.add_argument("--kuru", action="store_true", help="Yalnız ne yapılacağını yaz")
    a = ap.parse_args()

    ad = a.ad.strip()
    if not ad or "/" in ad or ad.startswith("."):
        sys.exit("HATA: geçersiz ad")

    if a.alan:
        if a.klasor or a.kod_yok:
            sys.exit("HATA: --alan ile --klasor / --kod-yok birlikte kullanılmaz")
        klasor_rel = a.alan.strip().strip("/")
        if not klasor_rel or klasor_rel.startswith("."):
            sys.exit("HATA: geçersiz alan klasörü")
        tetikler = [t.strip() for t in a.tetik.split(",") if t.strip()]
        kisa = [t for t in tetikler if len(t) < 3]
        if kisa:
            print(f"  ! Üç harften kısa tetik kanca tarafından yok sayılır: {', '.join(kisa)}")
        print(f"{'[KURU] ' if a.kuru else ''}Alan kuruluyor: {ad} ({klasor_rel})")
        alan_kur(ad, a.amac, tetikler, klasor_rel, a.kuru)
        hub_alan_satiri(ad, a.amac, klasor_rel, a.kuru)
        if not a.kuru:
            print("\nBitti. Sıradaki adım: Context'i doldur, ilk kararı Kararlar'a yaz, "
                  "tetik kelimelerini gözden geçir.")
        return
    if a.tetik:
        sys.exit("HATA: --tetik yalnız --alan ile kullanılır")

    ayar = beyin_ayar()
    klasor = None
    if not a.kod_yok:
        kok = a.klasor or ayar.get("projeler")
        if not kok:
            sys.exit("HATA: kod kökü yok; --klasor ver veya beyin.json 'projeler' alanını doldur")
        klasor = Path(a.klasor).expanduser() if a.klasor else Path(kok) / ad

    print(f"{'[KURU] ' if a.kuru else ''}Proje kuruluyor: {ad}")
    vault_kur(ad, a.amac, str(klasor) if klasor else "", a.kuru)
    if klasor:
        kod_kur(ad, klasor, a.kuru)
    hub_proje_satiri(ad, a.amac, a.kuru)
    if not a.kuru:
        print("\nBitti. Sıradaki adım: PRD'yi sohbetle doldur, ilk kararı Kararlar'a yaz, Context'i güncelle.")


if __name__ == "__main__":
    main()
