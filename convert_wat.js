const wabt = require('wabt')();
const fs = require('fs');

(async () => {
    const wabtModule = await wabt;
    const bytes = fs.readFileSync('spyder.wasm');
    const mod = wabtModule.readWasm(bytes, { readDebugNames: true });
    const wat = mod.toText({ foldExprs: true });
    fs.writeFileSync('spyder.wat', wat);
    console.log('已导出spyder.wat, 长度:', wat.length);
})();
