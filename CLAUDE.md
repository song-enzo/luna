# 系统工作流 / LUNA ATELIER

## 认证流程
- `index.html` → 登录页，管理员通过密码登录
- 登录后跳转 `dashboard.html`（管理员）或 `guest-styles.html`（客人浏览）

## 浏览端（客人可见）
- `guest-styles.html` — 款式浏览主页（分类网格 + 新款横向滚动）
  - 分类筛选（侧边栏 + 顶部标签）
  - 点击款式跳转下单页（净色→`order-page.html`，印花→`order-print.html`）
- `my-orders.html` — 客人查单

## 下单端
- `order-page.html` — 净色下单（轮播图、颜色/面料选择、尺码/数量、加入购物车）
- `order-print.html` — 印花下单（AI 识别花版 → 选择贴纸款式 → 加入购物车）
- `cart.html` — 购物车确认，提交订单

## 订单管理
- `orders.html` — 订单列表（筛选、搜索、状态标签）
- `order-detail.html` — 订单详情（里程碑 + 操作按钮，每步自动写时间戳）

## 生产流程
- `marker.html` — 排料/打唛架
- `cutting.html` — 裁剪
- `cutting_history.html` — 裁剪历史
- `ready-pickup.html` — 待拿货
- `shipping.html` — 发货管理（进度条/预计完工）

## 仓库管理
- `fabric-warehouse.html` — 面料仓库（色卡管理）
- `print-warehouse.html` — 花版仓库（印花贴纸管理）

## 系统管理
- `dashboard.html`, `style-manage.html`, `settings.html`, `people-manage.html` 等

## 核心数据流
- 所有数据通过 `luna-data.js` 的 `LUNA.*` API 读写
- 本地缓存 + 服务器同步（SQLite）
- 图片上传至 `photos/` 目录

## AI 功能（印花识别）
- 上传花版截图 → OpenCV HSV 饱和度阈值检测色块位置
- 裁剪每个色块 → Gemini 1.5 Flash 分析颜色名/色号/SKU
- 匹配方式：CV 检测位置排序后与 AI 结果 1:1 对应
- API key 配置在 `local_config.json`（gitignored）

## 技术栈
- 后端：Flask + SQLite + OpenCV + Gemini API
- 前端：纯 HTML + 内联 CSS + 原生 JS（无框架）
- 数据层：`luna-data.js`
- 服务器端口：8766
- 字体：Playfair Display / Inter
- 品牌色：#C8A56D

