from flask import Flask, render_template_string
import requests
import threading
import time
import sqlite3
from datetime import datetime, timedelta
import os

# Configuration
ADMIN_TOKEN = '5dfc33056f17eef7f440f2b677abaf7a'
API_URL = 'http://3.141.111.200:8081/api/orchestrators'
DB_FILE = 'orchestrators.db'
UPDATE_INTERVAL = 900  # 15 minutes in seconds

app = Flask(__name__)

orchestrators_data = []
db_initialized = False

def init_db():
    """Initialize the SQLite database"""
    global db_initialized
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                balance REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_address_timestamp ON balance_history(address, timestamp)')
        conn.commit()
        conn.close()
        db_initialized = True
    except Exception as e:
        print(f"Database init error: {e}")

def get_balance_24h_ago(address):
    """Get the balance from 24 hours ago"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        time_24h_ago = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        cursor.execute('''
            SELECT balance FROM balance_history 
            WHERE address = ? AND timestamp <= ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (address, time_24h_ago))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None

def save_balance(address, balance):
    """Save balance snapshot with timestamp"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        cursor.execute('''
            INSERT INTO balance_history (address, balance, timestamp)
            VALUES (?, ?, ?)
        ''', (address, balance, timestamp))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def cleanup_old_records():
    """Remove records older than 25 hours"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        time_25h_ago = (datetime.utcnow() - timedelta(hours=25)).isoformat()
        cursor.execute('DELETE FROM balance_history WHERE timestamp < ?', (time_25h_ago,))
        conn.commit()
        conn.close()
    except:
        pass

def format_timestamp(timestamp_str):
    """Format ISO timestamp to readable format"""
    if not timestamp_str:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('+00:00', ''))
        return dt.strftime('%b %d, %Y %H:%M')
    except:
        return timestamp_str

def fetch_orchestrators():
    global orchestrators_data
    while not db_initialized:
        time.sleep(1)
    
    while True:
        try:
            headers = {
                'X-Admin-Token': ADMIN_TOKEN
            }
            response = requests.get(API_URL, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'orchestrators' in data:
                    data = data['orchestrators']
                elif isinstance(data, list):
                    pass
                else:
                    data = []
                
                for o in data:
                    addr = o.get('address', '')
                    current_balance = float(o.get('balance_eth', 0))
                    balance_24h_ago = get_balance_24h_ago(addr)
                    
                    if balance_24h_ago is None:
                        balance_change = 0.0
                    else:
                        balance_change = current_balance - balance_24h_ago
                    
                    o['balance_change_24h'] = balance_change
                    save_balance(addr, current_balance)
                    o['last_healthy_at_formatted'] = format_timestamp(o.get('last_healthy_at'))
                
                data.sort(key=lambda x: (
                    x.get('last_healthy_at') is None,
                    x.get('orchestrator_id', '').lower()
                ))
                
                orchestrators_data = data
                cleanup_old_records()
                
        except Exception as e:
            pass
            
        time.sleep(UPDATE_INTERVAL)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orchestrators ETH Balances</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #e2e8f0;
    padding: 20px;
    min-height: 100vh;
}

.container {
    max-width: 1600px;
    margin: 0 auto;
}

.header {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 30px;
    margin-bottom: 30px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.header h1 {
    font-size: 28px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 8px;
}

.header .subtitle {
    color: #94a3b8;
    font-size: 14px;
}

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    text-align: center;
}

.stat-card .label {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

.stat-card .value {
    color: #f1f5f9;
    font-size: 32px;
    font-weight: 700;
}

.table-container {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

table {
    width: 100%;
    border-collapse: collapse;
}

thead {
    background: rgba(255, 255, 255, 0.08);
}

th {
    padding: 16px 20px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    color: #cbd5e1;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

td {
    padding: 16px 20px;
    color: #e2e8f0;
    font-size: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

tbody tr {
    transition: all 0.2s ease;
}

tbody tr:hover {
    background: rgba(255, 255, 255, 0.08);
}

tbody tr:last-child td {
    border-bottom: none;
}

.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}

.badge-success {
    background: rgba(34, 197, 94, 0.2);
    color: #86efac;
    border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-danger {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-warning {
    background: rgba(251, 191, 36, 0.2);
    color: #fde047;
    border: 1px solid rgba(251, 191, 36, 0.3);
}

.address {
    font-family: 'Courier New', monospace;
    color: #94a3b8;
    font-size: 13px;
}

.balance-positive {
    color: #86efac;
    font-weight: 600;
}

.balance-negative {
    color: #fca5a5;
    font-weight: 600;
}

.balance-zero {
    color: #94a3b8;
}

.orch-name {
    font-weight: 600;
    color: #f1f5f9;
}

@media (max-width: 768px) {
    .header h1 {
        font-size: 22px;
    }
    
    table {
        font-size: 12px;
    }
    
    th, td {
        padding: 12px 10px;
    }
    
    .stat-card .value {
        font-size: 24px;
    }
}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Livepeer Orchestrators Monitor</h1>
        <div class="subtitle">Real-time ETH balance tracking with 24-hour change analysis</div>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="label">Total Orchestrators</div>
            <div class="value">{{ orchestrators|length }}</div>
        </div>
        <div class="stat-card">
            <div class="label">Healthy Nodes</div>
            <div class="value">{{ orchestrators|selectattr('last_healthy_at')|list|length }}</div>
        </div>
        <div class="stat-card">
            <div class="label">Eligible for Payments</div>
            <div class="value">{{ orchestrators|selectattr('eligible_for_payments', 'equalto', true)|list|length }}</div>
        </div>
        <div class="stat-card">
            <div class="label">Top 100</div>
            <div class="value">{{ orchestrators|selectattr('is_top_100', 'equalto', true)|list|length }}</div>
        </div>
    </div>
    
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Orchestrator</th>
                    <th>Address</th>
                    <th>Balance (ETH)</th>
                    <th>24h Change</th>
                    <th>Status</th>
                    <th>Last Health Check</th>
                </tr>
            </thead>
            <tbody>
                {% for o in orchestrators %}
                <tr>
                    <td>
                        <div class="orch-name">{{ o.orchestrator_id }}</div>
                    </td>
                    <td>
                        <span class="address">{{ o.address[:10] }}...{{ o.address[-8:] }}</span>
                    </td>
                    <td>{{ o.balance_eth_fmt }}</td>
                    <td>
                        {% if o.balance_change_24h > 0 %}
                            <span class="balance-positive">+{{ o.balance_change_24h_fmt }}</span>
                        {% elif o.balance_change_24h < 0 %}
                            <span class="balance-negative">{{ o.balance_change_24h_fmt }}</span>
                        {% else %}
                            <span class="balance-zero">{{ o.balance_change_24h_fmt }}</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if o.eligible_for_payments and not o.cooldown_active %}
                            <span class="badge badge-success">Active</span>
                        {% elif o.cooldown_active %}
                            <span class="badge badge-warning">Cooldown</span>
                        {% else %}
                            <span class="badge badge-danger">Inactive</span>
                        {% endif %}
                    </td>
                    <td>{{ o.last_healthy_at_formatted }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
</body>
</html>
'''

@app.route('/')
def index():
    for o in orchestrators_data:
        o['balance_eth_fmt'] = f"{float(o.get('balance_eth', 0)):.8f}"
        o['balance_change_24h_fmt'] = f"{o.get('balance_change_24h', 0):.8f}"
    return render_template_string(HTML_TEMPLATE, orchestrators=orchestrators_data)

if __name__ == '__main__':
    init_db()
    thread = threading.Thread(target=fetch_orchestrators)
    thread.daemon = True
    thread.start()
    time.sleep(2)
    app.run(host='0.0.0.0', port=5000)
