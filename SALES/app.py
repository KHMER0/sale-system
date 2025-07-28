from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import os
import sqlite3
import database
from chatbot import get_chatbot_response # Import the chatbot function

# Initialize the database
database.init_db()
database.migrate_db()
database.populate_with_more_data()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['CSS_VERSION'] = 1 # Increment this number to force CSS refresh


def get_db_connection():
    conn = sqlite3.connect('sales.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/chatbot_api', methods=['POST'])
def chatbot_api():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    # Get conversation history from session, or initialize if not present
    conversation_history = session.get('chatbot_history', [])

    # Add user message to history
    conversation_history.append({'role': 'user', 'content': user_message})

    # Get chatbot response
    bot_response = get_chatbot_response(user_message)

    # Add bot response to history
    conversation_history.append({'role': 'bot', 'content': bot_response})

    # Store updated history back in session
    session['chatbot_history'] = conversation_history

    return jsonify({'response': bot_response})

@app.route('/get_chatbot_history', methods=['GET'])
def get_chatbot_history():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conversation_history = session.get('chatbot_history', [])

    if not conversation_history:
        # Add introductory message if history is empty
        intro_message = "您好！我是您的銷售管理系統助理。我可以協助您查詢客戶、訂單、報價單等銷售資料，並引導您使用系統功能。如果您需要我協助執行某些操作（例如建立或更新資料），請務必在執行前給予我明確的確認。請問有什麼可以為您服務的嗎？"
        conversation_history.append({'role': 'bot', 'content': intro_message})
        session['chatbot_history'] = conversation_history # Save the updated history to session

    return jsonify({'history': conversation_history})


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE employee_id = ? AND password = ?', (employee_id, password)).fetchone()
        conn.close()
        
        if user:
            session['user'] = dict(user)
            session['employee_id'] = user['employee_id']
            session['role'] = user['role'] # Store user's role in session
            return redirect(url_for('dashboard'))
        else:
            # 在 login 函數中的錯誤提示
            flash('使用者名稱或密碼錯誤')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    current_date = datetime.now().strftime('%Y年%m月%d日')
    return render_template('dashboard.html', 
                         user=session['user'],
                         current_date=current_date)

@app.route('/customers')
def customers():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search')
    
    conn = get_db_connection()
    
    base_query = "SELECT * FROM customers"
    params = []
    
    if search_query:
        if "WHERE" in base_query:
            base_query += " AND (name LIKE ? OR contact_person LIKE ? OR phone LIKE ? OR email LIKE ?)"
        else:
            base_query += " WHERE (name LIKE ? OR contact_person LIKE ? OR phone LIKE ? OR email LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
    
    customers = conn.execute(base_query, params).fetchall()
    conn.close()
    
    return render_template('customers.html', customers=customers, search_query=search_query)

@app.route('/customers/add', methods=['POST'])
def add_customer():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    name = request.form.get('name')
    contact_person = request.form.get('contact_person')
    phone = request.form.get('phone')
    email = request.form.get('email')
    creator_id = session['user']['id'] # Set creator_id to current user's ID
    
    conn = get_db_connection()
    conn.execute('INSERT INTO customers (name, contact_person, phone, email, creator_id) VALUES (?, ?, ?, ?, ?)',
                 (name, contact_person, phone, email, creator_id))
    conn.commit()
    conn.close()
    
    flash('客戶已成功新增')
    return redirect(url_for('customers'))

@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Fetch the customer to check ownership
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    if customer is None:
        flash('找不到該客戶')
        conn.close()
        return redirect(url_for('customers'))
    
    # Permission check: Only system_admin or administrator or creator can edit
    if not is_system_admin() and not is_administrator() and customer['creator_id'] != session['user']['id']:
        flash('您沒有權限修改此客戶資料。')
        conn.close()
        return redirect(url_for('customers'))

    if request.method == 'POST':
        name = request.form.get('name')
        contact_person = request.form.get('contact_person')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        conn.execute('UPDATE customers SET name = ?, contact_person = ?, phone = ?, email = ? WHERE id = ?',
                     (name, contact_person, phone, email, customer_id))
        conn.commit()
        conn.close()
        
        flash('客戶已成功更新')
        return redirect(url_for('customers'))
    
    conn.close() # Close connection after fetching for GET request
    return render_template('edit_customer.html', customer=customer)

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # Fetch the customer to check ownership
    customer = conn.execute('SELECT creator_id FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    if customer is None:
        flash('找不到該客戶')
        conn.close()
        return redirect(url_for('customers'))
    
    # Permission check: Only system_admin or administrator or creator can delete
    if not is_system_admin() and not is_administrator() and customer['creator_id'] != session['user']['id']:
        flash('您沒有權限刪除此客戶資料。')
        conn.close()
        return redirect(url_for('customers'))

    conn.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()
    
    flash('客戶已成功刪除')
    return redirect(url_for('customers'))

@app.route('/orders')
def orders():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search')
    
    conn = get_db_connection()
    
    base_query = "SELECT o.*, c.name as customer_name FROM orders o JOIN customers c ON o.customer_id = c.id"
    params = []

    if not is_system_admin() and not is_administrator(): # Administrators can view all orders
        base_query += " WHERE o.creator_id = ?"
        params.append(session['user']['id'])
    
    if search_query:
        if "WHERE" in base_query:
            base_query += " AND (o.id LIKE ? OR c.name LIKE ? OR o.status LIKE ?)"
        else:
            base_query += " WHERE (o.id LIKE ? OR c.name LIKE ? OR o.status LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
    
    orders = conn.execute(base_query, params).fetchall()
    conn.close()
    
    return render_template('orders.html', orders=orders, search_query=search_query)

@app.route('/orders/add', methods=['POST'])
def add_order():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    customer_id = request.form.get('customer_id')
    order_date = request.form.get('order_date')
    amount = request.form.get('amount')
    status = request.form.get('status')
    creator_id = session['user']['id'] # Set creator_id to current user's ID
    
    conn = get_db_connection()
    conn.execute('INSERT INTO orders (customer_id, order_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)',
                 (customer_id, order_date, amount, status, creator_id))
    conn.commit()
    conn.close()
    
    flash('訂單已成功新增')
    return redirect(url_for('orders'))

@app.route('/orders/edit/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Fetch the order to check ownership
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if order is None:
        flash('找不到該訂單')
        conn.close()
        return redirect(url_for('orders'))
    
    # Permission check: Only system_admin or creator can edit
    if not is_system_admin() and order['creator_id'] != session['user']['id']:
        flash('您沒有權限修改此訂單資料。')
        conn.close()
        return redirect(url_for('orders'))

    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        order_date = request.form.get('order_date')
        amount = request.form.get('amount')
        status = request.form.get('status')
        
        conn.execute('UPDATE orders SET customer_id = ?, order_date = ?, amount = ?, status = ? WHERE id = ?',
                     (customer_id, order_date, amount, status, order_id))
        conn.commit()
        conn.close()
        
        flash('訂單已成功更新')
        return redirect(url_for('orders'))
    
    conn.close() # Close connection after fetching for GET request
    return render_template('edit_order.html', order=order)

@app.route('/orders/delete/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # Fetch the order to check ownership
    order = conn.execute('SELECT creator_id FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if order is None:
        flash('找不到該訂單')
        conn.close()
        return redirect(url_for('orders'))
    
    # Permission check: Only system_admin or creator can delete
    if not is_system_admin() and order['creator_id'] != session['user']['id']:
        flash('您沒有權限刪除此訂單資料。')
        conn.close()
        return redirect(url_for('orders'))

    conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    
    flash('訂單已成功刪除')
    return redirect(url_for('orders'))

@app.route('/quotes')
def quotes():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search')
    
    conn = get_db_connection()
    
    base_query = "SELECT q.*, c.name as customer_name FROM quotes q JOIN customers c ON q.customer_id = c.id"
    params = []

    if not is_system_admin() and not is_administrator(): # Administrators can view all quotes
        base_query += " WHERE q.creator_id = ?"
        params.append(session['user']['id'])
    
    if search_query:
        if "WHERE" in base_query:
            base_query += " AND (q.id LIKE ? OR c.name LIKE ? OR q.status LIKE ?)"
        else:
            base_query += " WHERE (q.id LIKE ? OR c.name LIKE ? OR q.status LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
    
    quotes = conn.execute(base_query, params).fetchall()
    conn.close()
    
    return render_template('quotes.html', quotes=quotes, search_query=search_query)

@app.route('/quotes/add', methods=['POST'])
def add_quote():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    customer_id = request.form.get('customer_id')
    quote_date = request.form.get('quote_date')
    amount = request.form.get('amount')
    status = request.form.get('status')
    creator_id = session['user']['id'] # Set creator_id to current user's ID
    
    conn = get_db_connection()
    conn.execute('INSERT INTO quotes (customer_id, quote_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)',
                 (customer_id, quote_date, amount, status, creator_id))
    conn.commit()
    conn.close()
    
    flash('報價單已成功新增')
    return redirect(url_for('quotes'))

@app.route('/quotes/edit/<int:quote_id>', methods=['GET', 'POST'])
def edit_quote(quote_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Fetch the quote to check ownership
    quote = conn.execute('SELECT * FROM quotes WHERE id = ?', (quote_id,)).fetchone()
    
    if quote is None:
        flash('找不到該報價單')
        conn.close()
        return redirect(url_for('quotes'))
    
    # Permission check: Only system_admin or creator can edit
    if not is_system_admin() and quote['creator_id'] != session['user']['id']:
        flash('您沒有權限修改此報價單資料。')
        conn.close()
        return redirect(url_for('quotes'))

    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        quote_date = request.form.get('quote_date')
        amount = request.form.get('amount')
        status = request.form.get('status')
        
        conn.execute('UPDATE quotes SET customer_id = ?, quote_date = ?, amount = ?, status = ? WHERE id = ?',
                     (customer_id, quote_date, amount, status, quote_id))
        conn.commit()
        conn.close()
        
        flash('報價單已成功更新')
        return redirect(url_for('quotes'))
    
    conn.close() # Close connection after fetching for GET request
    return render_template('edit_quote.html', quote=quote)

@app.route('/quotes/delete/<int:quote_id>', methods=['POST'])
def delete_quote(quote_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # Fetch the quote to check ownership
    quote = conn.execute('SELECT creator_id FROM quotes WHERE id = ?', (quote_id,)).fetchone()
    
    if quote is None:
        flash('找不到該報價單')
        conn.close()
        return redirect(url_for('quotes'))
    
    # Permission check: Only system_admin or creator can delete
    if not is_system_admin() and quote['creator_id'] != session['user']['id']:
        flash('您沒有權限刪除此報價單資料。')
        conn.close()
        return redirect(url_for('quotes'))

    conn.execute('DELETE FROM quotes WHERE id = ?', (quote_id,))
    conn.commit()
    conn.close()
    
    flash('報價單已成功刪除')
    return redirect(url_for('quotes'))

@app.route('/automation')
def automation():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    base_query = "SELECT q.*, c.name as customer_name FROM quotes q JOIN customers c ON q.customer_id = c.id WHERE q.status = '已接受'"
    params = []

    if not is_system_admin() and not is_administrator(): # Administrators can view all accepted quotes for automation
        base_query += " AND q.creator_id = ?"
        params.append(session['user']['id'])
    
    accepted_quotes = conn.execute(base_query, params).fetchall()
    conn.close()
    
    return render_template('automation.html', accepted_quotes=accepted_quotes)

@app.route('/quotes/convert_to_order/<int:quote_id>', methods=['POST'])
def convert_to_order(quote_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # Get the quote details
    quote = conn.execute('SELECT * FROM quotes WHERE id = ?', (quote_id,)).fetchone()
    
    if quote is None or quote['status'] != '已接受':
        flash('無效的操作，或報價單不是「已接受」狀態。')
        conn.close()
        return redirect(url_for('automation'))
    
    # Permission check: Only system_admin or creator can convert
    if not is_system_admin() and quote['creator_id'] != session['user']['id']:
        flash('您沒有權限轉換此報價單。')
        conn.close()
        return redirect(url_for('automation'))
        
    # Create a new order
    order_date = quote['quote_date'] # Use quote date for order date
    creator_id = session['user']['id'] # Set creator_id to current user's ID
    conn.execute('INSERT INTO orders (customer_id, order_date, amount, status, creator_id) VALUES (?, ?, ?, ?, ?)',
                 (quote['customer_id'], order_date, quote['amount'], '未付款', creator_id))
                 
    # Update the quote status
    conn.execute("UPDATE quotes SET status = '已轉換' WHERE id = ?", (quote_id,))
    
    conn.commit()
    conn.close()
    
    flash(f"報價單 #{quote_id} 已成功轉換為新訂單。")
    return redirect(url_for('orders'))

@app.route('/analysis')
def analysis():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Sales Summary
    sales_summary_query = conn.execute('SELECT COUNT(*), SUM(amount) FROM orders').fetchone()
    total_orders = sales_summary_query[0] if sales_summary_query[0] else 0
    total_revenue = sales_summary_query[1] if sales_summary_query[1] else 0
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    sales_summary = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'average_order_value': average_order_value
    }
    
    # Quote Conversion Rate
    quote_summary_query = conn.execute("SELECT COUNT(*), (SELECT COUNT(*) FROM quotes WHERE status = '已接受' OR status = '已轉換') FROM quotes").fetchone()
    total_quotes = quote_summary_query[0] if quote_summary_query[0] else 0
    converted_quotes = quote_summary_query[1] if quote_summary_query[1] else 0
    conversion_rate = converted_quotes / total_quotes if total_quotes > 0 else 0
    quote_summary = {
        'total_quotes': total_quotes,
        'converted_quotes': converted_quotes,
        'conversion_rate': conversion_rate
    }
    
    # Top Customers
    top_customers = conn.execute('SELECT c.name, SUM(o.amount) AS total_spent FROM orders o JOIN customers c ON o.customer_id = c.id GROUP BY c.name ORDER BY total_spent DESC LIMIT 5').fetchall()
    
    # Order Status Distribution
    order_status_distribution = conn.execute('SELECT status, COUNT(*) as count FROM orders GROUP BY status').fetchall()
    
    conn.close()
    
    # Market Suggestions
    suggestions = []
    if top_customers:
        suggestions.append(f"您的頂尖客戶是 {top_customers[0]['name']}，可以考慮提供專屬優惠以維持良好客戶關係。")
    
    pending_orders = next((status['count'] for status in order_status_distribution if status['status'] == 'Pending'), 0)
    if pending_orders > 0:
        suggestions.append(f"您有 {pending_orders} 筆處理中的訂單，記得跟進以完成交易。")
        
    if quote_summary['conversion_rate'] < 0.5 and quote_summary['total_quotes'] > 10:
        suggestions.append("報價單轉換率偏低，建議分析拒絕原因或優化報價策略。")

    return render_template(
        'analysis.html',
        sales_summary=sales_summary,
        quote_summary=quote_summary,
        top_customers=top_customers,
        order_status_distribution=order_status_distribution,
        suggestions=suggestions
    )

@app.route('/ai_features')
def ai_features():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    customers = conn.execute('SELECT * FROM customers').fetchall()
    orders = conn.execute('SELECT * FROM orders').fetchall()
    quotes = conn.execute('SELECT * FROM quotes').fetchall()
    conn.close()

    # --- Customer Scoring ---
    customer_scores = {}
    for customer in customers:
        customer_scores[customer['id']] = {'name': customer['name'], 'score': 0}

    for order in orders:
        if order['customer_id'] in customer_scores:
            if order['status'] == '取消':
                customer_scores[order['customer_id']]['score'] -= 10
            else:
                customer_scores[order['customer_id']]['score'] += 10

    for quote in quotes:
        if quote['customer_id'] in customer_scores:
            if quote['status'] == '已接受' or quote['status'] == '已轉換':
                customer_scores[quote['customer_id']]['score'] += 5

    # --- Customer Segmentation ---
    customer_spending = {c['id']: {'name': c['name'], 'total_spent': 0} for c in customers}
    for order in orders:
        if order['customer_id'] in customer_spending and order['status'] != '取消':
            customer_spending[order['customer_id']]['total_spent'] += order['amount']
    
    spendings = sorted([v['total_spent'] for v in customer_spending.values() if v['total_spent'] > 0])
    
    p25, p75 = 0, 0
    if spendings:
        p25_index = int(len(spendings) * 0.25)
        p75_index = int(len(spendings) * 0.75)
        p25 = spendings[p25_index]
        p75 = spendings[p75_index]

    # Add spending to scores for sorting
    for cid, data in customer_scores.items():
        data['total_spent'] = customer_spending[cid]['total_spent']
        if data['total_spent'] > (sum(s for s in spendings) / len(spendings) if spendings else 0):
             data['score'] += 20


    segments = {'high_value': [], 'mid_value': [], 'low_value': []}
    for cid, data in customer_spending.items():
        if data['total_spent'] >= p75 and p75 > 0:
            segments['high_value'].append(data)
        elif data['total_spent'] >= p25:
            segments['mid_value'].append(data)
        else:
            segments['low_value'].append(data)

    scored_customers_list = sorted(customer_scores.values(), key=lambda x: x['score'], reverse=True)

    return render_template(
        'ai_features.html',
        scored_customers=scored_customers_list,
        segments=segments
    )



def is_system_admin():
    return 'user' in session and session['user']['role'] == 'system_admin'

def is_administrator():
    return 'user' in session and (session['user']['role'] == 'system_admin' or session['user']['role'] == 'administrator')

def can_manage_users():
    return is_system_admin() or is_administrator()

@app.route('/users')
def users():
    if 'user' not in session:
        return redirect(url_for('login'))

    # If the user is a regular user, redirect them to their own edit page immediately.
    if not can_manage_users():
        # flash('您只能管理自己的帳號，已為您導向專屬頁面。') # Optional: message can be annoying.
        return redirect(url_for('edit_user', user_id=session['user']['id']))

    # Admins and System Admins can see the full list.
    search_query = request.args.get('search')
    conn = get_db_connection()
    
    if search_query:
        query = "SELECT * FROM users WHERE employee_id LIKE ? OR name LIKE ? OR role LIKE ?"
        users_list = conn.execute(query, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')).fetchall()
    else:
        users_list = conn.execute('SELECT * FROM users').fetchall()
        
    conn.close()
    
    return render_template('users.html', users=users_list, search_query=search_query)

@app.route('/users/add', methods=['POST'])
def add_user():
    if not can_manage_users():
        flash('您沒有權限執行此操作。')
        return redirect(url_for('dashboard'))
    
    employee_id = request.form.get('employee_id')
    password = request.form.get('password')
    name = request.form.get('name')
    role = request.form.get('role')
    creator_id = session['user']['id']

    # Only system_admin can set any role.
    # Administrator can set roles but not 'system_admin'.
    if not is_system_admin():
        if role == 'system_admin':
            flash('您沒有權限新增系統管理員帳號。')
            return redirect(url_for('users'))
        # If the creator is an administrator, they can assign 'user' or 'administrator'.
        # If they are not a system_admin, we default to 'user' if the role is not specified or invalid.
        if role not in ['user', 'administrator']:
            role = 'user'
    elif not role: # If system_admin didn't specify, default to 'user'
        role = 'user'

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (employee_id, password, name, role, creator_id) VALUES (?, ?, ?, ?, ?)',
                     (employee_id, password, name, role, creator_id))
        conn.commit()
        flash('帳號已成功新增')
    except sqlite3.IntegrityError:
        flash('員工ID已存在，請使用其他ID。')
    finally:
        conn.close()
    
    return redirect(url_for('users'))

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    # Security Check: Allow access if the user is an admin OR they are editing their own profile.
    if not can_manage_users() and user_id != session['user']['id']:
        flash('您沒有權限訪問此頁面。')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    user_to_edit = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if user_to_edit is None:
        flash('找不到該帳號')
        conn.close()
        return redirect(url_for('users'))

    # Security Check: Prevent an administrator from editing a system_admin.
    if is_administrator() and not is_system_admin() and user_to_edit['role'] == 'system_admin':
        flash('您沒有權限修改系統管理員帳號。')
        conn.close()
        return redirect(url_for('users'))

    if request.method == 'POST':
        # --- Form Data ---
        password = request.form.get('password') # Optional
        role = request.form.get('role') # Optional, and only for admins

        # --- Build Query ---
        # Only update fields if they are provided.
        query_parts = []
        params = []

        if password:
            query_parts.append('password = ?')
            params.append(password)

        # Role can only be changed by an admin, and with restrictions.
        if can_manage_users() and role and role != user_to_edit['role']:
            if not is_system_admin() and role == 'system_admin':
                flash('您沒有權限將帳號權限提升為系統管理員。')
                conn.close()
                return redirect(url_for('edit_user', user_id=user_id))
            
            if user_to_edit['role'] == 'system_admin' and not is_system_admin():
                 flash('您沒有權限變更系統管理員的角色。')
                 conn.close()
                 return redirect(url_for('edit_user', user_id=user_id))

            query_parts.append('role = ?')
            params.append(role)

        # If there is something to update, execute the query.
        if query_parts:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(query_parts)} WHERE id = ?"

            try:
                conn.execute(query, tuple(params))
                conn.commit()
                flash('帳號已成功更新')

                if user_id == session['user']['id']:
                    updated_user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
                    if updated_user:
                        session['user'] = dict(updated_user)
                        session['employee_id'] = updated_user['employee_id']
                        session['role'] = updated_user['role']
                    session.modified = True

            except sqlite3.Error as e:
                flash(f"更新帳號時發生錯誤: {e}")
            finally:
                conn.close()
        else:
            flash('沒有提供任何需要更新的資訊。')
            conn.close()
        
        if can_manage_users():
            return redirect(url_for('users'))
        else:
            return redirect(url_for('dashboard'))

    # For GET request, simply render the page.
    conn.close()
    # The template should be 'edit_user.html', and we pass the user being edited.
    # The template will need logic to show/hide the 'role' field.
    return render_template('edit_user.html', user_to_edit=user_to_edit)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not can_manage_users():
        flash('您沒有權限執行此操作。')
        return redirect(url_for('dashboard'))
        
    conn = get_db_connection()
    
    # Prevent deleting the admin account (employee_id '1')
    target_user = conn.execute('SELECT employee_id FROM users WHERE id = ?', (user_id,)).fetchone()
    if target_user and target_user['employee_id'] == '1':
        flash('無法刪除最高權限帳號。')
        conn.close()
        return redirect(url_for('users'))

    # Prevent administrator from deleting system_admin or other administrator accounts
    target_user = conn.execute('SELECT employee_id, role FROM users WHERE id = ?', (user_id,)).fetchone()
    if target_user and (target_user['role'] == 'system_admin' or (target_user['role'] == 'administrator' and not is_system_admin())):
        flash('您沒有權限刪除此帳號。')
        conn.close()
        return redirect(url_for('users'))

    try:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        flash('帳號已成功刪除')
    except sqlite3.Error as e:
        flash(f'刪除帳號失敗: {e}')
    finally:
        conn.close()
    
    return redirect(url_for('users'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
