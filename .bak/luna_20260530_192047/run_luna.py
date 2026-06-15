
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
spec = importlib.util.spec_from_file_location('luna_app', 'luna_app.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with mod.app.app_context():
    mod.init_db()

mod.app.run(host='0.0.0.0', port=8766, debug=False)
