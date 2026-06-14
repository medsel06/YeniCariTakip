-- t_3 (ALSE PLASTIK) icin mukerrer kasa satirlarini goster (SALT-OKUNUR)
SELECT k.gelir_gider_id, k.id AS kasa_id, k.tarih, k.tur, k.tutar,
       k.odeme_sekli, left(k.aciklama, 45) AS aciklama
FROM t_3.kasa k
WHERE k.gelir_gider_id IN (
    SELECT gelir_gider_id FROM t_3.kasa
    WHERE gelir_gider_id IS NOT NULL
    GROUP BY gelir_gider_id HAVING COUNT(*) > 1
)
ORDER BY k.gelir_gider_id DESC, k.id;
