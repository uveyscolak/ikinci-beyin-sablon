#!/usr/bin/env python3
"""Git kaydı öncesi sır taraması.

GİZLİ/Anahtarlar.md içindeki değerleri ve orada dosya yolu olarak gösterilen
sır dosyalarının içeriğini bellekte toplar, sonra `git diff --cached` ile
eklenen satırlarda arar. Bir eşleşme bulursa dosya adını ve satır numarasını
yazar, değeri asla yazmaz ve 1 ile çıkar.

Vault dışından da çalışabilsin diye depo kökü VAULT ortam değişkeniyle
ya da ilk argümanla verilebilir; verilmezse git'in kendi kökü kullanılır.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Bir sır olarak sayılmak için en az bu kadar karakter gerekir.
ASGARI_UZUNLUK = 16

# Değer gibi görünse de sır olmayan, çok sık geçen kelimeler.
YOK_SAYILANLAR = {
    "application/json",
    "content-type",
    "authorization",
    "text/markdown",
    "multipart/form-data",
}

# Anahtar dosyası içinde değer taşıyabilecek satır kalıpları.
KALIPLAR = [
    re.compile(r"`([^`\s]{%d,})`" % ASGARI_UZUNLUK),          # ters tırnak içi
    re.compile(r"[:=]\s*([^\s`|]{%d,})\s*$" % ASGARI_UZUNLUK),  # iki nokta ya da eşittir sonrası
    re.compile(r"^([A-Za-z0-9_\-./+=]{%d,})$" % ASGARI_UZUNLUK),  # tek başına satır
]

# Anahtar dosyasında geçen sır dosyası yolları.
DOSYA_YOLU = re.compile(r"`(~?/[^`\s]+)`")

# Anahtar dosyası olmasa bile yakalanan genel kalıplar.
GENEL_KALIPLAR = [
    ("sk- ile başlayan uzun anahtar", re.compile(r"\bsk-[A-Za-z0-9_\-]{27,}")),
    ("EAA ile başlayan uzun token", re.compile(r"\bEAA[A-Za-z0-9]{57,}")),
    ("özel anahtar bloğu", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
]


def depo_koku(argv):
    if len(argv) > 1:
        return Path(argv[1]).resolve()
    ortam = os.environ.get("VAULT")
    if ortam:
        return Path(ortam).resolve()
    try:
        cikti = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(cikti.stdout.strip())
    except Exception:
        return Path.cwd()


def deger_mi(parca):
    """Bir metin parçası anahtar değeri gibi mi duruyor."""
    if len(parca) < ASGARI_UZUNLUK:
        return False
    if " " in parca or "\t" in parca:
        return False
    if parca.lower() in YOK_SAYILANLAR:
        return False
    # Adres, dosya yolu ve markdown bağlantısı sır değildir.
    # Vault klasör yolları ve <yer tutucu> içeren kalıplar da değer değildir.
    if "<" in parca or ">" in parca:
        return False
    if parca.startswith(("PROJELER/", "HAFIZA/", "İŞ/", "GİZLİ/", "EĞİTİMLER/", "KİŞİSEL/", "GÜNLÜK/", ".claude/", "ASSETS/")):
        return False
    if parca.startswith(("http://", "https://", "[[", "![", "/", "~/", "./")):
        return False
    # İçinde en az bir rakam ya da büyük harf olsun; düz Türkçe cümle elenir.
    if not re.search(r"[0-9]", parca) and not re.search(r"[A-Z]", parca):
        return False
    # Yalnız harf ve nokta içeren şeyler (alan adı, dosya adı) elenir.
    if re.fullmatch(r"[A-Za-z.\-_]+", parca):
        return False
    return True


def sirlari_topla(kok):
    """Anahtar dosyasından ve işaret ettiği dosyalardan değerleri toplar."""
    sirlar = set()
    anahtar_dosya = kok / "GİZLİ" / "Anahtarlar.md"
    if not anahtar_dosya.exists():
        return sirlar

    metin = anahtar_dosya.read_text(encoding="utf-8", errors="replace")

    for satir in metin.splitlines():
        for kalip in KALIPLAR:
            for eslesme in kalip.finditer(satir):
                parca = eslesme.group(1).strip().strip("`*_")
                if deger_mi(parca):
                    sirlar.add(parca)

    # Anahtar dosyasında yol olarak gösterilen sır dosyalarını da oku.
    for eslesme in DOSYA_YOLU.finditer(metin):
        yol = Path(os.path.expanduser(eslesme.group(1)))
        try:
            if yol.is_file() and yol.stat().st_size < 65536:
                for satir in yol.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines():
                    parca = satir.strip()
                    if deger_mi(parca):
                        sirlar.add(parca)
        except OSError:
            continue

    return sirlar


def eklenen_satirlar():
    """git diff --cached çıktısından eklenen satırları dosya ve satır numarasıyla verir."""
    try:
        cikti = subprocess.run(
            ["git", "diff", "--cached", "-U0", "--no-color"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return []

    sonuc = []
    dosya = "?"
    satir_no = 0
    for satir in cikti.splitlines():
        if satir.startswith("+++ b/"):
            dosya = satir[6:]
            continue
        if satir.startswith("@@"):
            eslesme = re.search(r"\+(\d+)", satir)
            satir_no = int(eslesme.group(1)) if eslesme else 0
            continue
        if satir.startswith("+") and not satir.startswith("+++"):
            sonuc.append((dosya, satir_no, satir[1:]))
            satir_no += 1
    return sonuc


def main():
    kok = depo_koku(sys.argv)
    sirlar = sirlari_topla(kok)
    bulgular = []

    for dosya, satir_no, icerik in eklenen_satirlar():
        for sir in sirlar:
            if sir in icerik:
                bulgular.append((dosya, satir_no))
                break
        else:
            for _ad, kalip in GENEL_KALIPLAR:
                if kalip.search(icerik):
                    bulgular.append((dosya, satir_no))
                    break

    if bulgular:
        for dosya, satir_no in bulgular[:20]:
            print(
                "Sır tespit edildi: %s:%d; değer gösterilmiyor. Kayıt durduruldu."
                % (dosya, satir_no)
            )
        if len(bulgular) > 20:
            print("... ve %d satır daha." % (len(bulgular) - 20))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
