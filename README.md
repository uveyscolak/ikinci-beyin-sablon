# İkinci Beyin

Obsidian ve Claude Code ile çalışan, oturumlar arası hatırlayan bir çalışma sistemi.
Her sohbetin başında dünü bilir, sonunda konuşulanı özetler, akşam özetleri kalıcı
bilgiye çevirir. Kimsenin bir şeyi hatırlaması gerekmez.

Bu depo, sistemin kişisel bilgiden arındırılmış şablonudur: vault iskeleti, motor ve
tek komutla kurulum. Bir kullanıcıda beş gün fiilen çalıştıktan sonra denetlenip
düzeltilmiş sürümdür.

## Sorun

Yapay zekayla her sohbet sıfırdan başlar. Dün ne konuştuğunuzu, hangi kararı neden
verdiğinizi, size nasıl davranmasını istediğinizi her seferinde yeniden anlatırsınız.
Projeler birbirinden habersizdir. Notlar üç uygulamaya dağılmıştır.

## Çözüm

Tek bir Obsidian klasörü ortak hafızadır. Claude Code o klasörden çalışır. Kanca denen
küçük script'ler her oturumun başında hafızayı konuşmanın içine koyar, sonunda konuşmayı
özetleyip günlüğe yazar ve klasörü git'e kaydeder. Akşam bir derleyici günlükleri kavram
makalelerine çevirir. Ertesi sabah hepsi kendiliğinden önünüzdedir.

Bulut hizmeti değil, her şey kendi diskinizde. Ayrı bir API anahtarı gerekmez; arka plan
çağrıları mevcut Claude aboneliğinizden gider. Sihir değil: beş bash kancası, birkaç
Python script'i ve markdown dosyaları.

## Bir gün nasıl geçer

Sabah klasörde Claude'u açar, "nerede kalmıştık" dersiniz. Dünkü oturumun sonucu, açık
konular ve size özel kurallar zaten oradadır. Gün içinde bir projenin adını anarsınız, o
projenin kuralları ve güncel durumu gelir. "Bunu böyle yapma" dersiniz, kural olur.
Pencereyi kapatırsınız; özet, günlük ve kayıt kendiliğinden olur.

## Kurulum

```bash
git clone https://github.com/uveyscolak/ikinci-beyin-sablon.git ~/ikinci-beyin-sablon
cd ~/ikinci-beyin-sablon
./kur.sh ~/Belgeler/Beyin --ad "Adınız" --projeler ~/Projeler
```

Script klasörü açar, iskeleti kopyalar, kancaları global Claude ayarınıza ekler (eskisini
yedekleyerek), git deposunu başlatır ve kancayı bir kez çalıştırıp çalıştığını gösterir.
Var olan hiçbir dosyanın üzerine yazmaz.

Sonrası: Obsidian'da klasörü vault olarak açın, `CLAUDE.md` içindeki kimlik bölümünü
kendiniz doldurun, bir oturum konuşup kapatın ve `GÜNLÜK/` klasöründe özetin oluştuğunu
görün.

Ayrıntılı anlatım, mekanizmanın işleyişi ve sorun giderme için [OKUBENİ.md](OKUBENİ.md).

## Gerekenler

macOS veya Linux, Claude Code aboneliği, Obsidian, python3 ve git. Üçüncü parti Python
paketi gerekmez. Vault için iç disk önerilir; iCloud gibi senkronlu klasörlerden kaçının.

## Neler var

| Katman | Ne yapar |
| --- | --- |
| Hafıza | Son oturum, açık konular, kurallar ve günce her açılışta bağlama girer |
| Günlük | Her oturumun özeti tarihli dosyaya yazılır, elle dokunulmaz |
| Bilgi | Akşam derleyicisi günlükleri kavram makalelerine çevirir, çelişkileri işaretler |
| Projeler | Kod kendi deposunda, projenin aklı vault'ta: hedef, kararlar, güncel durum |
| Alanlar | Kodsuz işler için aynı düzen; anahtar kelime geçince kendiliğinden gelir |
| Eğitimler | Satın alınan içerik salt okunur durur, sorulduğunda kaynak linkli cevaplanır |
| Sağlık | Kırık link, öksüz sayfa ve eskimiş makale her açılışta taranır |
| Gizlilik | Anahtarlar tek klasörde ve git dışında; değerleri sohbete yazılmaz |

Sohbette kullanılan yardımcılar: geçmişi arama, eğitimden soru sorma, dış kaynak
ekleme (link, PDF, video), proje kurma, haftalık bakım ve sistemin kendi sağlık raporu.

## Lisans

MIT. Kullanın, değiştirin, dağıtın.

## Kaynak

Motor, Avenox'un beyin.md v2 çalışmasından türetildi. Bilgi katmanı fikri Andrej
Karpathy'nin dil modeli wiki yaklaşımına dayanır.
