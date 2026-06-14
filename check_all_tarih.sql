-- SALT-OKUNUR: tum tenant schema'larinda ISO-disi (bozuk) tarih formatlarini bul.
DO $$
DECLARE
    r RECORD;
    bozuk INT;
    ornek TEXT;
BEGIN
    FOR r IN
        SELECT t.name, t.schema_name FROM public.tenants t
        WHERE t.is_active = 1 ORDER BY t.name
    LOOP
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables
            WHERE table_schema=r.schema_name AND table_name='kasa') THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'SELECT COUNT(*), MIN(tarih) FROM %I.kasa
             WHERE tarih IS NOT NULL AND tarih <> ''''
               AND tarih !~ ''^[0-9]{4}-[0-9]{2}-[0-9]{2}$''',
            r.schema_name)
        INTO bozuk, ornek;

        IF bozuk > 0 THEN
            RAISE NOTICE '### % (%) -> ISO-disi tarih: % adet, ornek: %',
                r.name, r.schema_name, bozuk, ornek;
        ELSE
            RAISE NOTICE '    % (%) -> tum tarihler ISO (temiz)', r.name, r.schema_name;
        END IF;
    END LOOP;
END $$;
