import sqlite3
import os
from datetime import datetime
from config_web import DB_PATH, COMPENSATION_RULES, REVIEW_CASHBACK_RULES


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    c = get_conn()
    cur = c.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        photo_url TEXT,
        balance_gold REAL DEFAULT 0,
        total_spent REAL DEFAULT 0,
        total_orders INTEGER DEFAULT 0,
        total_gold_bought INTEGER DEFAULT 0,
        consecutive_rejections INTEGER DEFAULT 0,
        total_reviews INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        telegram_id INTEGER NOT NULL,
        game TEXT NOT NULL,
        gold_amount INTEGER NOT NULL,
        price REAL NOT NULL,
        skin_price REAL DEFAULT 0,
        status TEXT DEFAULT 'awaiting_screenshot',
        game_id TEXT,
        screenshot_file_id TEXT,
        moderator_id INTEGER,
        moderator_username TEXT,
        reject_reason TEXT,
        message_id_in_group INTEGER,
        review_submitted INTEGER DEFAULT 0,
        review_rating INTEGER,
        review_comment TEXT,
        review_number INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        role TEXT DEFAULT 'moderator',
        added_by INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS promocodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        gold_amount INTEGER NOT NULL,
        max_activations INTEGER DEFAULT 1,
        current_activations INTEGER DEFAULT 0,
        expires_at TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS promo_activations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        promo_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        telegram_id INTEGER NOT NULL,
        activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(promo_id, telegram_id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        title TEXT,
        message TEXT NOT NULL,
        order_id INTEGER,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        telegram_id INTEGER NOT NULL,
        username TEXT,
        rating INTEGER NOT NULL,
        comment TEXT,
        gold_amount INTEGER NOT NULL,
        cashback_gold REAL DEFAULT 0,
        review_number INTEGER,
        published INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cur.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('gold_price','0.67')")
    cur.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('market_commission','0.20')")
    cur.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('review_counter','0')")

    c.commit()
    c.close()


def get_setting(key, default=None):
    c = get_conn()
    r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    c.close()
    return r['value'] if r else default


def set_setting(key, value):
    c = get_conn()
    c.execute('INSERT OR REPLACE INTO settings (key,value,updated_at) VALUES (?,?,?)',
              (key, str(value), datetime.now()))
    c.commit()
    c.close()


def get_gold_price():
    return float(get_setting('gold_price', '0.67'))


def get_market_commission():
    return float(get_setting('market_commission', '0.20'))


def get_next_review_number():
    c = get_conn()
    r = c.execute("SELECT value FROM settings WHERE key='review_counter'").fetchone()
    num = int(r['value']) + 1 if r else 1
    c.execute("INSERT OR REPLACE INTO settings (key,value,updated_at) VALUES ('review_counter',?,?)",
              (str(num), datetime.now()))
    c.commit()
    c.close()
    return num


def get_or_create_user(telegram_id, username=None, first_name=None, last_name=None, photo_url=None):
    c = get_conn()
    u = c.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,)).fetchone()
    if u is None:
        c.execute('INSERT INTO users (telegram_id,username,first_name,last_name,photo_url) VALUES (?,?,?,?,?)',
                  (telegram_id, username, first_name, last_name, photo_url))
        c.commit()
        u = c.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,)).fetchone()
    else:
        c.execute('UPDATE users SET username=COALESCE(?,username),first_name=COALESCE(?,first_name),last_name=COALESCE(?,last_name),photo_url=COALESCE(?,photo_url),last_active=? WHERE telegram_id=?',
                  (username, first_name, last_name, photo_url, datetime.now(), telegram_id))
        c.commit()
        u = c.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,)).fetchone()
    c.close()
    return dict(u)


def get_all_user_ids():
    c = get_conn()
    ids = [r['telegram_id'] for r in c.execute('SELECT telegram_id FROM users').fetchall()]
    c.close()
    return ids


def get_user_count():
    c = get_conn()
    n = c.execute('SELECT COUNT(*) as n FROM users').fetchone()['n']
    c.close()
    return n


def add_balance(telegram_id, gold):
    c = get_conn()
    c.execute('UPDATE users SET balance_gold=balance_gold+? WHERE telegram_id=?', (gold, telegram_id))
    c.commit()
    c.close()


def increment_rejections(telegram_id):
    c = get_conn()
    c.execute('UPDATE users SET consecutive_rejections=consecutive_rejections+1 WHERE telegram_id=?', (telegram_id,))
    u = c.execute('SELECT consecutive_rejections FROM users WHERE telegram_id=?', (telegram_id,)).fetchone()
    c.commit()
    c.close()
    return u['consecutive_rejections'] if u else 0


def reset_rejections(telegram_id):
    c = get_conn()
    c.execute('UPDATE users SET consecutive_rejections=0 WHERE telegram_id=?', (telegram_id,))
    c.commit()
    c.close()


def create_order(user_id, telegram_id, game, gold_amount, price, skin_price, game_id=None):
    c = get_conn()
    c.execute('''INSERT INTO orders (user_id,telegram_id,game,gold_amount,price,skin_price,game_id,status)
                 VALUES (?,?,?,?,?,?,?,'awaiting_screenshot')''',
              (user_id, telegram_id, game, gold_amount, price, skin_price, game_id))
    c.execute('UPDATE users SET total_spent=total_spent+?,total_orders=total_orders+1,total_gold_bought=total_gold_bought+? WHERE id=?',
              (price, gold_amount, user_id))
    oid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    c.commit()
    c.close()
    return oid


def get_order(order_id):
    c = get_conn()
    o = c.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    c.close()
    return dict(o) if o else None


def update_order(order_id, **kwargs):
    c = get_conn()
    sets = ['updated_at=?']
    vals = [datetime.now()]
    for k, v in kwargs.items():
        sets.append(f'{k}=?')
        vals.append(v)
    vals.append(order_id)
    c.execute(f'UPDATE orders SET {",".join(sets)} WHERE id=?', vals)
    c.commit()
    c.close()


def get_user_orders(telegram_id, limit=50):
    c = get_conn()
    orders = [dict(r) for r in c.execute(
        'SELECT * FROM orders WHERE telegram_id=? ORDER BY created_at DESC LIMIT ?',
        (telegram_id, limit)).fetchall()]
    c.close()
    return orders


def get_completed_orders_for_review(telegram_id):
    c = get_conn()
    orders = [dict(r) for r in c.execute(
        "SELECT * FROM orders WHERE telegram_id=? AND status='completed' AND review_submitted=0",
        (telegram_id,)).fetchall()]
    c.close()
    return orders


def get_user_purchase_history(telegram_id):
    c = get_conn()
    orders = [dict(r) for r in c.execute(
        "SELECT * FROM orders WHERE telegram_id=? AND status='completed' ORDER BY completed_at DESC",
        (telegram_id,)).fetchall()]
    c.close()
    return orders


def get_stats():
    c = get_conn()
    total = c.execute('SELECT COUNT(*) as n FROM orders').fetchone()['n']
    done = c.execute("SELECT COUNT(*) as n FROM orders WHERE status='completed'").fetchone()['n']
    pending = c.execute("SELECT COUNT(*) as n FROM orders WHERE status IN ('pending_review','awaiting_screenshot')").fetchone()['n']
    rev = c.execute("SELECT COALESCE(SUM(price),0) as s FROM orders WHERE status='completed'").fetchone()['s']
    c.close()
    return {'total': total, 'completed': done, 'pending': pending, 'revenue': rev}


def is_admin(tid):
    c = get_conn()
    r = c.execute("SELECT 1 FROM admins WHERE telegram_id=? AND role='admin'", (tid,)).fetchone()
    c.close()
    return r is not None


def is_moderator(tid):
    if is_admin(tid):
        return True
    c = get_conn()
    r = c.execute("SELECT 1 FROM admins WHERE telegram_id=?", (tid,)).fetchone()
    c.close()
    return r is not None


def add_staff(tid, role, added_by):
    c = get_conn()
    try:
        c.execute('INSERT INTO admins (telegram_id,role,added_by) VALUES (?,?,?)', (tid, role, added_by))
        c.commit()
        c.close()
        return True
    except:
        c.close()
        return False


def remove_staff(tid):
    c = get_conn()
    c.execute('DELETE FROM admins WHERE telegram_id=?', (tid,))
    ok = c.execute('SELECT changes()').fetchone()[0]
    c.commit()
    c.close()
    return ok > 0


def get_all_staff():
    c = get_conn()
    s = [dict(r) for r in c.execute('SELECT * FROM admins ORDER BY role DESC').fetchall()]
    c.close()
    return s


def create_promo(code, gold, max_act, expires=None, by=None):
    c = get_conn()
    try:
        c.execute('INSERT INTO promocodes (code,gold_amount,max_activations,expires_at,created_by) VALUES (?,?,?,?,?)',
                  (code.upper(), gold, max_act, expires, by))
        c.commit()
        c.close()
        return True
    except:
        c.close()
        return False


def remove_promo(code):
    c = get_conn()
    c.execute('DELETE FROM promocodes WHERE code=?', (code.upper(),))
    ok = c.execute('SELECT changes()').fetchone()[0]
    c.commit()
    c.close()
    return ok > 0


def get_all_promos():
    c = get_conn()
    p = [dict(r) for r in c.execute('SELECT * FROM promocodes ORDER BY created_at DESC').fetchall()]
    c.close()
    return p


def activate_promo(code, telegram_id):
    code = code.upper()
    c = get_conn()
    p = c.execute('SELECT * FROM promocodes WHERE code=?', (code,)).fetchone()
    if not p:
        c.close()
        return {'success': False, 'error': 'Промокод не найден'}
    if not p['is_active']:
        c.close()
        return {'success': False, 'error': 'Промокод неактивен'}
    if p['expires_at']:
        try:
            if datetime.now() > datetime.strptime(p['expires_at'], '%Y-%m-%d %H:%M:%S'):
                c.close()
                return {'success': False, 'error': 'Срок истёк'}
        except:
            pass
    if p['current_activations'] >= p['max_activations']:
        c.close()
        return {'success': False, 'error': 'Лимит активаций'}
    if c.execute('SELECT 1 FROM promo_activations WHERE promo_id=? AND telegram_id=?',
                 (p['id'], telegram_id)).fetchone():
        c.close()
        return {'success': False, 'error': 'Уже активирован'}
    u = c.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,)).fetchone()
    if not u:
        c.close()
        return {'success': False, 'error': 'Пользователь не найден'}
    c.execute('INSERT INTO promo_activations (promo_id,user_id,telegram_id) VALUES (?,?,?)',
              (p['id'], u['id'], telegram_id))
    c.execute('UPDATE promocodes SET current_activations=current_activations+1 WHERE id=?', (p['id'],))
    c.execute('UPDATE users SET balance_gold=balance_gold+? WHERE telegram_id=?',
              (p['gold_amount'], telegram_id))
    c.commit()
    c.close()
    return {'success': True, 'gold_amount': p['gold_amount'], 'code': code}


def add_notif(telegram_id, ntype, title, msg, order_id=None):
    c = get_conn()
    c.execute('INSERT INTO notifications (telegram_id,type,title,message,order_id) VALUES (?,?,?,?,?)',
              (telegram_id, ntype, title, msg, order_id))
    c.commit()
    c.close()


def get_notifs(telegram_id, limit=30):
    c = get_conn()
    n = [dict(r) for r in c.execute(
        'SELECT * FROM notifications WHERE telegram_id=? ORDER BY created_at DESC LIMIT ?',
        (telegram_id, limit)).fetchall()]
    c.close()
    return n


def mark_read(telegram_id):
    c = get_conn()
    c.execute('UPDATE notifications SET is_read=1 WHERE telegram_id=?', (telegram_id,))
    c.commit()
    c.close()


def unread_count(telegram_id):
    c = get_conn()
    n = c.execute('SELECT COUNT(*) as n FROM notifications WHERE telegram_id=? AND is_read=0',
                  (telegram_id,)).fetchone()['n']
    c.close()
    return n


def save_review(order_id, telegram_id, username, rating, comment, gold_amount, cashback, review_number):
    c = get_conn()
    c.execute('''INSERT INTO reviews (order_id,telegram_id,username,rating,comment,gold_amount,cashback_gold,review_number)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (order_id, telegram_id, username, rating, comment, gold_amount, cashback, review_number))
    c.execute('UPDATE orders SET review_submitted=1,review_rating=?,review_comment=?,review_number=? WHERE id=?',
              (rating, comment, review_number, order_id))
    c.execute('UPDATE users SET total_reviews=total_reviews+1,balance_gold=balance_gold+? WHERE telegram_id=?',
              (cashback, telegram_id))
    c.commit()
    c.close()


def get_review_count():
    c = get_conn()
    n = c.execute('SELECT COUNT(*) as n FROM reviews').fetchone()['n']
    c.close()
    return n


def get_review_cashback(gold_amount):
    for rule in REVIEW_CASHBACK_RULES:
        if rule['min'] <= gold_amount < rule['max']:
            return rule['gold']
    return 5


def get_compensation(gold_amount):
    for rule in COMPENSATION_RULES:
        if rule['min'] <= gold_amount < rule['max']:
            return rule['gold']
    return 5
