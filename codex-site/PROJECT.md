# LUNA ATELIER — 项目说明

## 启动
```bash
cd /tmp/alibaba-luna
PYTHONPATH=.venv/lib/python3.13/site-packages python3 app.py
```
监听 0.0.0.0:8765

## 停止
```bash
kill $(fuser 8765/tcp) 2>/dev/null
```

## 架构
- `app.py` — Flask + SQLite 后端（API + 静态文件）
- `luna-data.js` — 前端数据层（API 驱动，localStorage 缓存）
- `*.html` — 前端页面（纯静态，改 luna-data.js 不动 UI）
- `photos/` — 款式/色卡照片文件
- `luna.db` — SQLite 数据库
- `_data/` — 旧 JSON 数据（迁移后用不到了，保留作备份）
- `migrate.py` — 从 JSON → SQLite 迁移脚本

## 数据存储方式
- **主存储**: SQLite (`luna.db`)
- **照片**: 文件系统 (`photos/` 目录)
- **前端缓存**: localStorage（写操作同时写 API + localStorage）
- **无后台轮询**: 只读 localStorage，不做 API 刷新请求

## API 端点
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/login | POST | 登录 |
| /api/logout | POST | 登出 |
| /api/me | GET | 当前用户 |
| /api/data/:key | GET | 设置数据（categories/procacc/factories/fabrics/guests） |
| /api/data/:key | POST | 保存设置数据 |
| /api/styles | GET | 所有款式 |
| /api/styles | POST | 保存款式 |
| /api/styles/:id | GET | 单个款式 |
| /api/styles/:id | DELETE | 删除款式 |
| /api/orders | GET | 所有订单 |
| /api/orders | POST | 保存订单 |
| /api/orders/:id | GET | 单个订单 |
| /api/cart | POST | 购物车操作（add/remove/update_qty/clear）|
| /api/checkout | POST | 提交订单 |
| /api/upload | POST | 上传照片 |
| /api/init-defaults | POST | 初始化默认数据 |
| /api/export/csv | GET | 月结 CSV 导出 |

## 页面列表
- index.html — 登录页
- dashboard.html — 工作台
- guest-styles.html — 客人款式浏览（主页面）
- order-page.html — 下单页（含轮播图）
- add-style.html — 添加/编辑款式
- settings.html — 设置（面料、工序、客人管理）
- orders.html — 订单管理
- order-detail.html — 订单详情
- marker.html — 打唛架
- cutting.html — 裁剪
- ready-pickup.html — 待拿货
- shipping.html — 发货
- my-orders.html — 客人订单
- cart.html — 购物车
- cutting_history.html — 裁剪历史
- tryon.html — 试衣
- clear-orders.html — 清除订单数据

## 已知问题 & 已修复的问题

### 🔄 轮播图（carousel）—— 反复修过多次
**症状**: 翻页按钮不工作、图片不能翻页、卡在某张图不动  
**根因**: `track.children` 是 live HTMLCollection，克隆时插入元素导致索引错乱  
**正确修复（2026-05-23）**:
```js
// 用数组快照，不用live HTMLCollection
var slides = [].slice.call(track.children);
var clonesFront = slides.map(function(s) { return s.cloneNode(true); }).reverse();
var clonesBack = slides.map(function(s) { return s.cloneNode(true); });
clonesFront.forEach(function(c) { track.insertBefore(c, track.firstChild); });
clonesBack.forEach(function(c) { track.appendChild(c); });
```
**涉及文件**: order-page.html (renderCarousel 函数)

### 🐌 页面加载慢
**症状**: 页面加载需要 4-5 秒  
**根因**: `luna-data.js` 的 `luna-data-initialized` 事件在页面监听器注册前就发射了，事件丢失，页面等 5 秒超时才渲染  
**修复**: 用 `setTimeout(fn, 1)` 延迟发射事件，确保监听器已注册  
**涉及文件**: luna-data.js (底部初始化代码)

### 📸 款式图片不显示
**症状**: 主页、下单页的款式图片不显示  
**根因**: 旧代码判断 `images[0].length > 100` 才显示图片，迁移后照片存文件系统路径只有 50 字符  
**修复**: 增加 `photos/` 前缀、`data:` base64、`http` 协议三种路径判断  
**涉及文件**: guest-styles.html (renderGrid), order-page.html (renderCarousel)

### 💾 登录状态丢失
**症状**: 页面跳转后需要重新登录  
**根因**: 用户信息存内存变量，页面刷新后丢失  
**修复**: `setUser` 同时写入 `localStorage.luna_user_session`，`getUser` 优先读内存，没有则从 localStorage 恢复  
**涉及文件**: luna-data.js (getUser/setUser/clearUser)

## 备份位置
NAS: /nas/hermes/小天专用/luna-project-*.tar.gz

## 隧道地址
主站: https://regular-highs-sisters-chrome.trycloudflare.com (port 8765)
局域网: http://192.168.1.22:8765
