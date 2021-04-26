--
-- InitAdmin (insert static admins to DB)
--
DO $$
BEGIN
    IF NOT EXISTS (SELECT EMAIL FROM INITADMIN 
                    WHERE EMAIL = 'xx@xx.com') THEN
    INSERT INTO INITADMIN (EMAIL) VALUES ('xx@xx.com');
    END IF;
END
$$
--
