import sqlite3
import datetime
import random
import os

# 統一管理 DB 路徑
DB_PATH = os.environ.get("DB_PATH", "/tmp/sales.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            creator_id INTEGER DEFAULT 1
        )
    ''')

    # Add a default system_admin user if not exists
    cursor.execute("SELECT * FROM users WHERE employee_id = '1'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (employee_id, password, name, role, creator_id) VALUES (?, ?, ?, ?, ?)",
            ('1', '1', 'Frank', 'system_admin', 1)
        )

    # Create customers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            creator_id INTEGER DEFAULT 1
        )
    ''')

    # Add sample customers
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] < 2:
        sample_customers = [
            ('TechCorp', 'Alice', '123-456-7890', 'alice@techcorp.com', 1),
            ('Innovate Inc.', 'Bob', '098-765-4321', 'bob@innovateinc.com', 1)
        ]
        cursor.executemany(
            "INSERT INTO customers (name, contact_person, phone, email, creator_id) VALUES (?, ?, ?, ?, ?)",
            sample_customers
        )

    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            order_date TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            creator_id INTEGER DEFAULT 1,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    # Add sample orders
    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] < 2:
        sample_orders = [
            (1, datetime.date(2025, 7, 1).isoformat(), 1500.00, 'Completed', 1),
            (2, datetime.date(2025, 7, 5).isoformat(), 3000.50, 'Pending', 1)
        ]
        cursor.executemany(
            "INSERT INTO orders (customer_id, order_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)",
            sample_orders
        )

    # Create quotes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            quote_date TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            creator_id INTEGER DEFAULT 1,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')

    # Add sample quotes
    cursor.execute("SELECT COUNT(*) FROM quotes")
    if cursor.fetchone()[0] < 2:
        sample_quotes = [
            (1, datetime.date(2025, 6, 20).isoformat(), 1400.00, 'Accepted', 1),
            (2, datetime.date(2025, 7, 2).isoformat(), 2900.75, 'Sent', 1)
        ]
        cursor.executemany(
            "INSERT INTO quotes (customer_id, quote_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)",
            sample_quotes
        )

    conn.commit()
    conn.close()

def populate_with_more_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 如果記錄已經超過 20 筆，就不用再填入
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] >= 20:
        conn.close()
        return

    # 取得所有 user id
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()] or [1]

    # 產生額外客戶
    customer_first = ['宏達','聯發','台達','中華','遠傳','台灣','國泰','富邦','玉山','中信']
    customer_last  = ['電子','科技','實業','國際','開發','控股','金控','商業銀行','股份有限公司','有限公司']
    contact_sur   = ['陳','林','黃','張','李','王','吳','劉','蔡','楊']
    contact_title = ['先生','小姐','經理','總監']
    new_customers = []
    for i in range(20):
        name = random.choice(customer_first) + random.choice(customer_last)
        contact = random.choice(contact_sur) + random.choice(contact_title)
        phone   = f"09{random.randint(10,88)}-{random.randint(100000,999999)}"
        email   = f"contact{i}@example.com"
        creator = random.choice(user_ids)
        new_customers.append((name, contact, phone, email, creator))
    cursor.executemany(
        "INSERT INTO customers (name, contact_person, phone, email, creator_id) VALUES (?, ?, ?, ?, ?)",
        new_customers
    )

    # 其他 quote & order 生成省略，原邏輯不變
    # …

    conn.commit()
    conn.close()

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 檢查 users 欄位
    cursor.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'creator_id' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN creator_id INTEGER DEFAULT 1")
    if 'role' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")

    # customers / orders / quotes 同理
    for table in ('customers','orders','quotes'):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [col[1] for col in cursor.fetchall()]
        if 'creator_id' not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN creator_id INTEGER DEFAULT 1")

    conn.commit()
    conn.close()
