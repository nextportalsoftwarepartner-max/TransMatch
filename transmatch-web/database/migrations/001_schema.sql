-- =============================================================================
-- TransMatch schema, designed to TransMatch_RDBMS_Schema_Design_Standards.md
--
--   * All objects live in the Postgres schema "tm" and carry the TM_ prefix.
--   * Table categories: MST (master), TRN (transaction), HIS (history).
--   * Column prefixes: VCH, CHR, NUM, DTT, BOL, JSN.
--   * Business entities use the combination key PP + YY + MM + NNNNN,
--     VARCHAR(15), produced by tm_generate_combination_key() and assigned by
--     the tm_set_combination_key() trigger (ADR-0010).
--   * Every business table carries the standard audit columns:
--       DTT_CREATED_DATE, VCH_CREATED_BY, DTT_MODIFIED_DATE, VCH_MODIFIED_BY,
--       BOL_REC_ACTV_STT  (record validity only; false = logically deleted)
--   * Timestamps are TIMESTAMPTZ (stored in UTC).
--
-- Combination-key prefix registry (new prefixes need human approval):
--   US User              GP Group             RL Role
--   PM Permission        UR User role         RP Role permission
--   ST Status            BK Bank              CS Customer
--   DS Data entry source BL Blacklisted name  SP Suspicious name
--   IB Import batch      TR Transaction
--
-- HIS tables are append-only logs, not business entities; they use a BIGINT
-- identity key so their volume is not limited to 99,999 rows a month.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS tm;

-- -----------------------------------------------------------------------------
-- Combination-key generator
-- -----------------------------------------------------------------------------

CREATE TABLE tm.tm_mst_code_sequence (
    chr_entity_prefix   CHAR(2)      NOT NULL,
    chr_period_yymm     CHAR(4)      NOT NULL,
    num_last_sequence   INTEGER      NOT NULL CHECK (num_last_sequence BETWEEN 1 AND 99999),
    dtt_created_date    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    dtt_modified_date   TIMESTAMPTZ,
    CONSTRAINT pk_tm_mst_code_sequence PRIMARY KEY (chr_entity_prefix, chr_period_yymm)
);

-- Returns the next key for an entity prefix: PP + YY + MM + NNNNN.
-- The sequence restarts every month (Malaysia time). The upsert takes a row
-- lock, so concurrent callers are serialised and no number is handed out twice.
CREATE FUNCTION tm.tm_generate_combination_key(p_prefix TEXT, p_at TIMESTAMPTZ DEFAULT now())
RETURNS VARCHAR(15)
LANGUAGE plpgsql
AS $$
DECLARE
    v_period CHAR(4) := to_char(p_at AT TIME ZONE 'Asia/Kuala_Lumpur', 'YYMM');
    v_seq    INTEGER;
BEGIN
    IF p_prefix IS NULL OR p_prefix !~ '^[A-Z]{2}$' THEN
        RAISE EXCEPTION 'TM combination key: invalid entity prefix "%"', p_prefix;
    END IF;

    INSERT INTO tm.tm_mst_code_sequence AS s (chr_entity_prefix, chr_period_yymm, num_last_sequence)
    VALUES (p_prefix, v_period, 1)
    ON CONFLICT (chr_entity_prefix, chr_period_yymm)
    DO UPDATE SET num_last_sequence = s.num_last_sequence + 1,
                  dtt_modified_date = now()
        WHERE s.num_last_sequence < 99999
    RETURNING s.num_last_sequence INTO v_seq;

    IF v_seq IS NULL THEN
        RAISE EXCEPTION 'TM combination key: monthly capacity (99,999) reached for prefix % in period %',
            p_prefix, v_period;
    END IF;

    RETURN p_prefix || v_period || lpad(v_seq::TEXT, 5, '0');
END;
$$;

-- BEFORE INSERT trigger: tm_set_combination_key('<key column>', '<prefix>').
-- Fills the key when the row does not bring one.
CREATE FUNCTION tm.tm_set_combination_key()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_column TEXT := TG_ARGV[0];
    v_prefix TEXT := TG_ARGV[1];
BEGIN
    IF coalesce(to_jsonb(NEW) ->> v_column, '') = '' THEN
        NEW := jsonb_populate_record(NEW, jsonb_build_object(v_column, tm.tm_generate_combination_key(v_prefix)));
    END IF;
    RETURN NEW;
END;
$$;

-- BEFORE UPDATE trigger: creation fields are immutable, modification time is stamped.
CREATE FUNCTION tm.tm_touch_audit_columns()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.dtt_created_date  := OLD.dtt_created_date;
    NEW.vch_created_by    := OLD.vch_created_by;
    NEW.dtt_modified_date := now();
    RETURN NEW;
END;
$$;

-- -----------------------------------------------------------------------------
-- TM_MST_USER
-- -----------------------------------------------------------------------------

CREATE TABLE tm.tm_mst_user (
    vch_user_id             VARCHAR(15)   NOT NULL,
    vch_login_id            VARCHAR(100)  NOT NULL,
    vch_user_name           VARCHAR(100)  NOT NULL,
    vch_password_hash       VARCHAR(255),
    vch_email               VARCHAR(100),
    vch_contact_no          VARCHAR(20),
    vch_address_1           VARCHAR(255),
    vch_address_2           VARCHAR(255),
    vch_address_3           VARCHAR(255),
    vch_address_4           VARCHAR(255),
    vch_supervisor_user_id  VARCHAR(15),
    chr_user_status         CHAR(1)       NOT NULL DEFAULT 'A' CHECK (chr_user_status IN ('A', 'I')),
    bol_bypass_ind          BOOLEAN       NOT NULL DEFAULT FALSE,  -- bypasses permission checks (super user)
    bol_no_delete_ind       BOOLEAN       NOT NULL DEFAULT FALSE,  -- protected system record
    dtt_last_login_date     TIMESTAMPTZ,
    dtt_created_date        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by          VARCHAR(15)   NOT NULL,
    dtt_modified_date       TIMESTAMPTZ,
    vch_modified_by         VARCHAR(15),
    bol_rec_actv_stt        BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_user PRIMARY KEY (vch_user_id),
    CONSTRAINT fk_tm_mst_user_supervisor FOREIGN KEY (vch_supervisor_user_id) REFERENCES tm.tm_mst_user (vch_user_id),
    CONSTRAINT fk_tm_mst_user_created_by FOREIGN KEY (vch_created_by) REFERENCES tm.tm_mst_user (vch_user_id),
    CONSTRAINT fk_tm_mst_user_modified_by FOREIGN KEY (vch_modified_by) REFERENCES tm.tm_mst_user (vch_user_id)
);
CREATE UNIQUE INDEX uq_tm_mst_user_login ON tm.tm_mst_user (lower(vch_login_id)) WHERE bol_rec_actv_stt;
CREATE INDEX idx_tm_mst_user_supervisor ON tm.tm_mst_user (vch_supervisor_user_id);
CREATE TRIGGER trg_tm_mst_user_key BEFORE INSERT ON tm.tm_mst_user
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_user_id', 'US');
CREATE TRIGGER trg_tm_mst_user_audit BEFORE UPDATE ON tm.tm_mst_user
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

-- -----------------------------------------------------------------------------
-- TM_MST_STATUS: controlled list of status codes per domain
-- -----------------------------------------------------------------------------

CREATE TABLE tm.tm_mst_status (
    vch_status_id       VARCHAR(15)   NOT NULL,
    vch_status_domain   VARCHAR(30)   NOT NULL,
    chr_status_code     CHAR(1)       NOT NULL,
    vch_status_name     VARCHAR(50)   NOT NULL,
    dtt_created_date    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by      VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date   TIMESTAMPTZ,
    vch_modified_by     VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt    BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_status PRIMARY KEY (vch_status_id),
    CONSTRAINT uq_tm_mst_status_code UNIQUE (vch_status_domain, chr_status_code)
);
CREATE TRIGGER trg_tm_mst_status_key BEFORE INSERT ON tm.tm_mst_status
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_status_id', 'ST');
CREATE TRIGGER trg_tm_mst_status_audit BEFORE UPDATE ON tm.tm_mst_status
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

-- -----------------------------------------------------------------------------
-- Authorization: TM_MST_GROUP, TM_MST_ROLE, TM_MST_PERMISSION,
--                TM_MST_USER_ROLE, TM_MST_ROLE_PERMISSION
-- -----------------------------------------------------------------------------

CREATE TABLE tm.tm_mst_group (
    vch_group_id        VARCHAR(15)   NOT NULL,
    vch_group_name      VARCHAR(50)   NOT NULL,
    vch_group_desc      VARCHAR(100),
    chr_group_status    CHAR(1)       NOT NULL DEFAULT 'A' CHECK (chr_group_status IN ('A', 'I')),
    bol_no_delete_ind   BOOLEAN       NOT NULL DEFAULT FALSE,
    dtt_created_date    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by      VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date   TIMESTAMPTZ,
    vch_modified_by     VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt    BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_group PRIMARY KEY (vch_group_id)
);
CREATE UNIQUE INDEX uq_tm_mst_group_name ON tm.tm_mst_group (upper(vch_group_name)) WHERE bol_rec_actv_stt;
CREATE TRIGGER trg_tm_mst_group_key BEFORE INSERT ON tm.tm_mst_group
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_group_id', 'GP');
CREATE TRIGGER trg_tm_mst_group_audit BEFORE UPDATE ON tm.tm_mst_group
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

CREATE TABLE tm.tm_mst_role (
    vch_role_id         VARCHAR(15)   NOT NULL,
    vch_group_id        VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_group (vch_group_id),
    vch_role_name       VARCHAR(50)   NOT NULL,
    vch_role_desc       VARCHAR(255),
    chr_role_status     CHAR(1)       NOT NULL DEFAULT 'A' CHECK (chr_role_status IN ('A', 'I')),
    bol_no_delete_ind   BOOLEAN       NOT NULL DEFAULT FALSE,
    dtt_created_date    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by      VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date   TIMESTAMPTZ,
    vch_modified_by     VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt    BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_role PRIMARY KEY (vch_role_id)
);
CREATE UNIQUE INDEX uq_tm_mst_role_name ON tm.tm_mst_role (vch_group_id, upper(vch_role_name)) WHERE bol_rec_actv_stt;
CREATE INDEX idx_tm_mst_role_group ON tm.tm_mst_role (vch_group_id);
CREATE TRIGGER trg_tm_mst_role_key BEFORE INSERT ON tm.tm_mst_role
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_role_id', 'RL');
CREATE TRIGGER trg_tm_mst_role_audit BEFORE UPDATE ON tm.tm_mst_role
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

-- One permission per menu / screen. Main menus have no parent.
CREATE TABLE tm.tm_mst_permission (
    vch_permission_id         VARCHAR(15)   NOT NULL,
    vch_permission_code       VARCHAR(50)   NOT NULL,
    vch_permission_name       VARCHAR(50)   NOT NULL,
    vch_permission_desc       VARCHAR(100),
    vch_parent_permission_id  VARCHAR(15)   REFERENCES tm.tm_mst_permission (vch_permission_id),
    bol_main_menu_ind         BOOLEAN       NOT NULL DEFAULT FALSE,
    num_display_order         INTEGER       NOT NULL DEFAULT 0,
    dtt_created_date          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by            VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date         TIMESTAMPTZ,
    vch_modified_by           VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt          BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_permission PRIMARY KEY (vch_permission_id),
    CONSTRAINT uq_tm_mst_permission_code UNIQUE (vch_permission_code)
);
CREATE INDEX idx_tm_mst_permission_parent ON tm.tm_mst_permission (vch_parent_permission_id);
CREATE TRIGGER trg_tm_mst_permission_key BEFORE INSERT ON tm.tm_mst_permission
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_permission_id', 'PM');
CREATE TRIGGER trg_tm_mst_permission_audit BEFORE UPDATE ON tm.tm_mst_permission
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

CREATE TABLE tm.tm_mst_user_role (
    vch_user_role_id    VARCHAR(15)   NOT NULL,
    vch_user_id         VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    vch_role_id         VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_role (vch_role_id),
    dtt_created_date    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by      VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date   TIMESTAMPTZ,
    vch_modified_by     VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt    BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_user_role PRIMARY KEY (vch_user_role_id)
);
CREATE UNIQUE INDEX uq_tm_mst_user_role ON tm.tm_mst_user_role (vch_user_id, vch_role_id) WHERE bol_rec_actv_stt;
CREATE INDEX idx_tm_mst_user_role_role ON tm.tm_mst_user_role (vch_role_id);
CREATE TRIGGER trg_tm_mst_user_role_key BEFORE INSERT ON tm.tm_mst_user_role
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_user_role_id', 'UR');
CREATE TRIGGER trg_tm_mst_user_role_audit BEFORE UPDATE ON tm.tm_mst_user_role
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

-- CHR_ACCESS_RIGHTS: one flag per position, in the order
--   VIEW, CREATE, UPDATE, DELETE, APPROVE, REJECT, PUBLISH, ARCHIVE
-- e.g. '11110000' = view, create, update and delete.
CREATE TABLE tm.tm_mst_role_permission (
    vch_role_permission_id  VARCHAR(15)   NOT NULL,
    vch_role_id             VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_role (vch_role_id),
    vch_permission_id       VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_permission (vch_permission_id),
    chr_access_rights       CHAR(8)       NOT NULL DEFAULT '10000000' CHECK (chr_access_rights ~ '^[01]{8}$'),
    dtt_created_date        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by          VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date       TIMESTAMPTZ,
    vch_modified_by         VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt        BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_role_permission PRIMARY KEY (vch_role_permission_id)
);
CREATE UNIQUE INDEX uq_tm_mst_role_permission ON tm.tm_mst_role_permission (vch_role_id, vch_permission_id) WHERE bol_rec_actv_stt;
CREATE INDEX idx_tm_mst_role_permission_perm ON tm.tm_mst_role_permission (vch_permission_id);
CREATE TRIGGER trg_tm_mst_role_permission_key BEFORE INSERT ON tm.tm_mst_role_permission
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_role_permission_id', 'RP');
CREATE TRIGGER trg_tm_mst_role_permission_audit BEFORE UPDATE ON tm.tm_mst_role_permission
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

-- -----------------------------------------------------------------------------
-- Business masters
-- -----------------------------------------------------------------------------

CREATE TABLE tm.tm_mst_bank (
    vch_bank_id             VARCHAR(15)   NOT NULL,
    vch_bank_name           VARCHAR(100)  NOT NULL,
    vch_bank_display_name   VARCHAR(50),
    vch_bank_reg_no         VARCHAR(255),
    vch_bank_address        VARCHAR(255),
    dtt_created_date        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by          VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date       TIMESTAMPTZ,
    vch_modified_by         VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt        BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_bank PRIMARY KEY (vch_bank_id)
);
CREATE UNIQUE INDEX uq_tm_mst_bank_name ON tm.tm_mst_bank (vch_bank_name) WHERE bol_rec_actv_stt;
CREATE TRIGGER trg_tm_mst_bank_key BEFORE INSERT ON tm.tm_mst_bank
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_bank_id', 'BK');
CREATE TRIGGER trg_tm_mst_bank_audit BEFORE UPDATE ON tm.tm_mst_bank
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

CREATE TABLE tm.tm_mst_customer (
    vch_customer_id     VARCHAR(15)    NOT NULL,
    vch_customer_code   VARCHAR(30)    NOT NULL,
    vch_customer_name   VARCHAR(100)   NOT NULL,
    vch_email           VARCHAR(100),
    vch_contact_no      VARCHAR(20),
    vch_address         VARCHAR(255),
    vch_remark          VARCHAR(4000),
    dtt_created_date    TIMESTAMPTZ    NOT NULL DEFAULT now(),
    vch_created_by      VARCHAR(15)    NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date   TIMESTAMPTZ,
    vch_modified_by     VARCHAR(15)    REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt    BOOLEAN        NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_customer PRIMARY KEY (vch_customer_id)
);
CREATE UNIQUE INDEX uq_tm_mst_customer_code ON tm.tm_mst_customer (upper(vch_customer_code)) WHERE bol_rec_actv_stt;
CREATE INDEX idx_tm_mst_customer_name ON tm.tm_mst_customer (vch_customer_name);
CREATE TRIGGER trg_tm_mst_customer_key BEFORE INSERT ON tm.tm_mst_customer
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_customer_id', 'CS');
CREATE TRIGGER trg_tm_mst_customer_audit BEFORE UPDATE ON tm.tm_mst_customer
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

CREATE TABLE tm.tm_mst_data_entry_source (
    vch_data_entry_source_id  VARCHAR(15)   NOT NULL,
    vch_source_code           VARCHAR(10)   NOT NULL,
    vch_source_desc           VARCHAR(100),
    dtt_created_date          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by            VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date         TIMESTAMPTZ,
    vch_modified_by           VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt          BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_data_entry_source PRIMARY KEY (vch_data_entry_source_id),
    CONSTRAINT uq_tm_mst_data_entry_source_code UNIQUE (vch_source_code)
);
CREATE TRIGGER trg_tm_mst_data_entry_source_key BEFORE INSERT ON tm.tm_mst_data_entry_source
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_data_entry_source_id', 'DS');
CREATE TRIGGER trg_tm_mst_data_entry_source_audit BEFORE UPDATE ON tm.tm_mst_data_entry_source
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

CREATE TABLE tm.tm_mst_blacklisted (
    vch_blacklisted_id    VARCHAR(15)   NOT NULL,
    vch_blacklisted_name  VARCHAR(100)  NOT NULL,
    vch_remark_1          VARCHAR(255),
    vch_remark_2          VARCHAR(255),
    dtt_created_date      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by        VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date     TIMESTAMPTZ,
    vch_modified_by       VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt      BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_blacklisted PRIMARY KEY (vch_blacklisted_id)
);
CREATE UNIQUE INDEX uq_tm_mst_blacklisted_name ON tm.tm_mst_blacklisted (vch_blacklisted_name) WHERE bol_rec_actv_stt;
CREATE TRIGGER trg_tm_mst_blacklisted_key BEFORE INSERT ON tm.tm_mst_blacklisted
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_blacklisted_id', 'BL');
CREATE TRIGGER trg_tm_mst_blacklisted_audit BEFORE UPDATE ON tm.tm_mst_blacklisted
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

CREATE TABLE tm.tm_mst_suspicious (
    vch_suspicious_id     VARCHAR(15)   NOT NULL,
    vch_suspicious_name   VARCHAR(100)  NOT NULL,
    vch_remark_1          VARCHAR(255),
    vch_remark_2          VARCHAR(255),
    dtt_created_date      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by        VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date     TIMESTAMPTZ,
    vch_modified_by       VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt      BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_mst_suspicious PRIMARY KEY (vch_suspicious_id)
);
CREATE UNIQUE INDEX uq_tm_mst_suspicious_name ON tm.tm_mst_suspicious (vch_suspicious_name) WHERE bol_rec_actv_stt;
CREATE TRIGGER trg_tm_mst_suspicious_key BEFORE INSERT ON tm.tm_mst_suspicious
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_suspicious_id', 'SP');
CREATE TRIGGER trg_tm_mst_suspicious_audit BEFORE UPDATE ON tm.tm_mst_suspicious
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

-- -----------------------------------------------------------------------------
-- Transactions
-- -----------------------------------------------------------------------------

-- One row per saved upload or manual-entry session.
CREATE TABLE tm.tm_trn_import_batch (
    vch_import_batch_id       VARCHAR(15)   NOT NULL,
    vch_data_entry_source_id  VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_data_entry_source (vch_data_entry_source_id),
    vch_bank_id               VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_bank (vch_bank_id),
    vch_customer_id           VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_customer (vch_customer_id),
    vch_file_name             VARCHAR(255),
    vch_account_no            VARCHAR(30),
    dtt_statement_date        DATE,
    num_total_rows            INTEGER       NOT NULL DEFAULT 0,
    dtt_created_date          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    vch_created_by            VARCHAR(15)   NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date         TIMESTAMPTZ,
    vch_modified_by           VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt          BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_trn_import_batch PRIMARY KEY (vch_import_batch_id)
);
CREATE INDEX idx_tm_trn_import_batch_file ON tm.tm_trn_import_batch (vch_file_name);
CREATE TRIGGER trg_tm_trn_import_batch_key BEFORE INSERT ON tm.tm_trn_import_batch
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_import_batch_id', 'IB');
CREATE TRIGGER trg_tm_trn_import_batch_audit BEFORE UPDATE ON tm.tm_trn_import_batch
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

CREATE TABLE tm.tm_trn_transaction (
    vch_transaction_id        VARCHAR(15)    NOT NULL,
    vch_import_batch_id       VARCHAR(15)    REFERENCES tm.tm_trn_import_batch (vch_import_batch_id),
    vch_bank_id               VARCHAR(15)    NOT NULL REFERENCES tm.tm_mst_bank (vch_bank_id),
    vch_data_entry_source_id  VARCHAR(15)    NOT NULL REFERENCES tm.tm_mst_data_entry_source (vch_data_entry_source_id),
    vch_customer_id           VARCHAR(15)    NOT NULL REFERENCES tm.tm_mst_customer (vch_customer_id),
    vch_agent_user_id         VARCHAR(15)    NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    vch_account_no            VARCHAR(30),
    dtt_statement_date        DATE,
    dtt_transaction_date      DATE           NOT NULL,
    vch_trn_desc_1            VARCHAR(1000),
    vch_trn_desc_2            VARCHAR(4000),
    vch_target_name           VARCHAR(255),  -- counterparty ("Target Audience")
    num_credit_amount         NUMERIC(18,2)  NOT NULL DEFAULT 0,
    num_debit_amount          NUMERIC(18,2)  NOT NULL DEFAULT 0,
    num_statement_balance     NUMERIC(18,2)  NOT NULL DEFAULT 0,
    vch_file_name             VARCHAR(255),
    bol_printed_stt           BOOLEAN        NOT NULL DEFAULT FALSE,
    dtt_created_date          TIMESTAMPTZ    NOT NULL DEFAULT now(),
    vch_created_by            VARCHAR(15)    NOT NULL REFERENCES tm.tm_mst_user (vch_user_id),
    dtt_modified_date         TIMESTAMPTZ,
    vch_modified_by           VARCHAR(15)    REFERENCES tm.tm_mst_user (vch_user_id),
    bol_rec_actv_stt          BOOLEAN        NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_tm_trn_transaction PRIMARY KEY (vch_transaction_id)
);
CREATE INDEX idx_tm_trn_transaction_batch    ON tm.tm_trn_transaction (vch_import_batch_id);
CREATE INDEX idx_tm_trn_transaction_bank     ON tm.tm_trn_transaction (vch_bank_id);
CREATE INDEX idx_tm_trn_transaction_customer ON tm.tm_trn_transaction (vch_customer_id);
CREATE INDEX idx_tm_trn_transaction_agent    ON tm.tm_trn_transaction (vch_agent_user_id);
CREATE INDEX idx_tm_trn_transaction_date     ON tm.tm_trn_transaction (dtt_transaction_date);
CREATE INDEX idx_tm_trn_transaction_file     ON tm.tm_trn_transaction (vch_file_name);
CREATE TRIGGER trg_tm_trn_transaction_key BEFORE INSERT ON tm.tm_trn_transaction
    FOR EACH ROW EXECUTE FUNCTION tm.tm_set_combination_key('vch_transaction_id', 'TR');
CREATE TRIGGER trg_tm_trn_transaction_audit BEFORE UPDATE ON tm.tm_trn_transaction
    FOR EACH ROW EXECUTE FUNCTION tm.tm_touch_audit_columns();

-- -----------------------------------------------------------------------------
-- History
-- -----------------------------------------------------------------------------

CREATE TABLE tm.tm_his_login_log (
    num_login_log_id    BIGINT GENERATED ALWAYS AS IDENTITY,
    vch_login_id        VARCHAR(100)  NOT NULL,
    vch_user_id         VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    bol_success_ind     BOOLEAN       NOT NULL,
    vch_failure_reason  VARCHAR(100),
    vch_ip_address      VARCHAR(64),
    vch_user_agent      VARCHAR(255),
    dtt_login_date      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_tm_his_login_log PRIMARY KEY (num_login_log_id)
);
CREATE INDEX idx_tm_his_login_log_user ON tm.tm_his_login_log (vch_user_id, dtt_login_date);

CREATE TABLE tm.tm_his_audit_log (
    num_audit_log_id    BIGINT GENERATED ALWAYS AS IDENTITY,
    vch_user_id         VARCHAR(15)   REFERENCES tm.tm_mst_user (vch_user_id),
    vch_action          VARCHAR(30)   NOT NULL,   -- CREATE, UPDATE, DELETE, IMPORT, EXPORT, ...
    vch_entity_name     VARCHAR(50)   NOT NULL,   -- table the action applied to
    vch_entity_id       VARCHAR(50),
    jsn_change_detail   JSONB,
    dtt_action_date     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_tm_his_audit_log PRIMARY KEY (num_audit_log_id)
);
CREATE INDEX idx_tm_his_audit_log_entity ON tm.tm_his_audit_log (vch_entity_name, vch_entity_id);
CREATE INDEX idx_tm_his_audit_log_date ON tm.tm_his_audit_log (dtt_action_date);
