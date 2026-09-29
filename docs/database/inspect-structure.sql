-- Read-only metadata lookup. Connect to the authorized test database first.
-- Replace the schema/table literals when reviewing another environment.
-- TABLE_ROWS is an estimate; this does not read member or order details.
START TRANSACTION READ ONLY;
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, TABLE_ROWS, TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA IN ('fat', 'orders')
ORDER BY TABLE_SCHEMA, TABLE_NAME;
SELECT TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME,
       COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE (TABLE_SCHEMA = 'fat' AND TABLE_NAME IN
  ('fb_members', 'fb_members_login_log', 'fb_deposits', 'fb_withdraws',
   'fb_members_balance', 'fb_members_balance_new', 'fb_balance_transaction',
   'fb_report_basic_member', 'fb_report_balance'))
   OR (TABLE_SCHEMA = 'orders' AND TABLE_NAME IN
  ('tbl_game_record', 'tbl_game_record_sport'))
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE (TABLE_SCHEMA = 'fat' AND TABLE_NAME IN
  ('fb_members', 'fb_members_login_log', 'fb_deposits', 'fb_withdraws',
   'fb_members_balance', 'fb_members_balance_new', 'fb_balance_transaction'))
   OR (TABLE_SCHEMA = 'orders' AND TABLE_NAME IN
  ('tbl_game_record', 'tbl_game_record_sport'))
ORDER BY TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
ROLLBACK;
