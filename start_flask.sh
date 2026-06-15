cd /opt/data/luna-backend
python3 -c "
from luna_app import app, init_db
with app.app_context():
    init_db()
    print('DB initialized OK')
" 2>&1
exec python3 luna-app.py 2>&1
