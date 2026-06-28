// LUNA 新款批量添加脚本
// 使用方法：在浏览器控制台粘贴执行，或在HTML中引入此文件

window.addNewStyles = function() {
  var newStyles = [
    // ========== 吊带 (2款) ==========
    {
      code: 'CAM001',
      name: '真丝蝴蝶结吊带',
      type: 'normale',
      category: '吊带',
      suggestedPrice: 89.00,
      cost: 45.00,
      images: ['images/styles/CAM001_01.jpg', 'images/styles/CAM001_02.jpg', 'images/styles/CAM001_03.jpg'],
      fabrics: [
        { name: '桑蚕丝', pricePerM: 28.50, usage: 1.2, subtotal: 34.20 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },
    {
      code: 'CAM002',
      name: '蕾丝花边吊带背心',
      type: 'normale',
      category: '吊带',
      suggestedPrice: 69.00,
      cost: 35.00,
      images: ['images/styles/CAM002_01.jpg', 'images/styles/CAM002_02.jpg', 'images/styles/CAM002_03.jpg'],
      fabrics: [
        { name: '蕾丝面料', pricePerM: 22.00, usage: 0.8, subtotal: 17.60 },
        { name: '弹力内衬', pricePerM: 15.00, usage: 0.8, subtotal: 12.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },

    // ========== 外套/大衣 (2款) ==========
    {
      code: 'COA001',
      name: '羊毛双排扣大衣',
      type: 'normale',
      category: '外套',
      suggestedPrice: 299.00,
      cost: 150.00,
      images: ['images/styles/COA001_01.jpg', 'images/styles/COA001_02.jpg', 'images/styles/COA001_03.jpg', 'images/styles/COA001_04.jpg'],
      fabrics: [
        { name: '羊毛呢', pricePerM: 68.00, usage: 2.8, subtotal: 190.40 },
        { name: '铜氨纤维里布', pricePerM: 25.00, usage: 2.0, subtotal: 50.00 }
      ],
      sizes: ['S', 'M', 'L', 'XL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },
    {
      code: 'COA002',
      name: '轻薄防晒风衣',
      type: 'normale',
      category: '外套',
      suggestedPrice: 129.00,
      cost: 65.00,
      images: ['images/styles/COA002_01.jpg', 'images/styles/COA002_02.jpg', 'images/styles/COA002_03.jpg'],
      fabrics: [
        { name: '聚酯纤维', pricePerM: 18.00, usage: 2.0, subtotal: 36.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },

    // ========== 衬衫 (2款) ==========
    {
      code: 'SHI001',
      name: '法式棉质衬衫',
      type: 'normale',
      category: '衬衫',
      suggestedPrice: 119.00,
      cost: 60.00,
      images: ['images/styles/SHI001_01.jpg', 'images/styles/SHI001_02.jpg', 'images/styles/SHI001_03.jpg', 'images/styles/SHI001_04.jpg'],
      fabrics: [
        { name: '棉府绸', pricePerM: 32.00, usage: 2.0, subtotal: 64.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },
    {
      code: 'SHI002',
      name: '真丝飘带衬衫',
      type: 'normale',
      category: '衬衫',
      suggestedPrice: 189.00,
      cost: 95.00,
      images: ['images/styles/SHI002_01.jpg', 'images/styles/SHI002_02.jpg', 'images/styles/SHI002_03.jpg'],
      fabrics: [
        { name: '桑蚕丝', pricePerM: 45.00, usage: 2.2, subtotal: 99.00 }
      ],
      sizes: ['S', 'M', 'L', 'XL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },

    // ========== 连衣裙 (2款) ==========
    {
      code: 'DRE001',
      name: '碎花雪纺连衣裙',
      type: 'normale',
      category: '连衣裙',
      suggestedPrice: 159.00,
      cost: 80.00,
      images: ['images/styles/DRE001_01.jpg', 'images/styles/DRE001_02.jpg', 'images/styles/DRE001_03.jpg', 'images/styles/DRE001_04.jpg'],
      fabrics: [
        { name: '雪纺', pricePerM: 28.00, usage: 3.0, subtotal: 84.00 },
        { name: '弹力内衬', pricePerM: 15.00, usage: 2.0, subtotal: 30.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },
    {
      code: 'DRE002',
      name: '格纹衬衫连衣裙',
      type: 'normale',
      category: '连衣裙',
      suggestedPrice: 149.00,
      cost: 75.00,
      images: ['images/styles/DRE002_01.jpg', 'images/styles/DRE002_02.jpg', 'images/styles/DRE002_03.jpg'],
      fabrics: [
        { name: '棉府绸', pricePerM: 35.00, usage: 2.8, subtotal: 98.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },

    // ========== 套装 (2款) ==========
    {
      code: 'SUI001',
      name: '西装外套套装',
      type: 'normale',
      category: '套装',
      suggestedPrice: 259.00,
      cost: 130.00,
      images: ['images/styles/SUI001_01.jpg', 'images/styles/SUI001_02.jpg', 'images/styles/SUI001_03.jpg', 'images/styles/SUI001_04.jpg'],
      fabrics: [
        { name: '西装面料', pricePerM: 45.00, usage: 3.5, subtotal: 157.50 },
        { name: '铜氨纤维里布', pricePerM: 25.00, usage: 2.0, subtotal: 50.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },
    {
      code: 'SUI002',
      name: '雪纺两件套',
      type: 'normale',
      category: '套装',
      suggestedPrice: 199.00,
      cost: 100.00,
      images: ['images/styles/SUI002_01.jpg', 'images/styles/SUI002_02.jpg', 'images/styles/SUI002_03.jpg'],
      fabrics: [
        { name: '雪纺', pricePerM: 28.00, usage: 4.0, subtotal: 112.00 }
      ],
      sizes: ['S', 'M', 'L', 'XL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },

    // ========== 裤装 (2款) ==========
    {
      code: 'PAN001',
      name: '高腰阔腿裤',
      type: 'normale',
      category: '裤装',
      suggestedPrice: 109.00,
      cost: 55.00,
      images: ['images/styles/PAN001_01.jpg', 'images/styles/PAN001_02.jpg', 'images/styles/PAN001_03.jpg'],
      fabrics: [
        { name: '涤纶混纺', pricePerM: 22.00, usage: 1.5, subtotal: 33.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },
    {
      code: 'PAN002',
      name: '直筒休闲裤',
      type: 'normale',
      category: '裤装',
      suggestedPrice: 99.00,
      cost: 50.00,
      images: ['images/styles/PAN002_01.jpg', 'images/styles/PAN002_02.jpg', 'images/styles/PAN002_03.jpg', 'images/styles/PAN002_04.jpg'],
      fabrics: [
        { name: '棉麻混纺', pricePerM: 28.00, usage: 1.4, subtotal: 39.20 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },

    // ========== 半身裙 (2款) ==========
    {
      code: 'SKI001',
      name: 'A字百褶裙',
      type: 'normale',
      category: '半身裙',
      suggestedPrice: 89.00,
      cost: 45.00,
      images: ['images/styles/SKI001_01.jpg', 'images/styles/SKI001_02.jpg', 'images/styles/SKI001_03.jpg'],
      fabrics: [
        { name: '聚酯纤维', pricePerM: 18.00, usage: 1.8, subtotal: 32.40 },
        { name: '弹力内衬', pricePerM: 15.00, usage: 1.0, subtotal: 15.00 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL'],
      enabled: true,
      createdAt: new Date().toISOString()
    },
    {
      code: 'SKI002',
      name: '高腰铅笔裙',
      type: 'normale',
      category: '半身裙',
      suggestedPrice: 79.00,
      cost: 40.00,
      images: ['images/styles/SKI002_01.jpg', 'images/styles/SKI002_02.jpg', 'images/styles/SKI002_03.jpg', 'images/styles/SKI002_04.jpg'],
      fabrics: [
        { name: '弹力西装料', pricePerM: 32.00, usage: 1.2, subtotal: 38.40 }
      ],
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
      enabled: true,
      createdAt: new Date().toISOString()
    }
  ];

  // 执行添加
  var existing = LUNA.getStyles() || [];
  var added = 0;
  var skipped = 0;

  newStyles.forEach(function(style) {
    // 检查是否已存在
    var exists = existing.find(function(s) { return s.code === style.code; });
    if (exists) {
      console.log('⚠️ 款式 ' + style.code + ' 已存在，跳过');
      skipped++;
      return;
    }

    // 添加到现有款式数组
    existing.push(style);
    added++;
    console.log('✅ 已添加款式: ' + style.code + ' - ' + style.name);
  });

  // 保存到系统
  if (added > 0) {
    LUNA.saveStyles(existing);
    alert('🎉 成功添加 ' + added + ' 款新款式！');
    console.log('\n🎉 成功添加 ' + added + ' 款新款式！');
    if (skipped > 0) {
      console.log('⏭️ 跳过 ' + skipped + ' 个已存在的款式');
    }
    console.log('\n📋 款式列表:');
    newStyles.forEach(function(s) {
      console.log('  • ' + s.code + ' - ' + s.name + ' (€' + s.suggestedPrice + ')');
    });
    // 刷新页面显示新款式
    location.reload();
  } else {
    alert('⚠️ 没有新款式被添加（可能都已存在）');
    console.log('\n⚠️ 没有新款式被添加（可能都已存在）');
  }
};

// 自动添加执行按钮到页面
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  setTimeout(addStylesButton, 100);
} else {
  document.addEventListener('DOMContentLoaded', addStylesButton);
}

function addStylesButton() {
  // 只在款式管理页面显示按钮
  if (!document.querySelector('.style-manage, [class*="style"]')) return;

  var btn = document.createElement('button');
  btn.textContent = '➕ 批量添加14款新款式';
  btn.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;padding:12px 20px;background:#C8A56D;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;box-shadow:0 4px 12px rgba(0,0,0,.2);';
  btn.onclick = function() {
    if (confirm('确定要批量添加14款新款式吗？\n\n包括：吊带×2、外套×2、衬衫×2、连衣裙×2、套装×2、裤装×2、半身裙×2')) {
      window.addNewStyles();
    }
  };
  document.body.appendChild(btn);
  console.log('✅ 批量添加款式按钮已创建，点击右下角按钮即可添加');
}
