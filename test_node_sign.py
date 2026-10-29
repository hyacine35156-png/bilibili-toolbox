import subprocess, json, os, sys

os.chdir(r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot')

data = {
    "id": "[3,874,1,1791983148]",
    "device": '["AUTOtest1234567890","test-uuid"]',
    "ets": 1788429631,
    "benchmark": "seacasdgyijfhofiuxoannn",
    "time": 60,
    "ts": 1788429642412
}
secret_rule = [2, 5, 1, 4]

result = subprocess.run(
    ['node', 'calc_sign.js', json.dumps(data), json.dumps(secret_rule)],
    capture_output=True, text=True, encoding='utf-8'
)
print('stdout:', result.stdout.strip())
print('stderr:', result.stderr.strip())
print('returncode:', result.returncode)
