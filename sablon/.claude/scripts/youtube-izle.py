#!/usr/bin/env python3
"""YouTube 'Vault' oynatma listesini izler; yeni videonun transkriptini alır, notunu yazdırır.

Neden böyle: YouTube bir listeye video eklenince kimseye haber vermez. Gerçek tetikleme
mümkün değil; tek yol listeye belli aralıkla bakıp değişti mi diye karşılaştırmak. Bu
script oturum açılışında arka planda çalışır (session-start.sh), sonucu sonraki açılışta
kanca gösterir.

Akış (her yeni video için):
  1. Liste okunur (yt-dlp --flat-playlist). Kütükte olmayanlar yenidir.
  2. Video bilgisi çekilir (kanal, süre, yayın tarihi).
  3. Transkript: önce YouTube altyazısı (insan yazımı, sonra otomatik), yoksa ses
     indirilip mlx-whisper ile yerelde çıkarılır. Ham metin EĞİTİMLER/YOUTUBE/RAW/ altına.
  4. Not: Sonnet'e (claude -p, araçsız, vault dışı geçici klasörde) transkript verilir,
     Isaac kalıbında Türkçe not yazdırılır. Not EĞİTİMLER/YOUTUBE/<Kanal> — <Başlık>.md.
  5. Özet bugünün günlüğüne `### Kaynak` bloğu olarak eklenir; akşam derleyicisi makaleye çevirir.
  6. `00 İçindekiler.md` tablosuna satır eklenir.
  7. KUYRUK.md'ye "kontrol bekliyor" maddesi yazılır; şef notu okur, düzeltir, maddeyi siler.

Kullanım:
  youtube-izle.py <vault>            -> yeni videoları işler
  youtube-izle.py <vault> --kontrol  -> yalnız sayar, indirmez
Ayar: beyin.json -> "youtube": {"liste": "<oynatma listesi adresi>", "baglam": "<kullanıcı kim, ne iş, ne öncelik; not yazarına verilir>"}
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

KLASOR = "EĞİTİMLER/YOUTUBE"
KUTUK = ".claude/scripts/.state/youtube-islenmis.json"
DURUM = ".claude/scripts/.state/youtube-durum.json"
TUR_BASI_TAVAN = 3           # tek açılışta en fazla bu kadar video; liste kabarırsa saatler sürmesin
TRANSKRIPT_TAVAN = 150_000   # Sonnet'e verilen ham metin üst sınırı (karakter)
NOT_MODEL = "sonnet"         # Haiku hiçbir yerde kullanılmaz (anayasa §10)
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"


# ----------------------------------------------------------------- yardımcılar

def calistir(cmd: list[str], zaman_asimi: int = 600) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=zaman_asimi)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "zaman aşımı"
    except FileNotFoundError:
        return 127, f"komut yok: {cmd[0]}"


def json_oku(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def json_yaz(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def temiz_ad(s: str, tavan: int = 80) -> str:
    """Dosya adına uygun hale getirir; Türkçe harf korunur, yol ve wikilink karakteri atılır.

    Kesmek gerekirse kelime sınırından keser, açık kalan parantezi atar ("(influencer olma eği" olmasın).
    """
    s = re.sub(r"[/\\:*?\"<>|\[\]#^]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > tavan:
        kes = s[:tavan]
        s = kes[: kes.rfind(" ")] if " " in kes else kes
    if s.count("(") > s.count(")"):
        s = s[: s.rfind("(")]
    return s.strip(" .-—") or "video"


def bugun() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ----------------------------------------------------------------- liste ve video

def liste_oku(url: str) -> list[dict]:
    """Listedeki videoları indirmeden okur; yalnız kimlik ve başlık gelir."""
    kod, cikti = calistir(["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings", url], 180)
    if kod != 0:
        return []
    videolar = []
    for satir in cikti.splitlines():
        satir = satir.strip()
        if not satir.startswith("{"):
            continue
        try:
            v = json.loads(satir)
        except ValueError:
            continue
        vid = v.get("id")
        if vid:
            videolar.append({"id": vid, "baslik": v.get("title") or vid,
                             "url": f"https://www.youtube.com/watch?v={vid}"})
    return videolar


def video_bilgi(video: dict) -> dict:
    """Kanal, süre, yayın tarihi; tek yt-dlp çağrısı, indirme yok."""
    kod, cikti = calistir(["yt-dlp", "--dump-json", "--skip-download", "--no-warnings", video["url"]], 120)
    bilgi = dict(video)
    bilgi.setdefault("kanal", "")
    bilgi.setdefault("sure", 0)
    bilgi.setdefault("yayin", "")
    if kod != 0:
        return bilgi
    for satir in cikti.splitlines():
        if satir.startswith("{"):
            try:
                v = json.loads(satir)
            except ValueError:
                continue
            bilgi["baslik"] = v.get("title") or bilgi["baslik"]
            bilgi["kanal"] = v.get("channel") or v.get("uploader") or ""
            bilgi["sure"] = v.get("duration") or 0
            yd = v.get("upload_date") or ""
            if len(yd) == 8:
                bilgi["yayin"] = f"{yd[:4]}-{yd[4:6]}-{yd[6:]}"
            bilgi["aciklama"] = (v.get("description") or "")[:1500]
            break
    return bilgi


# ----------------------------------------------------------------- transkript

def vtt_duzlestir(metin: str) -> str:
    """WebVTT altyazıyı düz metne çevirir; zaman damgası ve kayan tekrar satırları atılır."""
    satirlar = []
    for ham in metin.splitlines():
        s = ham.strip()
        if not s or s == "WEBVTT" or "-->" in s or s.startswith(("Kind:", "Language:", "NOTE")):
            continue
        s = re.sub(r"<[^>]+>", "", s)
        if satirlar and satirlar[-1] == s:
            continue
        satirlar.append(s)
    suzgec: list[str] = []
    for s in satirlar:
        if suzgec and s in suzgec[-1]:
            continue
        if suzgec and suzgec[-1] in s:
            suzgec[-1] = s
            continue
        suzgec.append(s)
    return "\n".join(suzgec).strip()


def altyazi_dene(url: str, hedef: Path) -> str:
    hedef.mkdir(parents=True, exist_ok=True)
    kalip = str(hedef / "alt")
    for bayrak in (["--write-subs"], ["--write-auto-subs"]):
        for diller in ("tr", "en", "tr,en"):
            calistir(["yt-dlp", "--skip-download", *bayrak, "--sub-langs", diller,
                      "--sub-format", "vtt", "--no-warnings", "-o", kalip, url], 180)
            for f in sorted(hedef.glob("alt*.vtt")):
                metin = vtt_duzlestir(f.read_text(encoding="utf-8", errors="ignore"))
                f.unlink(missing_ok=True)
                if len(metin) > 200:
                    return metin
    return ""


def whisper_dene(url: str, hedef: Path) -> str:
    """Altyazı yoksa sesi indirip yerelde mlx-whisper ile yazıya döker.

    Python API'si kullanılır (`mlx_whisper.transcribe`); konsol komutu her kurulumda yok.
    Ayrı süreçte çalışır ki model yüklemesi çökse bile ana akış devam etsin.
    """
    hedef.mkdir(parents=True, exist_ok=True)
    kod, _ = calistir(["yt-dlp", "-f", "bestaudio", "-x", "--audio-format", "m4a",
                       "--no-warnings", "-o", str(hedef / "ses.%(ext)s"), url], 900)
    ses = next(iter(sorted(hedef.glob("ses*.m4a"))), None)
    if kod != 0 or not ses:
        return ""
    cikti = hedef / "ses.txt"
    kod_py = ("import sys, mlx_whisper\n"
              "r = mlx_whisper.transcribe(sys.argv[1], path_or_hf_repo=sys.argv[2])\n"
              "open(sys.argv[3], 'w', encoding='utf-8').write(r.get('text', ''))\n")
    calistir([sys.executable, "-c", kod_py, str(ses), WHISPER_MODEL, str(cikti)], 3600)
    ses.unlink(missing_ok=True)
    try:
        metin = cikti.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return ""
    cikti.unlink(missing_ok=True)
    # Whisper tek satır döker; cümle sonlarından böl ki ham metin okunabilsin.
    metin = re.sub(r"(?<=[.!?])\s+", "\n", metin)
    return metin if len(metin) > 200 else ""


def transkript_yaz(vault: Path, video: dict, metin: str, kaynak: str, kok_ad: str) -> Path:
    raw = vault / KLASOR / "RAW"
    raw.mkdir(parents=True, exist_ok=True)
    yol = raw / f"{kok_ad} — Transkript.md"
    basli = (f"# {video['baslik']} — Transkript\n\n"
             f"> Kaynak: [YouTube]({video['url']}) · {video.get('kanal') or 'bilinmiyor'} · "
             f"Transkript: {kaynak} · Çekildi {bugun()}\n\n"
             "Ham metindir, düzenlenmemiştir.\n\n---\n\n")
    yol.write_text(basli + metin + "\n", encoding="utf-8")
    return yol


# ----------------------------------------------------------------- not (Sonnet)

def alanlar(vault: Path) -> list[tuple[str, str]]:
    """Alan sayfaları: (vault'a göre yol, tetik kelimeleri). Sonnet bunlardan birini seçer."""
    ayar = json_oku(vault / ".claude" / "beyin.json")
    sonuc = []
    for kok in ayar.get("alan_kokleri") or ["İŞ", "KİŞİSEL"]:
        for p in sorted((vault / kok).rglob("*Alan.md")):
            try:
                bas = p.read_text(encoding="utf-8")[:1500]
            except OSError:
                continue
            m = re.search(r"^tetik:\s*(.+)$", bas, re.M)
            if m:
                sonuc.append((p.relative_to(vault).as_posix()[:-3], m.group(1).strip()))
    return sonuc


def alan_adi(vault: Path, alan_yol: str) -> str:
    """Alan sayfasının H1'i (' — Alan' eki atılır); yoksa klasör adı. Büyük-küçük çevirme Türkçe İ'yi bozar."""
    try:
        for satir in (vault / f"{alan_yol}.md").read_text(encoding="utf-8").splitlines()[:20]:
            if satir.startswith("# "):
                ad = re.sub(r"\s*[—–-]\s*Alan\s*$", "", satir[2:].strip()).strip()
                if ad:
                    return ad
    except OSError:
        pass
    return Path(alan_yol).parent.name


def not_prompt(video: dict, transkript: str, alan_listesi: list[tuple[str, str]], ayar: dict) -> str:
    """Kişisel bağlam (kim, ne iş, ne öncelik) beyin.json -> youtube.baglam'dan gelir; kod kişisiz kalır."""
    kullanici = ayar.get("kullanici") or "kullanıcı"
    baglam = ((ayar.get("youtube") or {}).get("baglam") or "").strip()
    if len(transkript) > TRANSKRIPT_TAVAN:
        transkript = transkript[:TRANSKRIPT_TAVAN] + "\n\n[… transkript burada kesildi …]"
    alan_metni = "\n".join(f"- {yol} — tetik: {tetik}" for yol, tetik in alan_listesi) or "- (alan yok)"
    dk = round((video.get("sure") or 0) / 60)
    return f"""Sen {kullanici} için ikinci beyin notu yazıyorsun: bir YouTube eğitim videosunun notu.

{kullanici} hakkında: {baglam or "bilgi verilmedi; notu genel iş bakışıyla yaz."}

Aşağıda bir YouTube videosunun bilgisi ve ham transkripti var. Görevin: {kullanici} bu videoyu hiç
izlemeden öğretilen her şeyi anlayabilsin, sonra "şunu nasıl yapıyordu" diye sorunca kaynak olarak
kullanılabilsin diye Türkçe bir not yazmak.

## Video
- Başlık: {video['baslik']}
- Kanal: {video.get('kanal') or 'bilinmiyor'}
- Süre: {dk} dk · Yayın: {video.get('yayin') or '?'} · Adres: {video['url']}
- Açıklama (kanalın yazdığı, kısaltılmış): {(video.get('aciklama') or '').strip() or '-'}

## Alanlar
Notun bağlanacağı çalışma alanını şu listeden seç. Tetik kelimeleri o alanın konularıdır. Hiçbiri
uymuyorsa `-` yaz; uydurma.
{alan_metni}

## Kurallar
- Türkçe, konuşur gibi, sade. Araç, efekt ve ayar adı dışında İngilizce kelime kullanma; Türkçesi varsa onu yaz
  (voiceover → seslendirme, footage → görüntü, rough cut → kaba kurgu). Kalan teknik terimin yanına iki
  kelimeyle ne olduğu (parantez içinde), yalnız ilk geçtiği yerde.
- Videoda söylenmeyen hiçbir şey yazma. Rakam, isim, araç adı birebir; yuvarlama yok.
- YAML üst bilgi bloğu (---) yazma. Başlıkları `##` ve `###` ile kur.
- Uzunluk: videonun içeriği kadar; 20 dakikalık dolu bir video için 120-200 satır normaldir.
  Boş laf, tekrar, süs yok.
- Wikilink yalnız Alanlar listesindeki yollarla; başka dosya uydurma.

## Çıktı biçimi — tam olarak bu dört bölüm, bu işaretlerle
===ALAN===
<Alanlar listesinden tek yol, ya da ->
===NOT===
## Ne öğretiyor
<3-6 cümle: videonun ana iddiası, kime hitap ettiği, hangi işi çözdüğü.>

## Çerçeve — adım adım
<İçeriğe uygun yapı. Süreç anlatıyorsa numaralı ### başlıklar; ilkeler anlatıyorsa her ilke bir ###.
Her başlığın altında ne yapıldığı, neden, dikkat edilecek yer. Araç ve ayar adları aynen.>

## Rakamlar ve alıntılar
<Videodaki sayı, eşik, fiyat, kritik cümle; birebir. Yoksa bu bölümü tamamen atla.>

## Bizde nasıl uygulanır
<3-8 madde: {kullanici}'in işine somut çeviri. Tahmin olduğu yerde "tahmin" de.>
===GÜNLÜK===
**Kaynak:** {video['url']} · YouTube video · {video.get('kanal') or 'bilinmiyor'}, {video.get('yayin') or '?'}
**Neden alındı:** {kullanici} YouTube listesine ekledi.

## Özet
<5-10 cümle. Ana iddia ve dayandığı şey.>

## Çıkarımlar
- <Bu iş için ne anlama geliyor>
- <Alınabilecek somut adım varsa>

## Rakamlar ve alıntılar
- <birebir; yoksa bölümü atla>
===ÖZET===
<Tek satır, en fazla 25 kelime: video ne öğretiyor. İçindekiler tablosuna girecek.>
===BAKILIR===
<Tek satır, 8-15 kelime: bu not hangi işi yaparken açılır. Örnek: "kurgu sırası, ses tasarımı ve animasyon kararlarında bakılır".>
===SON===

## Transkript
{transkript}
"""


def sonnet_calistir(prompt: str, vault: Path) -> tuple[str | None, str | None]:
    """Sonnet'i araçsız, vault dışı geçici klasörde çalıştırır; flush.py ile aynı yol."""
    claude = shutil.which("claude")
    if claude is None:
        return None, "claude-cli-yok"
    env = os.environ.copy()
    env["BEYIN_INVOKED_BY"] = "beyin-scripts"
    try:
        with tempfile.TemporaryDirectory(prefix="beyin-youtube-") as gecici:
            gp = Path(gecici).resolve()
            try:
                icerde = os.path.commonpath([gp, vault.resolve()]) == str(vault.resolve())
            except ValueError:
                icerde = False
            if icerde:
                return None, "gecici-klasor-vault-icinde"
            r = subprocess.run(
                [claude, "-p", "--model", NOT_MODEL, "--output-format", "text",
                 "--safe-mode", "--tools", ""],
                input=prompt, text=True, encoding="utf-8", errors="replace",
                capture_output=True, cwd=gp, env=env, timeout=900, check=False,
            )
    except subprocess.TimeoutExpired:
        return None, "sonnet-zaman-asimi"
    except OSError as e:
        return None, f"sonnet-calistirilamadi:{e}"
    if r.returncode != 0:
        kuyruk = re.sub(r"\s+", " ", (r.stderr or "")[-300:]).strip()
        return None, f"sonnet-cikis-{r.returncode}:{kuyruk}"
    return r.stdout.strip(), None


def cikti_parcala(metin: str) -> dict | None:
    """===ALAN=== / ===NOT=== / ===GÜNLÜK=== / ===ÖZET=== bölümlerini ayırır."""
    m = re.search(r"===ALAN===\s*(.*?)\s*===NOT===\s*(.*?)\s*===GÜNLÜK===\s*(.*?)\s*===ÖZET===\s*(.*?)"
                  r"\s*(?:===BAKILIR===\s*(.*?)\s*)?(?:===SON===|$)", metin, re.S)
    if not m:
        return None
    alan, not_, gunluk, ozet, bakilir = (x.strip() if x else "" for x in m.groups())
    if len(not_) < 300 or len(gunluk) < 100:
        return None
    return {"alan": alan.strip("`- ").strip() or "-", "not": not_, "gunluk": gunluk,
            "ozet": " ".join(ozet.split()), "bakilir": " ".join(bakilir.split())}


def not_yaz(vault: Path, video: dict, parca: dict, kok_ad: str, transkript_adi: str,
            alan_listesi: list[tuple[str, str]]) -> Path:
    alan_yol = parca["alan"] if parca["alan"] in {y for y, _ in alan_listesi} else ""
    if alan_yol:
        alan_link = f"[[{alan_yol}|{alan_adi(vault, alan_yol)}]]"
    else:
        alan_link = "—"
    dk = round((video.get("sure") or 0) / 60)
    kanal = video.get("kanal") or "bilinmiyor"
    yayin = video.get("yayin") or "?"
    basli = (f"# {video['baslik']} — {kanal}\n\n"
             f"> Kaynak: [YouTube]({video['url']}) · {kanal} · {dk} dk · {yayin} · "
             f"Alan: {alan_link} · Eklendi {bugun()} · Notu Sonnet yazdı, kontrol bekliyor\n\n")
    govde = parca["not"].rstrip() + "\n\n"
    kuyruk = f"## Transkript\n\n[[{KLASOR}/RAW/{transkript_adi}|Ham transkript]]\n"
    yol = vault / KLASOR / f"{kok_ad}.md"
    yol.write_text(basli + govde + kuyruk, encoding="utf-8")
    return yol


def gunluge_ekle(vault: Path, video: dict, gunluk_govde: str) -> None:
    """Bugünün günlüğüne `### Kaynak` bloğu; biçim `kaynak` skill'iyle aynı, derleyici tanır."""
    gd = vault / "GÜNLÜK"
    gd.mkdir(parents=True, exist_ok=True)
    p = gd / f"{bugun()}.md"
    if not p.exists():
        p.write_text(f"# Günlük Log: {bugun()}\n\n## Oturumlar\n", encoding="utf-8")
    saat = datetime.now().strftime("%H:%M")
    blok = f"\n### Kaynak ({saat}) — {video['baslik']}\n{gunluk_govde.rstrip()}\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(blok)


def icindekilere_ekle(vault: Path, video: dict, kok_ad: str, alan: str, ozet: str) -> None:
    p = vault / KLASOR / "00 İçindekiler.md"
    if not p.exists():
        p.write_text(
            "# YouTube — İçindekiler\n\n"
            "Vault listesinden gelen videolar. Satırları `youtube-izle.py` ekler; not sayfası linkte, "
            "ham transkript notun altındaki `## Transkript` bölümünde.\n\n"
            "| Video | Kanal | Süre | Alan | Özet | Eklendi |\n|---|---|---|---|---|---|\n",
            encoding="utf-8")
    dk = round((video.get("sure") or 0) / 60)
    alan_h = f"[[{alan}\\|{alan_adi(vault, alan)}]]" if alan and alan != "-" else "—"
    ozet_h = ozet.replace("|", "/")
    satir = (f"| [[{KLASOR}/{kok_ad}\\|{video['baslik'].replace('|', '/')}]] | "
             f"{video.get('kanal') or '—'} | {dk} dk | {alan_h} | {ozet_h} | {bugun()} |\n")
    with p.open("a", encoding="utf-8") as f:
        f.write(satir)


def kaynaklara_ekle(vault: Path, alan_yol: str, kok_ad: str, video: dict, ozet: str, bakilir: str) -> bool:
    """Alanın BEYİN/Durum.md dosyasındaki `## Kaynaklar` listesine notu bağlar.

    Kütüphanedeki not aynı kalır; alan kendi defterine "şu not benim" satırı düşer. Kanca alan
    uyanınca bu listeyi ayrı blokta basar (anayasa §9). Aynı not iki kez eklenmez.
    """
    durum = vault / Path(alan_yol).parent / "Durum.md"
    if not durum.exists():
        return False
    metin = durum.read_text(encoding="utf-8")
    not_yolu = f"{KLASOR}/{kok_ad}"
    if not_yolu in metin:
        return False
    kanal = video.get("kanal") or "—"
    kisa = video["baslik"] if len(video["baslik"]) <= 60 else video["baslik"][:57].rsplit(" ", 1)[0] + "…"
    madde = f"- [[{not_yolu}|{kanal} — {kisa}]] — {bakilir or ozet} · eklendi {bugun()}\n"
    if re.search(r"^## Kaynaklar\s*$", metin, re.M):
        # bölümün sonuna (bir sonraki ## başlığından önce) ekle
        bas = re.search(r"^## Kaynaklar\s*$", metin, re.M).end()
        sonraki = re.search(r"^## ", metin[bas:], re.M)
        kes = bas + sonraki.start() if sonraki else len(metin)
        govde = metin[bas:kes].rstrip("\n")
        metin = metin[:bas] + govde + "\n" + madde + "\n" + metin[kes:]
    else:
        blok = "## Kaynaklar\n\n" + madde + "\n"
        alt = re.search(r"^## Alt Sayfalar\s*$", metin, re.M)
        if alt:
            metin = metin[:alt.start()] + blok + metin[alt.start():]
        else:
            metin = metin.rstrip("\n") + "\n\n" + blok
    durum.write_text(metin, encoding="utf-8")
    return True


def kuyruga_ekle(vault: Path, video: dict, kok_ad: str, transkript_adi: str, durum: str) -> None:
    p = vault / KLASOR / "KUYRUK.md"
    if not p.exists():
        p.write_text(
            "# Kuyruk — kontrol bekleyen notlar\n\n"
            "Vault listesinden düşen videoların transkripti çıkarıldı, notunu Sonnet yazdı.\n"
            "Şef her notu bir kez okur, hatayı düzeltir, sonra maddeyi buradan siler.\n\n",
            encoding="utf-8")
    dk = round((video.get("sure") or 0) / 60)
    if durum == "not-hazir":
        madde = (f"- [[{KLASOR}/{kok_ad}|{video['baslik']}]] — {video.get('kanal') or '—'} · {dk} dk · "
                 f"not Sonnet'ten, kontrol bekliyor · düştü {bugun()}\n")
    else:
        madde = (f"- **{video['baslik']}** — {video.get('kanal') or '—'} · {dk} dk · "
                 f"NOT YAZILAMADI ({durum}); transkript hazır: "
                 f"[[{KLASOR}/RAW/{transkript_adi}|RAW]] · notu şef yazacak · düştü {bugun()}\n")
    with p.open("a", encoding="utf-8") as f:
        f.write(madde)


# ----------------------------------------------------------------- akış

def isle(vault: Path, video: dict) -> tuple[bool, str]:
    video = video_bilgi(video)
    kanal = temiz_ad(video.get("kanal") or "", 30)
    baslik = temiz_ad(video["baslik"], 80)
    kok_ad = f"{kanal} — {baslik}" if kanal else baslik
    # Not zaten varsa (kütük kaybolmuş ya da başka makine) yeniden işleme; kütüğe yazılır, geçilir.
    if (vault / KLASOR / f"{kok_ad}.md").exists():
        return True, "not zaten vardı, atlandı"

    gecici = vault / ".claude" / "scripts" / ".state" / "yt-gecici" / video["id"]
    gecici.mkdir(parents=True, exist_ok=True)
    try:
        metin = altyazi_dene(video["url"], gecici)
        kaynak = "YouTube altyazısı"
        if not metin:
            metin = whisper_dene(video["url"], gecici)
            kaynak = "mlx-whisper"
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    if not metin:
        return False, "transkript çıkarılamadı"

    t_yol = transkript_yaz(vault, video, metin, kaynak, kok_ad)
    t_ad = t_yol.name[:-3]

    alan_listesi = alanlar(vault)
    ayar = json_oku(vault / ".claude" / "beyin.json")
    cikti, hata = sonnet_calistir(not_prompt(video, metin, alan_listesi, ayar), vault)
    parca = cikti_parcala(cikti) if cikti else None
    if not parca:
        kuyruga_ekle(vault, video, kok_ad, t_ad, hata or "çıktı biçimi bozuk")
        return True, f"transkript hazır ({kaynak}), not yazılamadı: {hata or 'biçim'}"

    not_yaz(vault, video, parca, kok_ad, t_ad, alan_listesi)
    gunluge_ekle(vault, video, parca["gunluk"])
    icindekilere_ekle(vault, video, kok_ad, parca["alan"], parca["ozet"])
    if parca["alan"] in {y for y, _ in alan_listesi}:
        kaynaklara_ekle(vault, parca["alan"], kok_ad, video, parca["ozet"], parca.get("bakilir", ""))
    kuyruga_ekle(vault, video, kok_ad, t_ad, "not-hazir")
    return True, f"not hazır ({kaynak}, {NOT_MODEL})"


def durum_yaz(vault: Path, hata: str | None, islenen: int, bekleyen: int) -> None:
    json_yaz(vault / DURUM, {"son": datetime.now().strftime("%Y-%m-%d %H:%M"),
                             "hata": hata, "islenen": islenen, "bekleyen": bekleyen})


def main() -> int:
    if len(sys.argv) < 2:
        print("kullanım: youtube-izle.py <vault> [--kontrol]")
        return 2
    vault = Path(sys.argv[1])
    sadece_kontrol = "--kontrol" in sys.argv
    url = (json_oku(vault / ".claude" / "beyin.json").get("youtube") or {}).get("liste")
    if not url:
        print("[youtube] beyin.json içinde youtube.liste yok, atlandı")
        return 0

    kutuk = json_oku(vault / KUTUK)
    videolar = liste_oku(url)
    if not videolar:
        durum_yaz(vault, "liste okunamadı (ağ yok, yt-dlp eski ya da liste kapalı)", 0, 0)
        print("[youtube] liste okunamadı")
        return 1
    yeni = [v for v in videolar if v["id"] not in kutuk]
    if sadece_kontrol:
        print(f"[youtube] {len(yeni)} yeni video")
        return 0
    if not yeni:
        durum_yaz(vault, None, 0, 0)
        print("[youtube] yeni video yok")
        return 0

    hatalar, islenen = [], 0
    for video in yeni[:TUR_BASI_TAVAN]:
        tamam, bilgi = isle(vault, video)
        if tamam:
            kutuk[video["id"]] = {"baslik": video["baslik"], "tarih": bugun(), "sonuc": bilgi}
            islenen += 1
            print(f"[youtube] {video['baslik']}: {bilgi}")
        else:
            # Kütüğe hata ile yazılır ki her açılışta yeniden denenmesin; kanca hatayı bir kez gösterir.
            kutuk[video["id"]] = {"baslik": video["baslik"], "tarih": bugun(), "hata": bilgi}
            hatalar.append(f"{video['baslik']}: {bilgi} (yeniden denenmeyecek; kütükten silinirse denenir)")
            print(f"[youtube] HATA {video['baslik']}: {bilgi}")
    json_yaz(vault / KUTUK, kutuk)
    durum_yaz(vault, "; ".join(hatalar) or None, islenen, max(0, len(yeni) - TUR_BASI_TAVAN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
