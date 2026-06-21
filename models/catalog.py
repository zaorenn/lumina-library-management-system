"""Curated starter catalog shown on a fresh LibSys installation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CatalogBook:
    title: str
    author: str
    isbn: str
    category: str
    year: int
    summary: str
    copies: int = 4

    @property
    def cover_url(self) -> str:
        return f"https://covers.openlibrary.org/b/isbn/{self.isbn}-L.jpg?default=false"


DEFAULT_CATALOG: tuple[CatalogBook, ...] = (
    CatalogBook(
        "1984",
        "George Orwell",
        "9780451524935",
        "Bilim Kurgu",
        1949,
        "Winston Smith, her hareketin izlendiği Okyanusya'da geçmişi iktidarın istediği biçimde yeniden yazar. Yasak bir yakınlık ve hakikat arayışı, onu Büyük Birader'in baskıcı düzeniyle yüzleşmeye zorlar.",
    ),
    CatalogBook(
        "Cesur Yeni Dünya",
        "Aldous Huxley",
        "9780060850524",
        "Bilim Kurgu",
        1932,
        "İnsanların daha doğmadan sınıflara ayrıldığı, mutluluğun haz ve tüketimle üretildiği kusursuz görünen bir gelecek. Sistemin dışından gelen John, özgür irade ile konfor arasındaki bedeli sorgular.",
    ),
    CatalogBook(
        "Fahrenheit 451",
        "Ray Bradbury",
        "9781451673319",
        "Bilim Kurgu",
        1953,
        "Kitapların yasaklandığı bir toplumda itfaiyeci Guy Montag'ın görevi onları yakmaktır. Merak ettiği tek bir sayfa, ezberlediği hayatı ve sessizce itaat eden dünyayı değiştirmeye başlar.",
    ),
    CatalogBook(
        "Dune",
        "Frank Herbert",
        "9780441172719",
        "Bilim Kurgu",
        1965,
        "Paul Atreides, evrendeki en değerli madde olan baharatın tek kaynağı Arrakis'e gelir. Çölün ekolojisi, hanedan entrikaları ve kehanetler arasında kendi gücünün sonuçlarıyla tanışır.",
    ),
    CatalogBook(
        "Vakıf",
        "Isaac Asimov",
        "9780553293357",
        "Bilim Kurgu",
        1951,
        "Hari Seldon matematiksel psikotarih bilimiyle Galaktik İmparatorluk'un çöküşünü öngörür. İnsanlığın karanlık çağını kısaltmak için bilginlerden oluşan küçük bir Vakıf kurar.",
    ),
    CatalogBook(
        "Neuromancer",
        "William Gibson",
        "9780441569595",
        "Bilim Kurgu",
        1984,
        "Yeteneklerini kaybetmiş bilgisayar korsanı Case, tehlikeli bir yapay zekâ görevi için yeniden siberuzaya bağlanır. Neon şehirlerden dijital bilinçlere uzanan yolculuk siberpunk türünün temel taşlarından biridir.",
    ),
    CatalogBook(
        "Karanlığın Sol Eli",
        "Ursula K. Le Guin",
        "9780441478125",
        "Bilim Kurgu",
        1969,
        "Elçi Genly Ai, sabit cinsiyetin bulunmadığı kış gezegeni Gethen'i gezegenler birliğine katmaya çalışır. Siyasi güvensizlik içinde kurulan beklenmedik dostluk, kimlik ve bağlılık kavramlarını dönüştürür.",
    ),
    CatalogBook(
        "Mülksüzler",
        "Ursula K. Le Guin",
        "9780061054884",
        "Bilim Kurgu",
        1974,
        "Fizikçi Shevek, anarşist Anarres ile zengin Urras arasındaki duvarı aşarak bilimsel fikrini paylaşmak ister. İki toplumun kusurları üzerinden özgürlük, mülkiyet ve aidiyet sorgulanır.",
    ),
    CatalogBook(
        "Otostopçunun Galaksi Rehberi",
        "Douglas Adams",
        "9780345391803",
        "Bilim Kurgu",
        1979,
        "Dünya beklenmedik biçimde yok edilmeden saniyeler önce Arthur Dent bir uzay gemisine alınır. Yanında bir havlu ve tuhaf bir rehberle evrenin bürokrasisi içinde son derece komik bir yolculuğa çıkar.",
    ),
    CatalogBook(
        "Marslı",
        "Andy Weir",
        "9780553418026",
        "Bilim Kurgu",
        2011,
        "Astronot Mark Watney bir kaza sonrası Mars'ta tek başına kalır. Sınırlı erzak, bilimsel yaratıcılık ve inatçı mizahıyla hayatta kalmanın ve Dünya'ya sesini duyurmanın yolunu arar.",
    ),
    CatalogBook(
        "Hobbit",
        "J.R.R. Tolkien",
        "9780547928227",
        "Fantastik",
        1937,
        "Konforuna düşkün Bilbo Baggins, on üç cüce ve büyücü Gandalf'la kayıp bir krallığı geri almak üzere yola çıkar. Yolculuk onu troller, bilmeceler ve ejderha Smaug'la karşılaştırır.",
    ),
    CatalogBook(
        "Yüzüklerin Efendisi: Yüzük Kardeşliği",
        "J.R.R. Tolkien",
        "9780547928210",
        "Fantastik",
        1954,
        "Frodo, karanlık hükümdarın Tek Yüzük'ünü yok etmek için Shire'dan ayrılır. Farklı halklardan dokuz yolcunun kurduğu kardeşlik, Orta Dünya'nın kaderini taşıyan zorlu bir göreve başlar.",
    ),
    CatalogBook(
        "Harry Potter ve Felsefe Taşı",
        "J.K. Rowling",
        "9780590353427",
        "Fantastik",
        1997,
        "Harry on birinci yaş gününde bir büyücü olduğunu ve Hogwarts'a kabul edildiğini öğrenir. Yeni dostluklarının arasında okulun koridorlarında saklanan eski bir sırrın izini sürer.",
    ),
    CatalogBook(
        "Rüzgârın Adı",
        "Patrick Rothfuss",
        "9780756404741",
        "Fantastik",
        2007,
        "Efsanevi müzisyen ve büyücü Kvothe, kimliğini gizlediği bir handa hayat hikâyesini anlatmaya başlar. Çocukluğundan Üniversite'ye uzanan anlatı, zekâ, müzik ve kayıp bir ailenin gizemiyle örülür.",
    ),
    CatalogBook(
        "Yerdeniz Büyücüsü",
        "Ursula K. Le Guin",
        "9780547773742",
        "Fantastik",
        1968,
        "Genç Ged, gücünü kanıtlama hırsıyla dünyaya karanlık bir gölge salar. Yerdeniz adalarında onu izleyen bu varlıkla yüzleşirken büyünün denge ve sorumluluk istediğini öğrenir.",
    ),
    CatalogBook(
        "Aslan, Cadı ve Dolap",
        "C.S. Lewis",
        "9780064471046",
        "Fantastik",
        1950,
        "Dört kardeş eski bir dolaptan sonsuz kışın hüküm sürdüğü Narnia'ya geçer. Aslan'ın dönüşüyle Beyaz Cadı'ya karşı cesaret, sadakat ve fedakârlık sınavı başlar.",
    ),
    CatalogBook(
        "Taht Oyunları",
        "George R.R. Martin",
        "9780553593716",
        "Fantastik",
        1996,
        "Westeros'un soylu aileleri Demir Taht için ittifaklar kurup ihanetler planlar. Kuzeyde ise unutulduğu sanılan daha eski bir tehlike yaklaşmaktadır.",
    ),
    CatalogBook(
        "Son İmparatorluk",
        "Brandon Sanderson",
        "9780765350381",
        "Fantastik",
        2006,
        "Küllerin yağdığı ve karanlık hükümdarın bin yıldır hüküm sürdüğü dünyada hırsız Vin gizli gücünü keşfeder. Bir grup asiyle imkânsız görünen imparatorluk soygununa katılır.",
    ),
    CatalogBook(
        "Gurur ve Önyargı",
        "Jane Austen",
        "9780141439518",
        "Klasik",
        1813,
        "Elizabeth Bennet ile mesafeli Bay Darcy'nin ilk izlenimleri gurur ve yanlış anlamalarla biçimlenir. Zekâ dolu anlatı aşkın yanında sınıf, aile ve bağımsızlık üzerine de keskin bir bakış sunar.",
    ),
    CatalogBook(
        "Suç ve Ceza",
        "Fyodor Dostoyevski",
        "9780143058144",
        "Klasik",
        1866,
        "Yoksul öğrenci Raskolnikov, sıra dışı insanların ahlakın üzerinde olabileceği düşüncesini korkunç bir suçla sınar. Vicdanı ve çevresindeki insanlar onu adalet ile kefaret arasında sıkıştırır.",
    ),
    CatalogBook(
        "Sefiller",
        "Victor Hugo",
        "9780451419439",
        "Klasik",
        1862,
        "Jean Valjean küçük bir suçun gölgesinden kurtulup iyi bir hayat kurmaya çalışırken müfettiş Javert onu izler. Roman merhamet, adalet ve toplumsal eşitsizliği geniş bir insanlık panoramasıyla anlatır.",
    ),
    CatalogBook(
        "Bülbülü Öldürmek",
        "Harper Lee",
        "9780061120084",
        "Klasik",
        1960,
        "Scout Finch, küçük bir Güney kasabasında büyürken avukat babasının haksız yere suçlanan siyah bir adamı savunmasına tanık olur. Çocuk bakışı önyargı, cesaret ve empatiyi görünür kılar.",
    ),
    CatalogBook(
        "Don Kişot",
        "Miguel de Cervantes",
        "9780060934347",
        "Klasik",
        1605,
        "Şövalye romanslarını fazlasıyla ciddiye alan Alonso Quijano, Don Kişot adıyla adalet dağıtmak üzere yola çıkar. Sancho Panza ile maceraları hayal ile gerçek arasındaki sınırı mizahla sorgular.",
    ),
    CatalogBook(
        "Muhteşem Gatsby",
        "F. Scott Fitzgerald",
        "9780743273565",
        "Klasik",
        1925,
        "Gizemli milyoner Jay Gatsby görkemli partilerinin ardında geçmişte kalan bir aşka ulaşmaya çalışır. Caz Çağı'nın parıltısı altında Amerikan Rüyası'nın kırılganlığı ortaya çıkar.",
    ),
    CatalogBook(
        "Jane Eyre",
        "Charlotte Brontë",
        "9780141441146",
        "Klasik",
        1847,
        "Zorlu bir çocukluktan gelen Jane, Thornfield malikânesinde mürebbiye olur ve evin sahibi Rochester'a yakınlaşır. Ancak evin sakladığı sır, sevgisiyle özsaygısı arasında seçim yapmasına yol açar.",
    ),
    CatalogBook(
        "Uğultulu Tepeler",
        "Emily Brontë",
        "9780141439556",
        "Klasik",
        1847,
        "Heathcliff ile Catherine'in tutkulu ve yıkıcı bağı iki ailenin kuşaklarına yayılır. Yorkshire kırlarının sert atmosferi içinde aşk, intikam ve sınıf çatışması iç içe geçer.",
    ),
    CatalogBook(
        "Savaş ve Barış",
        "Lev Tolstoy",
        "9781400079988",
        "Klasik",
        1869,
        "Napolyon savaşları sırasında Rus aristokrasisinden ailelerin hayatları tarihsel dönüşümle kesişir. Tolstoy savaşın büyük anlatısını sevgi, kayıp ve anlam arayışının mahrem anlarıyla birleştirir.",
    ),
    CatalogBook(
        "Anna Karenina",
        "Lev Tolstoy",
        "9780143035008",
        "Klasik",
        1877,
        "Anna'nın Vronski ile ilişkisi onu toplumun katı beklentileriyle karşı karşıya getirir. Paralel hayatlar üzerinden aşk, aile, kıskançlık ve değişen Rusya incelenir.",
    ),
    CatalogBook(
        "Karamazov Kardeşler",
        "Fyodor Dostoyevski",
        "9780374528379",
        "Klasik",
        1880,
        "Bir babanın ölümü etrafında farklı karakterlere sahip üç kardeş şüphe altında kalır. İnanç, özgür irade, suç ve sorumluluk üzerine derin bir aile dramı gelişir.",
    ),
    CatalogBook(
        "Küçük Prens",
        "Antoine de Saint-Exupéry",
        "9780156012195",
        "Roman",
        1943,
        "Çöle düşen bir pilot, küçük asteroidinden gezegenleri dolaşarak gelen Küçük Prens'le tanışır. Onun sade soruları dostluk, sevgi ve yetişkinlerin unuttuğu değerleri yeniden görünür kılar.",
    ),
    CatalogBook(
        "Simyacı",
        "Paulo Coelho",
        "9780061122415",
        "Roman",
        1988,
        "Endülüslü çoban Santiago tekrar eden rüyasının peşinden Mısır piramitlerine gider. Yol boyunca kendi kişisel menkıbesini dinlemeyi ve aradığı hazinenin anlamını öğrenir.",
    ),
    CatalogBook(
        "Uçurtma Avcısı",
        "Khaled Hosseini",
        "9781594631931",
        "Roman",
        2003,
        "Amir ile Hassan'ın Kabil'deki çocukluk dostluğu bir ihanetle kırılır. Yıllar sonra gelen bir haber Amir'e geçmişiyle yüzleşme ve kefaret arama fırsatı verir.",
    ),
    CatalogBook(
        "Dönüşüm",
        "Franz Kafka",
        "9780553213690",
        "Roman",
        1915,
        "Gregor Samsa bir sabah dev bir böceğe dönüşmüş olarak uyanır. Ailesinin değişen tavrı, insan değerinin üretkenlik ve kabul üzerinden nasıl ölçüldüğünü çarpıcı biçimde gösterir.",
    ),
    CatalogBook(
        "Fareler ve İnsanlar",
        "John Steinbeck",
        "9780140177398",
        "Roman",
        1937,
        "Gezici işçiler George ile Lennie kendilerine ait küçük bir çiftlik kurma hayali taşır. Büyük Buhran'ın sert koşulları, dostluklarını ve kırılgan umutlarını sınar.",
    ),
    CatalogBook(
        "Sapiens",
        "Yuval Noah Harari",
        "9780062316097",
        "Tarih",
        2011,
        "Homo sapiens'in küçük topluluklardan küresel uygarlığa uzanan yolculuğu bilişsel, tarımsal ve bilimsel devrimlerle ele alınır. Para, din ve devlet gibi ortak kurguların işbirliğini nasıl mümkün kıldığı tartışılır.",
    ),
    CatalogBook(
        "Homo Deus",
        "Yuval Noah Harari",
        "9780062464316",
        "Tarih",
        2015,
        "İnsanlık açlık, salgın ve savaşla mücadelesinde ilerlerken yeni hedeflerini ölümsüzlük, mutluluk ve tanrısal güç olarak belirliyor. Biyoteknoloji ile algoritmaların gelecekteki etkileri sorgulanıyor.",
    ),
    CatalogBook(
        "Tüfek, Mikrop ve Çelik",
        "Jared Diamond",
        "9780393354324",
        "Tarih",
        1997,
        "Toplumların farklı hızlarda gelişmesini biyolojik üstünlük yerine coğrafya, evcilleştirilebilir türler ve hastalıklarla açıklar. Kıtalar arasındaki eşitsizliğin uzun tarihine bütüncül bir yaklaşım sunar.",
    ),
    CatalogBook(
        "İnsanın Anlam Arayışı",
        "Viktor E. Frankl",
        "9780807014295",
        "Psikoloji",
        1946,
        "Frankl toplama kamplarındaki deneyimlerini insanın en ağır koşullarda bile anlam bulabilme gücüyle birleştirir. Logoterapi yaklaşımı, yaşamın bizden ne beklediğine odaklanır.",
    ),
    CatalogBook(
        "Kendime Düşünceler",
        "Marcus Aurelius",
        "9780140449334",
        "Felsefe",
        180,
        "Roma İmparatoru Marcus Aurelius'un kendisi için tuttuğu notlar, gücün ortasında erdemli ve ölçülü kalma çabasını gösterir. Stoacı düşünce günlük kaygılara sade ve dirençli bir bakış getirir.",
    ),
    CatalogBook(
        "Devlet",
        "Platon",
        "9780140455113",
        "Felsefe",
        -375,
        "Sokrates ve arkadaşları adaletin bireyde ve toplumda ne anlama geldiğini tartışır. İdeal devlet, eğitim, yönetim ve mağara alegorisi üzerinden bilginin sorumluluğu araştırılır.",
    ),
    CatalogBook(
        "Böyle Buyurdu Zerdüşt",
        "Friedrich Nietzsche",
        "9780140441185",
        "Felsefe",
        1883,
        "Zerdüşt yıllar süren yalnızlığından dönerek insana kendi değerlerini yaratma çağrısı yapar. Şiirsel anlatı üstinsan, bengi dönüş ve geleneksel ahlakın aşılması fikirlerini işler.",
    ),
    CatalogBook(
        "Yabancı",
        "Albert Camus",
        "9780679720201",
        "Felsefe",
        1942,
        "Meursault, annesinin ölümünden sonra toplumun beklediği duyguları göstermeden yaşamına devam eder. İşlediği suçtan çok kayıtsızlığı yargılanırken hayatın absürtlüğü belirginleşir.",
    ),
    CatalogBook(
        "Doğu Ekspresinde Cinayet",
        "Agatha Christie",
        "9780062693662",
        "Polisiye",
        1934,
        "Lüks tren kar fırtınasıyla durduğunda bir yolcu kilitli kompartımanında ölü bulunur. Hercule Poirot, birbirinden farklı yolcuların ifadelerindeki ortak geçmişi çözmeye çalışır.",
    ),
    CatalogBook(
        "On Kişiydiler",
        "Agatha Christie",
        "9780062073488",
        "Polisiye",
        1939,
        "Birbirini tanımayan on kişi ıssız bir adadaki konağa davet edilir. Geçmiş suçlarını açıklayan bir kayıt çaldığında, adadan kaçışın olmadığı ölümcül bir hesaplaşma başlar.",
    ),
    CatalogBook(
        "Da Vinci Şifresi",
        "Dan Brown",
        "9780307474278",
        "Polisiye",
        2003,
        "Louvre'daki bir cinayetin ardında bırakılan semboller Robert Langdon ile Sophie Neveu'yü tarihsel bir sırrın peşine düşürür. Paris'ten Londra'ya uzanan yarışta sanat, inanç ve komplolar iç içe geçer.",
    ),
    CatalogBook(
        "Atomik Alışkanlıklar",
        "James Clear",
        "9780735211292",
        "Kişisel Gelişim",
        2018,
        "Kalıcı değişimin büyük hedeflerden çok her gün tekrarlanan küçük sistemlerle oluştuğunu savunur. İyi alışkanlıkları görünür ve kolay, kötü alışkanlıkları zor hâle getiren uygulanabilir bir çerçeve sunar.",
    ),
    CatalogBook(
        "Hızlı ve Yavaş Düşünme",
        "Daniel Kahneman",
        "9780374533557",
        "Psikoloji",
        2011,
        "Zihnin hızlı, sezgisel sistemiyle yavaş ve analitik sistemi arasındaki etkileşimi açıklar. Kararlarımızı etkileyen bilişsel yanılgılar deneyler ve gündelik örneklerle görünür kılınır.",
    ),
    CatalogBook(
        "Etkili İnsanların 7 Alışkanlığı",
        "Stephen R. Covey",
        "9781982137274",
        "Kişisel Gelişim",
        1989,
        "Kişisel ve profesyonel etkinliği geçici teknikler yerine karakter ilkeleri üzerine kurar. Proaktif olmaktan sinerji yaratmaya uzanan yedi alışkanlık, sürdürülebilir gelişim için bütünlüklü bir yol sunar.",
    ),
)


def ensure_default_catalog(connection) -> int:
    """Insert or enrich starter books without duplicating existing records."""

    inserted = 0
    for book in DEFAULT_CATALOG:
        existing = connection.execute(
            """
            SELECT id FROM books
            WHERE isbn = ? COLLATE NOCASE
               OR (title = ? COLLATE NOCASE AND author = ? COLLATE NOCASE)
            ORDER BY CASE WHEN isbn = ? COLLATE NOCASE THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (book.isbn, book.title, book.author, book.isbn),
        ).fetchone()
        if existing:
            isbn_owner = connection.execute(
                "SELECT id FROM books WHERE isbn = ? COLLATE NOCASE", (book.isbn,)
            ).fetchone()
            isbn_value = book.isbn if not isbn_owner or isbn_owner[0] == existing[0] else None
            connection.execute(
                """
                UPDATE books
                SET isbn = COALESCE(?, isbn), category = ?, published_year = ?,
                    description = ?, cover_image_url = ?
                WHERE id = ?
                """,
                (isbn_value, book.category, book.year, book.summary, book.cover_url, existing[0]),
            )
            continue

        connection.execute(
            """
            INSERT INTO books
                (title, author, isbn, category, published_year, description,
                 cover_image_url, total_copies, available_copies, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                book.title,
                book.author,
                book.isbn,
                book.category,
                book.year,
                book.summary,
                book.cover_url,
                book.copies,
                book.copies,
            ),
        )
        inserted += 1
    return inserted
