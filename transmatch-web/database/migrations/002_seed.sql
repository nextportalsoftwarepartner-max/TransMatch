-- =============================================================================
-- Reference data every installation needs.
-- =============================================================================

-- System administrator. Initial password: @@Adm123  (bcrypt) - change it after
-- the first login. The account creates itself, so it is its own VCH_CREATED_BY.
DO $$
DECLARE
    v_user_id VARCHAR(15) := tm.tm_generate_combination_key('US');
BEGIN
    INSERT INTO tm.tm_mst_user (
        vch_user_id, vch_login_id, vch_user_name, vch_password_hash, vch_email,
        bol_bypass_ind, bol_no_delete_ind, vch_created_by
    ) VALUES (
        v_user_id, 'superuser', 'System Administrator',
        '$2b$12$VDaJAycAeKAnsxqHTPsrCuhPNN0BKe.nqT98ou2nE7XuigpOuAVLG',
        'transmatch_superuser@gmail.com',
        TRUE, TRUE, v_user_id
    );
END;
$$;

-- Status codes
INSERT INTO tm.tm_mst_status (vch_status_domain, chr_status_code, vch_status_name, vch_created_by)
SELECT d.domain, s.code, s.name, u.vch_user_id
FROM (VALUES ('USER'), ('GROUP'), ('ROLE')) AS d (domain)
CROSS JOIN (VALUES ('A', 'Active'), ('I', 'Deactivated')) AS s (code, name)
CROSS JOIN tm.tm_mst_user u
WHERE u.vch_login_id = 'superuser';

-- Super group and role (protected)
INSERT INTO tm.tm_mst_group (vch_group_name, vch_group_desc, bol_no_delete_ind, vch_created_by)
SELECT 'SUPERGROUP', 'Super user group', TRUE, vch_user_id
FROM tm.tm_mst_user WHERE vch_login_id = 'superuser';

INSERT INTO tm.tm_mst_role (vch_group_id, vch_role_name, vch_role_desc, bol_no_delete_ind, vch_created_by)
SELECT g.vch_group_id, 'SUPERROLE', 'Super user role', TRUE, u.vch_user_id
FROM tm.tm_mst_group g, tm.tm_mst_user u
WHERE g.vch_group_name = 'SUPERGROUP' AND u.vch_login_id = 'superuser';

INSERT INTO tm.tm_mst_user_role (vch_user_id, vch_role_id, vch_created_by)
SELECT u.vch_user_id, r.vch_role_id, u.vch_user_id
FROM tm.tm_mst_user u, tm.tm_mst_role r
WHERE u.vch_login_id = 'superuser' AND r.vch_role_name = 'SUPERROLE';

-- Data entry sources
INSERT INTO tm.tm_mst_data_entry_source (vch_source_code, vch_source_desc, vch_created_by)
SELECT s.code, s.descr, u.vch_user_id
FROM (VALUES ('MI', 'Manual Input'), ('PU', 'PDF Upload'), ('SYS', 'System Generated')) AS s (code, descr)
CROSS JOIN tm.tm_mst_user u
WHERE u.vch_login_id = 'superuser';

-- Permissions: main menus first, then the screens under each
INSERT INTO tm.tm_mst_permission (vch_permission_code, vch_permission_name, vch_permission_desc, bol_main_menu_ind, num_display_order, vch_created_by)
SELECT p.code, p.name, p.descr, TRUE, p.ord, u.vch_user_id
FROM (VALUES
    ('TRN', 'Transaction',    'Transaction Main Menu',      1),
    ('ADM', 'Administration', 'Administration Main Menu',   2),
    ('RPT', 'Report/Enquiry', 'Reporting and Search Menu',  3)
) AS p (code, name, descr, ord)
CROSS JOIN tm.tm_mst_user u
WHERE u.vch_login_id = 'superuser'
ORDER BY p.ord;

INSERT INTO tm.tm_mst_permission (vch_permission_code, vch_permission_name, vch_permission_desc, vch_parent_permission_id, num_display_order, vch_created_by)
SELECT p.code, p.name, p.descr, parent.vch_permission_id, p.ord, u.vch_user_id
FROM (VALUES
    ('TRN', 'TRN_PDF_UPLOAD',       'Docx Upload',               'Transaction Upload by PDF',                1),
    ('TRN', 'TRN_MANUAL_INPUT',     'Manual Input',              'Manual Transaction Entry',                 2),
    ('TRN', 'TRN_IMAGE_UPLOAD',     'Image Upload',              'Transaction Upload by Image (OCR feature)', 3),
    ('TRN', 'TRN_DATA_ENRICHMENT',  'Data Enrichment',           'Edit Transaction by Data Enrichment',      4),
    ('ADM', 'ADM_USER_GROUP',       'User Group',                'User Group Management',                    1),
    ('ADM', 'ADM_USER_ROLE',        'User Role',                 'User Role Management',                     2),
    ('ADM', 'ADM_USER_RIGHTS',      'User Rights',               'Role Permission Assignment',               3),
    ('ADM', 'ADM_USER_PROFILE',     'User Profile',              'User Profile Maintenance',                 4),
    ('ADM', 'ADM_CUSTOMER_PROFILE', 'Customer Profile',          'Customer Profile Maintenance',             5),
    ('ADM', 'ADM_BANK_PROFILE',     'Bank Profile',              'Bank Profile Maintenance',                 6),
    ('ADM', 'ADM_BLACKLISTED',      'Blacklisted',               'Blacklisted Customer Setup',               7),
    ('ADM', 'ADM_SUSPICIOUS',       'Suspicious',                'Suspicious Customer Setup',                8),
    ('RPT', 'RPT_ENQUIRY',          'Enquiry / Generate Report', 'Search and Reporting Module',              1),
    ('RPT', 'RPT_KPI_REVIEW',       'KPI Review',                'View and Monitor User KPI Statistic',      2)
) AS p (parent_code, code, name, descr, ord)
JOIN tm.tm_mst_permission parent ON parent.vch_permission_code = p.parent_code
CROSS JOIN tm.tm_mst_user u
WHERE u.vch_login_id = 'superuser'
ORDER BY parent.num_display_order, p.ord;

-- The super role holds every permission with view, create, update and delete rights
INSERT INTO tm.tm_mst_role_permission (vch_role_id, vch_permission_id, chr_access_rights, vch_created_by)
SELECT r.vch_role_id, p.vch_permission_id, '11110000', u.vch_user_id
FROM tm.tm_mst_role r, tm.tm_mst_permission p, tm.tm_mst_user u
WHERE r.vch_role_name = 'SUPERROLE' AND u.vch_login_id = 'superuser'
ORDER BY p.vch_permission_id;
