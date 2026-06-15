# LUNA ATELIER

Tailoring business web app. Flask + SQLite backend, single-file HTML with inline CSS/JS, central data layer in luna-data.js.

## Project Structure

- `luna_app.py` — Flask server (port 8766), serves static files + JSON API
- `luna-data.js` — Shared data layer (LUNA namespace), API calls + local cache
- `order-page.html` — Product detail / order page (carousel, color/size selection, cart)
- `guest-styles.html` — Main browsing page (style grid, new arrivals scroll)
- `cart.html` — Cart page (legacy)
- `settings.html` — Fabric/color/category management
- `my-orders.html` — Customer order list
- `*.html` — Other pages (dashboard, marker, cutting, etc.)
- `luna.db` — SQLite database (auto-created)
- `photos/` — Uploaded images directory

## Common Commands

```bash
# Start server
/opt/data/luna/.venv/bin/python /opt/data/luna/luna_app.py

# Restart server (kill old first)
fuser -k 8766/tcp; sleep 2; nohup /opt/data/luna/.venv/bin/python /opt/data/luna/luna_app.py &>/tmp/luna_server.log &

# Check server status
curl -s -o /dev/null -w "%{http_code}" http://localhost:8766/
```

## Frontend Conventions

- All styles inline in `<style>` blocks per page
- Fonts: Playfair Display (serif headings), Inter (sans-serif body)
- Brand color: #C8A56D (gold)
- Code prefix: ART- (e.g. ART-STYLE001)
- Data layer: always use `LUNA.*` functions, never access localStorage directly

## Data Model

- Styles have: code, name, category, type, suggestedPrice, images[], fabrics[], colors[]
- Cart: session-based, stored via API, items have {code, name, color, qty, price, fabric, note}
- Orders: have {id, customer, date, items[], note, order_placed, marker_complete, ...}
- Fabrics: have {id, name, colors[{name, hex, img_path}]}
- Colors: managed in settings page, read-only on order page
