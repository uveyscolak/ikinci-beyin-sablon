#!/usr/bin/env python3
"""Sınırların tek doğru kaynağı: .claude/beyin.json içindeki "sinirlar" bölümü.

Aynı sayı iki ayrı script'te elle tutulunca biri değişince diğeri sessizce yanlış
kalıyordu. Bütün script'ler ve kancalar sayıyı buradan okur, kendi içinde tutmaz.
Dosya okunamazsa aşağıdaki varsayılanlar kullanılır ve iş durmaz.
"""
from __future__ import annotations

import json
from pathlib import Path

VARSAYILAN = {
    "kurallar_madde": 30,
    "kurallar_karakter": 8000,
    "acik_konular_madde": 20,
    "acik_konular_karakter": 6000,
    "son_oturum_karakter": 5000,
    "su_an_karakter": 3000,
    "kurallar_blok_karakter": 3000,
    "kaynaklar_blok_karakter": 1500,
    "kanca_acilis_karakter": 6000,
    "kanca_istem_karakter": 8500,
    "kararlar_bolme_karakter": 60000,
    "ipucu_en_fazla": 3,
    "bekleyenler_en_fazla": 3,
    "baglanmamis_en_fazla": 3,
}


def ayar_oku(vault: Path) -> dict:
    """beyin.json'un tamamını döner; okunamazsa boş sözlük."""
    try:
        veri = json.loads((vault / ".claude" / "beyin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}


def sinirlar(vault: Path) -> dict:
    """Sınır sözlüğü: beyin.json'daki değerler, eksik olanlar varsayılandan tamamlanır."""
    sonuc = dict(VARSAYILAN)
    bolum = ayar_oku(vault).get("sinirlar")
    if isinstance(bolum, dict):
        for anahtar, deger in bolum.items():
            if anahtar in sonuc and isinstance(deger, int) and deger > 0:
                sonuc[anahtar] = deger
    return sonuc
