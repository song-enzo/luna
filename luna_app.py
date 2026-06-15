#!/usr/bin/env python3
"""LUNA ATELIER — Flask + SQLite 后端"""
import json, os, sqlite3, uuid, re, base64, mimetypes
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import Flask, request, session, jsonify, send_from_directory, g

app = Flask(__name__, static_folder='.')
app.secret_key = 'luna-atelier-secret-key-2026'

DB_PATH = os.path.join(os.path.dirname(__file__), 'luna.db')
PHOTO_DIR = os.path.join(os.path.dirname(__file__), 'photos')
os.makedirs(PHOTO_DIR, exist_ok=True)

# ── White-label config ──

SYSTEM_CONFIG = {
    'brand_name': 'Diana Moda',
    'brand_prefix': 'dm',
    'port': 8767
}

# ── Database helpers ──

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'guest', phone TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY, name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS fabrics (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            price_per_m REAL DEFAULT 0, composition TEXT DEFAULT '',
            stock REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS fabric_colors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fabric_id TEXT REFERENCES fabrics(id) ON DELETE CASCADE,
            name TEXT NOT NULL, hex TEXT NOT NULL, img_path TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS styles (
            code TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '未命名款式',
            category TEXT DEFAULT '', type TEXT DEFAULT 'solid',
            labor_cost REAL DEFAULT 0, iron_cost REAL DEFAULT 0,
            edge_note TEXT DEFAULT '', processing_note TEXT DEFAULT '',
            total_cost REAL DEFAULT 0, suggested_price REAL DEFAULT 0,
            created_at TEXT DEFAULT '', enabled INTEGER DEFAULT 1,
            main_photo TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS style_fabrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_code TEXT REFERENCES styles(code) ON DELETE CASCADE,
            name TEXT, price_per_m REAL DEFAULT 0,
            usage REAL DEFAULT 0, subtotal REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS style_accessories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_code TEXT REFERENCES styles(code) ON DELETE CASCADE,
            name TEXT, price_per_unit REAL DEFAULT 0,
            qty REAL DEFAULT 1, subtotal REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS style_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_code TEXT REFERENCES styles(code) ON DELETE CASCADE,
            file_path TEXT NOT NULL, sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, customer TEXT NOT NULL,
            date TEXT NOT NULL, total_qty INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            order_placed_completed INTEGER DEFAULT 1,
            marker_completed INTEGER DEFAULT 0,
            marker_length REAL DEFAULT 0, marker_hands INTEGER DEFAULT 1,
            marker_operator TEXT DEFAULT '', marker_time TEXT DEFAULT '',
            cutting_completed INTEGER DEFAULT 0, cutting_total INTEGER DEFAULT 0,
            cutting_operator TEXT DEFAULT '', cutting_time TEXT DEFAULT '',
            pickup_completed INTEGER DEFAULT 0, pickup_factory TEXT DEFAULT '',
            pickup_operator TEXT DEFAULT '', pickup_time TEXT DEFAULT '',
            shipping_completed INTEGER DEFAULT 0, shipping_qty INTEGER DEFAULT 0,
            shipping_operator TEXT DEFAULT '', shipping_time TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT REFERENCES orders(id) ON DELETE CASCADE,
            code TEXT NOT NULL, name TEXT DEFAULT '',
            color TEXT DEFAULT '', fabric TEXT DEFAULT '',
            price REAL DEFAULT 0, qty_data TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS cutting_layers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT REFERENCES orders(id) ON DELETE CASCADE,
            color TEXT NOT NULL, layers INTEGER DEFAULT 1,
            total INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cutting_checkmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT REFERENCES orders(id) ON DELETE CASCADE,
            label TEXT NOT NULL, checked INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            code TEXT NOT NULL, name TEXT DEFAULT '',
            color TEXT DEFAULT '', fabric TEXT DEFAULT '',
            price REAL DEFAULT 0, note TEXT DEFAULT '',
            qty_data TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS procacc (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, price REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS factories (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            phone TEXT DEFAULT '', workers INTEGER DEFAULT 0,
            hourly_rate REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS order_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            step TEXT NOT NULL,
            action TEXT DEFAULT '',
            operator TEXT DEFAULT '',
            detail TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    db.commit()
    # Migration: add order_operations for old databases
    try:
        db.execute("SELECT 1 FROM order_operations LIMIT 1")
    except:
        db.execute("""CREATE TABLE IF NOT EXISTS order_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            step TEXT DEFAULT '',
            action TEXT DEFAULT '',
            operator TEXT DEFAULT '',
            detail TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )""")
        db.commit()
    # Migration: add parent_id to users
    try:
        db.execute("SELECT parent_id FROM users LIMIT 1")
    except:
        db.execute("ALTER TABLE users ADD COLUMN parent_id TEXT DEFAULT ''")
        db.commit()
    # Migration: add note to order_items
    try:
        db.execute("SELECT note FROM order_items LIMIT 1")
    except:
        db.execute("ALTER TABLE order_items ADD COLUMN note TEXT DEFAULT ''")
        db.commit()
    # Migration: add address, tax_id, shop_name to users
    try:
        db.execute("SELECT address FROM users LIMIT 1")
    except:
        db.execute("ALTER TABLE users ADD COLUMN address TEXT DEFAULT ''")
        db.execute("ALTER TABLE users ADD COLUMN tax_id TEXT DEFAULT ''")
        db.execute("ALTER TABLE users ADD COLUMN shop_name TEXT DEFAULT ''")
        db.commit()
    # Migration: create login_logs table
    try:
        db.execute("SELECT 1 FROM login_logs LIMIT 1")
    except:
        db.execute("""CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            ip TEXT DEFAULT '',
            location TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            success INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )""")
        db.commit()
    # Migration: add marker_data (fabrics array) to orders
    try:
        db.execute("SELECT marker_data FROM orders LIMIT 1")
    except:
        db.execute("ALTER TABLE orders ADD COLUMN marker_data TEXT DEFAULT ''")
        db.commit()
    # Migration: add pickup_data (factory_price etc) to orders
    try:
        db.execute("SELECT pickup_data FROM orders LIMIT 1")
    except:
        db.execute("ALTER TABLE orders ADD COLUMN pickup_data TEXT DEFAULT ''")
        db.commit()
    # Migration: add shipping_data (color_received etc) to orders
    try:
        db.execute("SELECT shipping_data FROM orders LIMIT 1")
    except:
        db.execute("ALTER TABLE orders ADD COLUMN shipping_data TEXT DEFAULT ''")
        db.commit()
    # Migration: add cutting_data (fabrics structure) to orders
    try:
        db.execute("SELECT cutting_data FROM orders LIMIT 1")
    except:
        db.execute("ALTER TABLE orders ADD COLUMN cutting_data TEXT DEFAULT ''")
        db.commit()
    # Migration: add sub_customer to orders
    try:
        db.execute("SELECT sub_customer FROM orders LIMIT 1")
    except:
        db.execute("ALTER TABLE orders ADD COLUMN sub_customer TEXT DEFAULT ''")
        db.commit()
    # Migration: add loss_per_layer to fabrics
    try:
        db.execute("SELECT loss_per_layer FROM fabrics LIMIT 1")
    except:
        db.execute("ALTER TABLE fabrics ADD COLUMN loss_per_layer REAL DEFAULT 6")
        db.commit()
    # Migration: add rapporto_cm, verso_unico to fabric_colors
    try:
        db.execute("SELECT rapporto_cm FROM fabric_colors LIMIT 1")
    except:
        db.execute("ALTER TABLE fabric_colors ADD COLUMN rapporto_cm REAL DEFAULT 0")
        db.commit()
    try:
        db.execute("SELECT verso_unico FROM fabric_colors LIMIT 1")
    except:
        db.execute("ALTER TABLE fabric_colors ADD COLUMN verso_unico INTEGER DEFAULT 0")
        db.commit()
    # Migration: add anchor_x, anchor_y to fabric_colors
    try:
        db.execute("SELECT anchor_x FROM fabric_colors LIMIT 1")
    except:
        db.execute("ALTER TABLE fabric_colors ADD COLUMN anchor_x REAL DEFAULT 0")
        db.execute("ALTER TABLE fabric_colors ADD COLUMN anchor_y REAL DEFAULT 0")
        db.commit()
    # Migration: add components_data to order_items
    try:
        db.execute("SELECT components_data FROM order_items LIMIT 1")
    except:
        db.execute("ALTER TABLE order_items ADD COLUMN components_data TEXT DEFAULT '[]'")
        db.commit()
    # Migration: add components_data to cart_items
    try:
        db.execute("SELECT components_data FROM cart_items LIMIT 1")
    except:
        db.execute("ALTER TABLE cart_items ADD COLUMN components_data TEXT DEFAULT '[]'")
        db.commit()
    # Migration: add item_type, stampa_img_url, stampa_code to order_items
    try:
        db.execute("SELECT item_type FROM order_items LIMIT 1")
    except:
        db.execute("ALTER TABLE order_items ADD COLUMN item_type TEXT DEFAULT 'tinta_unita'")
        db.commit()
    try:
        db.execute("SELECT stampa_img_url FROM order_items LIMIT 1")
    except:
        db.execute("ALTER TABLE order_items ADD COLUMN stampa_img_url TEXT DEFAULT ''")
        db.execute("ALTER TABLE order_items ADD COLUMN stampa_code TEXT DEFAULT ''")
        db.commit()
    # Migration: add item_type, stampa_img_url, stampa_code to cart_items
    try:
        db.execute("SELECT item_type FROM cart_items LIMIT 1")
    except:
        db.execute("ALTER TABLE cart_items ADD COLUMN item_type TEXT DEFAULT 'tinta_unita'")
        db.commit()
    try:
        db.execute("SELECT stampa_img_url FROM cart_items LIMIT 1")
    except:
        db.execute("ALTER TABLE cart_items ADD COLUMN stampa_img_url TEXT DEFAULT ''")
        db.execute("ALTER TABLE cart_items ADD COLUMN stampa_code TEXT DEFAULT ''")
        db.commit()
    # Create stampe history table
    db.execute("""
        CREATE TABLE IF NOT EXISTS stampe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            img_url TEXT NOT NULL DEFAULT '',
            style_code TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    db.commit()
    # Migration: hash existing plaintext passwords
    rows = db.execute("SELECT id, password FROM users").fetchall()
    for row in rows:
        pw = row['password']
        if pw and not pw.startswith(('scrypt:', 'pbkdf2:', 'bcrypt:', 'argon2:')):
            db.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(pw), row['id']))
    # Ensure admin user exists in DB with hashed password
    admin_cnt = db.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0]
    if admin_cnt == 0:
        db.execute(
            "INSERT INTO users (id, username, password, name, role) VALUES (?,?,?,?,?)",
            ('admin', 'admin', generate_password_hash('admin'), '管理员', 'admin')
        )
    db.commit()
    # Seed virtual guest accounts if none exist
    cnt = db.execute("SELECT COUNT(*) FROM users WHERE role='guest'").fetchone()[0]
    if cnt == 0:
        guests = [
            ('g-seed1', 'enzo', 'enzo123', 'Enzo Song', 'guest', '', 1, '', 'Via Roma 15, Prato', 'IT01234567890', 'Sartoria Rossi'),
            ('g-seed2', 'laura', 'laura123', 'Laura Bianchi', 'guest', '', 1, '', 'Via Firenze 28, Firenze', 'IT09876543210', 'Boutique Laura'),
            ('g-seed3', 'wei', 'wei123', '王伟', 'guest', '', 1, '', 'Via Pistoiese 120, Prato', 'IT05678901234', '东方时装'),
            ('g-seed4', 'li', 'li123', '李婷', 'guest', '', 1, 'g-seed1', 'Via Cavour 5, Prato', 'IT03456789012', 'Tina Moda'),
            ('g-seed5', 'giuseppe', 'giuseppe123', 'Giuseppe Verdi', 'guest', '', 1, 'g-seed3', 'Piazza Duomo 8, Milano', 'IT07890123456', 'Alta Moda Milano'),
        ]
        for g in guests:
            db.execute(
                "INSERT OR REPLACE INTO users (id, username, password, name, role, phone, enabled, parent_id, address, tax_id, shop_name) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (g[0], g[1], generate_password_hash(g[2]), g[3], g[4], g[5], g[6], g[7], g[8], g[9], g[10])
            )
        db.commit()

def row_to_dict(row):
    if row is None: return None
    return dict(row)

def rows_to_dicts(rows):
    return [dict(r) for r in rows]

# ── Auth ──

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'unauthorized'}), 401
        db = get_db()
        user = db.execute("SELECT role FROM users WHERE username=?", (session['user_id'],)).fetchone()
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'forbidden'}), 403
        return f(*args, **kwargs)
    return decorated

def get_user():
    if 'user_id' in session:
        uid = session['user_id']
        role = session.get('role')
        name = session.get('name')
        # Look up user id from db for guests
        user_id = uid
        if role != 'admin':
            try:
                db = get_db()
                row = db.execute("SELECT id FROM users WHERE username=?", (uid,)).fetchone()
                if row: user_id = row['id']
            except: pass
        return {'username': uid, 'role': role, 'name': name, 'id': user_id}
    return None

def get_operator():
    """Get current operator name for logging"""
    u = get_user()
    if u: return u.get('name') or u.get('username', '')
    return 'anonymous'

def log_operation(order_id, step, action='', detail=''):
    """Record an operation in the history log"""
    db = get_db()
    operator = get_operator()
    db.execute(
        "INSERT INTO order_operations (order_id, step, action, operator, detail) VALUES (?,?,?,?,?)",
        (order_id, step, action, operator, detail)
    )
    db.commit()

# ── Login tracking ──

_ip_location_cache = {}

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr or ''

def get_ip_location(ip):
    if not ip:
        return ''
    if ip in _ip_location_cache:
        return _ip_location_cache[ip]
    if ip.startswith(('127.', '192.168.', '10.', '172.', '::1', 'localhost')):
        _ip_location_cache[ip] = '内网'
        return '内网'
    try:
        import urllib.request, json as _json
        url = f'http://ip-api.com/json/{ip}?fields=status,country,city,isp&lang=zh-CN'
        r = urllib.request.urlopen(url, timeout=3)
        data = _json.loads(r.read())
        if data.get('status') == 'success':
            parts = list(filter(None, [data.get('country', ''), data.get('city', ''), data.get('isp', '')]))
            loc = ' · '.join(parts) if parts else ''
            _ip_location_cache[ip] = loc
            return loc
    except:
        pass
    _ip_location_cache[ip] = ''
    return ''

def log_login(user_id, username, success, ip='', location=''):
    db = get_db()
    ua = ''
    try:
        ua = (request.headers.get('User-Agent', '') or '')[:200]
    except:
        pass
    db.execute(
        "INSERT INTO login_logs (user_id, username, ip, location, user_agent, success) VALUES (?,?,?,?,?,?)",
        (user_id, username, ip, location or '', ua, 1 if success else 0)
    )
    db.commit()

# ── Generic helpers for settings CRUD ──

TABLE_MAP = {
    'categories': 'categories',
    'procacc': 'procacc',
    'factories': 'factories',
    'fabrics': 'fabrics',
    'users': 'users',
    'guests': 'users',
    'employees': 'users',
}

def get_settings_list(key):
    """Get flat settings list"""
    tbl = TABLE_MAP.get(key)
    if not tbl: return None
    db = get_db()
    if key == 'guests':
        rows = db.execute("SELECT id, username, name, phone, enabled, parent_id, address, tax_id, shop_name FROM users WHERE role='guest'").fetchall()
        return rows_to_dicts(rows)
    elif key == 'employees':
        rows = db.execute("SELECT id, username, name, phone, enabled FROM users WHERE role='employee'").fetchall()
        return rows_to_dicts(rows)
    elif key == 'fabrics':
        rows = db.execute("SELECT * FROM fabrics ORDER BY name").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            colors = db.execute(
                "SELECT name, hex, img_path, rapporto_cm, verso_unico, anchor_x, anchor_y FROM fabric_colors WHERE fabric_id=? ORDER BY id",
                (d['id'],)
            ).fetchall()
            # Convert field names to camelCase for frontend compatibility
            d['pricePerM'] = d.pop('price_per_m', 0)
            d['lossPerLayer'] = d.pop('loss_per_layer', 6)
            d['colors'] = [{'name': c['name'], 'hex': c['hex'], 'img': c['img_path'] or '',
                            'rapporto_cm': c['rapporto_cm'] or 0, 'verso_unico': c['verso_unico'] or 0,
                            'anchorX': c['anchor_x'] or 0, 'anchorY': c['anchor_y'] or 0} for c in colors]
            result.append(d)
        return result
    elif key == 'factories':
        rows = db.execute("SELECT * FROM factories ORDER BY name").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['hourlyRate'] = d.pop('hourly_rate', 0)
            result.append(d)
        return result
    elif key == 'procacc':
        rows = db.execute("SELECT * FROM procacc ORDER BY name").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['price'] = d.get('price', 0)
            result.append(d)
        return result
    elif key == 'users':
        rows = db.execute("SELECT id, username, name, role, phone, enabled, parent_id, address, tax_id, shop_name FROM users ORDER BY name").fetchall()
        return rows_to_dicts(rows)
    else:
        rows = db.execute(f"SELECT * FROM {tbl} ORDER BY name").fetchall()
        return rows_to_dicts(rows)

def save_settings_list(key, data):
    """Replace entire settings list"""
    tbl = TABLE_MAP.get(key)
    if not tbl: return False
    db = get_db()
    if key == 'fabrics':
        db.execute("DELETE FROM fabric_colors")
        db.execute("DELETE FROM fabrics")
        for item in data:
            db.execute(
                "INSERT INTO fabrics (id, name, price_per_m, composition, stock, loss_per_layer) VALUES (?,?,?,?,?,?)",
                (item['id'], item['name'], item.get('pricePerM', 0),
                 item.get('composition', ''), item.get('stock', 0),
                 item.get('lossPerLayer', 6))
            )
            for c in item.get('colors', []):
                db.execute(
                    "INSERT INTO fabric_colors (fabric_id, name, hex, img_path, rapporto_cm, verso_unico, anchor_x, anchor_y) VALUES (?,?,?,?,?,?,?,?)",
                    (item['id'], c['name'], c['hex'], c.get('img_path', '') or c.get('img', ''),
                     c.get('rapporto_cm', 0), c.get('verso_unico', 0),
                     c.get('anchorX', 0), c.get('anchorY', 0))
                )
    elif key == 'guests':
        db.execute("DELETE FROM users WHERE role='guest'")
        for item in data:
            pw = item.get('password', '')
            # Only hash if not already hashed
            if pw and not pw.startswith(('scrypt:', 'pbkdf2:', 'bcrypt:', 'argon2:')):
                pw = generate_password_hash(pw)
            db.execute(
                "INSERT OR REPLACE INTO users (id, username, password, name, role, phone, enabled, parent_id, address, tax_id, shop_name) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (item.get('id', 'g-'+uuid.uuid4().hex[:6]), item.get('username',''),
                 pw, item.get('name', ''),
                 'guest', item.get('phone', ''), item.get('enabled', 1),
                 item.get('parent_id', ''),
                 item.get('address', ''), item.get('tax_id', ''),
                 item.get('shop_name', ''))
            )
    elif key == 'categories':
        db.execute("DELETE FROM categories")
        for item in data:
            db.execute("INSERT INTO categories (id, name) VALUES (?,?)",
                       (item['id'], item['name']))
    elif key == 'procacc':
        db.execute("DELETE FROM procacc")
        for item in data:
            db.execute("INSERT INTO procacc (id, name, price) VALUES (?,?,?)",
                       (item['id'], item['name'], item.get('price', 0)))
    elif key == 'factories':
        db.execute("DELETE FROM factories")
        for item in data:
            db.execute("INSERT INTO factories (id, name, phone, workers, hourly_rate) VALUES (?,?,?,?,?)",
                       (item['id'], item['name'], item.get('phone', ''),
                        item.get('workers', 0), item.get('hourlyRate', 0)))
    db.commit()
    return True

def save_single_order(order):
    """Save an order with all nested data"""
    db = get_db()
    o = order
    # Read old state BEFORE any writes for step transition logging
    old_order = db.execute("SELECT * FROM orders WHERE id=?", (o['id'],)).fetchone()
    # Main order
    db.execute("""INSERT OR REPLACE INTO orders
        (id, customer, date, total_qty, note, sub_customer,
         order_placed_completed, marker_completed, marker_length, marker_hands,
         marker_operator, marker_time, marker_data,
         cutting_completed, cutting_total, cutting_operator, cutting_time, cutting_data,
         pickup_completed, pickup_factory, pickup_operator, pickup_time, pickup_data,
         shipping_completed, shipping_qty, shipping_operator, shipping_time, shipping_data)
        VALUES (?,?,?,?,?,?, ?,?,?,?, ?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?,?,?,?)""",
        (o['id'], o.get('customer',''), o.get('date',''), o.get('total_qty',0), o.get('note',''), o.get('sub_customer',''),
         o.get('order_placed',{}).get('completed',1),
         o.get('marker_complete',{}).get('completed',0),
         o.get('marker_complete',{}).get('length',0),
         o.get('marker_complete',{}).get('hands',1),
         o.get('marker_complete',{}).get('operator',''),
         o.get('marker_complete',{}).get('time',''),
         json.dumps(o.get('marker_complete',{}), ensure_ascii=False),
         o.get('cutting_complete',{}).get('completed',0),
         o.get('cutting_complete',{}).get('total_cut',0),
         o.get('cutting_complete',{}).get('operator',''),
         o.get('cutting_complete',{}).get('time',''),
         json.dumps(o.get('cutting_complete',{}), ensure_ascii=False),
         o.get('pickup_complete',{}).get('completed',0),
         o.get('pickup_complete',{}).get('factory',''),
         o.get('pickup_complete',{}).get('operator',''),
         o.get('pickup_complete',{}).get('time',''),
         json.dumps(o.get('pickup_complete',{}), ensure_ascii=False),
         o.get('shipping_complete',{}).get('completed',0),
         o.get('shipping_complete',{}).get('qty',0),
         o.get('shipping_complete',{}).get('operator',''),
         o.get('shipping_complete',{}).get('time',''),
         json.dumps(o.get('shipping_complete',{}), ensure_ascii=False)))
    # Items
    db.execute("DELETE FROM order_items WHERE order_id=?", (o['id'],))
    for item in o.get('items', []):
        db.execute(
            "INSERT INTO order_items (order_id, code, name, color, fabric, price, qty_data, note, components_data, item_type, stampa_img_url, stampa_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (o['id'], item.get('code',''), item.get('name',''),
             item.get('color',''), item.get('fabric',''),
             item.get('price',0), json.dumps(item.get('qty',{}), ensure_ascii=False),
             item.get('note',''),
             json.dumps(item.get('components', []), ensure_ascii=False),
             item.get('item_type', 'tinta_unita'),
             item.get('stampa_img_url', ''),
             item.get('stampa_code', ''))
        )
    # Cutting layers
    db.execute("DELETE FROM cutting_layers WHERE order_id=?", (o['id'],))
    cl = o.get('cutting_complete',{}).get('layers',{})
    if isinstance(cl, dict) and len(cl) > 0:
        for color, data in cl.items():
            db.execute(
                "INSERT INTO cutting_layers (order_id, color, layers, total) VALUES (?,?,?,?)",
                (o['id'], color, data.get('layers',1), data.get('total',0))
            )
    # Cutting checkmarks
    db.execute("DELETE FROM cutting_checkmarks WHERE order_id=?", (o['id'],))
    ck = o.get('cutting_complete',{}).get('checkmarks',{})
    if isinstance(ck, dict):
        for label, checked in ck.items():
            db.execute(
                "INSERT INTO cutting_checkmarks (order_id, label, checked) VALUES (?,?,?)",
                (o['id'], label, 1 if checked else 0)
            )
    db.commit()
    # ── Log step transitions ──
    if old_order:
        step_map = {
            'order_placed': ('order_placed_completed', '下单'),
            'marker_complete': ('marker_completed', '打唛架'),
            'cutting_complete': ('cutting_completed', '裁剪'),
            'pickup_complete': ('pickup_completed', '待拿货'),
            'shipping_complete': ('shipping_completed', '发货'),
        }
        for step_key, (col, label) in step_map.items():
            old_val = old_order[col]
            new_val = o.get(step_key, {}).get('completed', 0)
            if old_val == 0 and new_val == 1:
                detail_parts = []
                step_data = o.get(step_key, {})
                if 'length' in step_data: detail_parts.append(f'长度: {step_data["length"]}m')
                if 'hands' in step_data: detail_parts.append(f'手数: {step_data["hands"]}')
                if 'total_cut' in step_data: detail_parts.append(f'裁剪: {step_data["total_cut"]}件')
                if 'factory' in step_data and step_data['factory']: detail_parts.append(f'工厂: {step_data["factory"]}')
                if 'qty' in step_data: detail_parts.append(f'数量: {step_data["qty"]}件')
                if 'operator' in step_data and step_data['operator']: detail_parts.append(f'操作: {step_data["operator"]}')
                log_operation(o['id'], step_key, f'{label}完成',
                    ' | '.join(detail_parts) if detail_parts else '')

    db.commit()

def read_order(order_id):
    """Read an order with all nested data into the original format"""
    db = get_db()
    row = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row: return None
    d = dict(row)
    result = {
        'id': d['id'],
        'customer': d['customer'],
        'date': d['date'],
        'total_qty': d['total_qty'],
        'note': d['note'],
        'sub_customer': d.get('sub_customer', ''),
        'order_placed': {'completed': d['order_placed_completed']},
        'marker_complete': json.loads(d['marker_data']) if d.get('marker_data') else {
            'completed': d['marker_completed'],
            'length': d['marker_length'],
            'hands': d['marker_hands'],
            'operator': d['marker_operator'],
            'time': d['marker_time']
        },
        'cutting_complete': json.loads(d['cutting_data']) if d.get('cutting_data') else {
            'completed': d['cutting_completed'],
            'total_cut': d['cutting_total'],
            'operator': d['cutting_operator'],
            'time': d['cutting_time'],
            'layers': {},
            'checkmarks': {}
        },
        'pickup_complete': json.loads(d['pickup_data']) if d.get('pickup_data') else {
            'completed': d['pickup_completed'],
            'factory': d['pickup_factory'],
            'operator': d['pickup_operator'],
            'time': d['pickup_time']
        },
        'shipping_complete': json.loads(d['shipping_data']) if d.get('shipping_data') else {
            'completed': d['shipping_completed'],
            'qty': d['shipping_qty'],
            'operator': d['shipping_operator'],
            'time': d['shipping_time']
        }
    }
    # Items
    items = db.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
    result['items'] = []
    for item in items:
        idict = dict(item)
        idict['qty'] = json.loads(idict.pop('qty_data', '{}'))
        idict['components'] = json.loads(idict.pop('components_data', '[]'))
        idict['item_type'] = idict.get('item_type', 'tinta_unita')
        idict['stampa_img_url'] = idict.get('stampa_img_url', '')
        idict['stampa_code'] = idict.get('stampa_code', '')
        result['items'].append(idict)
    # Cutting layers
    layers = db.execute("SELECT * FROM cutting_layers WHERE order_id=?", (order_id,)).fetchall()
    for l in layers:
        ld = dict(l)
        result['cutting_complete']['layers'][ld['color']] = {
            'layers': ld['layers'], 'total': ld['total']
        }
    # Checkmarks
    cks = db.execute("SELECT * FROM cutting_checkmarks WHERE order_id=?", (order_id,)).fetchall()
    for ck in cks:
        cd = dict(ck)
        result['cutting_complete']['checkmarks'][cd['label']] = cd['checked']
    return result

def read_all_orders():
    db = get_db()
    ids = db.execute("SELECT id FROM orders ORDER BY id DESC").fetchall()
    return [read_order(r['id']) for r in ids]

def save_single_style(style):
    """Save a style with all nested data"""
    db = get_db()
    s = style
    db.execute("""INSERT OR REPLACE INTO styles
        (code, name, category, type, labor_cost, iron_cost,
         edge_note, processing_note, total_cost, suggested_price,
         created_at, enabled, main_photo)
        VALUES (?,?,?,?,?,?, ?,?,?,?, ?,?,?)""",
        (s.get('code',''), s.get('name',''), s.get('category',''),
         s.get('type','solid'), s.get('laborCost',0), s.get('ironCost',0),
         s.get('edgeNote',''), s.get('processingNote',''),
         s.get('totalCost',0) or 0, s.get('suggestedPrice',0) or 0,
         s.get('createdAt',''), 1, s.get('mainPhoto','')))
    # Fabrics
    db.execute("DELETE FROM style_fabrics WHERE style_code=?", (s['code'],))
    for f in s.get('fabrics', []):
        db.execute(
            "INSERT INTO style_fabrics (style_code, name, price_per_m, usage, subtotal) VALUES (?,?,?,?,?)",
            (s['code'], f.get('name',''), f.get('pricePerM',0) or f.get('price',0),
             f.get('usage',0) or f.get('quantity',0),
             f.get('subtotal',0))
        )
    # Accessories
    db.execute("DELETE FROM style_accessories WHERE style_code=?", (s['code'],))
    for a in s.get('accessories', []):
        db.execute(
            "INSERT INTO style_accessories (style_code, name, price_per_unit, qty, subtotal) VALUES (?,?,?,?,?)",
            (s['code'], a.get('name',''), a.get('pricePerUnit',0) or a.get('price',0),
             a.get('qty',1), a.get('subtotal',0))
        )
    # Images
    db.execute("DELETE FROM style_images WHERE style_code=?", (s['code'],))
    for i, img in enumerate(s.get('images', [])):
        if img.startswith('data:'):
            # Decode base64 data URL and save as file
            try:
                import re, uuid
                meta_match = re.match(r'data:image/(\w+);base64,(.+)', img)
                if meta_match:
                    ext = meta_match.group(1)
                    if ext == 'jpeg': ext = 'jpg'
                    b64_data = meta_match.group(2)
                    file_data = base64.b64decode(b64_data)
                    filename = 'style_{}_{}.{}'.format(s['code'], uuid.uuid4().hex[:8], ext)
                    filepath = os.path.join(PHOTO_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(file_data)
                    db.execute(
                        "INSERT INTO style_images (style_code, file_path, sort_order) VALUES (?,?,?)",
                        (s['code'], 'photos/' + filename, i)
                    )
            except Exception as e:
                print('Error saving image for style {}: {}'.format(s['code'], e))
        elif not (img.startswith('/9j') or len(img) > 200):
            db.execute(
                "INSERT INTO style_images (style_code, file_path, sort_order) VALUES (?,?,?)",
                (s['code'], img, i)
            )
    db.commit()

def read_style(code):
    """Read a style with all nested data into original format"""
    db = get_db()
    row = db.execute("SELECT * FROM styles WHERE code=?", (code,)).fetchone()
    if not row: return None
    d = dict(row)
    result = {
        'code': d['code'],
        'name': d['name'],
        'category': d['category'],
        'type': d['type'],
        'laborCost': d['labor_cost'],
        'ironCost': d['iron_cost'],
        'edgeNote': d['edge_note'],
        'processingNote': d['processing_note'],
        'totalCost': d['total_cost'],
        'suggestedPrice': d['suggested_price'],
        'createdAt': d['created_at'],
        'mainPhoto': d['main_photo'],
        'fabrics': [],
        'accessories': [],
        'images': []
    }
    fabrics = db.execute("SELECT * FROM style_fabrics WHERE style_code=? ORDER BY id", (code,)).fetchall()
    for f in fabrics:
        fd = dict(f)
        entry = {
            'name': fd['name'],
            'pricePerM': fd['price_per_m'],
            'usage': fd['usage'],
            'subtotal': fd['subtotal']
        }
        # Resolve to global fabric ID for color lookup
        fab = db.execute("SELECT id FROM fabrics WHERE name=?", (fd['name'],)).fetchone()
        if fab:
            entry['id'] = fab['id']
        result['fabrics'].append(entry)
    accs = db.execute("SELECT * FROM style_accessories WHERE style_code=? ORDER BY id", (code,)).fetchall()
    for a in accs:
        ad = dict(a)
        result['accessories'].append({
            'name': ad['name'],
            'pricePerUnit': ad['price_per_unit'],
            'qty': ad['qty'],
            'subtotal': ad['subtotal']
        })
    imgs = db.execute("SELECT * FROM style_images WHERE style_code=? ORDER BY sort_order", (code,)).fetchall()
    for img in imgs:
        result['images'].append(img['file_path'])
    return result

def read_all_styles():
    db = get_db()
    codes = db.execute("SELECT code FROM styles ORDER BY code").fetchall()
    return [read_style(r['code']) for r in codes if read_style(r['code'])]

# ── API Routes ──

@app.route('/api/config', methods=['GET'])
def api_config():
    return jsonify({
        'brandName': SYSTEM_CONFIG['brand_name'],
        'brandPrefix': SYSTEM_CONFIG['brand_prefix'],
        'port': SYSTEM_CONFIG['port']
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')
    db = get_db()
    ip = get_client_ip()
    # Check if user exists at all
    existing = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not existing:
        log_login('', username, False, ip)
        return jsonify({'error': '账号不存在'}), 401
    # Check if disabled
    ud = dict(existing)
    if not ud.get('enabled', 1):
        log_login(ud.get('id', ''), username, False, ip)
        return jsonify({'error': '该账号已被禁用，请联系管理员'}), 401
    # 二级客人不能独立登录
    if ud.get('parent_id') and ud['role'] == 'guest':
        log_login(ud.get('id', ''), username, False, ip)
        return jsonify({'error': '该账号为二级账号，不能独立登录'}), 401
    if not check_password_hash(ud['password'], password):
        log_login(ud.get('id', ''), username, False, ip)
        return jsonify({'error': '密码错误'}), 401
    # Successful login — fetch location
    location = get_ip_location(ip)
    log_login(ud.get('id', ''), username, True, ip, location)
    session['user_id'] = ud['username']
    session['role'] = ud['role']
    session['name'] = ud['name']
    return jsonify({'username': ud['username'], 'role': ud['role'], 'name': ud['name'], 'id': ud['id']})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def api_me():
    return jsonify(get_user())

@app.route('/api/change-password', methods=['POST'])
@require_auth
def api_change_password():
    data = request.get_json(silent=True) or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if not new_password or len(new_password) < 4:
        return jsonify({'error': '新密码至少4位'}), 400
    db = get_db()
    username = session['user_id']
    row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    ud = dict(row)
    if not check_password_hash(ud['password'], old_password):
        return jsonify({'error': '原密码错误'}), 401
    new_hashed = generate_password_hash(new_password)
    db.execute("UPDATE users SET password=? WHERE username=?", (new_hashed, username))
    db.commit()
    return jsonify({'ok': True, 'message': '密码修改成功'})

# ── Generic data endpoints ──

@app.route('/api/data/<key>', methods=['GET'])
def api_data_get(key):
    if key in ('categories', 'procacc', 'factories', 'fabrics', 'guests', 'employees', 'users'):
        result = get_settings_list(key)
        return jsonify(result if result else [])
    elif key == 'styles':
        return jsonify(read_all_styles())
    elif key == 'orders':
        return jsonify(read_all_orders())
    elif key == 'cart':
        sid = session.get('user_id', 'anon')
        db = get_db()
        rows = db.execute("SELECT * FROM cart_items WHERE session_id=? ORDER BY id", (sid,)).fetchall()
        cart = []
        for r in rows:
            d = dict(r)
            d['qty'] = json.loads(d.pop('qty_data', '{}'))
            d['components'] = json.loads(d.pop('components_data', '[]'))
            d['item_type'] = d.get('item_type', 'tinta_unita')
            d['stampa_img_url'] = d.get('stampa_img_url', '')
            d['stampa_code'] = d.get('stampa_code', '')
            cart.append(d)
        return jsonify(cart)
    else:
        return jsonify([])

@app.route('/api/data/<key>', methods=['POST'])
@require_auth
def api_data_save(key):
    if key in ('categories', 'procacc', 'factories', 'fabrics', 'guests', 'employees'):
        data = request.get_json(silent=True) or []
        ok = save_settings_list(key, data)
        return jsonify({'ok': ok})
    return jsonify({'error': 'unsupported'}), 400

# ── Style endpoints ──

@app.route('/api/styles', methods=['GET'])
def api_styles_list():
    return jsonify(read_all_styles())

@app.route('/api/styles', methods=['POST'])
@require_auth
def api_styles_save():
    data = request.get_json(silent=True) or {}
    if not data.get('code'):
        return jsonify({'error': 'missing code'}), 400
    try:
        save_single_style(data)
        return jsonify({'ok': True, 'code': data['code']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/styles/<code>', methods=['GET'])
def api_styles_get(code):
    style = read_style(code)
    if not style:
        return jsonify({'error': 'not found'}), 404
    return jsonify(style)

@app.route('/api/styles/<code>', methods=['DELETE'])
@require_auth
def api_styles_delete(code):
    db = get_db()
    db.execute("DELETE FROM style_images WHERE style_code=?", (code,))
    db.execute("DELETE FROM style_fabrics WHERE style_code=?", (code,))
    db.execute("DELETE FROM style_accessories WHERE style_code=?", (code,))
    db.execute("DELETE FROM styles WHERE code=?", (code,))
    db.commit()
    return jsonify({'ok': True})

# ── Fabric add-color endpoint ──

@app.route('/api/fabrics/add-color', methods=['POST'])
def api_fabric_add_color():
    data = request.get_json(silent=True) or {}
    fabric_id = data.get('fabric_id')
    name = data.get('name', '').strip()
    hex_val = data.get('hex', '#ccc')
    img_path = data.get('img_path', '')
    if not fabric_id or not name:
        return jsonify({'error': 'missing fabric_id or name'}), 400
    db = get_db()
    db.execute(
        "INSERT INTO fabric_colors (fabric_id, name, hex, img_path, rapporto_cm, verso_unico) VALUES (?,?,?,?,?,?)",
        (fabric_id, name, hex_val, img_path,
         data.get('rapporto_cm', 0), data.get('verso_unico', 0))
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/fabrics/update-color', methods=['POST'])
def api_fabric_update_color():
    """Update color metadata fields (name, hex, img_path, rapporto_cm, verso_unico) by fabric_id + name"""
    data = request.get_json(silent=True) or {}
    fabric_id = data.get('fabric_id')
    old_name = data.get('old_name', '')
    name = data.get('name', '').strip()
    if not fabric_id or not old_name:
        return jsonify({'error': 'missing fabric_id or old_name'}), 400
    db = get_db()
    # Find the color by fabric_id and old_name
    existing = db.execute(
        "SELECT id FROM fabric_colors WHERE fabric_id=? AND name=?", (fabric_id, old_name)
    ).fetchone()
    if not existing:
        return jsonify({'error': 'color not found'}), 404
    cid = existing['id']
    update_fields = []
    update_vals = []
    if name:
        update_fields.append("name=?")
        update_vals.append(name)
    if 'hex' in data:
        update_fields.append("hex=?")
        update_vals.append(data['hex'])
    if 'img_path' in data:
        update_fields.append("img_path=?")
        update_vals.append(data['img_path'])
    if 'rapporto_cm' in data:
        update_fields.append("rapporto_cm=?")
        update_vals.append(data['rapporto_cm'])
    if 'verso_unico' in data:
        update_fields.append("verso_unico=?")
        update_vals.append(data['verso_unico'])
    if update_fields:
        update_vals.append(cid)
        db.execute(
            "UPDATE fabric_colors SET " + ",".join(update_fields) + " WHERE id=?",
            update_vals
        )
        db.commit()
    return jsonify({'ok': True})

# ── Quick add color (order page) + anchor points ──

@app.route('/api/order/quick-add-color', methods=['POST'])
def api_order_quick_add_color():
    """Quick-add a color from the order page: save image, update style_images, insert fabric_colors"""
    data = request.get_json(silent=True) or {}
    style_code = data.get('style_code', '')
    color_name = data.get('color_name', '').strip()
    image_data = data.get('image_data', '')  # base64 data URL
    hex_color = data.get('hex_color', '')    # hex color for solid mode
    if not style_code or not color_name:
        return jsonify({'error': 'missing style_code or color_name'}), 400
    db = get_db()

    # 1. Save image to photos/
    file_path = ''
    if image_data and image_data.startswith('data:image'):
        try:
            meta_match = re.match(r'data:image/(\w+);base64,(.+)', image_data)
            if meta_match:
                ext = meta_match.group(1)
                if ext == 'jpeg': ext = 'jpg'
                b64_data = meta_match.group(2)
                file_data = base64.b64decode(b64_data)
                filename = f'quick_{style_code}_{uuid.uuid4().hex[:8]}.{ext}'
                filepath = os.path.join(PHOTO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                file_path = 'photos/' + filename
        except Exception as e:
            print('Error saving quick-add image:', e)

    # 2. Insert into style_images
    if file_path:
        max_order_res = db.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM style_images WHERE style_code=?",
            (style_code,)
        ).fetchone()
        max_order = max_order_res[0] if max_order_res else -1
        db.execute(
            "INSERT INTO style_images (style_code, file_path, sort_order) VALUES (?,?,?)",
            (style_code, file_path, max_order + 1)
        )

    # 3. Extract anchor data
    anchor_x = data.get('anchor_x', 0)
    anchor_y = data.get('anchor_y', 0)
    has_anchor = bool(data.get('has_anchor'))

    # 4. Determine target fabric(s)
    target_fabric_id = data.get('fabric_id')
    fabric_ids = []
    if target_fabric_id:
        fabric_ids = [target_fabric_id]
    else:
        # Fallback: find all fabrics associated with this style
        sf_rows = db.execute(
            "SELECT DISTINCT sf.name FROM style_fabrics sf WHERE sf.style_code=?",
            (style_code,)
        ).fetchall()
        for sf in sf_rows:
            fabric = db.execute(
                "SELECT id FROM fabrics WHERE name=?", (sf['name'],)
            ).fetchone()
            if fabric:
                fabric_ids.append(fabric['id'])
        if not fabric_ids:
            sty = db.execute("SELECT code, name FROM styles WHERE code=?", (style_code,)).fetchone()
            # read_style not used here to keep it simple
        if not fabric_ids:
            first_fabric = db.execute("SELECT id FROM fabrics LIMIT 1").fetchone()
            if first_fabric:
                fabric_ids.append(first_fabric['id'])

    for fid in set(fabric_ids):
        existing = db.execute(
            "SELECT id FROM fabric_colors WHERE fabric_id=? AND name=?",
            (fid, color_name)
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO fabric_colors (fabric_id, name, hex, img_path, anchor_x, anchor_y) VALUES (?,?,?,?,?,?)",
                (fid, color_name, hex_color or '#cccccc', file_path,
                 anchor_x if has_anchor else 0,
                 anchor_y if has_anchor else 0)
            )
        elif file_path:
            # Update img_path if we have a new image
            db.execute(
                "UPDATE fabric_colors SET img_path=?, anchor_x=?, anchor_y=? WHERE id=?",
                (file_path,
                 anchor_x if has_anchor else 0,
                 anchor_y if has_anchor else 0,
                 existing['id'])
            )

    db.commit()

    # Return updated fabrics + image path
    updated_fabrics = get_settings_list('fabrics')
    return jsonify({
        'ok': True,
        'image_path': file_path,
        'fabrics': updated_fabrics
    })

@app.route('/api/order/add-anchor-color', methods=['POST'])
def api_order_add_anchor_color():
    """Add an additional anchor-point color to an existing image"""
    data = request.get_json(silent=True) or {}
    style_code = data.get('style_code', '')
    color_name = data.get('color_name', '').strip()
    image_path = data.get('image_path', '')
    anchor_x = data.get('anchor_x', 0)
    anchor_y = data.get('anchor_y', 0)
    if not style_code or not color_name or not image_path:
        return jsonify({'error': 'missing fields'}), 400
    db = get_db()

    # Find associated fabrics and insert
    sf_rows = db.execute(
        "SELECT DISTINCT sf.name FROM style_fabrics sf WHERE sf.style_code=?",
        (style_code,)
    ).fetchall()
    fabric_ids = []
    for sf in sf_rows:
        fabric = db.execute("SELECT id FROM fabrics WHERE name=?", (sf['name'],)).fetchone()
        if fabric:
            fabric_ids.append(fabric['id'])

    if not fabric_ids:
        first_fabric = db.execute("SELECT id FROM fabrics LIMIT 1").fetchone()
        if first_fabric:
            fabric_ids.append(first_fabric['id'])

    for fid in set(fabric_ids):
        existing = db.execute(
            "SELECT id FROM fabric_colors WHERE fabric_id=? AND name=?",
            (fid, color_name)
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO fabric_colors (fabric_id, name, hex, img_path, anchor_x, anchor_y) VALUES (?,?,?,?,?,?)",
                (fid, color_name, '#cccccc', image_path, anchor_x, anchor_y)
            )

    db.commit()
    updated_fabrics = get_settings_list('fabrics')
    return jsonify({'ok': True, 'fabrics': updated_fabrics})

# ── Stampa / Print endpoints ──

@app.route('/api/history-stampe', methods=['GET'])
def api_history_stampe():
    """Return deduplicated list of all historical stampa images from past orders"""
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT stampa_code, stampa_img_url FROM order_items WHERE stampa_img_url IS NOT NULL AND stampa_img_url != '' ORDER BY stampa_code"
    ).fetchall()
    result = [{'code': r['stampa_code'], 'img_url': r['stampa_img_url']} for r in rows if r['stampa_code']]

    # Also include from stampe table
    stampe_rows = db.execute("SELECT code, img_url FROM stampe ORDER BY id DESC").fetchall()
    seen = {r['code'] for r in rows if r['stampa_code']}
    for sr in stampe_rows:
        if sr['code'] and sr['code'] not in seen:
            result.append({'code': sr['code'], 'img_url': sr['img_url']})
            seen.add(sr['code'])

    return jsonify(result)

@app.route('/api/stampe/upload', methods=['POST'])
def api_stampe_upload():
    """Upload a new stampa image and record it in the stampe history table"""
    data = request.get_json(silent=True) or {}
    stampa_code = data.get('stampa_code', '').strip()
    image_data = data.get('image_data', '')  # base64
    style_code = data.get('style_code', '')
    if not stampa_code or not image_data:
        return jsonify({'error': 'missing stampa_code or image_data'}), 400

    file_path = ''
    if image_data.startswith('data:image'):
        try:
            meta_match = re.match(r'data:image/(\w+);base64,(.+)', image_data)
            if meta_match:
                ext = meta_match.group(1)
                if ext == 'jpeg': ext = 'jpg'
                b64_data = meta_match.group(2)
                file_data = base64.b64decode(b64_data)
                filename = f'stampa_{stampa_code}_{uuid.uuid4().hex[:8]}.{ext}'
                filepath = os.path.join(PHOTO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                file_path = 'photos/' + filename
        except Exception as e:
            print('Error saving stampa image:', e)
            return jsonify({'error': str(e)}), 500

    if not file_path:
        return jsonify({'error': 'failed to save image'}), 500

    db = get_db()
    # Insert into stampe history table
    db.execute(
        "INSERT INTO stampe (code, img_url, style_code) VALUES (?,?,?)",
        (stampa_code, file_path, style_code)
    )
    db.commit()

    return jsonify({'ok': True, 'img_url': file_path})

# ── Order endpoints ──

@app.route('/api/orders', methods=['GET'])
def api_orders_list():
    return jsonify(read_all_orders())

@app.route('/api/orders', methods=['POST'])
@require_auth
def api_orders_save():
    data = request.get_json(silent=True) or {}
    # 支持批量保存（saveOrders 传入整个数组）
    if isinstance(data, list):
        saved = 0
        for order in data:
            if isinstance(order, dict) and order.get('id'):
                try:
                    save_single_order(order)
                    saved += 1
                except Exception:
                    pass
        return jsonify({'ok': True, 'count': saved})
    if not data.get('id'):
        return jsonify({'error': 'missing id'}), 400
    try:
        save_single_order(data)
        return jsonify({'ok': True, 'id': data['id']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
def api_orders_get(order_id):
    order = read_order(order_id)
    if not order:
        return jsonify({'error': 'not found'}), 404
    return jsonify(order)

@app.route('/api/orders/<order_id>', methods=['DELETE'])
@require_admin
def api_order_delete(order_id):
    db = get_db()
    db.execute("DELETE FROM cutting_checkmarks WHERE order_id=?", (order_id,))
    db.execute("DELETE FROM cutting_layers WHERE order_id=?", (order_id,))
    db.execute("DELETE FROM order_operations WHERE order_id=?", (order_id,))
    db.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
    db.execute("DELETE FROM orders WHERE id=?", (order_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Cart endpoints ──

@app.route('/api/cart', methods=['GET', 'POST'])
def api_cart():
    """GET: list cart, POST: cart actions (no auth required — anonymous cart via session)"""
    if 'cart_id' not in session:
        import secrets
        session['cart_id'] = 'cart-' + secrets.token_hex(8)
    sid = session['cart_id']
    db = get_db()

    if request.method == 'GET':
        rows = db.execute("SELECT * FROM cart_items WHERE session_id=? ORDER BY id", (sid,)).fetchall()
        cart = []
        for r in rows:
            d = dict(r)
            d['qty'] = json.loads(d.pop('qty_data', '{}'))
            d['components'] = json.loads(d.pop('components_data', '[]'))
            d['item_type'] = d.get('item_type', 'tinta_unita')
            d['stampa_img_url'] = d.get('stampa_img_url', '')
            d['stampa_code'] = d.get('stampa_code', '')
            cart.append(d)
        return jsonify(cart)

    # POST
    data = request.get_json(silent=True) or {}
    action = data.get('action', '')
    if action == 'add':
        qty = data.get('qty', {})
        code = data.get('code','')
        color = data.get('color','')
        components = data.get('components', [])
        note = data.get('note', '')
        item_type = data.get('item_type', 'tinta_unita')
        stampa_img_url = data.get('stampa_img_url', '')
        stampa_code = data.get('stampa_code', '')
        components_json = json.dumps(components, ensure_ascii=False) if components else '[]'
        # For merge detection: use color+components+stampa combo key
        existing = db.execute(
            "SELECT id, qty_data FROM cart_items WHERE session_id=? AND code=? AND color=? AND components_data=? AND stampa_code=?",
            (sid, code, color, components_json, stampa_code)
        ).fetchone()
        if existing:
            old_qty = json.loads(existing['qty_data'])
            for k, v in qty.items():
                old_qty[k] = old_qty.get(k, 0) + v
            db.execute(
                "UPDATE cart_items SET qty_data=?, name=?, fabric=?, price=?, item_type=?, stampa_img_url=? WHERE id=?",
                (json.dumps(old_qty, ensure_ascii=False),
                 data.get('name',''), data.get('fabric',''),
                 data.get('price',0), item_type, stampa_img_url, existing['id'])
            )
        else:
            db.execute(
                "INSERT INTO cart_items (session_id, code, name, color, fabric, price, note, qty_data, components_data, item_type, stampa_img_url, stampa_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, code, data.get('name',''),
                 color, data.get('fabric',''),
                 data.get('price',0), note,
                 json.dumps(qty, ensure_ascii=False),
                 components_json, item_type, stampa_img_url, stampa_code)
            )
        # One note per code group — if note provided, update ALL items of this code
        if note:
            db.execute(
                "UPDATE cart_items SET note=? WHERE session_id=? AND code=?",
                (note, sid, code)
            )
    elif action == 'remove':
        db.execute("DELETE FROM cart_items WHERE id=? AND session_id=?", (data.get('id'), sid))
    elif action == 'update_qty':
        row = db.execute("SELECT * FROM cart_items WHERE id=? AND session_id=?", (data.get('id'), sid)).fetchone()
        if row:
            qty = json.loads(row['qty_data'])
            size = data.get('size')
            delta = data.get('delta', 0)
            qty[size] = max(0, qty.get(size, 0) + delta)
            db.execute("UPDATE cart_items SET qty_data=? WHERE id=?", (json.dumps(qty, ensure_ascii=False), data['id']))
    elif action == 'update_note':
        db.execute("UPDATE cart_items SET note=? WHERE id=? AND session_id=?", (data.get('note',''), data.get('id'), sid))
    elif action == 'clear':
        db.execute("DELETE FROM cart_items WHERE session_id=?", (sid,))
    db.commit()
    # Return updated cart
    rows = db.execute("SELECT * FROM cart_items WHERE session_id=?", (sid,)).fetchall()
    cart = []
    for r in rows:
        d = dict(r)
        d['qty'] = json.loads(d.pop('qty_data', '{}'))
        d['components'] = json.loads(d.pop('components_data', '[]'))
        d['item_type'] = d.get('item_type', 'tinta_unita')
        d['stampa_img_url'] = d.get('stampa_img_url', '')
        d['stampa_code'] = d.get('stampa_code', '')
        cart.append(d)
    return jsonify({'ok': True, 'cart': cart})

@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    sid = session.get('cart_id', 'anon')
    db = get_db()
    rows = db.execute("SELECT * FROM cart_items WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    if not rows:
        return jsonify({'error': 'cart empty'}), 400
    from datetime import date, datetime
    today = date.today().isoformat()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    body = request.get_json(silent=True) or {}
    order_customer = body.get('customer', '')
    customer = order_customer if order_customer else session.get('name', sid)
    order_note = body.get('note', '')
    order_sub_customer = body.get('sub_customer', '')

    # Group cart items by style code → separate orders
    groups = {}  # code -> items list
    for r in rows:
        code = r['code']
        if code not in groups: groups[code] = []
        groups[code].append(r)

    base_count = db.execute("SELECT COUNT(*) FROM orders WHERE date=?", (today,)).fetchone()[0]
    orders_created = []
    idx = 0
    for code, grp in groups.items():
        idx += 1
        order_id = f'ORD-{today}-{base_count + idx:02d}'
        items = []
        total_qty = 0
        for r in grp:
            qty = json.loads(r['qty_data'])
            item_total = sum(qty.values())
            components = json.loads(r['components_data']) if r['components_data'] else []
            items.append({
                'code': r['code'], 'name': r['name'],
                'color': r['color'], 'fabric': r['fabric'],
                'price': r['price'], 'qty': qty,
                'note': r['note'] or '',
                'components': components,
                'item_type': r['item_type'] or 'tinta_unita',
                'stampa_img_url': r['stampa_img_url'] or '',
                'stampa_code': r['stampa_code'] or ''
            })
            total_qty += item_total
        order = {
            'id': order_id,
            'customer': customer,
            'sub_customer': order_sub_customer,
            'date': today,
            'items': items,
            'total_qty': total_qty,
            'note': order_note,
            'order_placed': {'completed': 1},
            'marker_complete': {'completed': 0, 'length': 0, 'hands': 1, 'operator': '', 'time': ''},
            'cutting_complete': {'completed': 0, 'layers': {}, 'total_cut': 0, 'operator': '', 'time': '', 'checkmarks': {}},
            'pickup_complete': {'completed': 0, 'factory': '', 'operator': '', 'time': ''},
            'shipping_complete': {'completed': 0, 'qty': 0, 'operator': '', 'time': ''}
        }
        save_single_order(order)
        log_operation(order_id, 'order_placed', '下单',
            f'客户: {customer} | 款式: {code} | 件数: {total_qty}')
        orders_created.append(order)

    db.execute("DELETE FROM cart_items WHERE session_id=?", (sid,))
    db.commit()
    return jsonify({'ok': True, 'orders': orders_created})

@app.route('/api/orders/<order_id>/operations', methods=['GET'])
def api_order_operations(order_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM order_operations WHERE order_id=? ORDER BY id DESC",
        (order_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/export/csv')
def api_export_csv():
    import datetime
    month = request.args.get('month', '')
    orders = read_all_orders()
    # Filter shipped and by month
    result = []
    for o in orders:
        if not o.get('shipping_complete',{}).get('time'):
            continue
        ship_time = o['shipping_complete']['time']
        ship_month = ship_time[:7]
        if month and ship_month != month:
            continue
        result.append(o)
    # Build CSV
    import io, csv as csv_module
    output = io.StringIO()
    writer = csv_module.writer(output)
    # Collect all sizes
    all_sizes = {}
    for o in result:
        for item in o.get('items', []):
            for s in item.get('qty', {}).keys():
                all_sizes[s] = True
    size_order = ['XXS','XS','S','M','L','XL','XXL','XXXL','UNICA','F']
    size_keys = sorted(all_sizes.keys(), key=lambda s: size_order.index(s) if s in size_order else 999)
    header = ['订单号','编号','颜色','下单备注','二级客人'] + size_keys + ['订单总数','裁剪总数','发货总数']
    writer.writerow(header)
    for o in result:
        order_note = (o.get('note','') or '').replace(',','，')
        order_sub = (o.get('sub_customer','') or '')
        ship_total = o.get('shipping_complete',{}).get('qty',0)
        cut_layers = o.get('cutting_complete',{}).get('layers',{})
        order_total = o.get('total_qty',0)
        if o.get('items'):
            for item in o['items']:
                row = [o['id'], item.get('code',''), item.get('color',''), order_note, order_sub]
                item_total = 0
                for s in size_keys:
                    v = item.get('qty',{}).get(s, 0)
                    item_total += v
                    row.append(v)
                cut_qty = 0
                if cut_layers and item.get('color') in cut_layers:
                    cut_qty = cut_layers[item['color']].get('total',0)
                ship_qty = round(ship_total * item_total / order_total) if order_total > 0 else 0
                row.extend([item_total, cut_qty, ship_qty])
                writer.writerow(row)
        else:
            row = [o['id'], '', '', order_note] + [0]*len(size_keys) + [order_total, cut_layers.get('total_cut',0) or 0, ship_total]
            writer.writerow(row)
    csv_content = output.getvalue()
    output.close()
    return csv_content, 200, {'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': f'attachment; filename=luna_{month or "all"}.csv'}

@app.route('/api/init-defaults', methods=['POST'])
def api_init_defaults():
    db = get_db()
    # Only if empty
    if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        defaults = [
            ('c0','西装外套'),('c1','西装裤'),('c2','裙装'),('c3','衬衫'),('c4','连衣裙')
        ]
        for cid, cname in defaults:
            db.execute("INSERT INTO categories (id, name) VALUES (?,?)", (cid, cname))
    if db.execute("SELECT COUNT(*) FROM procacc").fetchone()[0] == 0:
        defaults = [
            ('p0','裁剪',8),('p1','车缝',25),('p2','烫扣',5),('p3','锁边',3),
            ('p4','熨烫',4),('p5','包装',2),('p6','拉链',2),('p7','纽扣',1)
        ]
        for pid, pname, pprice in defaults:
            db.execute("INSERT INTO procacc (id, name, price) VALUES (?,?,?)", (pid, pname, pprice))
    if db.execute("SELECT COUNT(*) FROM fabrics").fetchone()[0] == 0:
        defaults = [
            {'id':'f0','name':'精纺羊毛','price_per_m':28,'composition':'羊毛100%','stock':50,
             'colors':[{'name':'黑色','hex':'#1a1a1a'},{'name':'驼色','hex':'#c9a96e'}]},
            {'id':'f1','name':'素罗马','price_per_m':12,'composition':'涤纶95% 氨纶5%','stock':100,
             'colors':[{'name':'黑色','hex':'#1a1a1a'},{'name':'白色','hex':'#f5f5f5'}]}
        ]
        for fb in defaults:
            db.execute("INSERT INTO fabrics (id, name, price_per_m, composition, stock) VALUES (?,?,?,?,?)",
                       (fb['id'], fb['name'], fb['price_per_m'], fb['composition'], fb['stock']))
            for c in fb['colors']:
                db.execute("INSERT INTO fabric_colors (fabric_id, name, hex) VALUES (?,?,?)",
                          (fb['id'], c['name'], c['hex']))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/upload', methods=['POST'])
@require_auth
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'no file'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'empty filename'}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg','.jpeg','.png','.webp'):
        return jsonify({'error': 'unsupported format'}), 400
    # Generate unique filename
    fname = uuid.uuid4().hex + ext
    save_path = os.path.join(PHOTO_DIR, fname)
    file.save(save_path)
    # Also save a thumbnail for style images (max 1200px wide)
    try:
        from PIL import Image
        img = Image.open(save_path)
        if img.width > 1200:
            ratio = 1200 / img.width
            img = img.resize((1200, int(img.height * ratio)), Image.LANCZOS)
            img.save(save_path, optimize=True, quality=85)
    except ImportError:
        pass  # PIL not available, keep original
    return jsonify({'ok': True, 'path': f'photos/{fname}'})

# ── Login logs & user control ──

@app.route('/api/login-logs', methods=['GET'])
@require_admin
def api_login_logs():
    username = request.args.get('username', '')
    limit = min(int(request.args.get('limit', 200)), 1000)
    db = get_db()
    if username:
        rows = db.execute(
            "SELECT * FROM login_logs WHERE username=? ORDER BY id DESC LIMIT ?",
            (username, limit)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM login_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/users/<username>/toggle-enabled', methods=['POST'])
@require_admin
def api_toggle_enabled(username):
    if username == 'admin':
        return jsonify({'error': '不能禁用管理员账号'}), 400
    db = get_db()
    row = db.execute("SELECT enabled FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    new_val = 0 if row['enabled'] else 1
    db.execute("UPDATE users SET enabled=? WHERE username=?", (new_val, username))
    db.commit()
    status_text = '已启用' if new_val else '已禁用'
    log_operation('system', 'user_toggle', f'用户 {username} {status_text}')
    return jsonify({'ok': True, 'enabled': new_val, 'status_text': status_text})

# ── Backup ──

@app.route('/api/backup', methods=['POST'])
@require_admin
def api_backup():
    """Create a timestamped backup of the SQLite database"""
    from datetime import datetime
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'luna_backup_{timestamp}.db')
    try:
        db = get_db()
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('luna_backup_') and f.endswith('.db')], reverse=True)
        for old in backups[30:]:
            try: os.remove(os.path.join(backup_dir, old))
            except: pass
        return jsonify({'ok': True, 'filename': os.path.basename(backup_path), 'size': os.path.getsize(backup_path)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backups', methods=['GET'])
@require_admin
def api_backups_list():
    """List available backups"""
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    if not os.path.isdir(backup_dir):
        return jsonify([])
    backups = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        if f.startswith('luna_backup_') and f.endswith('.db'):
            fpath = os.path.join(backup_dir, f)
            backups.append({
                'filename': f,
                'size': os.path.getsize(fpath),
                'mtime': os.path.getmtime(fpath)
            })
    return jsonify(backups)

# ── Static files ──

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_files(path):
    if path.startswith('photos/'):
        return send_from_directory(PHOTO_DIR, path[7:])
    return app.send_static_file(path)

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})

@app.after_request
def no_cache(response):
    if request.path.endswith('.html') or request.path.endswith('.js'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ── Main ──

if __name__ == '__main__':
    with app.app_context():
        init_db()
    port = SYSTEM_CONFIG['port']
    print(f'LUNA Flask Server on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
