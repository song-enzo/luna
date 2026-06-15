#!/usr/bin/env python3
"""LUNA ATELIER — 数据迁移脚本 (JSON → SQLite + filesystem)"""
import json, os, sys, base64, uuid, re

DATA_DIR = os.path.join(os.path.dirname(__file__), '_data')
PHOTO_DIR = os.path.join(os.path.dirname(__file__), 'photos')
os.makedirs(PHOTO_DIR, exist_ok=True)

def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if os.path.isfile(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []

def save_base64_as_file(b64_data, prefix='img'):
    """Save base64 image to photos/ directory, return relative path"""
    if not b64_data:
        return ''
    # Handle data URIs
    if b64_data.startswith('data:'):
        # extract the actual base64 part after the comma
        b64_data = b64_data.split(',', 1)[-1]
    # Clean base64 string
    b64_data = b64_data.strip()
    if not b64_data:
        return ''
    try:
        img_data = base64.b64decode(b64_data)
    except Exception:
        return ''
    # Determine extension from magic bytes
    ext = '.jpg'
    if img_data[:4] == b'\x89PNG':
        ext = '.png'
    elif img_data[:2] == b'\xff\xd8':
        ext = '.jpg'
    elif img_data[:4] == b'RIFF':
        ext = '.webp'
    fname = f'{prefix}_{uuid.uuid4().hex[:12]}{ext}'
    fpath = os.path.join(PHOTO_DIR, fname)
    with open(fpath, 'wb') as f:
        f.write(img_data)
    return f'photos/{fname}'

def migrate():
    print("=" * 50)
    print("LUNA ATELIER 数据迁移")
    print("=" * 50)
    
    # 1. Users / Guests
    print("\n[1/8] 迁移用户数据...")
    guests = load_json('luna_settings_guests.json')
    print(f"  → 发现 {len(guests)} 个客人账号")
    
    # 2. Categories
    print("\n[2/8] 迁移分类数据...")
    categories = load_json('luna_settings_categories.json')
    print(f"  → 发现 {len(categories)} 个分类")
    
    # 3. Procacc
    print("\n[3/8] 迁移工序/费用数据...")
    procacc = load_json('luna_settings_procacc.json')
    print(f"  → 发现 {len(procacc)} 个工序")
    
    # 4. Factories
    print("\n[4/8] 迁移工厂数据...")
    factories = load_json('luna_settings_factories.json')
    print(f"  → 发现 {len(factories)} 个工厂")
    
    # 5. Fabrics + Colors + Photos
    print("\n[5/8] 迁移面料/色卡数据...")
    fabrics = load_json('luna_settings_fabrics.json')
    color_imgs = 0
    for fb in fabrics:
        for c in fb.get('colors', []):
            if c.get('img') or c.get('img_path'):
                fpath = save_base64_as_file(c.get('img', '') or c.get('img_path', ''), 'color')
                if fpath:
                    c['img_path'] = fpath
                    c['img'] = fpath  # keep both for compat
                    color_imgs += 1
                    if 'img' in c and c['img'] != fpath:
                        pass  # was base64, now file path
    print(f"  → 发现 {len(fabrics)} 种面料")
    print(f"  → 迁移 {color_imgs} 张色卡照片")
    
    # 6. Styles + Photos
    print("\n[6/8] 迁移款式数据...")
    styles = load_json('luna_styles_data.json')
    total_imgs = 0
    for st in styles:
        new_images = []
        for i, img in enumerate(st.get('images', [])):
            if img and len(img) > 50:
                fpath = save_base64_as_file(img, f'style_{st["code"]}')
                if fpath:
                    new_images.append(fpath)
                    total_imgs += 1
                else:
                    new_images.append(img)
            elif img:
                new_images.append(img)
        if new_images:
            st['images'] = new_images
    print(f"  → 发现 {len(styles)} 个款式")
    print(f"  → 迁移 {total_imgs} 张款式照片")
    
    # 7. Orders
    print("\n[7/8] 迁移订单数据...")
    orders = load_json('luna_orders_data.json')
    print(f"  → 发现 {len(orders)} 个订单")
    
    # 8. Cart
    print("\n[8/8] 迁移购物车数据...")
    cart = load_json('luna_cart_data.json')
    print(f"  → 发现 {len(cart)} 个购物车项")
    
    # Build output data structure for DB import
    output = {}
    
    # Guests
    output['guests'] = guests
    
    # Categories
    output['categories'] = categories
    
    # Procacc
    output['procacc'] = procacc
    
    # Factories
    output['factories'] = factories
    
    # Fabrics (with photos as file paths)
    output['fabrics'] = fabrics
    
    # Styles (with photos as file paths)
    output['styles'] = styles
    
    # Orders
    output['orders'] = orders
    
    # Cart
    output['cart'] = cart
    
    # Write combined migration JSON
    out_path = os.path.join(os.path.dirname(__file__), 'migration_data.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n迁移数据已写入: {out_path}")
    print("迁移完成！")
    
    return output

def import_to_db():
    """Import migration data into SQLite via Flask API"""
    import urllib.request, urllib.error
    api_base = 'http://localhost:8765'
    
    # Read migration data
    data_path = os.path.join(os.path.dirname(__file__), 'migration_data.json')
    if not os.path.isfile(data_path):
        print("请先运行迁移脚本生成数据文件")
        return
    
    with open(data_path) as f:
        data = json.load(f)
    
    # First login
    login_req = urllib.request.Request(
        f'{api_base}/api/login',
        data=json.dumps({'username': 'admin', 'password': 'admin'}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        resp = urllib.request.urlopen(login_req)
        print(f"登录成功: {resp.read().decode()}")
    except Exception as e:
        print(f"登录失败: {e}")
        return
    
    # Import categories
    if data.get('categories'):
        req = urllib.request.Request(
            f'{api_base}/api/data/categories',
            data=json.dumps(data['categories']).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print(f"导入 {len(data['categories'])} 个分类")
    
    # Import procacc
    if data.get('procacc'):
        req = urllib.request.Request(
            f'{api_base}/api/data/procacc',
            data=json.dumps(data['procacc']).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print(f"导入 {len(data['procacc'])} 个工序")
    
    # Import factories
    if data.get('factories'):
        req = urllib.request.Request(
            f'{api_base}/api/data/factories',
            data=json.dumps(data['factories']).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print(f"导入 {len(data['factories'])} 个工厂")
    
    # Import fabrics
    if data.get('fabrics'):
        req = urllib.request.Request(
            f'{api_base}/api/data/fabrics',
            data=json.dumps(data['fabrics']).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print(f"导入 {len(data['fabrics'])} 种面料")
    
    # Import styles
    if data.get('styles'):
        for st in data['styles']:
            req = urllib.request.Request(
                f'{api_base}/api/styles',
                data=json.dumps(st).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            urllib.request.urlopen(req)
        print(f"导入 {len(data['styles'])} 个款式")
    
    # Import orders
    if data.get('orders'):
        for o in data['orders']:
            req = urllib.request.Request(
                f'{api_base}/api/orders',
                data=json.dumps(o).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            urllib.request.urlopen(req)
        print(f"导入 {len(data['orders'])} 个订单")
    
    print("\n全部数据导入完成！")

if __name__ == '__main__':
    migrate()
    import_to_db()
