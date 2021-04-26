--
-- InitAdmin (insert static admins to DB)
--
DO $$
BEGIN
    IF NOT EXISTS (SELECT EMAIL FROM INITADMIN 
                    WHERE EMAIL = 'monika.mullerova@sap.com') THEN
    INSERT INTO INITADMIN (EMAIL) VALUES ('monika.mullerova@sap.com');
    END IF;
END
$$
--