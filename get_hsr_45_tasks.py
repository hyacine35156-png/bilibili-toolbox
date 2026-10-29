import requests
import json

# 崩坏星穹铁道4.5任务的task_id列表
task_ids = [
    "6ERAcwloghvsal00",
    "6ERAcwloghvudj00",
    "18ERA1wloghvbtg00",
    "18ERA1wloghvv0w00",
    "18ERA1wloghvbye00",
    "18ERA1wloghvbr900",
    "6ERAcwloghvymq00",
    "6ERAcwloghva5j00",
    "6ERAcwloghvy4d00",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
}

results = []

for task_id in task_ids:
    url = f"https://api.bilibili.com/x/activity_components/mission/info?task_id={task_id}&web_location=888.126558"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            task_data = data.get("data", {})
            task_name = task_data.get("task_name", "未知")
            act_name = task_data.get("act_name", "未知")
            reward_info = task_data.get("reward_info", {})
            award_name = reward_info.get("award_name", "未知")
            results.append({
                "task_id": task_id,
                "task_name": task_name,
                "act_name": act_name,
                "award_name": award_name,
            })
            print(f"✓ {task_id}: {task_name} => {award_name}")
        else:
            print(f"✗ {task_id}: API返回错误 - {data.get('message', '未知')}")
    except Exception as e:
        print(f"✗ {task_id}: 请求异常 - {e}")

print("\n" + "="*80)
print("获取到的任务列表：")
print("="*80)
for r in results:
    print(f"task_id: {r['task_id']}")
    print(f"  活动: {r['act_name']}")
    print(f"  任务: {r['task_name']}")
    print(f"  奖励: {r['award_name']}")
    print()

# 保存到文件
with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\hsr_45_tasks.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"已保存到 hsr_45_tasks.json，共 {len(results)} 个任务")
