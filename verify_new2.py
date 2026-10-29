# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import requests
from main_gui_pro import HEADERS

bili_jct = "cf7b4db1923af3a8b618ce1270a6c549"
sessdata = "9ed49f2e%2C1807101793%2Cf59d0%2Aa1CjCnIp35CSS-Rb_30QamRdW6RRjKETOzyTkjbVX1woTQD80JtvY5wAIYef0eL8efu-oSVlNnSDBsZ204STJiZ3JzR29maTBLSEtCVDlKcEprZVdFcDktTEtZYXE0cmZRYjVaTVIzbU1vM0dCbV8zeS10REpqREo3R1JZeHZqWlByUGFLNEVOa3JRIIEC"

cookies = {
    "SESSDATA": sessdata,
    "bili_jct": bili_jct,
}

resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=HEADERS, cookies=cookies, timeout=10)
data = resp.json()
if data.get("code") == 0:
    print(f"用户名: {data['data']['uname']}")
    print(f"UID: {data['data']['mid']}")
else:
    print(f"失败: {data.get('message')}")
