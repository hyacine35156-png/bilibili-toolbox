import json
with open('risk_test_results_large.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

accounts = [k for k in data.keys() if not k.startswith('_')]
freqs = ['500', '550', '600', '650', '700', '750', '800']

# 先看一个样本的键
print("样本键:", list(data[accounts[0]]['500'].keys()))
print()

print("=" * 100)
print("风控间隔大样本测试完整结果（每档100次，6账号并发）")
print("=" * 100)

valid_accounts = ['银河最强流萤', 'G_TURNER', '苏霍伊']

for freq in freqs:
    print(f"\n--- {freq}ms ---")
    print(f"{'账号':<20} {'通过':<6} {'风控':<6} {'风控率':<8} {'其他':<6}")
    for acc in accounts:
        if freq in data[acc]:
            s = data[acc][freq]
            risk = s['risk_-702'] + s['risk_-705'] + s['risk_-509'] + s['risk_other']
            risk_rate = risk / 100 * 100
            print(f"{acc:<18} {s['success']:<6} {risk:<6} {risk_rate:<7.1f}% {s['other_error']:<6}")

print("\n" + "=" * 100)
print("【有效账号平均（银河最强流萤、G_TURNER、苏霍伊）】")
print(f"{'频率':<10} {'平均风控率':<12} {'变化':<10}")
print("-" * 40)
prev = None
for freq in freqs:
    risks = []
    for acc in valid_accounts:
        if freq in data[acc]:
            s = data[acc][freq]
            risk = s['risk_-702'] + s['risk_-705'] + s['risk_-509'] + s['risk_other']
            risks.append(risk)
    avg = sum(risks) / len(risks) if risks else 0
    change = ""
    if prev is not None:
        diff = avg - prev
        change = f"{'↓' if diff < 0 else '↑'} {abs(diff):.1f}%"
    print(f"{freq}ms{'':<6} {avg:<11.1f}% {change}")
    prev = avg
