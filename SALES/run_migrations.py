import database
database.init_db()
database.migrate_db()
print("Database migration complete.")