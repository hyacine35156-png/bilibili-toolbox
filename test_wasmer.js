// 用@wasmer/sdk运行wasm计算签名
const { init, Wasmer } = require('@wasmer/sdk');
const fs = require('fs');
const path = require('path');

async function main() {
    await init();
    
    const wasmPath = path.join(__dirname, 'spyder.wasm');
    const wasmBytes = fs.readFileSync(wasmPath);
    
    // 模拟DOM对象
    const window = { location: { href: 'https://live.bilibili.com/3', origin: 'https://live.bilibili.com', protocol: 'https:', host: 'live.bilibili.com', hostname: 'live.bilibili.com', pathname: '/3' } };
    const document = { body: { childNodes: { length: 1 } } };
    
    // 简单的stdweb实现
    let tmp = null;
    const idToRefMap = {};
    let lastRefid = 1;
    
    function acquireRustReference(ref) {
        if (ref === null || ref === undefined) return 0;
        let refid = ref.__refid;
        if (refid === undefined) { refid = lastRefid++; ref.__refid = refid; }
        idToRefMap[refid] = ref;
        return refid;
    }
    
    const imports = {
        env: {
            __cargo_web_snippet_0f503de1d61309643e0e13a7871406891e3691c9: () => {},
            __cargo_web_snippet_6fcce0aae651e2d748e085ff1f800f87625ff8c8: () => {},
            __cargo_web_snippet_0d39c013e2144171d64e2fac849140a7e54c939a: () => {},
            __cargo_web_snippet_10f5aa3985855124ab83b21d4e9f7297eb496508: () => 0,
            __cargo_web_snippet_2b0b92aee0d0de6a955f8e5540d7923636d951ae: () => {},
            __cargo_web_snippet_461d4581925d5b0bf583a3b445ed676af8701ca6: () => {},
            __cargo_web_snippet_4c895ac2b754e5559c1415b6546d672c58e29da6: () => {},
            __cargo_web_snippet_a466a2ab96cd77e1a77dcdb39f4f031701c195fc: () => {},
            __cargo_web_snippet_cdf2859151791ce4cad80688b200564fb08a8613: () => {},
            __cargo_web_snippet_e8ef87c41ded1c10f8de3c70dea31a053e19747c: () => {},
            __cargo_web_snippet_ab05f53189dacccf2d365ad26daa407d4f7abea9: () => {},
            __cargo_web_snippet_b06dde4acf09433b5190a4b001259fe5d4abcbc2: () => {},
            __cargo_web_snippet_614a3dd2adb7e9eac4a0ec6e59d37f87e0521c3b: () => {},
            __cargo_web_snippet_7ba9f102925446c90affc984f921f414615e07dd: () => {},
            __cargo_web_snippet_62ef43cf95b12a9b5cdec1639439c972d6373280: () => {},
            __cargo_web_snippet_b33a39de4ca954888e26fe9caa277138e808eeba: () => {},
            __cargo_web_snippet_80d6d56760c65e49b7be8b6b01c1ea861b046bf0: () => {},
            __cargo_web_snippet_8c32019649bb581b1b742eeedfc410e2bedd56a6: () => {},
            __cargo_web_snippet_ff5103e6cc179d13b4c7a785bdce2708fd559fc0: () => {},
            __cargo_web_snippet_897ff2d0160606ea98961935acb125d1ddbf4688: () => { throw new Error('not implemented'); },
            __cargo_web_snippet_e9638d6405ab65f78daf4a5af9c9de14ecf1e2ec: () => { throw new Error('not implemented'); },
            __web_on_grow: () => {},
        },
    };
    
    try {
        const module = await Wasmer.fromBinary(wasmBytes);
        const instance = await module.instantiate(imports);
        console.log('实例化成功');
        console.log('导出:', Object.keys(instance.exports));
        
        // 测试malloc
        const p = instance.exports.__web_malloc(16);
        console.log('malloc(16)=', p);
        instance.exports.__web_free(p);
        console.log('free成功');
        
        // 测试spyder
        const p1 = instance.exports.__web_malloc(16);
        const p2 = instance.exports.__web_malloc(16);
        console.log('调用spyder...');
        instance.exports.spyder(p1, p2);
        console.log('spyder调用成功');
    } catch (e) {
        console.error('错误:', e.message);
        console.error(e.stack);
    }
}

main();
