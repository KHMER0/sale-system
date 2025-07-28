import sqlite3

conn = sqlite3.connect('sales.db')
cursor = conn.cursor()

cursor.execute("SELECT role FROM users WHERE employee_id = '1'")
result = cursor.fetchone()

if result:
    print(f"Role for employee_id '1': {result[0]}")
else:
    print("Employee_id '1' not found.")

conn.close()