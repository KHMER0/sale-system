import os
import requests
import json
import sqlite3

# 從環境變數中讀取 DeepSeek API Key
DEEPSEEK_API_KEY = ("sk-14300a2e726d4835a1c6fc1e6f6c6d98")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = '''
你是一個專業、智慧的銷售管理系統助理。你的主要目標是協助使用者（業務人員、經理）有效率地查詢銷售資料。
你的語氣應始終保持專業、簡潔且樂於助人。

**重要規則:**
1.  **根據提供的資料庫脈絡回答問題:** 你接下來會收到一段包含「資料庫脈絡」的文字，裡面有從資料庫查詢到的真實資料。你 **必須** 根據這份脈絡來回答使用者的問題。
2.  **絕不捏造資訊:** 如果在提供的「資料庫脈絡」中找不到使用者問題的答案，你必須明確地告知使用者「我無法在資料庫中找到相關資訊」，**嚴禁** 自行編造或產生任何資料庫脈絡中不存在的內容。
3.  **提供 ID:** 當回覆內容提到特定的訂單、報價單或客戶資料時，必須一併提供其對應的 ID。例如：訂單 (ID: 10), 客戶 (ID: 5)。
4.  **安全與隱私:** 絕不透露使用者的密碼或任何敏感的個人身份資訊。
5.  **無關問題:** 如果提問的問題與銷售管理系統無關，請禮貌地拒絕回答。
6.  **語言與格式:** 請使用繁體中文與使用者溝通。回覆內容請使用純文字，並用換行和列表來組織資訊，使其清晰易讀。

你將會根據以下資料庫結構的脈絡進行回覆：
*   客戶 (Customers): id, name, contact_person, phone, email
*   訂單 (Orders): id, customer_id, order_date, amount, status
*   報價單 (Quotes): id, customer_id, quote_date, amount, status
'''

def query_database(query: str, params=()):
    """
    執行一個唯讀的查詢到 sales.db 資料庫並回傳結果。
    """
    try:
        conn = sqlite3.connect('sales.db')
        conn.row_factory = sqlite3.Row  # 這樣可以透過欄位名稱存取資料
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        # 將 row 物件轉換為字典列表，方便處理
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"資料庫錯誤: {e}")
        return []

def get_database_context_for_llm():
    """
    從所有相關表格中提取資料，為 LLM 建立一個文字脈絡。
    為了簡單起見，我們提取所有資料。在真實世界的應用中，你可能會想根據使用者問題來做更精準的提取。
    """
    context_parts = []

    # 提取客戶資料
    customers = query_database("SELECT id, name, contact_person, phone, email FROM customers")
    if customers:
        context_parts.append("客戶資料:\n" + json.dumps(customers, ensure_ascii=False, indent=2))

    # 提取訂單資料，並加入客戶名稱
    orders = query_database('''
        SELECT o.id, c.name as customer_name, o.order_date, o.amount, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
    ''')
    if orders:
        context_parts.append("訂單資料:\n" + json.dumps(orders, ensure_ascii=False, indent=2))

    # 提取報價單資料，並加入客戶名稱
    quotes = query_database('''
        SELECT q.id, c.name as customer_name, q.quote_date, q.amount, q.status
        FROM quotes q
        JOIN customers c ON q.customer_id = c.id
    ''')
    if quotes:
        context_parts.append("報價單資料:\n" + json.dumps(quotes, ensure_ascii=False, indent=2))

    if not context_parts:
        return "資料庫中目前沒有資料。"

    return "\n\n".join(context_parts)


def get_chatbot_response(user_message: str) -> str:
    """
    向 DeepSeek API 發送使用者訊息並獲取機器人回應。
    這個版本會先從資料庫查詢脈絡，再送給 LLM。
    """
    if not DEEPSEEK_API_KEY:
        return "錯誤：未設定 DEEPSEEK_API_KEY 環境變數。"

    # 1. 從資料庫取得脈絡
    db_context = get_database_context_for_llm()

    # 2. 建立傳送給 LLM 的訊息
    # 我們將資料庫脈絡和使用者問題結合在一個 user role message 中
    combined_user_message = f"請根據以下「資料庫脈絡」來回答問題。\n\n--- 資料庫脈絡 ---\n{db_context}\n\n--- 使用者問題 ---\n{user_message}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": combined_user_message}
    ]

    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "stream": False
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        response_data = response.json()
        if response_data and response_data.get('choices') and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            return "機器人回應格式不正確。"

    except requests.exceptions.RequestException as e:
        return f"與 DeepSeek API 通訊時發生錯誤: {e}"
    except json.JSONDecodeError:
        return "解析 DeepSeek API 回應時發生錯誤。"
    except Exception as e:
        return f"發生未知錯誤: {e}"

if __name__ == "__main__":
    # 測試新的 get_chatbot_response
    # 確保你的 sales.db 檔案存在且有資料
    print("--- 測試案例 1: 查詢存在的客戶訂單 ---")
    response = get_chatbot_response("查詢 TechCorp 的所有訂單。")
    print("機器人回應:", response)
    print("\n" + "="*20 + "\n")

    print("--- 測試案例 2: 查詢不存在的資料 ---")
    response = get_chatbot_response("蘋果公司有哪些報價單？")
    print("機器人回應:", response)
    print("\n" + "="*20 + "\n")

    print("--- 測試案例 3: 無關問題 ---")
    response = get_chatbot_response("今天天氣如何？")
    print("機器人回應:", response)