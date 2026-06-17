/* ============================================================
   LUNA ATELIER — 公共数据层 (luna-data.js)
   通过 Flask API 读写数据，缓存到 JS 内存
   ============================================================ */

var LUNA = (function() {
  'use strict';

  // ==================== 内存缓存 ====================
  var _cache = {};
  var _user = null;
  var _initialized = false;
  var _fetchQueue = [];

  // ==================== 工具函数 ====================

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function today() {
    var d = new Date();
    return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate());
  }

  function nowStr() {
    var d = new Date();
    return d.getFullYear() + '/' + pad(d.getMonth()+1) + '/' + pad(d.getDate()) + ' ' +
           pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }

  function uid(prefix) {
    return prefix + '-' + Date.now().toString(36) + '-' + Math.random().toString(36).substr(2, 5);
  }

  function api(path, method, body) {
    // Synchronous XHR for backward compatibility
    var xhr = new XMLHttpRequest();
    xhr.open(method || 'GET', path, false);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.withCredentials = true;
    try {
      xhr.send(body ? JSON.stringify(body) : null);
    } catch(e) {
      return {error: e.message};
    }
    if (xhr.status >= 200 && xhr.status < 300) {
      try { return JSON.parse(xhr.responseText); }
      catch(e) { return xhr.responseText; }
    }
    return {error: xhr.status + ': ' + xhr.statusText};
  }

  function apiAsync(path, method, body, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open(method || 'GET', path, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.withCredentials = true;
    xhr.onload = function() {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { callback(null, JSON.parse(xhr.responseText)); }
        catch(e) { callback(null, xhr.responseText); }
      } else {
        callback(xhr.status + ': ' + xhr.statusText);
      }
    };
    xhr.onerror = function() { callback('network error'); };
    xhr.send(body ? JSON.stringify(body) : null);
  }

  // ==================== 初始化 ====================

  function ensureInit() {
    // Force synchronous load from server if not initialized
    if (!_initialized) {
      loadAllData();
    }
  }

  function loadAllData() {
    // Load categories
    var r = api('/api/data/categories');
    if (!r.error) _cache.categories = r;
    // Load procacc
    r = api('/api/data/procacc');
    if (!r.error) _cache.procacc = r;
    // Load factories
    r = api('/api/data/factories');
    if (!r.error) _cache.factories = r;
    // Load fabrics
    r = api('/api/data/fabrics');
    if (!r.error) _cache.fabrics = r;
    // Load styles
    r = api('/api/styles');
    if (!r.error) _cache.styles = r;
    // Load orders
    r = api('/api/orders');
    if (!r.error) _cache.orders = r;
    // Fallback: if server orders are empty but localStorage has data, use it
    if ((!_cache.orders || _cache.orders.length === 0)) {
      try {
        var cached = localStorage.getItem('luna_orders_data');
        if (cached) { var parsed = JSON.parse(cached); if (parsed && parsed.length) _cache.orders = parsed; }
      } catch(e) {}
    }
    // Load cart
    r = api('/api/cart');
    if (!r.error) _cache.cart = r;
    // Load guests
    r = api('/api/data/guests');
    if (!r.error) _cache.guests = r;
    // Load current user
    r = api('/api/me');
    if (r && !r.error) _user = r;
    // Backward compat: sync to localStorage so old pages still work
    try {
      if (_cache.styles) localStorage.setItem('luna_styles_data', JSON.stringify(_cache.styles));
      if (_cache.orders) localStorage.setItem('luna_orders_data', JSON.stringify(_cache.orders));
      if (_cache.cart) localStorage.setItem('luna_cart_data', JSON.stringify(_cache.cart));
      if (_cache.fabrics) localStorage.setItem('luna_settings_fabrics', JSON.stringify(_cache.fabrics));
      if (_cache.procacc) localStorage.setItem('luna_settings_procacc', JSON.stringify(_cache.procacc));
      if (_cache.categories) localStorage.setItem('luna_settings_categories', JSON.stringify(_cache.categories));
      if (_cache.factories) localStorage.setItem('luna_settings_factories', JSON.stringify(_cache.factories));
    } catch(e) {}
    _initialized = true;
    syncCacheToLocalStorage();
    // Drain queue
    for (var i = 0; i < _fetchQueue.length; i++) {
      _fetchQueue[i]();
    }
    _fetchQueue = [];
  }

  function syncCacheToLocalStorage() {
    try {
      if (_cache.styles) localStorage.setItem('luna_styles_data', JSON.stringify(_cache.styles));
      if (_cache.orders) localStorage.setItem('luna_orders_data', JSON.stringify(_cache.orders));
      if (_cache.cart) localStorage.setItem('luna_cart_data', JSON.stringify(_cache.cart));
      if (_cache.fabrics) localStorage.setItem('luna_settings_fabrics', JSON.stringify(_cache.fabrics));
      if (_cache.procacc) localStorage.setItem('luna_settings_procacc', JSON.stringify(_cache.procacc));
      if (_cache.categories) localStorage.setItem('luna_settings_categories', JSON.stringify(_cache.categories));
      if (_cache.factories) localStorage.setItem('luna_settings_factories', JSON.stringify(_cache.factories));
      if (_cache.guests) localStorage.setItem('luna_settings_guests', JSON.stringify(_cache.guests));
    } catch(e) {}
  }

  // ==================== 用户 / 登录 ====================

  function getUser() {
    if (!_user) {
      try { var saved = localStorage.getItem('luna_user_session');
        if (saved) _user = JSON.parse(saved); } catch(e) {}
    }
    return _user;
  }

  function setUser(user) {
    _user = user;
    try { localStorage.setItem('luna_user_session', JSON.stringify(user)); } catch(e) {}
  }

  function clearUser() {
    _user = null;
    try { localStorage.removeItem('luna_user_session'); } catch(e) {}
  }

  function login(username, password) {
    var r = api('/api/login', 'POST', {username: username, password: password});
    if (r && !r.error) {
      setUser(r);
      return r;
    }
    return r && r.error ? {error: r.error} : {error: '登录失败'};
  }

  function canAccess(role, page) {
    if (role === 'admin') return true;
    if (role === 'guest') {
      var guestPages = ['guest-styles.html','order-page.html','cart.html','my-orders.html','order-detail.html','tryon.html'];
      return guestPages.indexOf(page) !== -1;
    }
    if (role === 'employee') {
      var perms = getEmployeePermissions();
      var list = perms[page] || [];
      return list.indexOf('all') !== -1 || list.some(function(p) { return p === role; });
    }
    return false;
  }

  function checkAuth(requiredRole) {
    var user = getUser();
    if (!user) { window.location.href = 'index.html'; return null; }
    if (requiredRole && user.role !== requiredRole) { window.location.href = 'index.html'; return null; }
    return user;
  }

  // ==================== 款式 ====================

  function getStyles() {
    ensureInit();
    if (_cache.styles) {
      _cache.styles.forEach(function(s) { delete s.name; });
    }
    return _cache.styles || [];
  }

  function saveStyles(styles) {
    styles.forEach(function(s) { delete s.name; });
    _cache.styles = styles;
    _cache.styles.forEach(function(s) {
      api('/api/styles', 'POST', s);
    });
    syncCacheToLocalStorage();
    fireChanged();
  }

  function findStyle(code) {
    ensureInit();
    var styles = _cache.styles || [];
    for (var i = 0; i < styles.length; i++) {
      if (styles[i].code === code) {
        var s = JSON.parse(JSON.stringify(styles[i]));
        delete s.name;
        return s;
      }
    }
    // 缓存未命中时直接从服务器查询（localStorage 可能延迟）
    var r = api('/api/styles/' + encodeURIComponent(code));
    if (r && !r.error) {
      delete r.name;
      // 补充到缓存
      _cache.styles = _cache.styles || [];
      _cache.styles.push(r);
      return r;
    }
    return null;
  }

  function deleteStyle(code) {
    var r = api('/api/styles/' + encodeURIComponent(code), 'DELETE');
    if (r && !r.error) {
      var styles = getStyles();
      for (var i = 0; i < styles.length; i++) {
        if (styles[i].code === code) { styles.splice(i, 1); break; }
      }
      syncCacheToLocalStorage();
      fireChanged();
      return true;
    }
    return false;
  }

  function getEnabledStyles() {
    ensureInit();
    var styles = _cache.styles || [];
    // Style toggles no longer used, return all
    return styles;
  }

  function getStyleCategories() {
    var styles = getEnabledStyles();
    var cats = {};
    for (var i = 0; i < styles.length; i++) {
      if (styles[i].category) cats[styles[i].category] = true;
    }
    return Object.keys(cats);
  }

  function calcStyleCost(style) {
    var fabricCost = 0, accCost = 0;
    if (style.fabrics) style.fabrics.forEach(function(f) { fabricCost += f.subtotal || (f.price * f.quantity); });
    if (style.accessories) style.accessories.forEach(function(a) { accCost += a.subtotal || a.price; });
    return fabricCost + accCost + (style.laborCost || 0) + (style.ironCost || 0);
  }

  function calcSuggestedPrice(cost, markup) {
    markup = markup || 0.25;
    return Math.round(cost * (1 + markup) * 100) / 100;
  }

  // ==================== 订单 ====================

  function getOrders() {
    ensureInit();
    return _cache.orders || [];
  }

  function saveOrders(orders) {
    _cache.orders = orders;
    syncCacheToLocalStorage();
    _cache.orders.forEach(function(o) {
      var res = api('/api/orders', 'POST', o);
      if (res && res.error) {
        // Retry once if failed
        api('/api/orders', 'POST', o);
      }
    });
    fireChanged();
  }

  function saveSingleOrder(order) {
    var orders = getOrders();
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === order.id) {
        orders[i] = order;
        break;
      }
    }
    _cache.orders = orders;
    syncCacheToLocalStorage();
    var res = api('/api/orders', 'POST', order);
    if (res && res.error) { res = api('/api/orders', 'POST', order); }
    if (!res || res.error) return null;
    fireChanged();
    return order;
  }

  function findOrder(id) {
    ensureInit();
    var orders = _cache.orders || [];
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === id) return orders[i];
    }
    return null;
  }

  // ====== 查询函数 ======

  function getPendingMarkerOrders() {
    return getOrders().filter(function(o) {
      return o.order_placed && o.order_placed.completed === 1 &&
             (!o.marker_complete || o.marker_complete.completed === 0);
    });
  }

  function getPendingCuttingOrders() {
    return getOrders().filter(function(o) {
      return o.marker_complete && o.marker_complete.completed === 1 &&
             (!o.cutting_complete || o.cutting_complete.completed === 0);
    });
  }

  function getPendingPickupOrders() {
    return getOrders().filter(function(o) {
      return o.cutting_complete && o.cutting_complete.completed === 1 &&
             (!o.pickup_complete || o.pickup_complete.completed === 0);
    });
  }

  function getPendingShipOrders() {
    return getOrders().filter(function(o) {
      return o.pickup_complete && o.pickup_complete.completed === 1 &&
             (!o.shipping_complete || o.shipping_complete.completed === 0);
    });
  }

  function getCompletedOrders() {
    return getOrders().filter(function(o) {
      return o.shipping_complete && o.shipping_complete.completed === 1;
    });
  }

  // 兼容旧函数名
  function getConfirmedOrders() { return getPendingMarkerOrders(); }
  function getCuttingOrders() { return getPendingCuttingOrders(); }
  function getSewingOrders() { return getPendingPickupOrders(); }
  function getPickupOrders() { return getPendingPickupOrders(); }

  function confirmOrder(orderId, operator) {
    var orders = getOrders();
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === orderId) {
        orders[i].order_placed.completed = 1;
        saveOrders(orders);
        return orders[i];
      }
    }
    return null;
  }

  // ====== 状态标签 ======

  function getOrderStatus(order) {
    if (order.shipping_complete && order.shipping_complete.completed === 1) return 'shipped';
    if (order.pickup_complete && order.pickup_complete.completed === 1) return 'sewing';
    if (order.cutting_complete && order.cutting_complete.completed === 1) return 'pickup';
    if (order.marker_complete && order.marker_complete.completed === 1) return 'cutting';
    if (order.order_placed && order.order_placed.completed === 1) return 'confirmed';
    return 'pending';
  }

  function getFactoryHistory(styleCode) {
    if (!styleCode) return [];
    var orders = getOrders();
    var history = [];
    orders.forEach(function(o) {
      if (o.pickup_complete && o.pickup_complete.completed === 1 && o.pickup_complete.factory) {
        var hasStyle = false;
        if (o.items) o.items.forEach(function(it) { if (it.code === styleCode) hasStyle = true; });
        if (hasStyle) {
          history.push({
            factory: o.pickup_complete.factory,
            price: o.pickup_complete.factory_price || 0,
            orderId: o.id,
            time: o.pickup_complete.time
          });
        }
      }
    });
    return history;
  }

  // ====== 步骤完成函数 ======

  function completeMarker(orderId, markerData, operator, fabrics) {
    var orders = getOrders();
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === orderId) {
        var existing = orders[i].marker_complete || {};
        var newFabrics = existing.fabrics ? existing.fabrics.slice() : [];
        if (fabrics) {
          fabrics.forEach(function(f) {
            var idx = -1;
            for (var fi = 0; fi < newFabrics.length; fi++) {
              if (newFabrics[fi].name === f.name) { idx = fi; break; }
            }
            if (idx >= 0) {
              newFabrics[idx] = f;
            } else {
              newFabrics.push(f);
            }
          });
        }
        // 判断是否所有面料都已完成出纸样
        var orderFabricsSet = {};
        (orders[i].items || []).forEach(function(item) {
          (item.fabric || '默认面料').split(/\s*,\s*/).forEach(function(fn) { orderFabricsSet[fn] = true; });
        });
        var totalOrderFabrics = Object.keys(orderFabricsSet).length;
        var doneFabrics = newFabrics.filter(function(f) { return f.done; }).length;
        var allDone = totalOrderFabrics > 0 && doneFabrics >= totalOrderFabrics;
        orders[i].marker_complete = {
          completed: allDone ? 1 : 0,
          length: markerData.length || 0,
          hands: markerData.hands || 1,
          fabrics: newFabrics,
          operator: operator || '',
          time: nowStr()
        };
        saveOrders(orders);
        return orders[i];
      }
    }
    return null;
  }

  function completeCutting(orderId, colorData, checkmarks, operator) {
    // colorData: { colorName: { fabric: fabricName, hands: N, layers: N, total: N } }
    var orders = getOrders();
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === orderId) {
        var order = orders[i];
        // 确定主面料（面料1）
        var fabric1 = '';
        var orderItems = order.items || [];
        if (orderItems.length > 0) {
          var ff = orderItems[0].fabric || '';
          fabric1 = ff.split(',')[0].trim();
        }
        // Group by fabric
        var fabrics = {};
        var totalCut = 0;
        for (var key in colorData) {
          var cd = colorData[key];
          if (!cd) continue;
          var fName = cd.fabric || '默认面料';
          // key may be composite (fabric\x00color) — extract real color name
          var realColor = key;
          var sep = key.indexOf('\x00');
          if (sep >= 0) realColor = key.substring(sep + 1);
          if (!fabrics[fName]) {
            fabrics[fName] = { hands: cd.hands || 1, colors: {} };
          }
          // Carry over pattern length and loss info from cutting page
          if (cd.patternLen !== undefined) fabrics[fName].patternLen = cd.patternLen;
          if (cd.lossCm !== undefined) fabrics[fName].lossCm = cd.lossCm;
          fabrics[fName].colors[realColor] = { layers: cd.layers || 1, total: cd.total || 0 };
          // total_cut 只统计面料1的数量（实际成衣件数）
          if (!fabric1 || fName === fabric1 || fName === '默认面料') {
            totalCut += cd.total || 0;
          }
        }
        // Calculate fabric usage for each fabric
        for (var fn in fabrics) {
          var f = fabrics[fn];
          var fLen = parseFloat(f.patternLen) || 0;
          var fLoss = parseFloat(f.lossCm) || 6;
          if (fLen > 0) {
            var totalLayers = 0;
            for (var cc in f.colors) totalLayers += f.colors[cc].layers || 0;
            f.fabricUsage = Math.round((fLen + fLoss / 100) * totalLayers * 100) / 100;
          }
        }
        order.cutting_complete = {
          completed: 1,
          fabrics: fabrics,
          total_cut: totalCut,
          operator: operator || '',
          time: nowStr(),
          checkmarks: checkmarks || {}
        };
        // Save only this order to the server (not all orders)
        var res = api('/api/orders', 'POST', order);
        if (res && res.error) { res = api('/api/orders', 'POST', order); }
        if (!res || res.error) {
          delete order.cutting_complete;
          return null;
        }
        syncCacheToLocalStorage();
        fireChanged();

        // 扣减库存：(纸样长度 + 损耗/层) × 层数
        var markerFabrics = (order.marker_complete && order.marker_complete.fabrics) || [];
        var allFabrics = getFabrics();
        var deductions = [];  // {name, amount}
        for (var fName in fabrics) {
          if (!fabrics.hasOwnProperty(fName)) continue;
          var patternLen = 0;
          for (var mi = 0; mi < markerFabrics.length; mi++) {
            if (markerFabrics[mi].name === fName) {
              patternLen = markerFabrics[mi].length || 0;
              break;
            }
          }
          // 合计该面料所有颜色的总件数和层数
          var fabricTotal = 0;
          var totalLayers = 0;
          for (var c in fabrics[fName].colors) {
            if (!fabrics[fName].colors.hasOwnProperty(c)) continue;
            totalLayers += fabrics[fName].colors[c].layers || 0;
            fabricTotal += fabrics[fName].colors[c].total || 0;
          }
          var deduction = 0;
          if (patternLen > 0) {
            var lossCm = 6;
            for (var fi = 0; fi < allFabrics.length; fi++) {
              if (allFabrics[fi].name === fName) { lossCm = allFabrics[fi].lossPerLayer || 6; break; }
            }
            deduction = (patternLen + (lossCm / 100)) * totalLayers;
          } else if (fabricTotal > 0) {
            deduction = fabricTotal * 0.5;
          }
          if (deduction > 0) {
            deductions.push({name: fName, amount: Math.round(deduction * 100) / 100});
          }
        }
        // 发送扣减请求给服务端（只更新受影响的面料库存，避免全表替换）
        if (deductions.length > 0) {
          var dsr = api('/api/fabrics/deduct-stock', 'POST', {
            deductions: deductions,
            order_id: orderId
          });
          if (dsr && dsr.ok) {
            // 同步更新本地缓存
            (dsr.results || []).forEach(function(r) {
              if (r.ok) {
                for (var fi = 0; fi < allFabrics.length; fi++) {
                  if (allFabrics[fi].name === r.name) {
                    allFabrics[fi].stock = r.new_stock;
                    break;
                  }
                }
              }
            });
            syncCacheToLocalStorage();
            fireChanged();
          } else {
            console.error('面料库存扣除失败:', dsr);
          }
        }

        return order;
      }
    }
    return null;
  }

  function completePickup(orderId, factory, operator, factoryPrice) {
    var orders = getOrders();
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === orderId) {
        orders[i].pickup_complete = {
          completed: 1,
          factory: factory || '',
          operator: operator || '',
          factory_price: factoryPrice || 0,
          time: nowStr()
        };
        var res = api('/api/orders', 'POST', orders[i]);
        if (res && res.error) { res = api('/api/orders', 'POST', orders[i]); }
        if (!res || res.error) {
          delete orders[i].pickup_complete;
          return null;
        }
        syncCacheToLocalStorage();
        fireChanged();
        return orders[i];
      }
    }
    return null;
  }

  function confirmFactoryReceipt(orderId, qty) {
    var orders = getOrders();
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === orderId) {
        orders[i].pickup_complete = orders[i].pickup_complete || {};
        orders[i].pickup_complete.factory_received_qty = qty;
        var res = api('/api/orders', 'POST', orders[i]);
        if (res && res.error) { res = api('/api/orders', 'POST', orders[i]); }
        if (!res || res.error) { return null; }
        syncCacheToLocalStorage();
        fireChanged();
        return orders[i];
      }
    }
    return null;
  }

  function shipOrder(orderId, shipQty, operator, colorReceived) {
    var orders = getOrders();
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id === orderId) {
        orders[i].shipping_complete = {
          completed: 1,
          qty: shipQty,
          operator: operator || '',
          time: nowStr(),
          color_received: colorReceived || {}
        };
        // Save only this order to the server
        var res = api('/api/orders', 'POST', orders[i]);
        if (res && res.error) {
          // Retry once
          res = api('/api/orders', 'POST', orders[i]);
        }
        if (res && !res.error) {
          // Server save succeeded
          syncCacheToLocalStorage();
          fireChanged();
          return orders[i];
        }
        // Server save failed — revert in-memory change
        delete orders[i].shipping_complete;
        return null;
      }
    }
    return null;
  }

  function deleteOrder(orderId, returnError) {
    var r = api('/api/orders/' + encodeURIComponent(orderId), 'DELETE');
    if (r && !r.error) {
      var orders = getOrders();
      for (var i = 0; i < orders.length; i++) {
        if (orders[i].id === orderId) { orders.splice(i, 1); break; }
      }
      syncCacheToLocalStorage();
      fireChanged();
      return true;
    }
    if (returnError) return r && r.error ? r.error : '服务器无响应';
    return false;
  }

  function calcSubtotal(order) {
    var total = 0;
    if (order.items) {
      order.items.forEach(function(item) {
        var qty = 0;
        if (item.qty) Object.keys(item.qty).forEach(function(s) { qty += item.qty[s] || 0; });
        total += qty * (item.price || 0);
      });
    }
    return Math.round(total * 100) / 100;
  }

  function calcShipSubtotal(order) {
    if (!order.shipping_complete || !order.shipping_complete.qty) return calcSubtotal(order);
    var shipQty = order.shipping_complete.qty;
    var totalQty = order.total_qty || 0;
    if (totalQty === 0) return 0;
    var ratio = shipQty / totalQty;
    return Math.round(calcSubtotal(order) * ratio * 100) / 100;
  }

  function getInvoices(month) {
    var orders = getCompletedOrders();
    var invoices = [];
    orders.forEach(function(o) {
      if (!o.shipping_complete || !o.shipping_complete.time) return;
      var shipTime = o.shipping_complete.time;
      var shipMonth = shipTime.substring(0, 7);
      if (month && shipMonth !== month) return;
      var amount = calcShipSubtotal(o);
      invoices.push({
        id: o.id,
        customer: o.customer,
        date: o.date,
        shipTime: shipTime,
        shipMonth: shipMonth,
        qty: o.shipping_complete.qty,
        amount: amount
      });
    });
    return invoices;
  }

  function generateOrderId() {
    var orders = getOrders();
    var d = today();
    var seq = 1;
    for (var i = 0; i < orders.length; i++) {
      if (orders[i].id.indexOf('ORD-' + d) === 0) seq++;
    }
    return 'ORD-' + d + '-' + pad(seq);
  }

  // ==================== 购物车 ====================

  function getCart() {
    ensureInit();
    return _cache.cart || [];
  }

  function saveCart(cart) {
    _cache.cart = cart;
    syncCacheToLocalStorage();
    // Sync via API
    api('/api/cart', 'POST', {action: 'clear'});
    if (cart && cart.length > 0) {
      for (var i = 0; i < cart.length; i++) {
        var item = cart[i];
        api('/api/cart', 'POST', {
          action: 'add',
          code: item.code,
          name: item.name,
          color: item.color,
          qty: item.qty,
          price: item.price,
          fabric: item.fabric,
          note: item.note || ''
        });
      }
    }
    fireChanged();
  }

  function getCartCount() {
    var cart = getCart();
    var count = 0;
    for (var i = 0; i < cart.length; i++) {
      if (cart[i].qty) Object.keys(cart[i].qty).forEach(function(s) { count += cart[i].qty[s] || 0; });
    }
    return count;
  }

  function addToCart(code, name, color, qty, price, fabric, note, components, item_type, stampa_img_url, stampa_code) {
    var result = api('/api/cart', 'POST', {
      action: 'add',
      code: code,
      name: name || '',
      color: color || '',
      qty: qty,
      price: price || 0,
      fabric: fabric || '',
      note: note || '',
      components: components || [],
      item_type: item_type || '',
      stampa_img_url: stampa_img_url || '',
      stampa_code: stampa_code || ''
    });
    if (result && result.ok && result.cart) {
      _cache.cart = result.cart;
      syncCacheToLocalStorage();
    }
    fireChanged();
  }

  function removeFromCart(index) {
    var cart = getCart();
    if (cart[index] && cart[index].id) {
      api('/api/cart', 'POST', {action: 'remove', id: cart[index].id});
    }
    cart.splice(index, 1);
    _cache.cart = cart;
    syncCacheToLocalStorage();
    fireChanged();
  }

  function updateCartQty(index, size, delta) {
    var cart = getCart();
    if (!cart[index] || !cart[index].qty) return;
    if (cart[index].id) {
      api('/api/cart', 'POST', {action: 'update_qty', id: cart[index].id, size: size, delta: delta});
    }
    cart[index].qty[size] = Math.max(0, (cart[index].qty[size] || 0) + delta);
    syncCacheToLocalStorage();
    fireChanged();
  }

  function updateCartNote(index, note) {
    var cart = getCart();
    if (!cart[index]) return;
    cart[index].note = note;
    if (cart[index].id) {
      api('/api/cart', 'POST', {action: 'update_note', id: cart[index].id, note: note});
    }
    fireChanged();
  }

  function clearCart() {
    api('/api/cart', 'POST', {action: 'clear'});
    _cache.cart = [];
    fireChanged();
  }

  function checkout(customer, note, subCustomer) {
    var result = api('/api/checkout', 'POST', {customer: customer || '', note: note || '', sub_customer: subCustomer || ''});
    if (result && result.ok) {
      _cache.cart = [];
      // Reload orders
      var r = api('/api/orders');
      if (!r.error) _cache.orders = r;
      syncCacheToLocalStorage();
      fireChanged();
      return result.orders || [];
    }
    return [];
  }

  // ==================== 设置数据 ====================

  function getFabrics() {
    ensureInit();
    return _cache.fabrics || [];
  }

  function saveFabrics(d) {
    _cache.fabrics = d;
    api('/api/data/fabrics', 'POST', d);
    syncCacheToLocalStorage();
    fireChanged();
  }

  function addFabricColor(fabricId, name, hex, imgPath, extraFields) {
    // 立即更新本地缓存（乐观更新，不等待服务器）
    if (_cache.fabrics) {
      for (var i = 0; i < _cache.fabrics.length; i++) {
        if (_cache.fabrics[i].id === fabricId) {
          if (!_cache.fabrics[i].colors) _cache.fabrics[i].colors = [];
          var newColor = {name: name, hex: hex, img: imgPath || ''};
          if (extraFields) {
            for (var k in extraFields) newColor[k] = extraFields[k];
          }
          _cache.fabrics[i].colors.push(newColor);
          break;
        }
      }
      try { localStorage.setItem('luna_settings_fabrics', JSON.stringify(_cache.fabrics)); } catch(e) {}
      fireChanged();
    }
    // 异步服务端同步（fetch 不阻塞 UI）
    var body = {fabric_id: fabricId, name: name, hex: hex, img_path: imgPath || ''};
    if (extraFields) {
      if (extraFields.rapporto_cm !== undefined) body.rapporto_cm = extraFields.rapporto_cm;
      if (extraFields.verso_unico !== undefined) body.verso_unico = extraFields.verso_unico;
    }
    fetch('/api/fabrics/add-color', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    }).catch(function(){});
    return {ok: true};
  }

  function getProcAcc() {
    ensureInit();
    return _cache.procacc || [];
  }

  function saveProcAcc(d) {
    _cache.procacc = d;
    api('/api/data/procacc', 'POST', d);
    fireChanged();
  }

  function getCategories() {
    ensureInit();
    return _cache.categories || [];
  }

  function saveCategories(d) {
    _cache.categories = d;
    api('/api/data/categories', 'POST', d);
    fireChanged();
  }

  function getFactories() {
    ensureInit();
    return _cache.factories || [];
  }

  function saveFactories(d) {
    _cache.factories = d;
    api('/api/data/factories', 'POST', d);
    fireChanged();
  }

  function getGuests() {
    ensureInit();
    return _cache.guests || [];
  }

  function saveGuests(d) {
    _cache.guests = d;
    api('/api/data/guests', 'POST', d);
    syncCacheToLocalStorage();
    fireChanged();
  }

  function getStyleToggles() {
    return []; // No longer supported
  }

  function saveStyleToggles(d) {}

  function getEmployees() {
    ensureInit();
    return _cache.employees || [];
  }

  function saveEmployees(d) {
    _cache.employees = d;
    api('/api/data/employees', 'POST', d);
    fireChanged();
  }

  function getEmployeePermissions() {
    return {};
  }

  function saveEmployeePermissions(d) {}

  function initDefaults() {
    api('/api/init-defaults', 'POST');
  }

  // ==================== 月结导出 ====================

  function exportMonthlySettlement(month) {
    var csvUrl = '/api/export/csv';
    if (month) csvUrl += '?month=' + month;
    var a = document.createElement('a');
    a.href = csvUrl;
    a.download = 'luna_' + (month || 'all') + '.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(function() { document.body.removeChild(a); }, 100);
    return '';
  }

  // ==================== 自定义弹窗 ====================

  function _initDialog() {
    var css = '.luna-dialog-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:99999;align-items:center;justify-content:center}.luna-dialog-box{background:#fff;border-radius:10px;padding:24px;max-width:360px;width:85vw;box-shadow:0 8px 32px rgba(0,0,0,.2)}.luna-dialog-msg{font-size:14px;color:#1C1C1C;line-height:1.6;margin-bottom:18px;white-space:pre-wrap}.luna-dialog-actions{display:flex;gap:10px;justify-content:flex-end}.luna-dialog-actions button{display:inline-flex;align-items:center;justify-content:center;padding:8px 18px;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;font-family:"Inter",sans-serif;min-width:72px}.luna-dialog-actions .luna-btn-gold{background:#C8A56D;color:#fff}.luna-dialog-actions .luna-btn-gold:hover{background:#b8963e}.luna-dialog-actions .luna-btn-cancel{background:#f5f5f5;color:#666;border:1px solid #ddd}.luna-dialog-actions .luna-btn-cancel:hover{background:#eee}';
    var s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
    var d = document.createElement('div');
    d.innerHTML = '<div class="luna-dialog-overlay" id="lunaDialogOverlay" onclick="if(event.target===this)this.style.display=\'none\'"><div class="luna-dialog-box"><div class="luna-dialog-msg" id="lunaDialogMsg"></div><div class="luna-dialog-actions" id="lunaDialogActions"><button class="luna-btn-cancel" id="lunaDialogCancel">取消</button><button class="luna-btn-gold" id="lunaDialogOk">确定</button></div></div></div>';
    document.body.appendChild(d.firstElementChild);
  }

  function _getDialog() {
    var overlay = document.getElementById('lunaDialogOverlay');
    if (!overlay) _initDialog();
    return document.getElementById('lunaDialogOverlay');
  }

  function showAlert(msg, onOk) {
    var overlay = _getDialog();
    document.getElementById('lunaDialogMsg').textContent = msg;
    document.getElementById('lunaDialogOk').textContent = '确定';
    document.getElementById('lunaDialogOk').onclick = function() { overlay.style.display = 'none'; if (onOk) onOk(); };
    document.getElementById('lunaDialogCancel').style.display = 'none';
    overlay.style.display = 'flex';
  }

  function showConfirm(msg, onOk) {
    var overlay = _getDialog();
    document.getElementById('lunaDialogMsg').textContent = msg;
    document.getElementById('lunaDialogOk').textContent = '确定';
    document.getElementById('lunaDialogOk').onclick = function() { overlay.style.display = 'none'; if (onOk) onOk(); };
    var cancelBtn = document.getElementById('lunaDialogCancel');
    cancelBtn.style.display = '';
    cancelBtn.onclick = function() { overlay.style.display = 'none'; };
    overlay.style.display = 'flex';
  }

  // ==================== 事件 ====================

  function fireChanged() {
    // Small delay to let the DOM update
    setTimeout(function() {
      window.dispatchEvent(new CustomEvent('luna-data-changed'));
    }, 0);
  }

  // ==================== 服务器同步（保留桩函数，不再使用） ====================

  function syncAllToServer() {
    // 从 localStorage 读取所有设置数据，推送到 API
    var maps = [
      {key: 'luna_settings_fabrics',   path: '/api/data/fabrics',    transform: function(d) { return d; }},
      {key: 'luna_settings_factories', path: '/api/data/factories',  transform: function(d) { return d; }},
      {key: 'luna_settings_procacc',   path: '/api/data/procacc',    transform: function(d) { return d; }},
      {key: 'luna_settings_categories',path: '/api/data/categories', transform: function(d) { return d; }},
      {key: 'luna_settings_guests',    path: '/api/data/guests',     transform: function(d) { return d; }}
    ];
    // 1. 设置数据（全量 POST）
    maps.forEach(function(m) {
      try {
        var raw = localStorage.getItem(m.key);
        if (raw) {
          var data = JSON.parse(raw);
          var r = api(m.path, 'POST', data);
          if (!r.error) console.log('sync ok: ' + m.key);
        }
      } catch(e) { console.error('sync error ' + m.key, e); }
    });
    // 2. 款式数据（逐个 POST）
    try {
      var stylesRaw = localStorage.getItem('luna_styles_data');
      if (stylesRaw) {
        var styles = JSON.parse(stylesRaw);
        if (Array.isArray(styles)) {
          styles.forEach(function(s) { api('/api/styles', 'POST', s); });
        }
      }
    } catch(e) { console.error('sync styles error', e); }
    // 3. 订单数据（逐个 POST）
    try {
      var ordersRaw = localStorage.getItem('luna_orders_data');
      if (ordersRaw) {
        var orders = JSON.parse(ordersRaw);
        if (Array.isArray(orders)) {
          orders.forEach(function(o) { api('/api/orders', 'POST', o); });
        }
      }
    } catch(e) { console.error('sync orders error', e); }
  }

  // ==================== 公共 API ====================

  return {
    get: function(key, def) {
      var map = {
        'luna_styles_data': _cache.styles,
        'luna_orders_data': _cache.orders,
        'luna_cart_data': _cache.cart,
        'luna_settings_fabrics': _cache.fabrics,
        'luna_settings_procacc': _cache.procacc,
        'luna_settings_categories': _cache.categories,
        'luna_settings_factories': _cache.factories,
        'luna_settings_guests': _cache.guests,
        'luna_settings_employees': _cache.employees
      };
      return map[key] !== undefined ? map[key] : def;
    },
    set: function(key, val) {
      // sync to server
      switch(key) {
        case 'luna_styles_data': saveStyles(val); break;
        case 'luna_orders_data': saveOrders(val); break;
        case 'luna_cart_data': saveCart(val); break;
        case 'luna_settings_fabrics': saveFabrics(val); break;
        case 'luna_settings_procacc': saveProcAcc(val); break;
        case 'luna_settings_categories': saveCategories(val); break;
        case 'luna_settings_factories': saveFactories(val); break;
        case 'luna_settings_guests': saveGuests(val); break;
        case 'luna_settings_employees': saveEmployees(val); break;
      }
      return true;
    },
    uid: uid, today: today, nowStr: nowStr,

    getUser: getUser, setUser: setUser, clearUser: clearUser,
    login: login, logout: function() { clearUser(); window.location.href = 'index.html'; },
    canAccess: canAccess, checkAuth: checkAuth,

    getStyles: getStyles, saveStyles: saveStyles, findStyle: findStyle,
    deleteStyle: deleteStyle,
    getEnabledStyles: getEnabledStyles, getStyleCategories: getStyleCategories,
    calcStyleCost: calcStyleCost, calcSuggestedPrice: calcSuggestedPrice,

    getOrders: getOrders, saveOrders: saveOrders, saveSingleOrder: saveSingleOrder, findOrder: findOrder,
    deleteOrder: deleteOrder,
    completeMarker: completeMarker, completeCutting: completeCutting,
    completePickup: completePickup, confirmFactoryReceipt: confirmFactoryReceipt, shipOrder: shipOrder,
    getPendingMarkerOrders: getPendingMarkerOrders,
    getPendingCuttingOrders: getPendingCuttingOrders,
    getPendingPickupOrders: getPendingPickupOrders,
    getPendingShipOrders: getPendingShipOrders, getCompletedOrders: getCompletedOrders,
    getConfirmedOrders: getConfirmedOrders, getCuttingOrders: getCuttingOrders,
    getSewingOrders: getSewingOrders, getPickupOrders: getPickupOrders,
    getOrderStatus: getOrderStatus, getFactoryHistory: getFactoryHistory,
    calcSubtotal: calcSubtotal,
    calcShipSubtotal: calcShipSubtotal, getInvoices: getInvoices,
    exportMonthlySettlement: exportMonthlySettlement,
    showAlert: showAlert, showConfirm: showConfirm,

    getCart: getCart, saveCart: saveCart, getCartCount: getCartCount,
    addToCart: addToCart, removeFromCart: removeFromCart,
    updateCartQty: updateCartQty, updateCartNote: updateCartNote, clearCart: clearCart, checkout: checkout,

    getFabrics: getFabrics, saveFabrics: saveFabrics, addFabricColor: addFabricColor,
    getProcAcc: getProcAcc, saveProcAcc: saveProcAcc,
    getCategories: getCategories, saveCategories: saveCategories,
    getFactories: getFactories, saveFactories: saveFactories,
    getGuests: getGuests, saveGuests: saveGuests,
    getStyleToggles: getStyleToggles, saveStyleToggles: saveStyleToggles,
    getEmployees: getEmployees, saveEmployees: saveEmployees,
    getEmployeePermissions: getEmployeePermissions, saveEmployeePermissions: saveEmployeePermissions,

    initDefaults: initDefaults,

    _syncToLocalStorage: function() {
      try {
        if (_cache.styles) localStorage.setItem('luna_styles_data', JSON.stringify(_cache.styles));
        if (_cache.orders) localStorage.setItem('luna_orders_data', JSON.stringify(_cache.orders));
        if (_cache.cart) localStorage.setItem('luna_cart_data', JSON.stringify(_cache.cart));
        if (_cache.fabrics) localStorage.setItem('luna_settings_fabrics', JSON.stringify(_cache.fabrics));
        if (_cache.procacc) localStorage.setItem('luna_settings_procacc', JSON.stringify(_cache.procacc));
        if (_cache.categories) localStorage.setItem('luna_settings_categories', JSON.stringify(_cache.categories));
        if (_cache.factories) localStorage.setItem('luna_settings_factories', JSON.stringify(_cache.factories));
        if (_cache.guests) localStorage.setItem('luna_settings_guests', JSON.stringify(_cache.guests));
      } catch(e) {}
    },
    _getCache: function() { return _cache; },
    _setCache: function(url, data) {
      if (url.indexOf('categories') >= 0) _cache.categories = data;
      else if (url.indexOf('procacc') >= 0) _cache.procacc = data;
      else if (url.indexOf('factories') >= 0) _cache.factories = data;
      else if (url.indexOf('fabrics') >= 0) _cache.fabrics = data;
      else if (url.indexOf('styles') >= 0) {
        _cache.styles = data;
        // 合并本地已有数据：服务端可能缺少某些字段（图片、辅料、加工备注等）
        if (_cache.styles) {
          var oldStyles = {};
          try {
            var oldRaw = localStorage.getItem('luna_styles_data');
            if (oldRaw) { var oldArr = JSON.parse(oldRaw); oldArr.forEach(function(s){ oldStyles[s.code] = s; }); }
          } catch(e) {}
          _cache.styles.forEach(function(s) {
            var old = oldStyles[s.code];
            if (old) {
              // 保留图片
              if ((!s.images || s.images.length === 0) && old.images && old.images.length > 0) {
                s.images = old.images;
              }
              // 保留辅料/包边备注
              if (!s.edgeNote && old.edgeNote) s.edgeNote = old.edgeNote;
              // 保留加工备注
              if (!s.processingNote && old.processingNote) s.processingNote = old.processingNote;
            }
            delete s.name;
          });
        }
      }
      else if (url.indexOf('orders') >= 0) {
        // 防止 firstLoad 覆盖本地刚保存的数据（各步骤完成状态）
        var _oldOrders = _cache.orders || [];
        var _oldMap = {};
        _oldOrders.forEach(function(o){ _oldMap[o.id] = o; });
        _cache.orders = data;
        if (_cache.orders) {
          _cache.orders.forEach(function(o) {
            var _old = _oldMap[o.id];
            if (_old) {
              ['marker_complete','cutting_complete','pickup_complete','shipping_complete'].forEach(function(step) {
                if (_old[step] && _old[step].completed === 1 && (!o[step] || o[step].completed === 0)) {
                  o[step] = _old[step];
                }
              });
            }
          });
        }
      }
      else if (url.indexOf('cart') >= 0) _cache.cart = data;
      else if (url.indexOf('guests') >= 0) _cache.guests = data;
    },
    _setUser: function(user) { _user = user; },
    _loadFromLocalStorage: function() {
      try {
        var keys = {
          'luna_styles_data': 'styles',
          'luna_orders_data': 'orders',
          'luna_cart_data': 'cart',
          'luna_settings_fabrics': 'fabrics',
          'luna_settings_procacc': 'procacc',
          'luna_settings_categories': 'categories',
          'luna_settings_factories': 'factories',
          'luna_settings_guests': 'guests'
        };
        for (var k in keys) {
          var raw = localStorage.getItem(k);
          if (raw) _cache[keys[k]] = JSON.parse(raw);
        }
        var userRaw = localStorage.getItem('luna_user_session');
        if (userRaw) _user = JSON.parse(userRaw);
        // 清理旧数据中的"未命名款式"（name 字段已废弃）
        if (_cache.styles) {
          for (var si = 0; si < _cache.styles.length; si++) {
            delete _cache.styles[si].name;
          }
        }
        if (_cache.orders) {
          _cache.orders.forEach(function(o){
            if (o.items) o.items.forEach(function(it){
              if (it.name === '未命名款式') it.name = '';
            });
          });
        }
        if (_cache.cart) {
          _cache.cart = _cache.cart.filter(function(it){ return it.name !== '未命名款式'; });
        }
      } catch(e) {}
      // 注意：此处故意不设 _initialized = true
      // 因为后续的 ensureInit() 需要执行 loadAllData() 从服务器拉取最新数据
      // 如果提前设了 true，getOrders() / findOrder() 等函数读到的将是 localStorage 旧数据
    },

    syncFromServer: function(callback) {
      // Stub — not needed anymore (API-driven)
      if (callback) callback(null);
    },
    syncAllToServer: syncAllToServer,

    // ─── 全局导航栏 ───
    renderNav: function() {
      if (document.getElementById('diana-nav')) return; // already rendered

      // Inject nav CSS once
      if (!document.getElementById('diana-nav-style')) {
        var s = document.createElement('style');
        s.id = 'diana-nav-style';
        s.textContent =
          '.diana-header{position:sticky;top:0;z-index:9999;background:#fff;border-bottom:1px solid #EBE8E3;height:48px;display:flex;align-items:center;padding:0 16px;gap:10px}' +
          '.diana-hamburger{background:none;border:none;font-size:22px;cursor:pointer;padding:4px;color:#1C1C1C;line-height:1;display:flex;align-items:center}' +
          '.diana-hamburger:hover{color:#C8A56D}' +
          '.diana-logo{font-family:\'Playfair Display\',serif;font-size:15px;letter-spacing:3px;color:#C8A56D;text-decoration:none}' +
          '.diana-logo:hover{opacity:.8}' +
          '.diana-nav-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:99999}' +
          '.diana-nav-overlay.open{display:block}' +
          '.diana-nav-drawer{position:fixed;top:0;left:0;bottom:0;width:280px;max-width:80vw;background:#fff;z-index:100000;transform:translateX(-100%);transition:transform .3s cubic-bezier(.25,.46,.45,.94);overflow-y:auto}' +
          '.diana-nav-overlay.open .diana-nav-drawer{transform:translateX(0)}' +
          '.diana-nav-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid #EBE8E3}' +
          '.diana-nav-logo{font-family:\'Playfair Display\',serif;font-size:16px;letter-spacing:3px;color:#C8A56D}' +
          '.diana-nav-close{background:none;border:none;font-size:22px;cursor:pointer;color:#999;padding:4px}' +
          '.diana-nav-close:hover{color:#1C1C1C}' +
          '.diana-nav-section{padding:12px 0;border-bottom:1px solid #F5F3EF}' +
          '.diana-nav-section:last-child{border-bottom:none}' +
          '.diana-nav-section-title{padding:4px 20px;font-size:10px;font-weight:600;color:#C8A56D;letter-spacing:1px;text-transform:uppercase}' +
          '.diana-nav-item{display:block;padding:10px 20px;font-size:14px;color:#1C1C1C;text-decoration:none;transition:background .15s}' +
          '.diana-nav-item:hover{background:#F8F6F0;color:#C8A56D}' +
          '.diana-nav-item.logout{color:#e05c5c}' +
          '.diana-nav-item.logout:hover{background:#fde8e8;color:#c0392b}' +
          '.luna-header,.header,.header-inner{display:none!important}';
        document.head.appendChild(s);
      }

      // Build HTML
      var div = document.createElement('div');
      div.id = 'diana-nav';
      div.innerHTML =
        '<header class="diana-header">' +
          '<button class="diana-hamburger" id="dianaHamburger" aria-label="菜单">☰</button>' +
          '<a href="guest-styles.html" class="diana-logo">DIANA</a>' +
        '</header>' +
        '<div class="diana-nav-overlay" id="dianaNavOverlay">' +
          '<div class="diana-nav-drawer">' +
            '<div class="diana-nav-header">' +
              '<span class="diana-nav-logo">DIANA</span>' +
              '<button class="diana-nav-close" id="dianaNavClose">&times;</button>' +
            '</div>' +
            '<div class="diana-nav-section">' +
              '<div class="diana-nav-section-title">款式</div>' +
              '<a href="style-manage.html?sort=new" class="diana-nav-item">最近添加</a>' +
              '<a href="style-manage.html?sort=category" class="diana-nav-item">类型</a>' +
            '</div>' +
            '<div class="diana-nav-section">' +
              '<div class="diana-nav-section-title">订单</div>' +
              '<a href="my-orders.html" class="diana-nav-item">我的订单</a>' +
              '<a href="orders.html" class="diana-nav-item">订单管理</a>' +
            '</div>' +
            '<div class="diana-nav-section">' +
              '<div class="diana-nav-section-title">管理</div>' +
              '<a href="dashboard.html" class="diana-nav-item">工作台</a>' +
              '<a href="login-logs.html" class="diana-nav-item">登录记录</a>' +
              '<a href="change-password.html" class="diana-nav-item">修改密码</a>' +
              '<a href="#" class="diana-nav-item logout" id="dianaNavLogout">退出登录</a>' +
            '</div>' +
          '</div>' +
        '</div>';

      document.body.insertBefore(div, document.body.firstChild);

      // Hide old per-page headers
      var oldHeaders = document.querySelectorAll('.luna-header, .header, .header-inner');
      oldHeaders.forEach(function(h) {
        if (h.closest && !h.closest('#diana-nav')) h.style.display = 'none';
      });

      // Fix body padding for the fixed header
      document.body.style.paddingTop = '0';

      // Event handlers
      var overlay = document.getElementById('dianaNavOverlay');
      document.getElementById('dianaHamburger').onclick = function() { overlay.classList.add('open'); };
      document.getElementById('dianaNavClose').onclick = function() { overlay.classList.remove('open'); };
      overlay.onclick = function(e) { if (e.target === overlay) overlay.classList.remove('open'); };
      document.getElementById('dianaNavLogout').onclick = function(e) {
        e.preventDefault();
        overlay.classList.remove('open');
        if (LUNA.logout) LUNA.logout();
      };
    }
  };

})();

// ===== 页面加载时自动初始化 =====
// 策略: 只从 localStorage 读，秒开，不做后台请求
(function() {
  // 1. 立即从 localStorage 加载到缓存
  if (typeof LUNA !== 'undefined' && LUNA._loadFromLocalStorage) {
    LUNA._loadFromLocalStorage();
  }

  // 2. 延迟发射初始化事件（确保页面的事件监听器已注册）
  // 页面 script 在 luna-data.js 之后，立即发射会导致监听器还没注册就错过了
  if (typeof window !== 'undefined') {
    setTimeout(function() {
      window.dispatchEvent(new CustomEvent('luna-data-initialized'));
    }, 1);
  }

  // 3. 每次加载页面都后台拉一次数据确保最新（localStorage 可能过时）
  if (typeof window !== 'undefined') {
    function firstLoad() {
      var u = ['categories','procacc','factories','fabrics','styles','orders','cart','guests'];
      var p = u.length;
      u.forEach(function(key) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/api/data/' + key, true);
        xhr.withCredentials = true;
        xhr.onload = function() {
          if (xhr.status === 200) {
            try {
              var d = JSON.parse(xhr.responseText);
              if (LUNA && LUNA._setCache) LUNA._setCache('/api/data/' + key, d);
            } catch(e) {}
          }
          p--;
          if (p === 0) {
            if (LUNA && LUNA._syncToLocalStorage) LUNA._syncToLocalStorage();
            window.dispatchEvent(new CustomEvent('luna-data-changed'));
          }
        };
        xhr.onerror = function() { p--; };
        xhr.send();
      });
    }
    setTimeout(firstLoad, 50);
  }

  // 4. 购物车徽标
  function updateCartBadge() {
    var els = document.querySelectorAll('.cart-float .badge, .cart-badge');
    var count = LUNA.getCartCount();
    els.forEach(function(el) {
      el.textContent = count;
      el.style.display = count > 0 ? 'flex' : 'none';
    });
  }
  if (typeof window !== 'undefined') {
    updateCartBadge();
    window.addEventListener('luna-data-changed', updateCartBadge);
  }

  // 5. 首次加载时后台拉一次客人数据（仅 localStorage 为空时）
  var hasGuests = false;
  try { hasGuests = !!localStorage.getItem('luna_settings_guests'); } catch(e) {}
  if (!hasGuests && typeof window !== 'undefined') {
    var gxhr = new XMLHttpRequest();
    gxhr.open('GET', '/api/data/guests', true);
    gxhr.withCredentials = true;
    gxhr.onload = function() {
      if (gxhr.status === 200) {
        try {
          var d = JSON.parse(gxhr.responseText);
          if (LUNA && LUNA._setCache) LUNA._setCache('/api/data/guests', d);
          if (LUNA && LUNA._syncToLocalStorage) LUNA._syncToLocalStorage();
          window.dispatchEvent(new CustomEvent('luna-data-changed'));
        } catch(e) {}
      }
    };
    gxhr.send();
  }
})();

// ===== 全局弹窗覆盖 =====
(function() {
  if (typeof window === 'undefined') return;
  // 注入 CSS + 弹窗 DOM（如果还没有的话）
  (function ensureDialog() {
    if (document.getElementById('lunaDialogOverlay')) return;
    if (LUNA && LUNA._getDialog) {
      try { LUNA._getDialog(); } catch(e) {}
    }
  })();
  // 覆盖 alert → 自定义弹窗
  window.alert = function(msg) {
    if (LUNA && LUNA.showAlert) {
      LUNA.showAlert(msg);
    }
  };
})();

// 跨标签页同步
if (typeof window !== 'undefined') {
  window.addEventListener('storage', function(e) {
    if (LUNA && LUNA._loadFromLocalStorage) {
      LUNA._loadFromLocalStorage();
    }
    var badge = document.querySelector('.cart-badge');
    if (badge) {
      try { badge.textContent = LUNA.getCartCount(); } catch(e) {}
    }
  });
}
