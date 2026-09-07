# İkinci Beyin — dağıtım şablonu

Bu depo, ikinci beyin sisteminin kişisel bilgiden arındırılmış dağıtım şablonudur.
Burada yalnız dağıtılan dosyalar durur: `sablon/` iskeleti, `kur.sh`, `OKUBENİ.md`, `README.md`.

**Kural: buraya kişisel iz girmez.** İsim, disk yolu, marka veya proje adı içeren hiçbir
şey kopyalanmaz. `sablon/.claude/scripts/sablon-guncelle.py` bunu tarar ve iz bulduğu
dosyayı kopyalamaz.

Motor dosyaları (kancalar, script'ler, ajanlar, genel skill'ler) elle düzenlenmez; canlı
bir vault'tan `python3 .claude/scripts/sablon-guncelle.py` ile kopyalanır. Elle yazılan
tek şeyler: `sablon/CLAUDE.md` anayasası, tohum dosyaları, `kur.sh`, `OKUBENİ.md` ve
`README.md`.
