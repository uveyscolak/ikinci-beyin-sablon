#!/usr/bin/env python3
"""Beynin hızlı sağlık kontrolü. Oturum başında kanca çalıştırır, sorun varsa bağlama düşer.

Kullanıcının hiçbir şeyi hatırlaması gerekmez: Son Oturum bayatladı mı, derleme düştü mü,
push gitti mi, aynı oturum iki kez özetlendi mi, linkler kopuk mu, yapı kuralları bozuk mu,
haftalık bakım zamanı geldi mi; hepsine makine bakar. Argümansız çağrı `tablo()` çıktısını
insan için basar, `--linkler` vault genelindeki kırık wiki-link ve ölü düz metin yolların tam
listesini dosya başına gruplu basar, `--yapi` anayasanın yapı kurallarını (öksüz sayfa, eksik
proje çekirdeği, tek yönlü link, bayat kavram makalesi vb.) kategori başına gruplu basar,
`--yaz` sonucu .state/saglik.json'a atomik yazar, `--bakim-yapildi` haftalık bakımın tarihini
kaydeder.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
STATE = VAULT / ".claude" / "scripts" / ".state"
HAFTALIK_GUN = 7


def _json(path: Path) -> dict:
    try:
        v = json.loads(path.read_text(encoding="utf-8"))
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def _ayar() -> dict:
    return _json(VAULT / ".claude" / "beyin.json")


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


# --- Kırık wiki-link ve ölü düz metin yol taraması ---------------------------
# Taranmayan klasörler: makine yazar ve tarihîdir (GÜNLÜK, BİLGİ), yedektir,
# ya da vault notu değildir (.git, .obsidian, .claude, .trash).
TARAMA_ATLA = {"GÜNLÜK", "BİLGİ", "YEDEK", ".git", ".obsidian", ".claude", ".trash"}
# Kaynak olarak taranmayan ama link HEDEFİ olarak sayılan klasörler. BİLGİ makine
# yazar, oradaki linkler bize bir şey söylemez; ama kavram makaleleri gerçek notlardır
# ve Obsidian onlara giden linki çözer, kırık göstermez. Envanterde olmayınca
# [[X-M5 Kılavuz Wiki]] gibi geçerli linkler kırık sayılıyordu.
ENVANTER_EK = ("BİLGİ/kavramlar/",)
KOK_KLASOR = "HAFIZA|GÜNLÜK|BİLGİ|GİZLİ|EĞİTİMLER|İŞ|KİŞİSEL|PROJELER|ASSETS|RAW|YEDEK|\\.claude"
RE_LINK = re.compile(r"!?\[\[([^\]\n]+?)\]\]")
RE_FENCE = re.compile(r"(?ms)^\s*```.*?^\s*```")
RE_INLINE = re.compile(r"`[^`\n]*`")
# Yol yalnız sınırlı bağlamdan okunur: `backtick` ya da **kalın**. Yollarda boşluk
# olduğu için serbest metinden okumak yolu ilk boşlukta kesip yanlış pozitif üretir.
RE_KUTU = re.compile(r"`([^`\n]{3,200})`|\*\*`?([^*\n]{3,200}?)`?\*\*")
# Vault'un bulunduğu diskin kökü (ör. bir harici disk) mutlak yol öneki sayılır.
DIS_KOK = re.escape(str(VAULT.parent)) if str(VAULT.parent) not in ("/", "") else None
RE_YOL = re.compile(
    rf"^(?:{DIS_KOK}/.+|(?:{KOK_KLASOR})/.+)$" if DIS_KOK
    else rf"^(?:{KOK_KLASOR})/.+$"
)
# Şablon yer tutucuları ve komut satırları gerçek dosya değildir.
RE_YERTUTUCU = re.compile(r"\*|<|\||\bYYYY\b|\bAA-GG\b|\bNN-|\bxx\b|\{|\$")
# " --bayrak" ile biten komut, backtick kalıntısı taşıyan ya da cümleye dönüşen aday.
RE_KOMUT = re.compile(r"\s--|\s-[a-zA-Z]\b|`")


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _parcalar(rel: Path) -> tuple[str, ...]:
    """macOS dosya adlarını NFD verir; karşılaştırmadan önce NFC'ye çek."""
    return tuple(_nfc(x) for x in rel.parts)


def _taranir(parcalar: tuple[str, ...]) -> bool:
    """Bir yol kaynak olarak taranır mı: TARAMA_ATLA uygulanır, BİLGİ özel durumdur.

    BİLGİ altında yalnız BİLGİ/kavramlar/ gerçek nottur (kavram makaleleri); index.md,
    log.md gibi makine üretimi diğer BİLGİ dosyaları hiçbir taramaya girmez. Yalnız
    link_taramasi() kullanır; yapı taraması (_yapi_dosyalar) BİLGİ'yi tamamen dışarıda
    bırakıyor, oraya bu fonksiyon karışmaz.
    """
    if not parcalar:
        return False
    if parcalar[0] == "BİLGİ":
        return len(parcalar) > 1 and parcalar[1] == "kavramlar"
    return not (set(parcalar) & TARAMA_ATLA)


def _tarihi_kayit(rel: Path) -> bool:
    """Dosya tarihî kayıt mı: içindeki yol "o tarihte şuradaydı" demek için yazılmıştır.

    Kararlar dosyaları append-only'dir, denetim raporları o günün fotoğrafıdır, HAFIZA
    dosyaları geçmiş oturumları anlatır. Üçünde de artık var olmayan bir yolun geçmesi
    beklenen durumdur, bozukluk değil; ölü yol taraması bunları atlar.
    Kırık wiki-link taraması bu dosyalarda sürer: Obsidian kırık linki kullanıcıya
    kırık gösterir, o yüzden düzeltilmesi gerekir.
    BİLGİ/kavramlar/ da aynı muameleyi görür: derlenmiş makaleler geçmişi anlatır,
    eski yol adı geçmesi doğaldır.
    """
    ad = _nfc(rel.name)
    return (
        ad.endswith(" Kararlar.md")
        or " Denetim-" in ad
        or _parcalar(rel)[:1] == ("HAFIZA",)
        or _parcalar(rel)[:2] == ("BİLGİ", "kavramlar")
    )


def _egitim_kokleri() -> list[Path]:
    """EĞİTİMLER/KAYNAKLAR altındaki eğitim kökleri.

    Bir klasör eğitim köküdür: adında `(!)` geçiyorsa ya da içinde `00 İçindekiler.md`
    varsa. META gibi ara klasörler yalnız gruplayıcıdır, kök değildir.
    """
    kaynaklar = VAULT / "EĞİTİMLER" / "KAYNAKLAR"
    if not kaynaklar.is_dir():
        return []
    kokler: list[Path] = []

    def gez(dizin: Path, derinlik: int) -> None:
        if derinlik > 2:
            return
        try:
            altlar = sorted(d for d in dizin.iterdir() if d.is_dir() and not d.name.startswith("."))
        except OSError:
            return
        for d in altlar:
            if "(!)" in _nfc(d.name) or (d / "00 İçindekiler.md").is_file():
                kokler.append(d)
            else:
                gez(d, derinlik + 1)

    gez(kaynaklar, 1)
    return kokler


def _egitime_gore_var(p: Path, aday: str, kokler: list[Path]) -> bool:
    """Yol eğitimin köküne göre çözülüyor mu.

    Ders sayfasındaki `RAW/BELGELER/x.txt` vault köküne göre değil, o eğitimin köküne
    göredir: EĞİTİMLER/KAYNAKLAR/<Eğitim>/RAW/BELGELER/x.txt. Ayrıca `RAW/VİDEOLAR`
    gibi yalın yollar eğitim klasör yapısını anlatır (hangi eğitim olduğu söylenmez);
    herhangi bir eğitimde o alt yol varsa yapı doğrudur, yol ölü değildir.
    """
    for kok in kokler:
        # Önce dosyanın kendi eğitimi, sonra yapı anlatımı için bütün eğitimler.
        try:
            if (kok / aday).exists():
                return True
        except OSError:
            continue
    return False


def _envanter() -> tuple[set[str], set[str], set[str]]:
    """Link hedefi envanteri: dosya adları, uzantısız yollar ve tam yollar (NFC, casefold).

    Taranmayan klasörler burada da atlanır; tek istisna ENVANTER_EK: oradaki dosyalar
    kaynak olarak okunmaz ama hedef olarak vardır.
    """
    adlar: set[str] = set()
    yollar: set[str] = set()
    tam: set[str] = set()
    for p in VAULT.rglob("*"):
        rel = p.relative_to(VAULT)
        if set(_parcalar(rel)) & TARAMA_ATLA and not _nfc(str(rel)).startswith(ENVANTER_EK):
            continue
        if not p.is_file():
            continue
        r = _nfc(str(rel)).casefold()
        tam.add(r)
        if p.suffix == ".md":
            adlar.add(_nfc(p.stem).casefold())
            yollar.add(_nfc(str(rel.with_suffix(""))).casefold())
        else:
            adlar.add(_nfc(p.name).casefold())
            yollar.add(r)
    return adlar, yollar, tam


def link_taramasi() -> dict:
    """Bütün notlarda kırık wiki-link ve var olmayan düz metin yolları bulur."""
    adlar, yollar, tam = _envanter()
    egitim_kokleri = _egitim_kokleri()
    kirik: list[tuple[str, str]] = []
    olu: list[tuple[str, str]] = []
    kaynak_kirik = 0
    kaynak_olu = 0

    for p in VAULT.rglob("*.md"):
        rel = p.relative_to(VAULT)
        parcalar = _parcalar(rel)
        if not _taranir(parcalar):
            continue
        # KAYNAKLAR içeriği dokunulmaz orijinal kaynak: kırıkları ayrı sayılır.
        salt = parcalar[:2] == ("EĞİTİMLER", "KAYNAKLAR")
        try:
            ham = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        govde = RE_FENCE.sub(" ", ham)
        metin = RE_INLINE.sub(" ", govde)
        yol_adi = _nfc(str(rel))

        for m in RE_LINK.finditer(metin):
            hedef = m.group(1).split("|")[0].split("#")[0].split("^")[0].strip().rstrip("\\").strip()
            # Şablon yer tutucusu ([[...]], [[ad.mp4]], [[<Proje> Context]]) hedef değildir.
            if not hedef or set(hedef) <= {"."} or RE_YERTUTUCU.search(hedef):
                continue
            k = _nfc(hedef).casefold()
            if k in adlar or k in yollar or k in tam or (k + ".md") in tam:
                continue
            # Obsidian hedefi klasörden bağımsız dosya adıyla da çözer:
            # [[ASSETS/X.png]] dosya başka klasörde olsa bile geçerlidir.
            taban = k.rsplit("/", 1)[-1]
            if taban in adlar or taban in tam or (taban + ".md") in tam:
                continue
            # Göreli hedef (../ ile) not dosyasının bulunduğu klasöre göre çözülür.
            if "/" in hedef:
                try:
                    goreli = (p.parent / hedef).resolve()
                    if goreli.exists() or goreli.with_suffix(".md").exists():
                        continue
                except (OSError, ValueError):
                    pass
            if salt:
                kaynak_kirik += 1
            else:
                kirik.append((yol_adi, hedef))

        # Tarihî kayıtta ölü yol beklenen durumdur; yalnız yol taraması atlanır,
        # kırık wiki-link taraması yukarıda bu dosyalarda da çalıştı.
        if _tarihi_kayit(rel):
            continue

        # Wiki-link içerikleri yukarıda sayıldı; yol taramasında tekrar sayılmasın.
        yol_govde = RE_LINK.sub(" ", govde)
        for m in RE_KUTU.finditer(yol_govde):
            aday = (m.group(1) or m.group(2) or "").strip().rstrip(".,:;»'\"` ")
            if aday.endswith(")") and "(" not in aday:
                aday = aday[:-1]
            if not RE_YOL.match(aday) or RE_YERTUTUCU.search(aday) or RE_KOMUT.search(aday):
                continue
            aday = aday.rstrip("/")
            if aday.count("/") < 1:
                continue
            hedef = Path(aday) if aday.startswith("/") else VAULT / aday
            try:
                if hedef.exists():
                    continue
            except OSError:
                continue
            # Vault köküne göre yok: eğitim köküne göre de dene (ders sayfasındaki
            # RAW/BELGELER/x.txt o eğitimin altındadır, vault kökünde değil).
            if not aday.startswith("/") and _egitime_gore_var(p, aday, egitim_kokleri):
                continue
            if salt:
                kaynak_olu += 1
            else:
                olu.append((yol_adi, aday))

    sayac: dict[str, int] = {}
    for f, _ in kirik + olu:
        sayac[f] = sayac.get(f, 0) + 1
    return {
        "kirik": kirik,
        "olu": olu,
        "kaynak_kirik": kaynak_kirik,
        "kaynak_olu": kaynak_olu,
        "en_cok": sorted(sayac.items(), key=lambda x: (-x[1], x[0]))[:3],
    }


def linkler_raporu() -> str:
    """--linkler: dosya başına gruplu tam liste."""
    r = link_taramasi()
    gruplar: dict[str, list[str]] = {}
    for f, h in r["kirik"]:
        gruplar.setdefault(f, []).append(f"kırık link: [[{h}]]")
    for f, y in r["olu"]:
        gruplar.setdefault(f, []).append(f"ölü yol: {y}")
    satirlar = [
        f"Kırık wiki-link: {len(r['kirik'])}, ölü yol: {len(r['olu'])}, "
        f"etkilenen dosya: {len(gruplar)}",
        f"EĞİTİMLER/KAYNAKLAR (dokunulmaz kaynak): {r['kaynak_kirik']} kırık link, "
        f"{r['kaynak_olu']} ölü yol",
        "",
    ]
    for f in sorted(gruplar):
        satirlar.append(f)
        for s in gruplar[f]:
            satirlar.append(f"    {s}")
    if not gruplar:
        satirlar.append("Kırık link ve ölü yol yok.")
    return "\n".join(satirlar)


# --- Yapısal sağlık taraması (--yapi) ---------------------------------------
# Anayasanın "Projelerde çalışma düzeni" bölümündeki kuralları makine kontrol eder:
# öksüz sayfa yasak, proje çekirdeği tam olmalı, linkleme çift yönlü, her alanın
# tetiği ve durumu olmalı, İŞ altındaki her klasör bir alana bağlanmalı, hub güncel.

# Öksüz taramasından muaf kökler: makine yazar, gizlidir ya da vault notu değildir.
YAPI_MUAF_KOK = {"HAFIZA", "GÜNLÜK", "BİLGİ", "GİZLİ", "YEDEK", ".git", ".obsidian", ".claude", ".trash"}
# Bu adlar tasarım gereği linksizdir: katalog, anayasa, eğitim içindekileri, kişisel not dosyası.
YAPI_MUAF_AD = {"CLAUDE.md", "index.md", "00 İçindekiler.md"}
PROJE_CEKIRDEK = ("— Proje", "Context", "Kararlar", "PRD")
ALAN_SONEK = " — Alan.md"
RE_FRONTMATTER_AD = re.compile(r"^ad:\s*(.+)$", re.MULTILINE)


def cekirdek(klasor: Path, ad: str, tur: str) -> Path | None:
    """`Context`, `Kararlar`, `PRD`, `Yönerge`, `Proje`, `Alan` dosyasını bulur.
    Önce sade ad (Context.md), yoksa eski önekli ad (<Ad> Context.md)."""
    sade = klasor / f"{tur}.md"
    if sade.is_file():
        return sade
    onekli = klasor / f"{ad} {tur}.md"
    if onekli.is_file():
        return onekli
    if tur in ("Proje", "Alan"):
        tireli = klasor / f"{ad} — {tur}.md"
        if tireli.is_file():
            return tireli
    return None


def alan_dosyasi_mi(isim: str) -> bool:
    return isim == "Alan.md" or isim.endswith(" — Alan.md")


def alan_adi_oku(sayfa: Path, ad_dosyadan: str) -> str:
    """`Alan.md` ise frontmatter'daki `ad:` alanını okur; yoksa/eksikse dosyadan türetilen adı döner."""
    if sayfa.name != "Alan.md":
        return ad_dosyadan
    try:
        with sayfa.open("r", encoding="utf-8") as f:
            bas = f.read(2048)
    except OSError:
        return ad_dosyadan
    satirlar = bas.splitlines()
    if not satirlar or satirlar[0].strip() != "---":
        return ad_dosyadan
    son = None
    for i, satir in enumerate(satirlar[1:], 1):
        if satir.strip() in ("---", "..."):
            son = i
            break
    if son is None:
        return ad_dosyadan
    blok = "\n".join(satirlar[1:son])
    eslesme = RE_FRONTMATTER_AD.search(blok)
    if eslesme:
        deger = eslesme.group(1).strip().strip("\"'").strip()
        if deger:
            return deger
    return ad_dosyadan


def _yapi_dosyalar() -> list[Path]:
    """Taranacak notlar: muaf kökler dışındaki bütün .md dosyaları.

    BİLGİ (kavramlar dahil) burada tamamen dışarıda kalır: BİLGİ/index.md makalelerin
    hub'ıdır, derleyici her makaleyi oraya yazar; öksüz sayfa kavramı BİLGİ için
    anlamsızdır. Bayat makale kontrolü (bayatlama_taramasi) bu listeye bağlı değildir,
    BİLGİ/kavramlar'ı kendi başına gezer.
    """
    cikti = []
    for p in VAULT.rglob("*.md"):
        rel = p.relative_to(VAULT)
        if set(_parcalar(rel)) & YAPI_MUAF_KOK:
            continue
        cikti.append(p)
    return cikti


def _link_hedefleri(dosyalar: list[Path]) -> set[str]:
    """Bütün notlardaki [[hedef]] adları: hem uzantısız tam yol hem taban ad (NFC, casefold)."""
    hedefler: set[str] = set()
    for p in dosyalar:
        try:
            ham = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        metin = RE_INLINE.sub(" ", RE_FENCE.sub(" ", ham))
        for m in RE_LINK.finditer(metin):
            h = m.group(1).split("|")[0].split("#")[0].split("^")[0].strip().rstrip("\\").strip()
            if not h or RE_YERTUTUCU.search(h):
                continue
            k = _nfc(h).casefold()
            if k.endswith(".md"):
                k = k[:-3]
            hedefler.add(k)
            hedefler.add(k.rsplit("/", 1)[-1])
    return hedefler


def _bolum_hedefleri(dosya: Path, baslik: str) -> set[str]:
    """Bir başlığın altındaki wiki-link hedefleri (taban ad, casefold). Bölüm yoksa boş küme."""
    try:
        satirlar = dosya.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return set()
    hedefler: set[str] = set()
    icinde = False
    for s in satirlar:
        if s.startswith("## "):
            if icinde:
                break
            icinde = _nfc(s).strip().casefold().startswith(_nfc(baslik).casefold())
            continue
        if not icinde:
            continue
        for m in RE_LINK.finditer(s):
            h = m.group(1).split("|")[0].split("#")[0].split("^")[0].strip()
            if not h:
                continue
            k = _nfc(h).casefold()
            if k.endswith(".md"):
                k = k[:-3]
            hedefler.add(k.rsplit("/", 1)[-1])
    return hedefler


def _icerik_alan_linkliyor_mu(icerik: str, alanlar: list[tuple[str, Path | None]]) -> bool:
    """İçerikteki wiki-linklerden biri verilen alanlardan birini işaret ediyor mu.

    Hedef sade ("Alan"), önekli ("<Ad> — Alan") ya da tam yollu ("İŞ/.../Alan")
    olabilir; ölçüt hedefin taban adının "Alan" olması veya adla eşleşmesi.
    """
    adlar_kucuk = {_nfc(ad).casefold() for ad, _ in alanlar}
    govde = RE_INLINE.sub(" ", RE_FENCE.sub(" ", icerik))
    for m in RE_LINK.finditer(govde):
        hedef = m.group(1).split("|")[0].split("#")[0].split("^")[0].strip()
        if not hedef:
            continue
        k = _nfc(hedef).casefold()
        if k.endswith(".md"):
            k = k[:-3]
        taban = k.rsplit("/", 1)[-1]
        if taban == "alan":
            return True
        for ad_kucuk in adlar_kucuk:
            if taban == f"{ad_kucuk} — alan":
                return True
    return False


def _alanlari_bul() -> list[tuple[str, Path]]:
    """İŞ ve KİŞİSEL altındaki `Alan.md` / `<Ad> — Alan.md` sayfaları."""
    bulunan: list[tuple[str, Path]] = []
    for kok_adi in (_ayar().get("alan_kokleri") or ["İŞ", "KİŞİSEL"]):
        kok = VAULT / kok_adi
        if not kok.is_dir():
            continue
        for p in kok.rglob("*.md"):
            ad = _nfc(p.name)
            if alan_dosyasi_mi(ad):
                if ad == "Alan.md":
                    ad_dosyadan = _nfc(p.parent.name)
                else:
                    ad_dosyadan = ad[: -len(ALAN_SONEK)]
                bulunan.append((alan_adi_oku(p, ad_dosyadan), p))
    bulunan.sort(key=lambda x: x[0])
    return bulunan


def yapi_taramasi() -> dict:
    """Anayasanın yapı kurallarını kontrol eder; kategori başına bulgu listesi döner."""
    dosyalar = _yapi_dosyalar()
    hedefler = _link_hedefleri(dosyalar)
    notlar_dosyasi = _nfc(str(_ayar().get("notlar_dosyasi") or "NOTLARIM.md"))
    egitim_kokleri = {p.resolve() for p in _egitim_kokleri()}

    # 1) Öksüz sayfa: hiçbir nottan [[link]] almayan .md
    oksuz: list[str] = []
    for p in dosyalar:
        rel = p.relative_to(VAULT)
        parcalar = _parcalar(rel)
        ad = _nfc(p.name)
        if ad in YAPI_MUAF_AD or ad == notlar_dosyasi:
            continue
        if parcalar[:2] == ("ASSETS", "TEMPLATES"):
            continue
        # Eğitim transkriptleri (KAYNAKLAR/<Eğitim>/RAW/...) ders sayfasından
        # dosya adıyla değil bölümle anılır; öksüzlük beklenen durumdur.
        if parcalar[:2] == ("EĞİTİMLER", "KAYNAKLAR") and "RAW" in parcalar:
            continue
        k = _nfc(str(rel.with_suffix(""))).casefold()
        if k in hedefler or k.rsplit("/", 1)[-1] in hedefler:
            continue
        oksuz.append(_nfc(str(rel)))

    # 2) Proje çekirdeği ve 3) çift yönlü link
    # Sade çekirdek adları ("Context.md" ...) ve eski önekli adlar ("<Ad> Context.md")
    # ikisi de geçerlidir; hangisi varsa cekirdek() bulur (öneklendirme kuralı kalktı).
    CEKIRDEK_SADE = {"Context.md", "Kararlar.md", "PRD.md", "Yönerge.md", "Proje.md", "Alan.md"}
    proje_eksik: list[str] = []
    link_tek_yon: list[str] = []
    projeler = VAULT / "PROJELER"
    if projeler.is_dir():
        for d in sorted(x for x in projeler.iterdir() if x.is_dir() and not x.name.startswith(".")):
            ad = _nfc(d.name)
            for son in PROJE_CEKIRDEK:
                tur = "Proje" if son == "— Proje" else son
                if cekirdek(d, ad, tur) is None:
                    proje_eksik.append(f"PROJELER/{ad}: {tur}.md yok")
            cekirdek_dosyalari = {
                f.name for son in PROJE_CEKIRDEK
                for f in [cekirdek(d, ad, "Proje" if son == "— Proje" else son)]
                if f is not None
            }
            yonerge_dosyasi = cekirdek(d, ad, "Yönerge")
            if yonerge_dosyasi is not None:
                cekirdek_dosyalari.add(yonerge_dosyasi.name)
            context = cekirdek(d, ad, "Context")
            alt_sayfalar = _bolum_hedefleri(context, "## Alt Sayfalar") if context is not None else set()
            for p in sorted(d.rglob("*.md")):
                dosya_adi = _nfc(p.name)
                rel = _nfc(str(p.relative_to(VAULT)))
                if dosya_adi in CEKIRDEK_SADE or dosya_adi in cekirdek_dosyalari:
                    continue
                govde_stem = _nfc(p.stem).casefold()
                if govde_stem not in alt_sayfalar:
                    link_tek_yon.append(f"{rel}: Context'in '## Alt Sayfalar' listesinde yok")
                try:
                    icerik = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                icerik_kucuk = _nfc(icerik).casefold()
                if f"[[{ad} context".casefold() not in icerik_kucuk \
                        and "[[context" not in icerik_kucuk \
                        and f"[[projeler/{ad.casefold()}/context".casefold() not in icerik_kucuk:
                    link_tek_yon.append(f"{rel}: içinde Context geri linki yok")

    # 4) Alanlar: tetik satırı, Context ve Kararlar
    alanlar = _alanlari_bul()
    alan_eksik: list[str] = []
    for ad, sayfa in alanlar:
        rel = _nfc(str(sayfa.relative_to(VAULT)))
        try:
            bas = sayfa.read_text(encoding="utf-8", errors="replace")[:2048]
        except OSError:
            bas = ""
        if not re.search(r"(?m)^tetik\s*:", bas):
            alan_eksik.append(f"{rel}: 'tetik:' satırı yok")
        for son in ("Context", "Kararlar"):
            if cekirdek(sayfa.parent, ad, son) is None:
                alan_eksik.append(f"{rel}: aynı klasörde {son}.md yok")

    # 5) Alan kapsamı: İŞ altındaki her klasör bir alana bağlı olmalı
    alan_klasorleri = {p.parent.resolve() for _, p in alanlar}
    kapsam: list[str] = []
    is_kok = VAULT / "İŞ"
    if is_kok.is_dir():
        for d in sorted(x for x in is_kok.rglob("*") if x.is_dir()):
            rel_parts = _parcalar(d.relative_to(VAULT))
            if len(rel_parts) - 1 > 2 or any(x.startswith(".") for x in rel_parts):
                continue
            coz = d.resolve()
            if coz in alan_klasorleri or any(coz.is_relative_to(a) for a in alan_klasorleri):
                continue
            # Hub sayfası: kendi `Alan.md`'si yok ama alt alanları linkliyor.
            # Link hedefi sade ("Alan"), önekli ("<Ad> — Alan") ya da tam yollu
            # ("İŞ/GÖRSEL ÜRETİM/Alan") olabilir; ölçüt hedefin son parçasının
            # ilgili alanı işaret etmesi.
            hub = False
            for p in d.glob("*.md"):
                try:
                    icerik = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if _icerik_alan_linkliyor_mu(icerik, alanlar):
                    hub = True
                    break
            if not hub:
                kapsam.append(f"{_nfc(str(d.relative_to(VAULT)))}: alan klasörü değil, alan altında değil, hub sayfası yok")

    # 6) Hub: Projeler.md her projeyi ve her alanı linkliyor mu
    hub_eksik: list[str] = []
    hub_dosya = projeler / "Projeler.md"
    if hub_dosya.is_file():
        try:
            hub_ham = hub_dosya.read_text(encoding="utf-8", errors="replace")
        except OSError:
            hub_ham = ""
        hub_metin = _nfc(hub_ham).casefold()
        for d in sorted(x for x in projeler.iterdir() if x.is_dir() and not x.name.startswith(".")):
            if f"[[{_nfc(d.name).casefold()} " not in hub_metin \
                    and f"[[{_nfc(d.name).casefold()}/" not in hub_metin \
                    and f"projeler/{_nfc(d.name).casefold()}/" not in hub_metin:
                hub_eksik.append(f"PROJELER/Projeler.md: {_nfc(d.name)} projesi linklenmemiş")
        for ad, _ in alanlar:
            if not _icerik_alan_linkliyor_mu(hub_ham, [(ad, None)]):
                hub_eksik.append(f"PROJELER/Projeler.md: {ad} alanı linklenmemiş")
    elif projeler.is_dir():
        # PROJELER klasörü hiç yoksa (yeni kurulum) hub'ın da olmaması normaldir.
        hub_eksik.append("PROJELER/Projeler.md yok")

    return {
        "oksuz": oksuz,
        "proje_eksik": proje_eksik,
        "link_tek_yon": link_tek_yon,
        "alan_eksik": alan_eksik,
        "kapsam": kapsam,
        "hub_eksik": hub_eksik,
    }


YAPI_ETIKET = [
    ("oksuz", "öksüz sayfa"),
    ("proje_eksik", "eksik proje çekirdeği"),
    ("link_tek_yon", "tek yönlü link"),
    ("alan_eksik", "eksik alan dosyası"),
    ("kapsam", "kapsam dışı klasör"),
    ("hub_eksik", "hub'da eksik"),
]


def yapi_ozet(r: dict) -> list[str]:
    """Oturum açılışına giren kısa özet: yalnız sıfır olmayan kategoriler, en fazla 3 satır."""
    parca = [f"{len(r[k])} {etiket}" for k, etiket in YAPI_ETIKET if r.get(k)]
    if not parca:
        return []
    return [
        "Yapı taraması: " + ", ".join(parca) + ".",
        "Tam liste: python3 .claude/scripts/saglik.py --yapi",
    ]


def yapi_raporu() -> str:
    """--yapi: kategori ve dosya başına gruplu tam liste."""
    r = yapi_taramasi()
    toplam = sum(len(r[k]) for k, _ in YAPI_ETIKET)
    satirlar = [f"Yapısal sağlık: {toplam} bulgu.", ""]
    for anahtar, etiket in YAPI_ETIKET:
        bulgular = r[anahtar]
        satirlar.append(f"## {etiket} ({len(bulgular)})")
        if not bulgular:
            satirlar.append("    temiz")
            satirlar.append("")
            continue
        if anahtar == "oksuz":
            # Öksüzler çok olabilir: üst klasöre göre grupla.
            gruplar: dict[str, list[str]] = {}
            for yol in bulgular:
                ust = yol.rsplit("/", 1)[0] if "/" in yol else "(kök)"
                gruplar.setdefault(ust, []).append(yol.rsplit("/", 1)[-1])
            for ust in sorted(gruplar):
                satirlar.append(f"    {ust} ({len(gruplar[ust])})")
                for ad in sorted(gruplar[ust]):
                    satirlar.append(f"        {ad}")
        else:
            for b in bulgular:
                satirlar.append(f"    {b}")
        satirlar.append("")
    return "\n".join(satirlar).rstrip() + "\n"


def _git(*args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(VAULT), *args], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _git_ts(yol: Path, filtre: str, follow: bool = False) -> float | None:
    """Dosyanın git geçmişindeki ilgili son commit zamanı (unix epoch). Git'te yoksa None."""
    args = ["log", "-1", "--format=%ct", f"--diff-filter={filtre}"]
    if follow:
        args.append("--follow")
    args += ["--", str(yol.relative_to(VAULT))]
    out = _git(*args)
    return float(out) if out.strip().isdigit() else None


def _tum_notlar_haritasi() -> dict[str, Path]:
    """Bütün .md notlarının taban adı ve göreli yolu (uzantısız, casefold) -> tam yol.

    Kavram makalesindeki [[hedef]] linkinin gerçek dosyaya çözümü için; BİLGİ ve
    GÜNLÜK dosyaları da haritada durur (bayatlama_taramasi onları sonradan eler).
    """
    harita: dict[str, Path] = {}
    for p in VAULT.rglob("*.md"):
        rel = p.relative_to(VAULT)
        harita.setdefault(_nfc(p.stem).casefold(), p)
        harita.setdefault(_nfc(str(rel.with_suffix(""))).casefold(), p)
    return harita


def bayatlama_taramasi() -> dict[str, list[tuple[str, str]]]:
    """Kavram makalesi, linklediği vault notundan eski mi.

    Her BİLGİ/kavramlar/*.md için son değişiklik tarihi git'ten alınır (yoksa mtime).
    Makaledeki [[hedef]] linklerinden BİLGİ ve GÜNLÜK dışındaki hedeflerin son İÇERİK
    değişikliği (yalnız M; taşıma ve yeniden adlandırma sayılmaz) makaleden en az bir
    gün yeniyse makale "bayat" sayılır. Dönüş: {makale_adı: [(hedef_adı, hedef_tarihi), ...]}.
    """
    kavramlar_dizin = VAULT / "BİLGİ" / "kavramlar"
    if not kavramlar_dizin.is_dir():
        return {}
    harita = _tum_notlar_haritasi()
    hedef_cache: dict[Path, float | None] = {}
    sonuc: dict[str, list[tuple[str, str]]] = {}

    for p in sorted(kavramlar_dizin.glob("*.md")):
        makale_adi = _nfc(p.stem)
        makale_ts = _git_ts(p, "AM")
        if makale_ts is None:
            makale_ts = _mtime(p)
        try:
            metin = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        govde = RE_INLINE.sub(" ", RE_FENCE.sub(" ", metin))
        bayat_hedefler: list[tuple[str, str]] = []
        gorulen: set[Path] = set()
        for m in RE_LINK.finditer(govde):
            hedef = m.group(1).split("|")[0].split("#")[0].split("^")[0].strip()
            if not hedef:
                continue
            k = _nfc(hedef).casefold()
            if k.endswith(".md"):
                k = k[:-3]
            hedef_p = harita.get(k) or harita.get(k.rsplit("/", 1)[-1])
            if hedef_p is None or hedef_p in gorulen:
                continue
            gorulen.add(hedef_p)
            parcalar = _parcalar(hedef_p.relative_to(VAULT))
            if parcalar[0] in ("BİLGİ", "GÜNLÜK"):
                continue
            if hedef_p not in hedef_cache:
                ts = _git_ts(hedef_p, "M", follow=True)
                hedef_cache[hedef_p] = ts if ts is not None else _mtime(hedef_p)
            hedef_ts = hedef_cache[hedef_p]
            if hedef_ts and hedef_ts - makale_ts >= 86400:
                bayat_hedefler.append((_nfc(hedef_p.stem), dt.date.fromtimestamp(hedef_ts).isoformat()))
        if bayat_hedefler:
            sonuc[makale_adi] = bayat_hedefler
    return sonuc


def _bayat_ozet(bayat: dict[str, list[tuple[str, str]]]) -> str | None:
    """kontrol() özetine giren tek satır: en fazla 3 makale adı, fazlası '+K'."""
    if not bayat:
        return None
    adlar = sorted(bayat)
    parca = [f"{ad} ({bayat[ad][0][0]}'ten)" for ad in adlar[:3]]
    ekstra = len(adlar) - 3
    metin = ", ".join(parca) + (f", +{ekstra}" if ekstra > 0 else "")
    return f"BİLGİ: {len(adlar)} makale kaynağından eski: {metin}"


def bayat_raporu(bayat: dict[str, list[tuple[str, str]]]) -> list[str]:
    """--yapi çıktısına eklenen '## bayat makale' bölümü: tam liste."""
    satirlar = [f"## bayat makale ({len(bayat)})"]
    if not bayat:
        satirlar.append("    temiz")
        satirlar.append("")
        return satirlar
    for ad in sorted(bayat):
        satirlar.append(f"    {ad}")
        for hedef_adi, tarih in bayat[ad]:
            satirlar.append(f"        {hedef_adi} ({tarih}'ten)")
    satirlar.append("")
    return satirlar


def kontrol() -> dict:
    sorunlar: list[str] = []
    bilgi: list[str] = []
    simdi = time.time()

    # 1) Son Oturum, son günlükten geride mi
    gunlukler = sorted((VAULT / "GÜNLÜK").glob("*.md"), key=_mtime)
    son_gunluk = gunlukler[-1] if gunlukler else None
    son_oturum = VAULT / "HAFIZA" / "Son Oturum.md"
    if son_gunluk and son_oturum.exists():
        fark = _mtime(son_gunluk) - _mtime(son_oturum)
        if fark > 12 * 3600:
            sorunlar.append(f"Son Oturum, son günlük kaydından {fark/3600:.0f} saat geride: makine yazımı çalışmamış olabilir ({son_gunluk.name}).")
    if son_gunluk and simdi - _mtime(son_gunluk) > 96 * 3600:
        bilgi.append(f"Son günlük kaydı {(simdi - _mtime(son_gunluk))/86400:.0f} gün önce ({son_gunluk.name}).")

    # 2) Derleme
    cs = _json(STATE / "compile-state.json")
    durum = str(cs.get("last_status", ""))
    if durum.startswith("fail"):
        sorunlar.append(f"Akşam derlemesi son koşuda düştü: {durum[:80]}.")
    kosular = cs.get("runs", [])[-4:]
    if isinstance(kosular, list) and len(kosular) >= 4:
        dusen = sum(1 for r in kosular if isinstance(r, dict) and str(r.get("status", "")).startswith("fail"))
        if dusen >= 3:
            sorunlar.append(f"Derleyici son {len(kosular)} koşunun {dusen}'ünde düştü.")

    # 3) health.json (48 saat içindeki hata, sonradan başarılı koşuyla çözülmediyse)
    h = _json(STATE / "health.json")
    if isinstance(h.get("ts"), (int, float)) and simdi - float(h["ts"]) < 48 * 3600 and h.get("error"):
        hata_ts = float(h["ts"])
        cozuldu = False
        if h.get("component") == "compile":
            tum_kosular = cs.get("runs", [])
            if isinstance(tum_kosular, list):
                for r in tum_kosular:
                    if not isinstance(r, dict) or str(r.get("status", "")) != "ok":
                        continue
                    r_ts = r.get("ts")
                    if isinstance(r_ts, str):
                        try:
                            r_zaman = dt.datetime.fromisoformat(r_ts).timestamp()
                        except ValueError:
                            continue
                        if r_zaman > hata_ts:
                            cozuldu = True
                            break
        if not cozuldu:
            sorunlar.append(f"Motor hatası ({h.get('component')}): {str(h.get('error'))[:140]}")

    # 4) Bugün aynı içerikli iki özet var mı
    bugun = VAULT / "GÜNLÜK" / f"{dt.date.today().isoformat()}.md"
    if bugun.exists():
        metin = bugun.read_text(encoding="utf-8", errors="replace")
        bloklar = re.split(r"(?m)^### Oturum", metin)[1:]
        imzalar = []
        for b in bloklar:
            m = re.search(r"## Bağlam\s*\n(.{0,160})", b, re.S)
            if m:
                imzalar.append(re.sub(r"\s+", " ", m.group(1)).strip()[:120])
        if len(imzalar) != len(set(imzalar)):
            sorunlar.append("Bugünün günlüğünde aynı içerikli iki özet var; tekrar denetimi kaçırmış.")

    # 5) Git: remote, push, bekleyen
    if not _git("remote", "get-url", "origin"):
        sorunlar.append("Vault'un uzak deposu yok; yedek tek diskte.")
    else:
        sb = _git("status", "-sb").splitlines()
        if sb and "ahead" in sb[0]:
            m = re.search(r"ahead (\d+)", sb[0])
            n = int(m.group(1)) if m else 0
            if n >= 3:
                sorunlar.append(f"{n} commit push edilmemiş; push kancası çalışmıyor olabilir.")
    bekleyen = _git("status", "--porcelain").splitlines()
    if len(bekleyen) > 150:
        sorunlar.append(f"{len(bekleyen)} dosya commit bekliyor; oturum sonu commit'i çalışmıyor olabilir.")

    # 7) Vault geneli kırık wiki-link ve ölü düz metin yol (BİLGİ/kavramlar dahil)
    lt = link_taramasi()
    n_kirik, n_olu = len(lt["kirik"]), len(lt["olu"])
    if n_kirik:
        # Kırık wiki-link gerçek sorundur: Obsidian'da tıklanınca hiçbir yere gitmez.
        sorunlar.append(
            f"Vault'ta {n_kirik} kırık wiki-link var; taşımadan kalmış olabilir. "
            "Tam liste: python3 .claude/scripts/saglik.py --linkler"
        )
        for f, c in lt["en_cok"]:
            bilgi.append(f"En çok kırık taşıyan: {f} ({c})")
    if n_olu:
        # Ölü düz metin yol çoğunlukla Kararlar dosyalarındaki tarihli geçmiş kaydıdır
        # ("şu klasör şuraya taşındı"); olduğu gibi kalması doğrudur, bu yüzden yalnız bilgi.
        bilgi.append(
            f"{n_olu} ölü düz metin yol var (çoğu Kararlar dosyalarındaki tarihli kayıt). "
            "Liste: python3 .claude/scripts/saglik.py --linkler"
        )
    if lt["kaynak_kirik"] or lt["kaynak_olu"]:
        bilgi.append(
            f"EĞİTİMLER/KAYNAKLAR (dokunulmaz kaynak): {lt['kaynak_kirik']} kırık link, "
            f"{lt['kaynak_olu']} ölü yol (bilgi)."
        )

    # 7b) Yapısal sağlık (anayasanın çalışma düzeni kuralları)
    yapi = yapi_taramasi()
    yapi_satir = yapi_ozet(yapi)
    bilgi.extend(yapi_satir)

    # 7c) Bayat kavram makalesi (kaynağından eski)
    try:
        bayat_satir = _bayat_ozet(bayatlama_taramasi())
    except Exception as e:  # bayatlama yardımcı kontroldür, ana kontrolü düşürmesin
        bayat_satir = f"Bayatlama taraması çalışmadı: {type(e).__name__}: {e}"
    if bayat_satir:
        bilgi.append(bayat_satir)

    # 8) Haftalık bakım
    hb = _json(STATE / "haftalik.json")
    son = hb.get("son")
    gecen = None
    try:
        gecen = (dt.date.today() - dt.date.fromisoformat(son)).days if isinstance(son, str) else None
    except ValueError:
        gecen = None
    haftalik = gecen is None or gecen >= HAFTALIK_GUN
    def _aday_say(ad: str) -> int:
        yol = VAULT / "HAFIZA" / ad
        if not yol.exists():
            return 0
        return sum(1 for s in yol.read_text(encoding="utf-8").splitlines() if s.lstrip().startswith("- ["))

    aday = _aday_say("Kural Adayları.md")
    celiski = _aday_say("Çelişki Adayları.md")

    return {
        "ts": int(simdi),
        "sorunlar": sorunlar,
        "bilgi": bilgi,
        "haftalik": haftalik,
        "haftalik_son": son,
        "kural_adayi": aday,
        "celiski_adayi": celiski,
        "kirik_link": n_kirik,
        "olu_yol": n_olu,
        "yapi_temiz": not yapi_satir,
    }


def tablo(r: dict) -> str:
    satirlar = ["| Kontrol | Durum |", "| --- | --- |"]
    if r["sorunlar"]:
        for s in r["sorunlar"]:
            satirlar.append(f"| 🔴 | {s} |")
    else:
        satirlar.append("| 🟢 | Son Oturum, derleme, push, tekrar ve linkler temiz |")
    for b in r.get("bilgi", []):
        satirlar.append(f"| 🟡 | {b} |")
    if r.get("yapi_temiz"):
        satirlar.append("| 🟢 | Yapı temiz: öksüz sayfa, eksik proje çekirdeği, tek yönlü link yok |")
    satirlar.append(f"| {'🟡' if r['haftalik'] else '🟢'} | Haftalık bakım: {'zamanı geldi' if r['haftalik'] else 'yapıldı (' + str(r['haftalik_son']) + ')'} |")
    if r["kural_adayi"]:
        satirlar.append(f"| 🟡 | {r['kural_adayi']} kural adayı onay bekliyor |")
    if r.get("celiski_adayi"):
        satirlar.append(f"| 🟡 | {r['celiski_adayi']} çelişki adayı onay bekliyor |")
    return "\n".join(satirlar)


def main() -> int:
    if "--linkler" in sys.argv:
        print(linkler_raporu())
        return 0
    if "--yapi" in sys.argv:
        cikti = yapi_raporu().rstrip("\n") + "\n\n" + "\n".join(bayat_raporu(bayatlama_taramasi()))
        print(cikti)
        return 0
    if "--bakim-yapildi" in sys.argv:
        STATE.mkdir(parents=True, exist_ok=True)
        (STATE / "haftalik.json").write_text(json.dumps({"son": dt.date.today().isoformat()}) + "\n", encoding="utf-8")
        print("haftalık bakım tarihi kaydedildi:", dt.date.today().isoformat())
        return 0
    r = kontrol()
    if "--yaz" in sys.argv:
        STATE.mkdir(parents=True, exist_ok=True)
        tmp = STATE / f".saglik.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(r, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, STATE / "saglik.json")
        return 0
    print(tablo(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
