import json

# 读取两轮测试结果
with open('risk_test_results_large.json', 'r', encoding='utf-8') as f:
    data1 = json.load(f)
with open('risk_test_results_800_1000.json', 'r', encoding='utf-8') as f:
    data2 = json.load(f)

accounts = ['t0级长夜月lover', '银河最强流萤', 'G_TURNER', '做法长夜月不是跑条c', '灵砂是无敌的', '苏霍伊']
freqs = ['500', '550', '600', '650', '700', '750', '800', '850', '900', '950', '1000']

def get_risk_rate(data, acc, freq):
    if acc in data and freq in data[acc]:
        s = data[acc][freq]
        risk = s['risk_-702'] + s['risk_-705'] + s['risk_-509'] + s['risk_other']
        return risk / s['total'] * 100
    return None

print("=" * 120)
print("B站抢码风控间隔大样本测试完整汇总（每档100次，6账号并发）")
print("=" * 120)

# 完整数据表
print("\n【各账号各频率风控率（%）】")
header = f"{'频率':<8}"
for acc in accounts:
    short = acc[:6]
    header += f"{short:<8}"
header += f"{'6账号平均':<10}"
print(header)
print("-" * 120)

for freq in freqs:
    row = f"{freq}ms{'':<4}"
    rates = []
    for acc in accounts:
        r1 = get_risk_rate(data1, acc, freq)
        r2 = get_risk_rate(data2, acc, freq)
        r = r1 if r1 is not None else r2
        if r is not None:
            row += f"{r:<8.1f}"
            rates.append(r)
        else:
            row += f"{'N/A':<8}"
    avg = sum(rates) / len(rates) if rates else 0
    row += f"{avg:<10.1f}"
    print(row)

# 有效账号平均（排除第一轮有bug的3个账号在550-750ms的数据）
print("\n" + "=" * 120)
print("【有效数据汇总】")
print("第一轮500-800ms：银河最强流萤、G_TURNER、苏霍伊（3账号数据一致）")
print("第二轮850-1000ms：全部6账号数据一致")
print("=" * 120)

valid_accounts_1 = ['银河最强流萤', 'G_TURNER', '苏霍伊']
print(f"\n{'频率':<10} {'有效风控率':<12} {'较上档变化':<12} {'15秒窗口有效请求期望':<20}")
print("-" * 60)

prev = None
for freq in freqs:
    rates = []
    if int(freq) <= 800:
        for acc in valid_accounts_1:
            r = get_risk_rate(data1, acc, freq)
            if r is not None:
                rates.append(r)
    else:
        for acc in accounts:
            r = get_risk_rate(data2, acc, freq)
            if r is not None:
                rates.append(r)
    avg = sum(rates) / len(rates) if rates else 0
    
    # 15秒窗口期有效请求期望
    window_ms = 15000
    requests = window_ms / int(freq)
    effective = requests * (1 - avg / 100)
    
    change = ""
    if prev is not None:
        diff = avg - prev
        change = f"{'↓' if diff < 0 else '↑'} {abs(diff):.1f}%"
    
    print(f"{freq}ms{'':<6} {avg:<11.1f}% {change:<12} {effective:<20.1f}")
    prev = avg

# 关键结论
print("\n" + "=" * 120)
print("【关键结论】")
print("=" * 120)
print("1. 完美线性关系：500ms→1000ms，每增加50ms，风控率降低约5%")
print("2. 1000ms时几乎零风控（0.3%），500ms时近半请求被风控（49%）")
print("3. 15秒窗口期有效请求期望恒为约15次——B站风控本质是'每秒允许1次有效请求'")
print("4. 高间隔（900-1000ms）更优：风控累积少、请求稳定、避免IP级封禁")
print("5. 第一轮550-750ms时3个账号显示0%是脚本bug（错误码解析失败），第二轮已修复")
print("=" * 120)
