const fs = require('fs');
let c = fs.readFileSync('fabric-warehouse.html', 'utf8');

// Find the exact addCompRow function block
let start = c.indexOf('function addCompRow(fi)');
let end = c.indexOf('function removeCompRow', start);
let oldFunc = c.substring(start, end).trim();
console.log('Found addCompRow, length:', oldFunc.length);

// Build new function
let newFunc = 
unction addCompRow(fi) {
  var wrap = document.getElementById('comp-wrap-' + fi);
  if (!wrap) return;
  var div = document.createElement('div');
  div.className = 'comp-group';
  div.innerHTML = '<input class="cp" type="text" inputmode="numeric" maxlength="3" value="" placeholder="5" oninput="saveComp(' + fi + ')">' +
    '<span class="pct-suffix">%</span>' +
    '<input class="ci" type="text" value="" placeholder="POLIESTERE" oninput="saveComp(' + fi + ')">' +
    '<button class="comp-grp-del" onclick="removeCompRow(this,' + fi + ')" title="删除此组">✕</button>';
  wrap.insertBefore(div, wrap.lastElementChild);
};

c = c.substring(0, start) + newFunc + c.substring(end);
fs.writeFileSync('fabric-warehouse.html', c, 'utf8');
console.log('OK: addCompRow replaced');
