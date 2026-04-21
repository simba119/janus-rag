import requests
import json

API_KEY = "sk-e8cd2d632e1047b18ea046ae744bb009"

# 方式1：用 json= 参数（requests 自动序列化+设 Content-Type）
print("=== 方式1: json= 参数 ===")
try:
    resp = requests.post(
        "https://api.bocha.cn/v1/web-search",
        json={"query": "测试", "count": 1},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(resp.text[:500])
except Exception as e:
    print(f"Error: {e}")

# 方式2：用 data= + 手动 json.dumps
print("\n=== 方式2: data= + json.dumps ===")
try:
    resp = requests.post(
        "https://api.bocha.cn/v1/web-search",
        data=json.dumps({"query": "测试", "count": 1}),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(resp.text[:500])
except Exception as e:
    print(f"Error: {e}")
