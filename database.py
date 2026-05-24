import sqlite3
import os
from datetime import datetime, date, timedelta

DB_PATH = os.getenv('DB_PATH', '/data/hanoibox.db')

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT, email TEXT, plan TEXT,
        status TEXT DEFAULT 'active', start_date TEXT, expiry_date TEXT,
        sessions_remaining INTEGER DEFAULT 0, amount_paid_vnd INTEGER DEFAULT 0,
        notes TEXT, created_at TEXT DEFAULT (datetime('now')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, member_name TEXT,
        date TEXT, time TEXT, type TEXT DEFAULT 'group', coach TEXT, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, member_name TEXT,
        amount_vnd INTEGER, amount_usd REAL, plan TEXT, method TEXT DEFAULT 'cash',
        date TEXT, notes TEXT, confirmed INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bot_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, message TEXT,
        response TEXT, timestamp TEXT DEFAULT (datetime('now')))''')
    conn.commit(); conn.close()

class Database:
    def find_member(self, q):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM members WHERE LOWER(name) LIKE ?", (f'%{q.lower()}%',))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

    def get_member(self, mid):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM members WHERE id=?", (mid,))
        r = c.fetchone(); conn.close(); return dict(r) if r else None

    def add_member(self, name, phone='', email='', plan='group_3month', sessions=0, amount_vnd=0, notes=''):
        conn = get_conn(); c = conn.cursor()
        today = date.today().isoformat()
        days = {'group_3month':90,'private_10pack':120,'private_monthly':30}.get(plan,30)
        expiry = (date.today()+timedelta(days=days)).isoformat()
        c.execute("""INSERT INTO members(name,phone,email,plan,status,start_date,expiry_date,sessions_remaining,amount_paid_vnd,notes)
            VALUES(?,?,?,?,'active',?,?,?,?,?)""", (name,phone,email,plan,today,expiry,sessions,amount_vnd,notes))
        mid = c.lastrowid; conn.commit(); conn.close(); return mid

    def log_attendance(self, member_id, member_name, session_type='group', coach=''):
        conn = get_conn(); c = conn.cursor(); now = datetime.now()
        c.execute("INSERT INTO attendance(member_id,member_name,date,time,type,coach) VALUES(?,?,?,?,?,?)",
            (member_id, member_name, now.date().isoformat(), now.strftime('%H:%M'), session_type, coach))
        if session_type == 'private':
            c.execute("UPDATE members SET sessions_remaining=MAX(0,sessions_remaining-1) WHERE id=?", (member_id,))
        conn.commit(); conn.close()

    def log_payment(self, member_name, amount_vnd, plan, method='cash', member_id=None, notes=''):
        conn = get_conn(); c = conn.cursor()
        c.execute("INSERT INTO payments(member_id,member_name,amount_vnd,amount_usd,plan,method,date,notes) VALUES(?,?,?,?,?,?,?,?)",
            (member_id, member_name, amount_vnd, round(amount_vnd/25000,2), plan, method, date.today().isoformat(), notes))
        pid = c.lastrowid; conn.commit(); conn.close(); return pid

    def confirm_payment(self, pid):
        conn = get_conn(); c = conn.cursor()
        c.execute("UPDATE payments SET confirmed=1 WHERE id=?", (pid,)); conn.commit(); conn.close()

    def get_expiring_members(self, days=7):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM members WHERE expiry_date BETWEEN ? AND ? AND status!='expired' ORDER BY expiry_date",
            (date.today().isoformat(), (date.today()+timedelta(days=days)).isoformat()))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

    def get_expired_members(self):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM members WHERE expiry_date < ? AND status!='expired' ORDER BY expiry_date DESC", (date.today().isoformat(),))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

    def get_active_members(self):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM members WHERE status='active' ORDER BY name")
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

    def get_today_attendance(self):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM attendance WHERE date=? ORDER BY time", (date.today().isoformat(),))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

    def get_monthly_revenue(self, year=None, month=None):
        if not year: year = date.today().year
        if not month: month = date.today().month
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT SUM(amount_vnd) as total_vnd, SUM(amount_usd) as total_usd, COUNT(*) as cnt FROM payments WHERE strftime('%Y',date)=? AND strftime('%m',date)=?",
            (str(year), f'{month:02d}'))
        r = c.fetchone(); conn.close(); return dict(r) if r else {}

    def get_recent_payments(self, limit=10):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM payments ORDER BY date DESC, id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

    def get_recent_bot_log(self, limit=10):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM bot_log ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

    def log_message(self, sender, message, response=''):
        conn = get_conn(); c = conn.cursor()
        c.execute("INSERT INTO bot_log(sender,message,response) VALUES(?,?,?)", (sender, message[:500], response[:500]))
        conn.commit(); conn.close()

    def get_context(self):
        active = self.get_active_members(); today = self.get_today_attendance()
        rev = self.get_monthly_revenue(); exp = self.get_expiring_members()
        return {'active_members':len(active),'today_checkins':len(today),
            'monthly_revenue_usd':round((rev.get('total_usd') or 0),2),
            'expiring_soon':len(exp),'member_names':[m['name'] for m in active]}

    def get_dashboard_data(self):
        active = self.get_active_members(); today = self.get_today_attendance()
        rev = self.get_monthly_revenue(); expiring = self.get_expiring_members(14)
        expired = self.get_expired_members()
        monthly = []
        for i in range(5,-1,-1):
            m = date.today().month - i; y = date.today().year
            while m<=0: m+=12; y-=1
            r = self.get_monthly_revenue(y,m)
            monthly.append({'month':date(y,m,1).strftime('%b'),'usd':round((r.get('total_usd') or 0),2)})
        return {'active_members':len(active),'today_checkins':len(today),
            'monthly_revenue_usd':round((rev.get('total_usd') or 0),2),
            'expiring_count':len(expiring)+len(expired),
            'members':active,'today_attendance':today,'expiring':expiring,'expired':expired,
            'recent_payments':self.get_recent_payments(5),
            'bot_log':self.get_recent_bot_log(5),'monthly_revenue':monthly}
