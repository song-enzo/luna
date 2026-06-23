import urllib.request, json

base = 'http://127.0.0.1:8766'

# Test config
r = urllib.request.urlopen(f'{base}/api/config')
print('Config:', r.read().decode())

# Test styles
r = urllib.request.urlopen(f'{base}/api/styles')
data = json.loads(r.read())
print(f'\n款式总数: {len(data)}')
for s in data[:20]:
    print(f'  {s["code"]}: {s["name"]} (type={s.get("type","?")})')

# Test print warehouse groups
r = urllib.request.urlopen(f'{base}/api/print-warehouse/groups')
warehouse = json.loads(r.read())
print(f'\n花版仓库分组: {len(warehouse)}')
for g in warehouse[:10]:
    print(f'  {g["print_code"]}: {g.get("print_count",0)}个花版, 缩略图: {"有" if g.get("thumb") else "无"}')

print('\n✅ 全部 API 测试通过')