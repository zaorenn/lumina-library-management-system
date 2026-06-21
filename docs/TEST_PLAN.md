# LibSys Test Planı

Bu belge otomatik testlerin kapsamını ve teslim öncesi uygulanacak kısa arayüz kontrolünü tanımlar.

## Otomatik test kapsamı

`python -m pytest -q` komutu aşağıdaki risk alanlarını gerçek ve geçici bir SQLite veritabanı üzerinde doğrular:

| Alan | Doğrulanan davranış |
|---|---|
| Veritabanı | Foreign key etkinliği, şema sürümü, trigger varlığı ve `integrity_check` |
| Kimlik doğrulama | bcrypt hash, doğru/yanlış parola, onay bekleyen hesap, büyük-küçük harf duyarsız e-posta |
| Validasyon | E-posta, güçlü parola, telefon, ISBN, yayın yılı ve kopya sayısı |
| Kitap CRUD | Ekleme, okuma, güncelleme, arşivleme, benzersiz ISBN ve kapak URL koruması |
| Üye CRUD | Kayıt, onay, giriş ve güvenli arşivleme |
| Ödünç akışı | Stok azaltma/artırma, çift iade koruması, aynı kitabı tekrar alma engeli ve 3 kitap sınırı |
| Veri bütünlüğü | Stok dışı doğrudan SQL eklemesini trigger ile reddetme |
| Gecikme | Geciken gün başına 5 TL ceza hesabı |
| Talepler | Tekrarlanan kitap/profil talebi ve e-posta çakışması |
| Bildirim | Bildirimin yalnız sahibi tarafından okundu işaretlenebilmesi |
| Hazır katalog | 80 benzersiz ISBN/kapak, dolu özet, idempotent yükleme ve metadata onarımı |
| Çevrimiçi arama | Open Library kapak filtresi, Google Books yedeği, önbellek ve ISBN tekilleştirme |
| Yönetici özeti | Eser, kopya, üye, bekleyen işlem ve audit hareketlerinin tutarlılığı |

## Otomatik GUI ve kapak kontrolleri

- `python -m tools.smoke_gui`: internet çağrısı yapmadan 5 üye ve 10 yönetici ekranını gerçek CustomTkinter widget ağacında açar; 80 katalog satırını, fare tekerleğiyle kaydırmayı ve tema geçişini doğrular.
- `python -m tools.verify_catalog --online`: 80 ISBN'i, özet uzunluğunu ve Open Library kapaklarının görsel yanıt verdiğini doğrular.

## Manuel arayüz duman testi

Teslim öncesinde şu akışlar iki uygulamada bir kez uygulanır:

1. `python main.py` ile katalog açılır; arama, tema değişimi ve ziyaretçi görünümü kontrol edilir.
2. Demo üye ile giriş yapılır; kitap alınır, profil ekranında görülür ve iade edilir.
3. `python admin_app.py` ile yönetici girişi yapılır.
4. Kitap ekleme, düzenleme ve arşivleme akışı kontrol edilir.
5. Üye onayı, kitap isteği ve profil talebi ekranları açılır.
6. Pencere 960×680 ile 1920×1080 aralığında yeniden boyutlandırılır; kritik kontrollerin erişilebilir kaldığı doğrulanır.

## Kabul ölçütleri

- `python -m pytest -q`: tüm testler başarılı.
- `ruff check .`: sıfır hata/uyarı.
- `python -m compileall -q .`: sözdizimi hatası yok.
- `PRAGMA integrity_check`: `ok`.
- GUI smoke: 5 üye + 10 yönetici ekranı başarılı.
- Kapak kontrolü: 80/80 görsel erişilebilir.
