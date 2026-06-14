-- SALT-OKUNUR: tum tenant schema'larinda mukerrer kasa kayitlari (ayni gelir_gider_id ile >1 satir)
-- Hicbir sey SILMEZ. Sadece RAISE NOTICE ile raporlar.
DO $$
DECLARE
    r RECORD;
    grp_cnt INT;
    fazla_cnt INT;
    toplam_grup INT := 0;
    toplam_fazla INT := 0;
BEGIN
    FOR r IN
        SELECT t.name, t.schema_name
        FROM public.tenants t
        WHERE t.is_active = 1
        ORDER BY t.name
    LOOP
        -- schema'da kasa tablosu var mi?
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = r.schema_name AND table_name = 'kasa'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'SELECT COALESCE(COUNT(*),0), COALESCE(SUM(cnt-1),0) FROM (
                SELECT gelir_gider_id, COUNT(*) cnt
                FROM %I.kasa
                WHERE gelir_gider_id IS NOT NULL
                GROUP BY gelir_gider_id
                HAVING COUNT(*) > 1
             ) q', r.schema_name)
        INTO grp_cnt, fazla_cnt;

        IF grp_cnt > 0 THEN
            toplam_grup := toplam_grup + grp_cnt;
            toplam_fazla := toplam_fazla + fazla_cnt;
            RAISE NOTICE '### % (%)  -> mukerrer grup: %, silinecek fazla satir: %',
                r.name, r.schema_name, grp_cnt, fazla_cnt;
        END IF;
    END LOOP;

    RAISE NOTICE '=== OZET: toplam mukerrer grup=%, toplam silinecek fazla satir=% ===',
        toplam_grup, toplam_fazla;
END $$;
