-- =============================================================================
-- One-off data migration: desktop application tables (schema "public")
--                         -> new standards-based tables (schema "tm").
--
-- Run once, after 001_schema.sql and 002_seed.sql, against a database that
-- still holds the desktop application's tables. It only reads from "public";
-- the old tables are left untouched, so the desktop application keeps working
-- on its own copy of the data.
--
-- What it does
--   * Gives every row a combination key (PP+YY+MM+NNNNN) dated by the month the
--     row was originally created, in the order of the old numeric ids.
--   * NUM_CREATED_BY / NUM_UPDATED_BY -> VCH_CREATED_BY / VCH_MODIFIED_BY. Ids
--     that match no user (the desktop app wrote 0 and 1 everywhere) become the
--     system administrator.
--   * CHR_ACTIVE_IND: for groups and roles it meant "deactivated" and becomes
--     CHR_*_STATUS; for every other table it meant "deleted" and becomes
--     BOL_REC_ACTV_STT.
--   * User assignments -> TM_MST_USER_ROLE. Menu access, which was held per
--     user, is merged per role into TM_MST_ROLE_PERMISSION with full rights.
--   * Created/updated timestamps: the desktop app stored Malaysia wall-clock
--     time in a UTC session, so stored instants are 8 hours late. They are
--     corrected here. Remove the lg_ts() conversion below if your database
--     session time zone was not UTC.
--
-- A month holding more than 99,999 legacy transactions exceeds the combination
-- key capacity and aborts the migration; nothing is written in that case.
-- =============================================================================

BEGIN;

-- Legacy timestamp -> true instant (see header).
CREATE FUNCTION pg_temp.lg_ts(p TIMESTAMPTZ) RETURNS TIMESTAMPTZ
LANGUAGE sql IMMUTABLE AS $$
    SELECT (p AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Kuala_Lumpur'
$$;

CREATE TEMP TABLE lg_sys ON COMMIT DROP AS
    SELECT vch_user_id AS id FROM tm.tm_mst_user WHERE vch_login_id = 'superuser';

CREATE TEMP TABLE lg_map_user     (old_id INTEGER PRIMARY KEY, new_id VARCHAR(15) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lg_map_group    (old_id INTEGER PRIMARY KEY, new_id VARCHAR(15) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lg_map_role     (old_id INTEGER PRIMARY KEY, new_id VARCHAR(15) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lg_map_bank     (old_id INTEGER PRIMARY KEY, new_id VARCHAR(15) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lg_map_customer (old_id INTEGER PRIMARY KEY, new_id VARCHAR(15) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lg_map_source   (old_id INTEGER PRIMARY KEY, new_id VARCHAR(15) NOT NULL) ON COMMIT DROP;

-- Legacy user id -> new user id, falling back to the system administrator.
CREATE FUNCTION pg_temp.lg_user(p INTEGER) RETURNS VARCHAR
LANGUAGE sql STABLE AS $$
    SELECT coalesce((SELECT new_id FROM lg_map_user WHERE old_id = p), (SELECT id FROM lg_sys))
$$;

-- ---------------------------------------------------------------- users
-- A legacy login that already exists in tm (the seeded superuser) is reused.
INSERT INTO lg_map_user (old_id, new_id)
SELECT l.num_user_id,
       coalesce(t.vch_user_id, tm.tm_generate_combination_key('US', pg_temp.lg_ts(coalesce(l.dtt_created_at, now()))))
FROM public.tm_mst_user l
LEFT JOIN tm.tm_mst_user t
       ON lower(t.vch_login_id) = lower(l.vch_login_id) AND t.bol_rec_actv_stt AND l.chr_active_ind = 'Y'
ORDER BY l.num_user_id;

INSERT INTO tm.tm_mst_user (
    vch_user_id, vch_login_id, vch_user_name, vch_password_hash, vch_email, vch_contact_no,
    vch_address_1, vch_address_2, vch_address_3, vch_address_4,
    bol_bypass_ind, bol_no_delete_ind, dtt_last_login_date,
    dtt_created_date, vch_created_by, bol_rec_actv_stt
)
SELECT m.new_id, l.vch_login_id, l.vch_user_name, l.vch_password, l.vch_email, l.vch_contact,
       l.vch_address_1, l.vch_address_2, l.vch_address_3, l.vch_address_4,
       l.chr_bypass_ind = 'Y', l.chr_no_delete_ind = 'Y', l.dtt_last_login_time,
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), (SELECT id FROM lg_sys), l.chr_active_ind = 'Y'
FROM public.tm_mst_user l
JOIN lg_map_user m ON m.old_id = l.num_user_id
WHERE NOT EXISTS (SELECT 1 FROM tm.tm_mst_user t WHERE t.vch_user_id = m.new_id)
ORDER BY l.num_user_id;

-- The existing superuser keeps the password and details it had in the desktop application.
UPDATE tm.tm_mst_user t
SET vch_password_hash = l.vch_password,
    vch_user_name     = l.vch_user_name,
    vch_email         = l.vch_email,
    vch_contact_no    = l.vch_contact,
    vch_address_1     = l.vch_address_1,
    vch_address_2     = l.vch_address_2,
    vch_address_3     = l.vch_address_3,
    vch_address_4     = l.vch_address_4,
    vch_modified_by   = (SELECT id FROM lg_sys)
FROM public.tm_mst_user l
JOIN lg_map_user m ON m.old_id = l.num_user_id
WHERE t.vch_user_id = m.new_id AND t.vch_user_id = (SELECT id FROM lg_sys);

-- Supervisors and creators can only be linked once every user exists.
UPDATE tm.tm_mst_user t
SET vch_supervisor_user_id = (SELECT new_id FROM lg_map_user WHERE old_id = l.num_supervisor_id),
    vch_modified_by        = CASE WHEN l.num_updated_by IS NULL THEN t.vch_modified_by ELSE pg_temp.lg_user(l.num_updated_by) END
FROM public.tm_mst_user l
JOIN lg_map_user m ON m.old_id = l.num_user_id
WHERE t.vch_user_id = m.new_id AND (l.num_supervisor_id IS NOT NULL OR l.num_updated_by IS NOT NULL);

-- ---------------------------------------------------------------- groups
INSERT INTO lg_map_group (old_id, new_id)
SELECT l.num_group_id,
       coalesce(t.vch_group_id, tm.tm_generate_combination_key('GP', pg_temp.lg_ts(coalesce(l.dtt_created_at, now()))))
FROM public.tm_mst_group l
LEFT JOIN tm.tm_mst_group t ON upper(t.vch_group_name) = upper(l.vch_group_name) AND t.bol_rec_actv_stt
ORDER BY l.num_group_id;

INSERT INTO tm.tm_mst_group (
    vch_group_id, vch_group_name, vch_group_desc, chr_group_status, bol_no_delete_ind,
    dtt_created_date, vch_created_by, vch_modified_by
)
SELECT m.new_id, l.vch_group_name, l.vch_desc, CASE WHEN l.chr_active_ind = 'Y' THEN 'A' ELSE 'I' END,
       l.chr_no_delete_ind = 'Y',
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), pg_temp.lg_user(l.num_created_by),
       CASE WHEN l.num_updated_by IS NULL THEN NULL ELSE pg_temp.lg_user(l.num_updated_by) END
FROM public.tm_mst_group l
JOIN lg_map_group m ON m.old_id = l.num_group_id
WHERE NOT EXISTS (SELECT 1 FROM tm.tm_mst_group t WHERE t.vch_group_id = m.new_id)
ORDER BY l.num_group_id;

-- ---------------------------------------------------------------- roles
INSERT INTO lg_map_role (old_id, new_id)
SELECT l.num_role_id,
       coalesce(t.vch_role_id, tm.tm_generate_combination_key('RL', pg_temp.lg_ts(coalesce(l.dtt_created_at, now()))))
FROM public.tm_mst_role l
JOIN lg_map_group g ON g.old_id = l.num_group_id
LEFT JOIN tm.tm_mst_role t
       ON t.vch_group_id = g.new_id AND upper(t.vch_role_name) = upper(l.vch_role_name) AND t.bol_rec_actv_stt
ORDER BY l.num_role_id;

INSERT INTO tm.tm_mst_role (
    vch_role_id, vch_group_id, vch_role_name, vch_role_desc, chr_role_status, bol_no_delete_ind,
    dtt_created_date, vch_created_by, vch_modified_by
)
SELECT m.new_id, g.new_id, l.vch_role_name, l.vch_desc, CASE WHEN l.chr_active_ind = 'Y' THEN 'A' ELSE 'I' END,
       l.chr_no_delete_ind = 'Y',
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), pg_temp.lg_user(l.num_created_by),
       CASE WHEN l.num_updated_by IS NULL THEN NULL ELSE pg_temp.lg_user(l.num_updated_by) END
FROM public.tm_mst_role l
JOIN lg_map_role m ON m.old_id = l.num_role_id
JOIN lg_map_group g ON g.old_id = l.num_group_id
WHERE NOT EXISTS (SELECT 1 FROM tm.tm_mst_role t WHERE t.vch_role_id = m.new_id)
ORDER BY l.num_role_id;

-- ---------------------------------------------------------------- user roles
INSERT INTO tm.tm_mst_user_role (vch_user_id, vch_role_id, dtt_created_date, vch_created_by)
SELECT u.new_id, r.new_id, pg_temp.lg_ts(min(coalesce(l.dtt_created_at, now()))), (SELECT id FROM lg_sys)
FROM public.tm_mst_user_assignment l
JOIN lg_map_user u ON u.old_id = l.num_user_id
JOIN lg_map_role r ON r.old_id = l.num_role_id
WHERE l.chr_active_ind = 'Y'
  AND NOT EXISTS (
      SELECT 1 FROM tm.tm_mst_user_role t
      WHERE t.vch_user_id = u.new_id AND t.vch_role_id = r.new_id AND t.bol_rec_actv_stt)
GROUP BY u.new_id, r.new_id
ORDER BY min(l.num_user_acs_id);

-- ---------------------------------------------------------------- role permissions
-- Legacy menu ids are fixed by the desktop application's install script.
INSERT INTO tm.tm_mst_role_permission (vch_role_id, vch_permission_id, chr_access_rights, vch_created_by)
SELECT DISTINCT r.new_id, p.vch_permission_id, '11110000', (SELECT id FROM lg_sys)
FROM public.tm_mst_menu_access a
JOIN public.tm_mst_user_assignment ua ON ua.num_user_acs_id = a.num_user_acs_id AND ua.chr_active_ind = 'Y'
JOIN lg_map_role r ON r.old_id = ua.num_role_id
JOIN (VALUES
    (1, 'TRN'), (2, 'ADM'), (3, 'RPT'),
    (4, 'TRN_PDF_UPLOAD'), (5, 'TRN_MANUAL_INPUT'), (6, 'TRN_IMAGE_UPLOAD'), (7, 'TRN_DATA_ENRICHMENT'),
    (8, 'ADM_USER_GROUP'), (9, 'ADM_USER_ROLE'), (10, 'ADM_USER_RIGHTS'), (11, 'ADM_BLACKLISTED'),
    (12, 'ADM_SUSPICIOUS'), (13, 'ADM_CUSTOMER_PROFILE'), (14, 'ADM_USER_PROFILE'), (15, 'ADM_BANK_PROFILE'),
    (16, 'RPT_ENQUIRY'), (17, 'RPT_KPI_REVIEW')
) AS menu (old_id, code) ON menu.old_id = a.num_menu_id
JOIN tm.tm_mst_permission p ON p.vch_permission_code = menu.code
WHERE a.chr_active_ind = 'Y'
  AND NOT EXISTS (
      SELECT 1 FROM tm.tm_mst_role_permission t
      WHERE t.vch_role_id = r.new_id AND t.vch_permission_id = p.vch_permission_id AND t.bol_rec_actv_stt);

-- ---------------------------------------------------------------- banks
INSERT INTO lg_map_bank (old_id, new_id)
SELECT num_bank_id, tm.tm_generate_combination_key('BK', pg_temp.lg_ts(coalesce(dtt_created_at, now())))
FROM public.tm_mst_bank l
ORDER BY l.num_bank_id;

INSERT INTO tm.tm_mst_bank (
    vch_bank_id, vch_bank_name, vch_bank_display_name, vch_bank_reg_no, vch_bank_address,
    dtt_created_date, vch_created_by, vch_modified_by, bol_rec_actv_stt
)
SELECT m.new_id, l.vch_bank_name, l.vch_bank_display_nm, l.vch_bank_reg_no, l.vch_address,
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), pg_temp.lg_user(l.num_created_by),
       CASE WHEN l.num_updated_by IS NULL THEN NULL ELSE pg_temp.lg_user(l.num_updated_by) END,
       l.chr_active_ind = 'Y'
FROM public.tm_mst_bank l
JOIN lg_map_bank m ON m.old_id = l.num_bank_id
ORDER BY l.num_bank_id;

-- ---------------------------------------------------------------- customers
INSERT INTO lg_map_customer (old_id, new_id)
SELECT num_cust_id, tm.tm_generate_combination_key('CS', pg_temp.lg_ts(coalesce(dtt_created_at, now())))
FROM public.tm_mst_customer l
ORDER BY l.num_cust_id;

INSERT INTO tm.tm_mst_customer (
    vch_customer_id, vch_customer_code, vch_customer_name, vch_email, vch_contact_no, vch_address, vch_remark,
    dtt_created_date, vch_created_by, vch_modified_by, bol_rec_actv_stt
)
SELECT m.new_id, l.vch_cust_code, l.vch_cust_name, l.vch_email, l.vch_contact, l.vch_address,
       -- the desktop app stored line breaks as the two characters "\n"
       replace(l.vch_remark, '\n', E'\n'),
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), pg_temp.lg_user(l.num_created_by),
       CASE WHEN l.num_updated_by IS NULL THEN NULL ELSE pg_temp.lg_user(l.num_updated_by) END,
       l.chr_active_ind = 'Y'
FROM public.tm_mst_customer l
JOIN lg_map_customer m ON m.old_id = l.num_cust_id
ORDER BY l.num_cust_id;

-- ---------------------------------------------------------------- data entry sources
INSERT INTO tm.tm_mst_data_entry_source (vch_source_code, vch_source_desc, vch_created_by, bol_rec_actv_stt)
SELECT l.vch_dt_ent_code, l.vch_dt_ent_desc, (SELECT id FROM lg_sys), l.chr_active_ind = 'Y'
FROM public.tm_mst_data_entry_source l
WHERE NOT EXISTS (SELECT 1 FROM tm.tm_mst_data_entry_source t WHERE t.vch_source_code = l.vch_dt_ent_code)
ORDER BY l.num_dt_ent_id;

INSERT INTO lg_map_source (old_id, new_id)
SELECT l.num_dt_ent_id, t.vch_data_entry_source_id
FROM public.tm_mst_data_entry_source l
JOIN tm.tm_mst_data_entry_source t ON t.vch_source_code = l.vch_dt_ent_code;

-- ---------------------------------------------------------------- blacklisted / suspicious names
INSERT INTO tm.tm_mst_blacklisted (
    vch_blacklisted_id, vch_blacklisted_name, vch_remark_1, vch_remark_2,
    dtt_created_date, vch_created_by, vch_modified_by, bol_rec_actv_stt
)
SELECT tm.tm_generate_combination_key('BL', pg_temp.lg_ts(coalesce(l.dtt_created_at, now()))),
       l.vch_blacklisted_name, nullif(l.vch_remark_1, ''), nullif(l.vch_remark_2, ''),
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), pg_temp.lg_user(l.num_created_by),
       CASE WHEN l.num_updated_by IS NULL THEN NULL ELSE pg_temp.lg_user(l.num_updated_by) END,
       l.chr_active_ind = 'Y'
FROM public.tm_mst_blacklisted l
ORDER BY l.num_bl_id;

INSERT INTO tm.tm_mst_suspicious (
    vch_suspicious_id, vch_suspicious_name, vch_remark_1, vch_remark_2,
    dtt_created_date, vch_created_by, vch_modified_by, bol_rec_actv_stt
)
SELECT tm.tm_generate_combination_key('SP', pg_temp.lg_ts(coalesce(l.dtt_created_at, now()))),
       l.vch_suspicious_name, nullif(l.vch_remark_1, ''), nullif(l.vch_remark_2, ''),
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), pg_temp.lg_user(l.num_created_by),
       CASE WHEN l.num_updated_by IS NULL THEN NULL ELSE pg_temp.lg_user(l.num_updated_by) END,
       l.chr_active_ind = 'Y'
FROM public.tm_mst_suspicious l
ORDER BY l.num_susp_id;

-- ---------------------------------------------------------------- transactions
-- Rows without a transaction date cannot be carried over (the column is mandatory).
INSERT INTO tm.tm_trn_transaction (
    vch_transaction_id, vch_bank_id, vch_data_entry_source_id, vch_customer_id, vch_agent_user_id,
    vch_account_no, dtt_statement_date, dtt_transaction_date,
    vch_trn_desc_1, vch_trn_desc_2, vch_target_name,
    num_credit_amount, num_debit_amount, num_statement_balance,
    vch_file_name, bol_printed_stt,
    dtt_created_date, vch_created_by, vch_modified_by, bol_rec_actv_stt
)
SELECT tm.tm_generate_combination_key('TR', pg_temp.lg_ts(coalesce(l.dtt_created_at, now()))),
       b.new_id, s.new_id, c.new_id, pg_temp.lg_user(l.num_user_id),
       l.num_account_no::TEXT, l.dtt_statement_date::DATE, l.dtt_transaction_date::DATE,
       l.vch_trn_desc_1, l.vch_trn_desc_2, l.vch_ner,
       coalesce(l.num_amount_credit, 0), coalesce(l.num_amount_debit, 0), coalesce(l.num_statement_balance, 0),
       l.vch_file_name, coalesce(l.chr_printed_ind, 'N') = 'Y',
       pg_temp.lg_ts(coalesce(l.dtt_created_at, now())), pg_temp.lg_user(l.num_created_by),
       CASE WHEN l.num_updated_by IS NULL THEN NULL ELSE pg_temp.lg_user(l.num_updated_by) END,
       l.chr_active_ind = 'Y'
FROM public.tm_trn_transaction l
JOIN lg_map_bank b     ON b.old_id = l.num_bank_id
JOIN lg_map_customer c ON c.old_id = l.num_cust_id
JOIN lg_map_source s   ON s.old_id = l.num_dt_ent_id
WHERE l.dtt_transaction_date IS NOT NULL
ORDER BY l.num_trn_id;

COMMIT;

-- Row counts to check against the old tables
SELECT 'users' AS entity, count(*) FROM tm.tm_mst_user
UNION ALL SELECT 'groups', count(*) FROM tm.tm_mst_group
UNION ALL SELECT 'roles', count(*) FROM tm.tm_mst_role
UNION ALL SELECT 'banks', count(*) FROM tm.tm_mst_bank
UNION ALL SELECT 'customers', count(*) FROM tm.tm_mst_customer
UNION ALL SELECT 'blacklisted', count(*) FROM tm.tm_mst_blacklisted
UNION ALL SELECT 'suspicious', count(*) FROM tm.tm_mst_suspicious
UNION ALL SELECT 'transactions', count(*) FROM tm.tm_trn_transaction;
