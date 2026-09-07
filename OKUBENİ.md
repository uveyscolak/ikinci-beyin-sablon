# İkinci Beyin

Obsidian ve Claude Code ile çalışan, kendi kendine hatırlayan bir ikinci beyin. Her oturumun
başında dünü bilir, sonunda konuştuklarınızı özetler, akşam özetleri kalıcı bilgiye çevirir,
haftada bir temizlik zamanı geldiğini söyler. Kimsenin bir şeyi hatırlaması gerekmez.

Bu depo o sistemin kişisel bilgiden arındırılmış şablonudur: vault iskeleti, motor ve tek
komutla kurulum. Motor Avenox'un beyin.md v2 çalışmasından türetildi, fikir Andrej Karpathy'nin
LLM wiki yaklaşımına dayanır. Bu sürüm bir kullanıcıda beş gün fiilen çalıştıktan sonra denetlenip
düzeltilmiş halidir (v2.1).

---

## 1. Ne yapar

**Sorun.** Yapay zekayla her sohbet sıfırdan başlar. Projeler birbirinden habersizdir. Alınan
eğitimler izlenir, unutulur. Notlar üç uygulamaya dağılmıştır.

**Çözüm.** Tek bir Obsidian klasörü (vault) ortak hafızadır. Claude Code o klasörden çalışır.
Kanca denen küçük script'ler her oturumun başında hafızayı konuşmanın içine koyar; sonunda
konuşmayı özetleyip günlüğe yazar ve klasörü git'e kaydeder. Akşam bir derleyici günlükleri bilgi
makalelerine çevirir. Ertesi sabah hepsi kendiliğinden önündedir.

**Bir gün nasıl geçer.** Sabah vault'ta Claude'u açarsın, "nerede kalmıştık" dersin; dünkü
oturumun sonucu, açık konular ve sana özel kurallar zaten bağlamdadır. Gün içinde bir projenin
adını anarsın, o projenin kuralları ve durumu gelir. Bir eğitimden soru sorarsın, ders sayfası ve
transkripti okunup kaynak linkli cevap gelir. "Bunu böyle yapma" dersin, kural olur. Pencereyi
kapatırsın; özet, günlük, commit kendiliğinden olur.

**Ne değildir.** Bulut hizmeti değil, her şey kendi diskinde. API anahtarı gerekmez; arka plan
çağrıları mevcut Claude aboneliğinden gider (oturum özeti ve akşam derlemesi için birer Sonnet
çağrısı; en düşük seviye Sonnet, Haiku hiçbir yerde kullanılmaz). Sihir değil: beş bash kancası,
birkaç Python script'i, markdown dosyaları.
Sohbet arayüzü de değil; terminalde veya VS Code içinde Claude Code gerekir, tarayıcı tabanlı
sohbet araçları kanca mekanizmasını çalıştırmaz.

**Gerekenler.** macOS (Linux muhtemelen çalışır, doğrulanmadı), Claude Code aboneliği, Obsidian,
python3, git. Kurulum bir öğleden sonra; eski veri taşıma ayrıca bir gün.

---

## 2. Kurulum

Vault için iç disk önerilir; iCloud gibi senkronlu klasörlerden kaçının, Türkçe klasör adları ve
senkron çakışma dosyaları sorun çıkarabilir. Harici disk de çalışır.

```bash
git clone <bu depo> ~/ikinci-beyin-sablon
cd ~/ikinci-beyin-sablon
./kur.sh ~/Belgeler/Beyin --ad "Ayşe" --projeler ~/Projeler
```

Script şunları yapar: vault klasörünü açar ve iskeleti kopyalar (var olan dosyanın üzerine
yazmaz), kancaları çalıştırılabilir yapar, adını ve proje klasörünü `.claude/beyin.json` içine
yazar, yer tutucuları doldurur, global kanca ayarını (`~/.claude/settings.json`) yedekleyip
birleştirir, git deposunu açıp ilk commit'i atar, kancayı bir kez çalıştırıp bağlam ürettiğini
gösterir. `~/.claude/CLAUDE.md` yoksa `sablon/.claude/CLAUDE.global.ornek.md` dosyasından vault
yolu doldurulmuş halde oluşturur; dosya zaten varsa dokunmaz. Bu global dosya iki bölümden
oluşur: hafıza her zaman vault'a yazılır kuralı ve gizlilik (anahtarları sohbete yazma).

Sonra:

1. Obsidian'ı aç, "Open folder as vault" ile klasörü seç. Ayarlar: wikilink açık, "Automatically
   update internal links" açık, silinen dosyalar Obsidian çöpüne.
2. `CLAUDE.md` dosyasını aç ve 1. bölümdeki iki üç cümleyi kendin yaz: kimsin, ne yapıyorsun,
   nasıl konuşulmasını istiyorsun. `KİŞİSEL/Kimlik.md` dosyasını doldur.
3. Terminalde vault klasörüne gir, `claude` yaz, beş altı mesajlık gerçek bir şey konuş, kapat.
   Otuz saniye sonra `GÜNLÜK/` klasöründe bugünün dosyasına bak: beş başlıklı özet orada olmalı.
   Yoksa Claude'a "beyin doktor" yaz; tek tabloda nerede takıldığını söyler.
4. Yedek: `gh repo create <ad> --private --source=. --remote=origin --push`. Klasördeki videolar,
   görseller ve `GİZLİ/` git'e girmez; depo küçük kalır. Push her oturum sonunda kendiliğinden gider.
   Oluşturduktan sonra `gh repo view --json visibility -q .visibility` ile gerçekten özel olduğunu
   doğrula, varsayma.

---

## 3. Nasıl çalışır

**Üç sahip.** Sen kendi notlarını yazarsın (`İŞ/`, `KİŞİSEL/`, `EĞİTİMLER/KENDİ NOTLARIM/`,
`GİZLİ/`). Claude ilişki katmanını yazar (`HAFIZA/`, `PROJELER/` altındaki proje beyinleri).
Makine günlüğü ve bilgi tabanını yazar (`GÜNLÜK/`, `BİLGİ/`); oraya elle dokunulmaz.

```
Vault/
├── CLAUDE.md              anayasa: kimlik, üslup, kurallar, harita (tek kural kaynağı)
├── index.md               kendi notlarının kataloğu
├── HAFIZA/                Son Oturum, Açık Konular, Kurallar, Kural Adayları, Günce
├── GÜNLÜK/                makine yazar: her günün oturum özetleri
├── BİLGİ/                 makine derler: index.md, log.md, kavramlar/
├── GİZLİ/                 anahtarlar, git dışı
├── PROJELER/              her proje bir klasör: sayfa, yönerge (varsa), PRD, Kararlar, Context
├── İŞ/  KİŞİSEL/          kendi notların
├── EĞİTİMLER/KAYNAKLAR/   satın alınan eğitimler, salt okunur
├── EĞİTİMLER/KENDİ NOTLARIM/
└── .claude/               hooks/ scripts/ skills/ settings.json beyin.json
```

**`index.md`** kök notların kataloğudur; `index-uret.py` her oturum sonunda diskten yeniden
üretir. Giriş metni `.claude/index-giris.md` dosyasından gelir; kurulumla birlikte genel bir
örnek gelir, kullanıcı isterse kendi diline göre değiştirir.

**Kancalar** (global; hangi klasörde Claude açarsan aç hafıza vault'a yazılır):

| Olay | Ne yapar |
| --- | --- |
| Oturum açılışı | Hızlı sağlık kontrolü; Son Oturum'un "Nerede kalındı" bölümü, açık konular, kuralların tamamı, kural adayları, `HAFIZA/Çelişki Adayları.md` (varsa), güncenin son girişi, bilgi indeksinin son sekiz satırı (yeniden eskiye) ve bugünün günlük kuyruğu bağlama girer. Kaçan oturumlar ve gecikmiş derleme arka planda tamamlanır. |
| Her mesaj | Proje adı geçince o projenin `PROJELER/<Proje>/` klasöründeki yönerge ve Context gelir (oturumda bir kez); aynı blokta `BİLGİ/` içindeki ilgili kavram makaleleri de listelenir (en fazla beş, en yenisi önce). 15 mesajda bir hatırlatma. |
| Sıkıştırma öncesi | Bağlam dolmadan özet alınır. |
| Oturum kapanışı | Vault commit'lenir, konuşma Sonnet ile beş başlıkla özetlenir (`GÜNLÜK/`), `HAFIZA/Son Oturum.md` yenilenir, push gider. 18'den sonraysa derleyici çalışır. |

**Sağlık kontrolü** (`saglik.py`) argümansız çalışınca özet tablo basar. `--linkler` kırık
wiki-link ve ölü düz metin yollarını dosya başına listeler; `--yapi` öksüz sayfa, eksik proje
çekirdeği, tek yönlü link ve bayat makaleyi tarar. `BİLGİ/kavramlar/` makaleleri de taranır.

Bir makale link verdiği vault notundan bir gün eskiyse "bayat makale" sayılır ve oturum açılışında
tek satır uyarı düşer. `--yaz` sonucu kancanın okuduğu durum dosyasına yazar; `--bakim-yapildi`
haftalık bakımın tarihini kaydeder.

**Derleyici** akşam 18'den sonraki ilk kapanışta çalışır: bilgi klasörünün kopyasını vault
dışında bir kum havuzuna alır, Sonnet'e günün logunu verir, çıkan makaleleri beyaz listeden
geçirip atomik kopyalar. Model canlı vault'a hiç yazmaz. Kullanıcının verdiği düzeltmeleri
`HAFIZA/Kural Adayları.md` dosyasına aday olarak yazar; sabah Claude sorar, onaylanan kural olur.

**Bağlam bütçesi.** Oturum başına 10 ile 15 bin token. Sınırlı ve tavanlı bir paket girer; gerisi
gerektiğinde okunur. Kırpma her zaman eskiyi düşürür, yeniyi değil.

**Projeler** kod olarak vault dışında, kendi git'lerinde yaşar; akıl vault'ta `PROJELER/<Proje>/`
klasöründedir: `<Proje> PRD.md` (hedef), `<Proje> Kararlar.md` (neden, yalnız eklenir),
`<Proje> Context.md` (şu an), `<Proje> — Proje.md` (vitrin). Proje köküne yalnız vault'u gösteren
işaretçi `CLAUDE.md` konur. Claude asla proje klasöründen açılmaz; vault'tan çalışır, adı geçince
yönerge ve durum gelir. Yeni proje sohbette "şu adla proje kur" demekle `proje-kur` skill'inden
açılır; elle şablon kopyalanmaz. Detay: anayasa §8 ve `proje-kur` skill'i.

**Proje ve alan.** Proje kodlu iş, alan kodsuz iş. Reklam, kişisel marka, video edit gibi kod
gerektirmeyen bir konu proje değil **alan**dır: `İŞ/` veya `KİŞİSEL/` altında `<Ad> — Alan.md`
sayfasıyla açılır. Sayfadaki `tetik:` listesi anahtar kelimelerdir; biri sohbette geçince alanın
yönergesi ve durumu kendiliğinden gelir. Açmak için "şu konuda alan aç" demek yeter.

**Eğitimler.** Satın alınan eğitim `EĞİTİMLER/KAYNAKLAR/<EĞİTİM>/RAW/` (video, transkript) ve
`WİKİ/` (her ders bir sayfa) ile durur. `python3 .claude/scripts/egitim-icindekiler.py --kilitle`
her eğitime içindekiler sayfası yazar ve klasörü dosya izniyle kilitler; kendi notun için
eğitimin kökündeki `NOTLARIM.md` açık kalır. `egitim` skill'i üç modda çalışır: sor, öğret, damıt.

**Sırlar** yalnız `GİZLİ/` içinde; klasör git'e girmez. Claude değeri sohbete yazmaz, adıyla anar.

**Orkestra.** Ana oturumdaki model şeftir; okuma, arama, mekanik düzenleme ve kontrol işlerini
`.claude/agents/` altındaki dört alt ajana verir: `arastirmaci` (Sonnet), `amele` (Sonnet),
`mimar` (Opus), `denetci` (Sonnet). Adsız açılan alt ajanların varsayılan modeli de Sonnet;
bu `sablon/.claude/settings.json` içindeki `env.CLAUDE_CODE_SUBAGENT_MODEL` ayarıyla sabitlenir.
Çok parçalı işi kendisi paralel yürütür; "ajan kullan" demen gerekmez. Aboneliğin düşüp en iyi
modelin Opus kalırsa düzen aynı kalır, şef Opus olur. Anayasa 10. bölüm.

---

## 4. Günlük kullanım

- Hep vault'tan aç; proje adını aynen yaz.
- Kapatırken bir şey yapman gerekmez. Bilinçli bitiriyorsan "kapat" de.
- Beni düzelt: "bunu böyle yapma" kural olur. Sabah kural adayı sorulursa evet veya hayır de.
- Geçmiş için "hatırla: ...", eğitim için "eğitim sor / beni ... konusunda eğit / damıt".
- Kaynak eklemek için "kaynak ekle", "şu linki beyne al", "bu PDF'i oku ve kaydet", "bu videoyu
  özetle ve kaydet" de; link, PDF veya video özeti bugünün günlüğüne `### Kaynak` bloğu olarak
  düşer, akşam kavram makalesine dönüşür. Ham metin vault'a girmez.
- Haftada bir kanca "bakım zamanı" der; Claude teklif eder: açık konular budanır, kural adayları
  sorulur, bayat projeler listelenir, hafta özeti günceye yazılır. Hatırlaman gerekmez.
- Bir oturum bir konu; karma üç saatlik oturum özetin kalitesini düşürür.
- Anahtar değerini sohbete yazma.

**Sorun giderme**

| Belirti | Çözüm |
| --- | --- |
| Sabah "son oturum" eski | Sağlık kontrolü zaten söyler; "beyin doktor" tabloyu verir |
| Günlüğe giriş düşmedi | Kısa oturumda normaldir (motor bilerek yazmaz); değilse python3 ve claude yolda mı |
| Derleme günlerdir çalışmadı | `python3 .claude/scripts/compile.py --dry-run`, sonra `compile.py`; hata `.claude/scripts/.state/health.json` içinde |
| Kanca iki kez çalışıyor | Kanca hem global hem vault ayarında; vault'takini sil |
| Proje adı geçti, gelmedi | Adı aynen yaz; oturumda bir kez gelir; `.claude/beyin.json` içindeki proje kökü doğru mu |

---

## 5. Elinde eski veri varsa

Önce kurulumu bitir, sonra taşı. Sıra: sırları ayıkla, notları taşı, projeleri bağla, eski
sohbetleri içe aktar.

- **Eski notlar** (OneNote, Notion, Evernote): markdown'a çevir, `İŞ/`, `KİŞİSEL/`,
  `EĞİTİMLER/KENDİ NOTLARIM/` altına klasörle. Taşımadan önce TC, IBAN, şifre, token ara; bunlar
  `GİZLİ/`'ye. Bu taramayı atlayıp commit atarsan geçmişi sonradan temizlemek gerekir
  (`git filter-repo` veya `.git`'i sıfırlamak); önce tara, sonra commit'le. Sonra Claude'a
  "index.md'yi diskten üret" de. Frontmatter yok.
- **Eski sohbetler** (ChatGPT, Claude, Gemini dışa aktarımı): Claude'a "geçmiş import" de. Onay
  kapılıdır, tarih ve anahtar kelime filtresi ister; `GÜNLÜK/import-...md` dosyaları yazar,
  derleyici birkaç akşamda sindirir.
- **Eski Claude Code projeleri:** proje başına kancaları sök, `CLAUDE.md`'yi vault'u gösteren
  işaretçiye indir (`ASSETS/TEMPLATES/`), vault'ta `PROJELER/<Proje>/` klasörü aç; özel kuralları
  `<Proje> Yönerge.md`'ye (yalnız kural), bilgiyi `<Proje> PRD/Kararlar/Context.md` üçlüsüne,
  anahtarları `GİZLİ/`'ye; git geçmişini tara, sızmışsa yenile; hub satırı aç; repo görünürlüğünü
  doğrula.
- **Satın alınan eğitimler:** `KAYNAKLAR/<EĞİTİM>/RAW` ve `WİKİ` düzeni, transkript (yt-dlp veya
  Whisper), sonra `egitim-icindekiler.py --kilitle`.

---

## 6. Tasarım ilkeleri

1. Hafıza disiplin değil mekanizmadır. Son Oturum'u bile makine yazar.
2. Enjekte et, işaret etme. "Şuraya bak" güvenilmez; kanca içeriği koyar.
3. Bağlam şişmez, seçilir; kırpma eskiyi düşürür.
4. Bir kural tek yerde yaşar.
5. Bilgi kopyalanmaz, işaret edilir.
6. Makinenin alanı ile insanın alanı ayrıdır.
7. Her oturum iz bırakır ve geri alınabilir (commit, push).
8. Sır tek yerde ve git dışında.

---

## 7. Depo düzeni ve bakım

```
ikinci-beyin-sablon/
├── OKUBENİ.md       bu dosya
├── CLAUDE.md        bu deponun vault'u gösteren işaretçisi (proje beyni vault'ta)
├── kur.sh           kurulum
└── sablon/          vault iskeleti (kur.sh bunu kopyalar)
    ├── CLAUDE.md, index.md, gitignore.sablon
    ├── HAFIZA/ GÜNLÜK/ BİLGİ/ GİZLİ/ PROJELER/ İŞ/ KİŞİSEL/ EĞİTİMLER/ ASSETS/
    └── .claude/     hooks/ scripts/ skills/ agents/ settings.json beyin.json
                     settings.global.ornek.json CLAUDE.global.ornek.md index-giris.md
```

Motor dosyaları (`sablon/.claude/hooks`, `scripts`, genel skill'ler) canlı bir vault'tan
`python3 .claude/scripts/sablon-guncelle.py` ile kopyalanır; script kişisel iz taraması yapar.
Anayasa, tohumlar ve `egitim`, `hatirla` skill'leri şablonda kendi genel sürümleriyle durur.

Kaynaklar: Avenox beyin.md v2 (github.com/avenoxai/avenoxbeyin), Karpathy LLM wiki
(gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
