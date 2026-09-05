// B站直播心跳签名计算（Node.js调试版）
const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, 'spyder.wasm');
const wasmBytes = fs.readFileSync(wasmPath);

const ValueKind = {
    UNDEFINED: 0, NONE: 1, INT: 2, FLOAT: 3, STRING: 4,
    FALSE: 5, TRUE: 6, ARRAY: 7, OBJECT: 8, ANY: 9,
};

const window = { location: { href: 'https://live.bilibili.com/3', origin: 'https://live.bilibili.com', protocol: 'https:', host: 'live.bilibili.com', hostname: 'live.bilibili.com', pathname: '/3' } };
const document = { body: { childNodes: { length: 1 } } };

let debugLog = [];
function log(msg) { debugLog.push(msg); if (debugLog.length > 100) debugLog.shift(); }

class StdWeb {
    constructor(wasm) {
        this.wasm = wasm;
        this.tmp = null;
        this.idToRefMap = {};
        this.idToRefcountMap = {};
        this.lastRefid = 1;
    }

    get memView() { return new Uint8Array(this.wasm.memory.buffer); }
    get memView32() { return new Uint32Array(this.wasm.memory.buffer); }

    alloc(size) { const p = this.wasm.webMalloc(size); log(`alloc(${size}) = ${p}`); return p; }

    prepareAnyArg(value) {
        const address = this.alloc(16);
        this.fromPy(address, value);
        return address;
    }

    acquireTmp() { const v = this.tmp; this.tmp = null; return v; }
    acquirePyReference(refid) { return this.idToRefMap[refid]; }

    acquireRustReference(ref) {
        if (ref === null || ref === undefined) return 0;
        let refid = ref.__refid;
        if (refid === undefined) { refid = this.lastRefid++; ref.__refid = refid; }
        if (refid in this.idToRefMap) { this.idToRefcountMap[refid]++; }
        else { this.idToRefMap[refid] = ref; this.idToRefcountMap[refid] = 1; }
        return refid;
    }

    decrementRefcount(refid) {
        if (--this.idToRefcountMap[refid] === 0) {
            delete this.idToRefMap[refid];
            delete this.idToRefcountMap[refid];
        }
    }

    fromPy(address, value) {
        const u8 = this.memView;
        const u32 = this.memView32;
        log(`fromPy(${address}, ${typeof value}: ${String(value).substring(0, 50)})`);
        if (value === null || value === undefined) {
            u8[address + 12] = ValueKind.NONE;
        } else if (value === true) {
            u8[address + 12] = ValueKind.TRUE;
        } else if (value === false) {
            u8[address + 12] = ValueKind.FALSE;
        } else if (typeof value === 'number' && Number.isInteger(value)) {
            u8[address + 12] = ValueKind.INT;
            u32[address >> 2] = value >>> 0;
        } else if (typeof value === 'string') {
            u8[address + 12] = ValueKind.STRING;
            this.toUtf8String(address, value);
        } else if (Array.isArray(value)) {
            this.serializeArray(address, value);
        } else {
            const refid = this.acquireRustReference(value);
            u8[address + 12] = ValueKind.ANY;
            u32[address >> 2] = refid >>> 0;
        }
    }

    toPy(address) {
        const u8 = this.memView;
        const u32 = this.memView32;
        const kind = u8[address + 12];
        log(`toPy(${address}) kind=${kind}`);
        if (kind === ValueKind.NONE) return null;
        if (kind === ValueKind.TRUE) return true;
        if (kind === ValueKind.FALSE) return false;
        if (kind === ValueKind.INT) return u32[address >> 2];
        if (kind === ValueKind.STRING) {
            const pointer = u32[address >> 2];
            const length = u32[(address + 4) >> 2];
            return this.toPyString(pointer, length);
        }
        if (kind === ValueKind.ARRAY) {
            const pointer = u32[address >> 2];
            const length = u32[(address + 4) >> 2];
            const arr = [];
            for (let i = 0; i < length; i++) arr.push(this.toPy(pointer + i * 16));
            return arr;
        }
        if (kind === ValueKind.ANY) {
            const refid = u32[address >> 2];
            return this.acquirePyReference(refid);
        }
        throw new Error(`Unsupported value kind: ${kind}`);
    }

    toUtf8String(address, string) {
        const bytes = Buffer.from(string, 'utf8');
        const length = bytes.length;
        let pointer = 0;
        if (length > 0) {
            pointer = this.alloc(length);
            const u8 = this.memView;
            u8.set(bytes, pointer);
        }
        const u32 = this.memView32;
        u32[address >> 2] = pointer >>> 0;
        u32[(address + 4) >> 2] = length >>> 0;
    }

    toPyString(pointer, length) {
        const u8 = this.memView;
        return Buffer.from(u8.slice(pointer, pointer + length)).toString('utf8');
    }

    serializeArray(address, array) {
        const length = array.length;
        const pointer = this.alloc(length * 16);
        const u8 = this.memView;
        const u32 = this.memView32;
        u8[address + 12] = ValueKind.ARRAY;
        u32[address >> 2] = pointer >>> 0;
        u32[(address + 4) >> 2] = length >>> 0;
        for (let i = 0; i < length; i++) this.fromPy(pointer + i * 16, array[i]);
    }
}

function createImports(stdweb) {
    const wrap = (name, fn) => (...args) => {
        try { log(`call ${name}(${args.map(a=>typeof a === 'number'?a:String(a).substring(0,30)).join(', ')})`); const r = fn(...args); log(`  -> ${typeof r === 'number'?r:String(r).substring(0,30)}`); return r; }
        catch (e) { log(`  ERROR: ${e.message}`); throw e; }
    };
    return {
        env: {
            __cargo_web_snippet_0f503de1d61309643e0e13a7871406891e3691c9: wrap('snippet_0f50', (address) => { stdweb.fromPy(address, window); return address; }),
            __cargo_web_snippet_6fcce0aae651e2d748e085ff1f800f87625ff8c8: wrap('snippet_6fc', (address) => { stdweb.fromPy(address, document); return address; }),
            __cargo_web_snippet_0d39c013e2144171d64e2fac849140a7e54c939a: wrap('snippet_0d39', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, obj.location); return dst; }),
            __cargo_web_snippet_10f5aa3985855124ab83b21d4e9f7297eb496508: wrap('snippet_10f5', (refid) => { const val = stdweb.acquirePyReference(refid); return Array.isArray(val) ? 1 : 0; }),
            __cargo_web_snippet_2b0b92aee0d0de6a955f8e5540d7923636d951ae: wrap('snippet_2b0b', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, { value: obj.origin, success: true }); return dst; }),
            __cargo_web_snippet_461d4581925d5b0bf583a3b445ed676af8701ca6: wrap('snippet_461d', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, { value: obj.host, success: true }); return dst; }),
            __cargo_web_snippet_4c895ac2b754e5559c1415b6546d672c58e29da6: wrap('snippet_4c89', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, { value: obj.protocol, success: true }); return dst; }),
            __cargo_web_snippet_a466a2ab96cd77e1a77dcdb39f4f031701c195fc: wrap('snippet_a466', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, { value: obj.pathname, success: true }); return dst; }),
            __cargo_web_snippet_cdf2859151791ce4cad80688b200564fb08a8613: wrap('snippet_cdf2', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, { value: obj.href, success: true }); return dst; }),
            __cargo_web_snippet_e8ef87c41ded1c10f8de3c70dea31a053e19747c: wrap('snippet_e8ef', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, { value: obj.hostname, success: true }); return dst; }),
            __cargo_web_snippet_ab05f53189dacccf2d365ad26daa407d4f7abea9: wrap('snippet_ab05', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, obj.value); return dst; }),
            __cargo_web_snippet_b06dde4acf09433b5190a4b001259fe5d4abcbc2: wrap('snippet_b06d', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, obj.success); return dst; }),
            __cargo_web_snippet_614a3dd2adb7e9eac4a0ec6e59d37f87e0521c3b: wrap('snippet_614a', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, obj.error); return dst; }),
            __cargo_web_snippet_7ba9f102925446c90affc984f921f414615e07dd: wrap('snippet_7ba9', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, obj.body); return dst; }),
            __cargo_web_snippet_62ef43cf95b12a9b5cdec1639439c972d6373280: wrap('snippet_62ef', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, obj.childNodes); return dst; }),
            __cargo_web_snippet_b33a39de4ca954888e26fe9caa277138e808eeba: wrap('snippet_b33a', (dst, src) => { const obj = stdweb.toPy(src); stdweb.fromPy(dst, obj.length); return dst; }),
            __cargo_web_snippet_80d6d56760c65e49b7be8b6b01c1ea861b046bf0: wrap('snippet_80d6', (refid) => { stdweb.decrementRefcount(refid); return refid; }),
            __cargo_web_snippet_8c32019649bb581b1b742eeedfc410e2bedd56a6: wrap('snippet_8c32', (refid, address) => { const array = stdweb.acquirePyReference(refid); stdweb.serializeArray(address, array); return address; }),
            __cargo_web_snippet_ff5103e6cc179d13b4c7a785bdce2708fd559fc0: wrap('snippet_ff51', (address) => { stdweb.tmp = stdweb.toPy(address); return address; }),
            __cargo_web_snippet_897ff2d0160606ea98961935acb125d1ddbf4688: wrap('snippet_897f', () => { throw new Error('Not implemented 897f'); }),
            __cargo_web_snippet_e9638d6405ab65f78daf4a5af9c9de14ecf1e2ec: wrap('snippet_e963', () => { throw new Error('Not implemented e963'); }),
            __web_on_grow: () => {},
        },
    };
}

async function main() {
    let dataStr, secretRuleStr;
    if (process.argv[2] === '--file') {
        const f = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
        dataStr = JSON.stringify(f.data);
        secretRuleStr = JSON.stringify(f.secret_rule);
    } else {
        dataStr = process.argv[2];
        secretRuleStr = process.argv[3];
    }
    if (!dataStr || !secretRuleStr) { console.error('用法: node calc_sign_debug.js \'{"data":...}\' \'[2,5,1,4]\''); process.exit(1); }
    const data = JSON.parse(dataStr);
    const secretRule = JSON.parse(secretRuleStr);

    const wasmModule = await WebAssembly.compile(wasmBytes);
    const dummyWasm = { memory: null, webMalloc: null, webFree: null };
    const stdweb = new StdWeb(dummyWasm);
    const imports = createImports(stdweb);
    const instance = await WebAssembly.instantiate(wasmModule, imports);
    const exports = instance.exports;
    const wasm = { memory: exports.memory, webMalloc: exports.__web_malloc, webFree: exports.__web_free };
    stdweb.wasm = wasm;

    const inputString = JSON.stringify(data);
    log(`inputString: ${inputString}`);
    const stringAddr = stdweb.prepareAnyArg(inputString);
    const arrayAddr = stdweb.prepareAnyArg(secretRule);

    log(`calling spyder(${stringAddr}, ${arrayAddr})`);
    try {
        exports.spyder(stringAddr, arrayAddr);
    } catch (e) {
        console.error('WASM ERROR:', e.message);
        console.error('Debug log:');
        debugLog.forEach(l => console.error('  ', l));
        process.exit(1);
    }

    const result = stdweb.acquireTmp();
    console.log(result);
}

main().catch(err => {
    console.error('错误:', err.message);
    console.error('Debug log:');
    debugLog.forEach(l => console.error('  ', l));
    process.exit(1);
});
