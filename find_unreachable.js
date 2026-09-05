const fs = require('fs');
const wat = fs.readFileSync('spyder.wat', 'utf8');
const lines = wat.split('\n');
let start = -1, end = -1;
for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('(func $spyder')) start = i;
    if (start >= 0 && i > start && lines[i].match(/^\s*\)\s*$/) && !lines[i].includes('(')) { end = i; break; }
}
console.log('spyder函数范围:', start + 1, '-', end + 1);
for (let i = start; i <= end; i++) {
    if (lines[i].includes('unreachable')) console.log('行', i + 1, ':', lines[i].trim());
}
// 也搜索call 104
console.log('\ncall 104位置:');
for (let i = start; i <= end; i++) {
    if (lines[i].includes('call 104')) console.log('行', i + 1, ':', lines[i].trim());
}
