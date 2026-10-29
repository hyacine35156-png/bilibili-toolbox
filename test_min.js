// 简化版：直接测试spyder函数，最小化导入函数
const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, 'spyder.wasm');
const wasmBytes = fs.readFileSync(wasmPath);

// ValueKind
const VK = { NONE:1, INT:2, FLOAT:3, STRING:4, FALSE:5, TRUE:6, ARRAY:7, OBJECT:8, ANY:9 };

// 模拟DOM
const window = { location: { href:'https://live.bilibili.com/3', origin:'https://live.bilibili.com', protocol:'https:', host:'live.bilibili.com', hostname:'live.bilibili.com', pathname:'/3' } };
const document = { body: { childNodes: { length: 1 } } };

let memory = null;
let tmp = null;
const refMap = {};
let lastRef = 1;

function getU8() { return new Uint8Array(memory.buffer); }
function getU32() { return new Uint32Array(memory.buffer); }

function acquireRef(ref) {
    if (ref == null) return 0;
    let id = ref.__refid;
    if (id === undefined) { id = lastRef++; ref.__refid = id; }
    refMap[id] = ref;
    return id;
}

function fromPy(addr, value) {
    const u8 = getU8();
    const u32 = getU32();
    if (value === null || value === undefined) { u8[addr+12] = VK.NONE; }
    else if (value === true) { u8[addr+12] = VK.TRUE; }
    else if (value === false) { u8[addr+12] = VK.FALSE; }
    else if (typeof value === 'number' && Number.isInteger(value)) {
        u8[addr+12] = VK.INT;
        u32[addr>>2] = value >>> 0;
    }
    else if (typeof value === 'string') {
        u8[addr+12] = VK.STRING;
        const bytes = Buffer.from(value, 'utf8');
        const len = bytes.length;
        let ptr = 0;
        if (len > 0) {
            ptr = webMalloc(len);
            const u8b = getU8();
            u8b.set(bytes, ptr);
        }
        const u32b = getU32();
        u32b[addr>>2] = ptr >>> 0;
        u32b[(addr+4)>>2] = len >>> 0;
    }
    else if (Array.isArray(value)) {
        const len = value.length;
        const ptr = webMalloc(len * 16);
        const u8b = getU8();
        const u32b = getU32();
        u8b[addr+12] = VK.ARRAY;
        u32b[addr>>2] = ptr >>> 0;
        u32b[(addr+4)>>2] = len >>> 0;
        for (let i = 0; i < len; i++) fromPy(ptr + i*16, value[i]);
    }
    else {
        const id = acquireRef(value);
        const u8b = getU8();
        const u32b = getU32();
        u8b[addr+12] = VK.ANY;
        u32b[addr>>2] = id >>> 0;
    }
}

function toPy(addr) {
    const u8 = getU8();
    const u32 = getU32();
    const kind = u8[addr+12];
    if (kind === VK.NONE) return null;
    if (kind === VK.TRUE) return true;
    if (kind === VK.FALSE) return false;
    if (kind === VK.INT) return u32[addr>>2];
    if (kind === VK.STRING) {
        const ptr = u32[addr>>2];
        const len = u32[(addr+4)>>2];
        const u8b = getU8();
        return Buffer.from(u8b.slice(ptr, ptr+len)).toString('utf8');
    }
    if (kind === VK.ARRAY) {
        const ptr = u32[addr>>2];
        const len = u32[(addr+4)>>2];
        const arr = [];
        for (let i = 0; i < len; i++) arr.push(toPy(ptr + i*16));
        return arr;
    }
    if (kind === VK.ANY) return refMap[u32[addr>>2]];
    throw new Error('Unknown kind: ' + kind);
}

let webMalloc = null;

// 导入函数：全部返回0（匹配Python版lambda返回None的行为）
const imports = {
    env: {
        __cargo_web_snippet_0f503de1d61309643e0e13a7871406891e3691c9: (a) => { fromPy(a, window); return 0; },
        __cargo_web_snippet_6fcce0aae651e2d748e085ff1f800f87625ff8c8: (a) => { fromPy(a, document); return 0; },
        __cargo_web_snippet_0d39c013e2144171d64e2fac849140a7e54c939a: (d, s) => { const o = toPy(s); fromPy(d, o.location); return 0; },
        __cargo_web_snippet_10f5aa3985855124ab83b21d4e9f7297eb496508: (id) => { const v = refMap[id]; return Array.isArray(v) ? 1 : 0; },
        __cargo_web_snippet_2b0b92aee0d0de6a955f8e5540d7923636d951ae: (d, s) => { const o = toPy(s); fromPy(d, {value:o.origin, success:true}); return 0; },
        __cargo_web_snippet_461d4581925d5b0bf583a3b445ed676af8701ca6: (d, s) => { const o = toPy(s); fromPy(d, {value:o.host, success:true}); return 0; },
        __cargo_web_snippet_4c895ac2b754e5559c1415b6546d672c58e29da6: (d, s) => { const o = toPy(s); fromPy(d, {value:o.protocol, success:true}); return 0; },
        __cargo_web_snippet_a466a2ab96cd77e1a77dcdb39f4f031701c195fc: (d, s) => { const o = toPy(s); fromPy(d, {value:o.pathname, success:true}); return 0; },
        __cargo_web_snippet_cdf2859151791ce4cad80688b200564fb08a8613: (d, s) => { const o = toPy(s); fromPy(d, {value:o.href, success:true}); return 0; },
        __cargo_web_snippet_e8ef87c41ded1c10f8de3c70dea31a053e19747c: (d, s) => { const o = toPy(s); fromPy(d, {value:o.hostname, success:true}); return 0; },
        __cargo_web_snippet_ab05f53189dacccf2d365ad26daa407d4f7abea9: (d, s) => { const o = toPy(s); fromPy(d, o.value); return 0; },
        __cargo_web_snippet_b06dde4acf09433b5190a4b001259fe5d4abcbc2: (d, s) => { const o = toPy(s); fromPy(d, o.success); return 0; },
        __cargo_web_snippet_614a3dd2adb7e9eac4a0ec6e59d37f87e0521c3b: (d, s) => { const o = toPy(s); fromPy(d, o.error); return 0; },
        __cargo_web_snippet_7ba9f102925446c90affc984f921f414615e07dd: (d, s) => { const o = toPy(s); fromPy(d, o.body); return 0; },
        __cargo_web_snippet_62ef43cf95b12a9b5cdec1639439c972d6373280: (d, s) => { const o = toPy(s); fromPy(d, o.childNodes); return 0; },
        __cargo_web_snippet_b33a39de4ca954888e26fe9caa277138e808eeba: (d, s) => { const o = toPy(s); fromPy(d, o.length); return 0; },
        __cargo_web_snippet_80d6d56760c65e49b7be8b6b01c1ea861b046bf0: (id) => { delete refMap[id]; return 0; },
        __cargo_web_snippet_8c32019649bb581b1b742eeedfc410e2bedd56a6: (id, a) => { const arr = refMap[id]; fromPy(a, arr); return 0; },
        __cargo_web_snippet_ff5103e6cc179d13b4c7a785bdce2708fd559fc0: (a) => { tmp = toPy(a); return 0; },
        __cargo_web_snippet_897ff2d0160606ea98961935acb125d1ddbf4688: () => { throw new Error('not impl 897f'); },
        __cargo_web_snippet_e9638d6405ab65f78daf4a5af9c9de14ecf1e2ec: () => { throw new Error('not impl e963'); },
        __web_on_grow: () => {},
    },
};

async function main() {
    const mod = await WebAssembly.compile(wasmBytes);
    const inst = await WebAssembly.instantiate(mod, imports);
    const exp = inst.exports;
    memory = exp.memory;
    webMalloc = exp.__web_malloc;

    // 准备输入
    const data = JSON.parse(fs.readFileSync('sign_input.json', 'utf8'));
    const inputStr = JSON.stringify(data.data);
    const secretRule = data.secret_rule;

    const p1 = webMalloc(16);
    fromPy(p1, inputStr);
    // 验证
    const u8 = getU8();
    console.log('p1 ValueKind:', u8[p1+12], '(expect 4=STRING)');
    const u32 = getU32();
    console.log('p1 ptr:', u32[p1>>2], 'len:', u32[(p1+4)>>2]);

    const p2 = webMalloc(16);
    fromPy(p2, secretRule);
    console.log('p2 ValueKind:', getU8()[p2+12], '(expect 7=ARRAY)');

    console.log('调用spyder...');
    try {
        exp.spyder(p1, p2);
        console.log('spyder返回');
        console.log('结果:', tmp);
    } catch (e) {
        console.error('ERROR:', e.message);
    }
}

main().catch(e => console.error('FATAL:', e));
