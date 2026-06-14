-- t_3.kasa tarih alaninin formatini ve tipini kontrol et (SALT-OKUNUR)
SELECT data_type FROM information_schema.columns
WHERE table_schema='t_3' AND table_name='kasa' AND column_name='tarih';

-- Baska formatta (leading-zero olmayan veya ISO disi) tarih var mi?
SELECT tarih, COUNT(*) FROM t_3.kasa
WHERE tarih !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
GROUP BY tarih ORDER BY tarih
LIMIT 30;
