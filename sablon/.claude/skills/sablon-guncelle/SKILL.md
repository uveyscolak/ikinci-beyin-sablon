---
name: sablon-guncelle
description: Motor dosyası (kanca, script, skill, ajan tanımı) veya anayasa değiştiğinde değişikliği dağıtım şablonuna taşır. "şablonu güncelle", "şablona işle", "dağıtım şablonu", "sablon-guncelle" dendiğinde ve bir yapısal değişiklik bittiğinde kullan.
---
# Şablon güncelleme

Bu sistemin bir dağıtım kopyası var: başkasının kendi vault'unda kurabileceği şablon deposu.
Motor değiştiğinde şablon da aynı oturumda değişir, yoksa iki kopya sessizce ayrışır.

kullanıcının bunu söylemesi gerekmez. Yapısal bir değişiklik bittiğinde bu skill kendiliğinden çalışır.

## Ne zaman çalışır

Şu dosyalardan biri değiştiyse:

- `.claude/hooks/` altındaki kancalar
- `.claude/scripts/` altındaki script'ler
- `.claude/skills/` altındaki skill tanımları
- `.claude/agents/` altındaki ajan tanımları
- `.claude/beyin.json` yapısı
- Kök `CLAUDE.md`, yani anayasa

Bir projenin kendi kodu, bir notun içeriği veya hafıza dosyaları değiştiyse bu skill çalışmaz.

## Adımlar

1. **Script'i çalıştır.**

   ```
   python3 .claude/scripts/sablon-guncelle.py
   ```

   Script motor dosyalarını şablon deposuna kopyalar. Anayasayı kopyalamaz; o elle işlenir.

2. **Kişisel iz uyarısını oku.** Script bir dosyada kişisel iz bulursa (kullanıcının adı, disk yolu,
   marka adı, anahtar parçası) o dosyayı kopyalamaz ve uyarır. Uyarı görülünce dosyadaki iz
   temizlenir, sonra script tekrar çalıştırılır. Uyarıyı görmezden gelme; kopyalanmayan dosya
   şablonda eksik kalır.

3. **Anayasayı elle işle.** `CLAUDE.md` değiştiyse aynı değişiklik şablonun `sablon/CLAUDE.md`
   dosyasına elle yazılır. Kişiye özel her şey çıkarılır: kullanıcının adı, doğum tarihi, işletme adı,
   disk yolları, proje adları. Yerine genel karşılığı konur.

4. **Şablon deposunu commit'le.** Commit mesajı ne değiştiğini tek cümleyle söyler. Push kullanıcının
   işidir; commit atıldıysa oturum sonunda tek cümleyle hatırlat.

5. **kullanıcıya tek cümleyle söyle:** ne değişti ve şablona işlendi mi.

## Yapma

- Şablona kişisel bilgi taşıma. Şablon deposu dışarı açıktır.
- Script'in uyardığı dosyayı elle kopyalayıp geçme; uyarının sebebi temizlenir.
- Şablon deposunu push etme.
