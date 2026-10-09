-- Cleanup script to remove synced Azure AD groups from the database
-- This removes all system groups (is_system=true) except "Administrators"
--
-- Usage:
--   psql -h <host> -U <user> -d <database> -f backend/cleanup_azure_ad_groups.sql
--
-- For UAT environment:
--   First get the database credentials from the Kubernetes secret or environment
--   Then run the script

-- Start a transaction for safety
BEGIN;

-- Show what will be deleted (for verification)
SELECT
    '=== Groups to be deleted ===' as info;

SELECT
    id,
    name,
    is_system,
    created_at,
    (SELECT COUNT(*) FROM group_memberships WHERE group_id = groups.id) as member_count
FROM groups
WHERE is_system = true
  AND name != 'Administrators'
ORDER BY name;

-- Show membership count
SELECT
    '=== Membership records to be deleted ===' as info;

SELECT COUNT(*) as total_memberships_to_delete
FROM group_memberships
WHERE group_id IN (
    SELECT id FROM groups
    WHERE is_system = true
      AND name != 'Administrators'
);

-- Ask user to review before uncommenting the DELETE statements
-- UNCOMMENT THE LINES BELOW AFTER REVIEWING THE OUTPUT ABOVE

-- Delete Azure AD synced groups (memberships will cascade delete)
-- DELETE FROM groups
-- WHERE is_system = true
--   AND name != 'Administrators';

-- Show final state
-- SELECT
--     '=== Remaining system groups ===' as info;
--
-- SELECT id, name, is_system, created_at
-- FROM groups
-- WHERE is_system = true
-- ORDER BY name;

-- COMMIT or ROLLBACK after reviewing
-- COMMIT;

ROLLBACK;  -- Remove this line and run the script again after reviewing
