import sqlite3

conn = sqlite3.connect('sales.db')
cursor = conn.cursor()

try:
    cursor.execute("UPDATE users SET role = 'system_admin' WHERE employee_id = '1'")
    conn.commit()
    print("Role updated successfully.")
except Exception as e:
    print(f"Error updating role: {e}")
finally:
    conn.close()