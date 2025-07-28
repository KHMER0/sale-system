import sqlite3
import os
import database

def test_database_connection():
    """Tests if the database file exists and can be connected to."""
    assert os.path.exists("sales.db"), f"Database file 'sales.db' not found."
    try:
        conn = sqlite3.connect("sales.db")
        conn.close()
        print("Database connection test passed.")
        return True
    except sqlite3.Error as e:
        print(f"Database connection test failed: {e}")
        return False

def test_user_data():
    """Tests if the default user data is present and correct."""
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name, password FROM users WHERE employee_id = '1'")
        user = cursor.fetchone()
        assert user is not None, "User with employee_id '1' not found."
        name, password = user
        assert name == "Frank", f"Expected user name 'Frank', but got ''{name}''_"
        assert password == "1", f"Expected password '1', but got ''{password}''_"
        print("User data test passed.")
        return True
    except (sqlite3.Error, AssertionError) as e:
        print(f"User data test failed: {e}")
        return False
    finally:
        conn.close()

def test_customer_data():
    """Tests if sample customer data exists."""
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM customers")
        count = cursor.fetchone()[0]
        assert count > 0, "No data found in 'customers' table."
        print(f"Customer data test passed: Found {count} records.")
        return True
    except (sqlite3.Error, AssertionError) as e:
        print(f"Customer data test failed: {e}")
        return False
    finally:
        conn.close()

def test_order_data():
    """Tests if sample order data exists."""
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        assert count > 0, "No data found in 'orders' table."
        print(f"Order data test passed: Found {count} records.")
        return True
    except (sqlite3.Error, AssertionError) as e:
        print(f"Order data test failed: {e}")
        return False
    finally:
        conn.close()

def test_quote_data():
    """Tests if sample quote data exists."""
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM quotes")
        count = cursor.fetchone()[0]
        assert count > 0, "No data found in 'quotes' table."
        print(f"Quote data test passed: Found {count} records.")
        return True
    except (sqlite3.Error, AssertionError) as e:
        print(f"Quote data test failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Initializing database for test...")
    database.init_db()
    print("\nRunning database tests...")
    
    tests = [
        test_database_connection,
        test_user_data,
        test_customer_data,
        test_order_data,
        test_quote_data
    ]
    
    all_passed = True
    for test_func in tests:
        if not test_func():
            all_passed = False
            
    print("\n--------------------")
    if all_passed:
        print("All database tests passed successfully!")
    else:
        print("Some database tests failed.")
    print("--------------------")
