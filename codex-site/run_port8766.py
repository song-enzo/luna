#!/usr/bin/env python3
"""LUNA ATELIER — Flask + SQLite 后端 (port 8766)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from luna_app import app, init_db

with app.app_context():
    init_db()

app.run(host='0.0.0.0', port=8766, debug=False)
