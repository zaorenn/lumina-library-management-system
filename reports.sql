-- LibSys Kütüphane Yönetim Sistemi
-- Teslim ve raporlama için örnek JOIN / GROUP BY sorguları.

-- 1) Aktif ödünçler ve kalan gün sayısı
SELECT
    br.id AS odunc_id,
    b.title AS kitap,
    br.member_name_snapshot AS uye,
    br.borrow_date AS alis_tarihi,
    br.return_date AS son_teslim,
    CAST(julianday(br.return_date) - julianday('now', 'localtime') AS INTEGER) AS kalan_gun
FROM borrows AS br
JOIN books AS b ON b.id = br.book_id
WHERE br.actual_return_date IS NULL
ORDER BY br.return_date;

-- 2) Kategori bazında envanter özeti
SELECT
    category AS kategori,
    COUNT(*) AS eser_sayisi,
    SUM(total_copies) AS toplam_kopya,
    SUM(available_copies) AS raftaki_kopya,
    SUM(total_copies - available_copies) AS oduncteki_kopya
FROM books
WHERE is_active = 1
GROUP BY category
ORDER BY toplam_kopya DESC, kategori;

-- 3) En çok ödünç alınan 10 kitap
SELECT
    b.title AS kitap,
    b.author AS yazar,
    COUNT(br.id) AS odunc_sayisi
FROM books AS b
LEFT JOIN borrows AS br ON br.book_id = b.id
GROUP BY b.id, b.title, b.author
ORDER BY odunc_sayisi DESC, b.title
LIMIT 10;

-- 4) Üye etkinliği ve toplam gecikme cezası
SELECT
    m.name AS uye,
    m.email,
    COUNT(br.id) AS toplam_odunc,
    SUM(CASE WHEN br.actual_return_date IS NULL THEN 1 ELSE 0 END) AS aktif_odunc,
    COALESCE(SUM(br.late_fee), 0) AS toplam_ceza_tl
FROM members AS m
LEFT JOIN borrows AS br ON br.member_id = m.id
WHERE m.is_active = 1
GROUP BY m.id, m.name, m.email
ORDER BY toplam_odunc DESC, m.name;

-- 5) Geciken aktif ödünçler
SELECT
    b.title AS kitap,
    br.member_name_snapshot AS uye,
    br.return_date AS son_teslim,
    CAST(julianday('now', 'localtime') - julianday(br.return_date) AS INTEGER) AS geciken_gun,
    CAST(julianday('now', 'localtime') - julianday(br.return_date) AS INTEGER) * 5 AS tahmini_ceza_tl
FROM borrows AS br
JOIN books AS b ON b.id = br.book_id
WHERE br.actual_return_date IS NULL
  AND br.return_date < DATE('now', 'localtime')
ORDER BY geciken_gun DESC;

-- 6) Aylık ödünç işlem hacmi
SELECT
    strftime('%Y-%m', borrow_date) AS ay,
    COUNT(*) AS odunc_sayisi,
    SUM(CASE WHEN actual_return_date IS NOT NULL THEN 1 ELSE 0 END) AS iade_sayisi
FROM borrows
GROUP BY strftime('%Y-%m', borrow_date)
ORDER BY ay DESC;
