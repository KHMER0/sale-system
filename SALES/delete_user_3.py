import sqlite3

conn = sqlite3.connect('sales.db')
cursor = conn.cursor()

try:
    cursor.execute("DELETE FROM users WHERE employee_id = '3'")
    conn.commit()
    print("User with employee_id '3' deleted successfully.")
except Exception as e:
    print(f"Error deleting user: {e}")
finally:
    conn.close()