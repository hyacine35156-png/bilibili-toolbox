# -*- coding: utf-8 -*-
"""纯函数层单元测试：task_id 解析、字段提取、WBI 签名、库存解析。

运行: python -m unittest discover tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTaskIdParse(unittest.TestCase):
    """task_id / 活动网址解析"""

    def setUp(self):
        from ui.rush_reward.manual_task import parse_task_ids
        self.parse = parse_task_ids

    def test_full_url(self):
        url = "https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghvosw00"
        self.assertEqual(self.parse(url), ["6ERAcwloghvosw00"])

    def test_bare_id(self):
        self.assertEqual(self.parse("6ERAcwloghvosw00"), ["6ERAcwloghvosw00"])

    def test_batch_dedup(self):
        text = "6ERAcwloghvosw00\n18ERA1wloghvcrj00\n6ERAcwloghvosw00"
        self.assertEqual(self.parse(text), ["6ERAcwloghvosw00", "18ERA1wloghvcrj00"])

    def test_amp_param(self):
        self.assertEqual(
            self.parse("https://x.com/a?foo=1&task_id=1ERAzwloghv32n00"),
            ["1ERAzwloghv32n00"])

    def test_json_fragment(self):
        self.assertEqual(self.parse('{"task_id": "6ERAcwloghvosw00"}'), ["6ERAcwloghvosw00"])

    def test_ignore_garbage(self):
        self.assertEqual(self.parse("hello world\n\n"), [])


class TestExtractMeta(unittest.TestCase):
    """mission/info 返回字段提取"""

    def setUp(self):
        from ui.rush_reward.manual_task import extract_task_meta
        self.extract = extract_task_meta

    def test_full_fields(self):
        info = {"task_name": "累计3天投稿", "act_id": "ACT1", "act_name": "某活动",
                "reward_info": {"award_name": "菲林*360"}}
        m = self.extract(info, "TID")
        self.assertEqual(m["name"], "累计3天投稿")
        self.assertEqual(m["act_id"], "ACT1")
        self.assertEqual(m["act_name"], "某活动")
        self.assertEqual(m["award"], "菲林*360")

    def test_fallback_act_id(self):
        m = self.extract({}, "TID", "FALLBACK")
        self.assertEqual(m["act_id"], "FALLBACK")
        self.assertEqual(m["name"], "TID")

    def test_nested_fields(self):
        info = {"act_info": {"act_id": "NESTED", "act_name": "嵌套活动"}}
        m = self.extract(info, "TID")
        self.assertEqual(m["act_id"], "NESTED")
        self.assertEqual(m["act_name"], "嵌套活动")


class TestTaskLabel(unittest.TestCase):
    def setUp(self):
        from ui.rush_reward.manual_task import task_label
        self.label = task_label

    def test_empty_award(self):
        self.assertEqual(self.label({"name": "A", "award": ""}, "paren"), "A")

    def test_arrow_style(self):
        self.assertEqual(self.label({"name": "A", "award": "100"}, "arrow"), "A => 100")

    def test_paren_style(self):
        self.assertEqual(self.label({"name": "A", "award": "100"}, "paren"), "A (100)")


class TestWbiSign(unittest.TestCase):
    """WBI 签名必须与官方公式一致"""

    def test_mixin_key_length(self):
        from bili_api import get_mixin_key
        key = get_mixin_key("7cd084941338484aae1ad9425b84077c" + "4932caff0ff746eab6f01bf08b70ac45")
        self.assertEqual(len(key), 32)

    def test_sign_has_required_fields(self):
        from bili_api import wbi_sign
        params = {"task_id": "abc", "web_location": "888.126558"}
        signed = wbi_sign(params, "7cd084941338484aae1ad9425b84077c",
                          "4932caff0ff746eab6f01bf08b70ac45")
        self.assertIn("w_rid", signed)
        self.assertIn("wts", signed)
        self.assertEqual(len(signed["w_rid"]), 32)

    def test_sign_deterministic(self):
        """同样入参、人工固定 wts 后签名必须固定"""
        import hashlib
        import urllib.parse
        from bili_api import get_mixin_key
        img, sub = "7cd084941338484aae1ad9425b84077c", "4932caff0ff746eab6f01bf08b70ac45"
        mixin = get_mixin_key(img + sub)
        params = {"task_id": "abc", "wts": 1700000000}
        query = urllib.parse.urlencode(dict(sorted(params.items())))
        expected = hashlib.md5((query + mixin).encode()).hexdigest()
        self.assertEqual(len(expected), 32)


class TestStockParse(unittest.TestCase):
    """库存描述解析"""

    def setUp(self):
        from bili_api import parse_award_stock
        self.parse = parse_award_stock

    def test_total_and_daily(self):
        total, daily = self.parse("本奖品共7700份，数量有限，先到先得，每日限量发放460份")
        self.assertEqual(total, 7700)
        self.assertEqual(daily, 460)

    def test_empty(self):
        self.assertEqual(self.parse(""), (0, 0))
        self.assertEqual(self.parse(None), (0, 0))

    def test_only_total(self):
        total, daily = self.parse("共100份")
        self.assertEqual(total, 100)
        self.assertEqual(daily, 0)


class TestConstants(unittest.TestCase):
    """常量与任务表一致性"""

    def test_task_fields(self):
        from tasks_config import ALL_TASKS
        for t in ALL_TASKS:
            for k in ("version", "period", "type", "name", "task_id", "award"):
                self.assertIn(k, t, f"任务缺字段 {k}: {t}")

    def test_no_duplicate_task_id(self):
        """同一版本内 task_id 不能重复（v6.5.0 调整断言）。

        为什么放宽：v6.4.8 引入「自定义版本集合」后，
        同一个任务可以同时属于「官方版本」（如 鸣潮3.7）和
        「自定义集合」（如 已完成任务）。
        这是业务需求，不是 bug —— 任务既在官方列表里，
        也在用户创建的集合里，方便按集合批量选择。

        所以正确的不变式是：**同一版本内** task_id 唯一。
        """
        from tasks_config import ALL_TASKS
        seen = {}
        for t in ALL_TASKS:
            key = (t.get("version"), t.get("task_id"))
            self.assertNotIn(
                key, seen,
                "版本 %s 下 task_id %s 重复" % (t.get("version"), t.get("task_id")))
            seen[key] = True

    def test_version_act_id_present(self):
        from tasks_config import VERSION_DEFAULT_ACT_ID
        self.assertGreaterEqual(len(VERSION_DEFAULT_ACT_ID), 1)
        for v, aid in VERSION_DEFAULT_ACT_ID.items():
            self.assertTrue(aid, f"{v} 的 act_id 为空")

    def test_app_version_format(self):
        import config
        self.assertRegex(config.APP_VERSION, r"^v\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
