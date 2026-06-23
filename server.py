import json, os, mimetypes, re, sys
from http.server import HTTPServer, BaseHTTPRequestHandler

B = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(B, '_data')

def load(f):
    p = os.path.join(D, f)
    if not os.path.isfile(p): return None
    try:
        with open(p, encoding='utf-8') as h: return json.load(h)
    except: return None

def save(f, data):
    p = os.path.join(D, f)
    with open(p, 'w', encoding='utf-8') as h:
        json.dump(data, h, ensure_ascii=False)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split('?')[0]
        # API endpoints — exact match
        api = {
            '/api/styles': 'luna_styles_data.json',
            '/api/data/styles': 'luna_styles_data.json',
            '/api/orders': 'luna_orders_data.json',
            '/api/cart': 'luna_cart_data.json',
            '/api/data/guests': 'luna_settings_guests.json',
            '/api/data/fabrics': 'luna_settings_fabrics.json',
            '/api/data/categories': 'luna_settings_categories.json',
            '/api/data/procacc': 'luna_settings_procacc.json',
            '/api/data/factories': 'luna_settings_factories.json',
        }
        if p in api:
            d = load(api[p])
            return self.json(200, d if d is not None else ([] if 'cart' not in p else {}))
        if p == '/api/me':
            return self.json(200, {'username': 'admin', 'name': 'Admin'})
        # /api/styles/<code> — individual style lookup
        m = re.match(r'^/api/styles/(.+)$', p)
        if m:
            code = m.group(1)
            styles = load('luna_styles_data.json') or []
            for s in styles:
                if s.get('code') == code:
                    return self.json(200, s)
            return self.json(404, {'error': 'style not found'})
        # /api/print-warehouse/groups
        if p == '/api/print-warehouse/groups':
            pw = load('luna_print_warehouse.json') or []
            return self.json(200, pw)
        # /api/print-warehouse/by-style/<code>
        m = re.match(r'^/api/print-warehouse/by-style/(.+)$', p)
        if m:
            code = m.group(1)
            pw = load('luna_print_warehouse.json') or []
            matches = [x for x in pw if x.get('print_code') == code]
            return self.json(200, matches)
        # Static file
        fp = os.path.join(B, p.lstrip('/') if p != '/' else 'order-print.html')
        if not os.path.isfile(fp):
            return self.json(404, {'error': 'not found'})
        ct, _ = mimetypes.guess_type(fp)
        self.send_response(200)
        self.send_header('Content-Type', ct or 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            with open(fp, 'rb') as f:
                self.wfile.write(f.read())
        except: pass

    def do_POST(self):
        p = self.path.split('?')[0]
        l = int(self.headers.get('Content-Length', 0))
        b = self.rfile.read(l)
        try:
            d = json.loads(b) if b else {}
        except:
            d = {}
        # Save order
        if p == '/api/orders':
            try:
                ex = load('luna_orders_data.json') or []
                ex.append(d)
                save('luna_orders_data.json', ex)
                return self.json(200, {'ok': True})
            except:
                return self.json(400, {'error': 'bad'})
        # Cart operations
        if p == '/api/cart':
            action = d.get('action', '')
            cart = load('luna_cart_data.json') or []
            if action == 'add':
                cart.append({
                    'id': len(cart) + 1,
                    'code': d.get('code', ''),
                    'name': d.get('name', ''),
                    'color': d.get('color', ''),
                    'fabric': d.get('fabric', ''),
                    'price': d.get('price', 0),
                    'note': d.get('note', ''),
                    'qty': d.get('qty', {}),
                    'item_type': d.get('item_type', ''),
                    'stampa_img_url': d.get('stampa_img_url', ''),
                    'sku_code': d.get('sku_code', ''),
                    'print_id': d.get('print_id', 0),
                })
            elif action == 'remove':
                idx = d.get('id')
                cart = [c for c in cart if c.get('id') != idx]
            elif action == 'update_qty':
                for c in cart:
                    if c.get('id') == d.get('id'):
                        sz = d.get('size')
                        delta = d.get('delta', 0)
                        c['qty'][sz] = max(0, c['qty'].get(sz, 0) + delta)
            elif action == 'clear':
                cart = []
            save('luna_cart_data.json', cart)
            return self.json(200, {'ok': True, 'cart': cart})
        # Checkout (simple: saves order from cart)
        if p == '/api/checkout':
            cart = load('luna_cart_data.json') or []
            if not cart:
                return self.json(400, {'error': 'cart empty'})
            from datetime import date
            today = date.today().isoformat()
            orders = load('luna_orders_data.json') or []
            count = sum(1 for o in orders if o.get('date') == today)
            order_id = f'ORD-{today}-{count+1:02d}'
            items = []
            total_qty = 0
            for c in cart:
                qty = c.get('qty', {})
                item_total = sum(qty.values())
                items.append({
                    'code': c.get('code',''), 'name': c.get('name',''),
                    'color': c.get('color',''), 'fabric': c.get('fabric',''),
                    'price': c.get('price',0), 'qty': qty
                })
                total_qty += item_total
            order = {
                'id': order_id, 'customer': d.get('guest', ''),
                'date': today, 'items': items, 'total_qty': total_qty,
                'note': d.get('note', ''),
                'order_placed': {'completed': 1},
                'marker_complete': {'completed': 0},
                'cutting_complete': {'completed': 0},
                'pickup_complete': {'completed': 0},
                'shipping_complete': {'completed': 0},
            }
            orders.append(order)
            save('luna_orders_data.json', orders)
            save('luna_cart_data.json', [])
            return self.json(200, {'ok': True, 'order': order})
        # AI analyze pattern (stub)
        if p == '/api/ai/analyze-pattern':
            return self.json(200, {
                'status': 'success',
                'data': {
                    'pattern_no': 'PAT-001',
                    'cycle_size': '9cm',
                    'master_image': '',
                    'colorways': []
                }
            })
        # AI confirm pattern (stub)
        if p == '/api/ai/confirm-pattern':
            saved = []
            for i, cw in enumerate(d.get('colorways', [])):
                saved.append({'id': i+1, 'sku_code': cw.get('sku_code', '')})
            return self.json(200, {'status': 'success', 'saved': saved})
        return self.json(404, {'error': 'nf'})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def json(self, c, o):
        try:
            b = json.dumps(o, ensure_ascii=False).encode('utf-8')
            self.send_response(c)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', len(b))
            self.end_headers()
            self.wfile.write(b)
        except: pass

    def log_message(self, *a): pass

HTTPServer(('0.0.0.0', 8765), H).serve_forever()
