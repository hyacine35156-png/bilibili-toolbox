# -*- coding: utf-8 -*-
"""账户管理：增删改查、cookie 组装。"""

from config import ACCOUNTS_FILE
from storage import atomic_write_json, safe_load_json
from bili_api import verify_login


class AccountManager:
    def __init__(self):
        self.accounts = []
        self.load()

    def load(self):
        self.accounts = safe_load_json(ACCOUNTS_FILE, [])

    def save(self):
        atomic_write_json(ACCOUNTS_FILE, self.accounts)

    def add_account(self, name, sessdata, bili_jct, dede_userid=""):
        MAX_ACCOUNTS = 8
        if len(self.accounts) >= MAX_ACCOUNTS:
            return False, f"最多只能添加 {MAX_ACCOUNTS} 个账户，当前已有 {len(self.accounts)} 个"
        for acc in self.accounts:
            if acc["name"] == name:
                return False, f"账户名「{name}」已存在"
        cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
        if dede_userid:
            cookie_str += f"; DedeUserID={dede_userid}"
        ok, msg = verify_login(cookie_str)
        if not ok:
            return False, f"登录验证失败: {msg}"
        account = {
            "name": name,
            "SESSDATA": sessdata,
            "bili_jct": bili_jct,
            "DedeUserID": dede_userid,
            "username": msg,
        }
        self.accounts.append(account)
        self.save()
        return True, f"账户「{name}」添加成功（登录用户: {msg}）\n已保存到: {ACCOUNTS_FILE}"

    def update_account(self, old_name, name, sessdata, bili_jct, dede_userid=""):
        """更新账户信息（先验证cookie有效性，失效则禁止修改）"""
        # 先验证新cookie是否有效
        cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
        if dede_userid:
            cookie_str += f"; DedeUserID={dede_userid}"
        ok, msg = verify_login(cookie_str)
        if not ok:
            return False, f"登录验证失败，无法修改账户信息: {msg}"
        # 检查新名称是否与其他账户冲突
        for acc in self.accounts:
            if acc["name"] == name and acc["name"] != old_name:
                return False, f"账户名「{name}」已存在"
        # 更新账户
        for acc in self.accounts:
            if acc["name"] == old_name:
                acc["name"] = name
                acc["SESSDATA"] = sessdata
                acc["bili_jct"] = bili_jct
                acc["DedeUserID"] = dede_userid
                acc["username"] = msg
                break
        self.save()
        return True, f"账户「{name}」更新成功（当前用户: {msg}）"

    def delete_account(self, name):
        self.accounts = [a for a in self.accounts if a["name"] != name]
        self.save()

    def get_account(self, name):
        for acc in self.accounts:
            if acc["name"] == name:
                return acc
        return None

    def get_cookie_string(self, name):
        acc = self.get_account(name)
        if not acc:
            return ""
        parts = [f"SESSDATA={acc['SESSDATA']}", f"bili_jct={acc['bili_jct']}"]
        if acc.get("DedeUserID"):
            parts.append(f"DedeUserID={acc['DedeUserID']}")
        return "; ".join(parts)
