import urllib.request, json

base = 'http://127.0.0.1:8766'
r = urllib.request.urlopen(f'{base}/api/styles')
data = json.loads(r.read())
for s in data:
    if s.get('type') in ('print', 'stampa'):
        print(f'{s["code"]}: name={s["name"]}, type={s["type"]}, images={s.get("images",[])}')