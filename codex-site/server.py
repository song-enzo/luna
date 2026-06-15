#!/usr/bin/env python3
"""LUNA ATELIER — 简易服务器（静态文件 + 数据持久化）"""
import json, os, mimetypes, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

DATA_DIR = os.path.join(os.path.dirname(__file__), '_data')
os.makedirs(DATA_DIR, exist_ok=True)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/data':
            self._send_json(200, self._load_all())
            return
        # Static file
        path = self.path.split('?')[0]
        if path == '/': path = '/settings.html'
        filepath = os.path.join(os.path.dirname(__file__), path.lstrip('/'))
        if not os.path.isfile(filepath):
            self.send_response(404)
            self.end_headers()
            return
        ctype, _ = mimetypes.guess_type(filepath)
        self.send_response(200)
        self.send_header('Content-Type', ctype or 'application/octet-stream')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())

    def do_POST(self):
        if self.path == '/api/data':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                self._save_all(data)
                self._send_json(200, {'ok': True, 'saved': len(data)})
            except Exception as e:
                self._send_json(400, {'error': str(e)})
            return
        self._send_json(404, {'error': 'not found'})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _load_all(self):
        data = {}
        for fname in os.listdir(DATA_DIR):
            fpath = os.path.join(DATA_DIR, fname)
            if fname.endswith('.json') and os.path.isfile(fpath):
                try:
                    with open(fpath, 'r') as f:
                        data[fname[:-5]] = json.load(f)
                except: pass
        return data

    def _save_all(self, data):
        for key, val in data.items():
            fpath = os.path.join(DATA_DIR, key + '.json')
            with open(fpath, 'w') as f:
                json.dump(val, f, ensure_ascii=False)

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # quiet

if __name__ == '__main__':
    port = 8765
    print(f'LUNA Server on http://0.0.0.0:{port}')
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
