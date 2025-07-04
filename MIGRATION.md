# Database migration for unique constraints

The `sources` and `filtered_users` tables now enforce uniqueness.

## Steps

1. **Backup your database** before making changes.
2. Remove any duplicate records:
   ```sql
   DELETE FROM sources
     WHERE rowid NOT IN (
       SELECT MIN(rowid) FROM sources GROUP BY tg_id, chat_id, topic_id
   );
   DELETE FROM filtered_users
     WHERE rowid NOT IN (
       SELECT MIN(rowid) FROM filtered_users GROUP BY tg_id, user_id
   );
   ```
3. Create the new unique indexes:
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_unique
     ON sources(tg_id, chat_id, topic_id);
   CREATE UNIQUE INDEX IF NOT EXISTS idx_filtered_users_unique
     ON filtered_users(tg_id, user_id);
   ```
4. Restart the bot.

New installations automatically create tables with these constraints.
