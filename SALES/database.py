import sqlite3
import datetime
import random

def init_db():
    conn = sqlite3.connect('sales.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            creator_id INTEGER DEFAULT 1
        )
    ''')

    # Add a default user if not exists
    cursor.execute("SELECT * FROM users WHERE employee_id = '1'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (employee_id, password, name, role, creator_id) VALUES (?, ?, ?, ?, ?)", ('1', '1', 'Frank', 'system_admin', 1))

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
        cursor.executemany("INSERT INTO customers (name, contact_person, phone, email, creator_id) VALUES (?, ?, ?, ?, ?)", sample_customers)


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
        cursor.executemany("INSERT INTO orders (customer_id, order_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)", sample_orders)


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
        cursor.executemany("INSERT INTO quotes (customer_id, quote_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)", sample_quotes)


    conn.commit()
    conn.close()

def populate_with_more_data():
    conn = sqlite3.connect('sales.db')
    cursor = conn.cursor()

    # Check if we need to populate
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] >= 20:
        conn.close()
        return # Data already populated

    # Get existing user IDs for creator_id
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    if not user_ids: # Fallback if no users exist (shouldn't happen with default user)
        user_ids = [1] 

    # --- Generate Customers ---
    customer_first_names = ['宏達', '聯發', '台達', '中華', '遠傳', '台灣', '國泰', '富邦', '玉山', '中信']
    customer_last_names = ['電子', '科技', '實業', '國際', '開發', '控股', '金控', '商業銀行', '股份有限公司', '有限公司']
    contact_surnames = ['陳', '林', '黃', '張', '李', '王', '吳', '劉', '蔡', '楊']
    contact_titles = ['先生', '小姐', '經理', '總監']
    
    new_customers = []
    for i in range(20):
        name = f"{random.choice(customer_first_names)}{random.choice(customer_last_names)}"
        contact = f"{random.choice(contact_surnames)}{random.choice(contact_titles)}"
        phone = f"09{random.randint(10, 88)}-{random.randint(100000, 999999)}"
        email = f"contact{i}@example.com"
        creator_id = random.choice(user_ids)
        new_customers.append((name, contact, phone, email, creator_id))
    cursor.executemany("INSERT INTO customers (name, contact_person, phone, email, creator_id) VALUES (?, ?, ?, ?, ?)", new_customers)
    
    # Get all customer IDs
    cursor.execute("SELECT id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]

    # --- Generate Quotes ---
    quote_statuses = ['草稿', '已發送', '已接受', '已拒絕']
    new_quotes = []
    for _ in range(20):
        customer_id = random.choice(customer_ids)
        quote_date = (datetime.date.today() - datetime.timedelta(days=random.randint(0, 365))).isoformat()
        amount = round(random.uniform(5000, 100000), 2)
        status = random.choice(quote_statuses)
        creator_id = random.choice(user_ids)
        new_quotes.append((customer_id, quote_date, amount, status, creator_id))
    cursor.executemany("INSERT INTO quotes (customer_id, quote_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)", new_quotes)

    # --- Generate Orders ---
    order_statuses = ['已付款', '未付款', '取消']
    new_orders = []
    for _ in range(20):
        customer_id = random.choice(customer_ids)
        order_date = (datetime.date.today() - datetime.timedelta(days=random.randint(0, 365))).isoformat()
        amount = round(random.uniform(10000, 200000), 2)
        status = random.choice(order_statuses)
        creator_id = random.choice(user_ids)
        new_orders.append((customer_id, order_date, amount, status, creator_id))
    cursor.executemany("INSERT INTO orders (customer_id, order_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)", new_orders)

    conn.commit()
    conn.close()

def migrate_db():
    conn = sqlite3.connect('sales.db')
    cursor = conn.cursor()

    # Add creator_id to users table if not exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'creator_id' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN creator_id INTEGER DEFAULT 1")
        cursor.execute("UPDATE users SET creator_id = 1 WHERE creator_id IS NULL") # Set existing users to admin
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'role' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        cursor.execute("UPDATE users SET role = 'admin' WHERE employee_id = '1'") # Set admin role for employee_id '1'
        cursor.execute("UPDATE users SET role = 'user' WHERE role IS NULL") # Set default role for others

    # Add creator_id to customers table if not exists
    cursor.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'creator_id' not in columns:
        cursor.execute("ALTER TABLE customers ADD COLUMN creator_id INTEGER DEFAULT 1")
        cursor.execute("UPDATE customers SET creator_id = 1 WHERE creator_id IS NULL") # Set existing customers to admin

    # Add creator_id to orders table if not exists
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'creator_id' not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN creator_id INTEGER DEFAULT 1")
        cursor.execute("UPDATE orders SET creator_id = 1 WHERE creator_id IS NULL") # Set existing orders to admin

    # Add creator_id to quotes table if not exists
    cursor.execute("PRAGMA table_info(quotes)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'creator_id' not in columns:
        cursor.execute("ALTER TABLE quotes ADD COLUMN creator_id INTEGER DEFAULT 1")
        cursor.execute("UPDATE quotes SET creator_id = 1 WHERE creator_id IS NULL") # Set existing quotes to admin

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    migrate_db()
    populate_with_more_data()
