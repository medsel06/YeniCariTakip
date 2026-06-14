\echo '=== ONCESI: bozuk tarihler ==='
SELECT id, tarih, tur, tutar, left(aciklama,30) AS aciklama
FROM t_6.kasa
WHERE tarih IS NOT NULL AND tarih <> ''
  AND tarih !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
ORDER BY id;

BEGIN;

-- Yedek tablo (sadece bozuk satirlar)
DROP TABLE IF EXISTS t_6.kasa_tarih_yedek_20260614;
CREATE TABLE t_6.kasa_tarih_yedek_20260614 AS
SELECT id, tarih FROM t_6.kasa
WHERE tarih IS NOT NULL AND tarih <> ''
  AND tarih !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$';

-- Normalize: 2026-06-8 -> 2026-06-08
UPDATE t_6.kasa
SET tarih = to_char(tarih::date, 'YYYY-MM-DD')
WHERE tarih IS NOT NULL AND tarih <> ''
  AND tarih !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$';

COMMIT;

\echo '=== SONRASI: ayni satirlar (yedekten id ile) ==='
SELECT k.id, y.tarih AS eski_tarih, k.tarih AS yeni_tarih
FROM t_6.kasa k
JOIN t_6.kasa_tarih_yedek_20260614 y ON y.id = k.id
ORDER BY k.id;

\echo '=== KONTROL: hala ISO-disi var mi? (0 olmali) ==='
SELECT COUNT(*) AS kalan_bozuk FROM t_6.kasa
WHERE tarih IS NOT NULL AND tarih <> ''
  AND tarih !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$';
