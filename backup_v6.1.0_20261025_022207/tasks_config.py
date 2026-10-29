# -*- coding: utf-8 -*-
"""游戏活动任务表与 act_id 缓存。"""

import json

from config import ACT_ID_CACHE_FILE
from storage import atomic_write_json

# 活动任务列表（按版本+期数+类型分类）
ALL_TASKS = [
    # ===== 鸣潮3.7 =====
    # 上半（第一期）- 投稿任务
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "6ERAcwloghvp8b00", "award": "60星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "6ERAcwloghvpff00", "award": "120星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "6ERAcwloghvpvq00", "award": "180星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "6ERAcwloghvpb400", "award": "300星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "6ERAcwloghvoao00", "award": "500星声"},
    # 上半 - 直播任务
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "开播时长60min", "task_id": "6ERAcwloghvod500", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "开播时长120min", "task_id": "6ERAcwloghvp1h00", "award": "中级能源核心*2"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "直播间弹幕20条", "task_id": "6ERAcwloghvpo100", "award": "贝币*10000"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "观看人数≥5人", "task_id": "6ERAcwloghvoxr00", "award": "中级复苏吸雾*2"},
    # 上半 - 直播里程碑
    {"version": "鸣潮3.7", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务3天", "task_id": "18ERA1wloghvcsm00", "award": "星声*180"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务5天", "task_id": "18ERA1wloghv1nf00", "award": "星声*300"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务10天", "task_id": "18ERA1wloghvcvs00", "award": "唤声涡纹*3"},
    # 下半（第二期）- 投稿任务
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "6ERAcwloghvpah00", "award": "60星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "6ERAcwloghvoll00", "award": "120星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "6ERAcwloghvpg700", "award": "180星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "6ERAcwloghvpic00", "award": "300星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "6ERAcwloghvazd00", "award": "500星声"},
    # 下半 - 直播任务
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "开播时长60min", "task_id": "6ERAcwloghvoxc00", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "开播时长120min", "task_id": "6ERAcwloghvawq00", "award": "中级能源核心*2"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "直播间弹幕20条", "task_id": "6ERAcwloghvppd00", "award": "贝币*10000"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "观看人数≥5人", "task_id": "6ERAcwloghvazv00", "award": "中级复苏吸雾*2"},
    # 下半 - 直播里程碑
    {"version": "鸣潮3.7", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务3天", "task_id": "18ERA1wloghvcl800", "award": "星声*180"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务5天", "task_id": "18ERA1wloghv17v00", "award": "星声*300"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务10天", "task_id": "18ERA1wloghvcpj00", "award": "唤声涡纹*3"},
    # 全版本（新人开播奖励等）
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计1天开播", "task_id": "18ERA1wloghvcrq00", "award": "星声*50"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计2天开播", "task_id": "18ERA1wloghvcl700", "award": "星声*80"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计3天开播", "task_id": "18ERA1wloghvcje00", "award": "星声*120"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计7天开播", "task_id": "18ERA1wloghvcue00", "award": "星声*180"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计14天开播", "task_id": "18ERA1wloghvvc700", "award": "唤声涡纹*2"},

    # ===== 原神7.1 =====
    # 直播任务
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日开播满60分钟", "task_id": "6ERAcwloghvatw00", "award": "精锻用魔矿*5"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "分区开播满60分钟且直播间发送弹幕2人", "task_id": "6ERAcwloghvofk00", "award": "原石*50"},
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日直播间累计收到≥10电池价值的礼物", "task_id": "6ERAcwloghvpil00", "award": "大英雄的经验*2"},
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日直播间弹幕数满6条", "task_id": "6ERAcwloghvofj00", "award": "冒险家的经验*6"},
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日直播间至少有1名用户观看满10分钟", "task_id": "6ERAcwloghvp7k00", "award": "摩拉*11111"},
    # 直播里程碑任务
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积1天开播", "task_id": "18ERA1wloghvcxd00", "award": "原石*200"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积5天开播", "task_id": "18ERA1wloghvvzn00", "award": "原石*600"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积10天开播", "task_id": "18ERA1wloghvcdt00", "award": "原石*1000"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积20天开播", "task_id": "18ERA1wloghv1b900", "award": "原石*1000"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积30天开播", "task_id": "18ERA1wloghvcty00", "award": "原石*1000"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积40天开播", "task_id": "18ERA1wloghvckw00", "award": "原石*1000"},
    # 看播里程碑任务
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积1天看播", "task_id": "18ERA1wloghvcxf00", "award": "原石*50"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积5天看播", "task_id": "18ERA1wloghvcv400", "award": "原石*50"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积10天看播", "task_id": "18ERA1wloghvvcp00", "award": "原石*100"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积20天看播", "task_id": "18ERA1wloghv12p00", "award": "原石*100"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积30天看播", "task_id": "18ERA1wloghv1ng00", "award": "原石*200"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积40天看播", "task_id": "18ERA1wloghv1me00", "award": "原石*200"},


    # ===== 崩坏星穹铁道4.6（投稿任务）=====
    # 上半 - 投稿任务
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAcwloghvp2600", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计3天投稿，且收到三连2", "task_id": "6ERAcwloghvauo00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计5天投稿，总播≥1000且收到三连10", "task_id": "6ERAcwloghvp6y00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计7天投稿，总播≥2000且收到三连30", "task_id": "6ERAcwloghvp2500", "award": "星琼*500"},
    # 下半 - 投稿任务
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAcwloghvpt100", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计3天投稿，且收到三连2", "task_id": "6ERAcwloghvp4g00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计5天投稿，总播≥1000且收到三连10", "task_id": "6ERAcwloghvpii00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计7天投稿，总播≥2000且收到三连30", "task_id": "6ERAcwloghvayj00", "award": "星琼*500"},
    # 特殊投稿任务
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量3万", "task_id": "6ERAcwloghvozs00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量5万", "task_id": "6ERAcwloghvolz00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量10万", "task_id": "6ERAcwloghvpga00", "award": "星琼*1000"},
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量30万", "task_id": "6ERAcwloghvpnt00", "award": "星轨通票*10"},
    # 新人限定 - 直播任务
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积1天开播", "task_id": "18ERA1wloghvcjw00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积3天开播", "task_id": "18ERA1wloghv18w00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积5天开播", "task_id": "18ERA1wloghvctt00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积10天开播", "task_id": "18ERA1wloghv1cn00", "award": "星琼*200"},


    # 每日任务
    {"version": "崩坏星穹铁道4.6", "period": "每日", "type": "直播", "name": "【每日】开播60分钟+观看15分钟", "task_id": "6ERAcwloghvalh00", "award": "冒险记录*6+遗失碎金*5"},
    {"version": "崩坏星穹铁道4.6", "period": "每日", "type": "直播", "name": "【每日】礼物≥10电池+弹幕≥4人", "task_id": "6ERAcwloghvoaq00", "award": "漫游指南*2+信用点*11111"},
    # 限时直播任务
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【限时】开播（9.28-10.4）", "task_id": "6ERAcwloghvpjz00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【限时】开播（10.21-10.27）", "task_id": "6ERAcwloghvp4k00", "award": "星琼*50"},
    # 直播里程碑 - 上半
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积3天开播", "task_id": "18ERA1wloghvcg100", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积5天开播", "task_id": "18ERA1wloghvczg00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积10天开播", "task_id": "18ERA1wloghvcer00", "award": "星琼*800"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积15天开播", "task_id": "18ERA1wloghv16700", "award": "星琼*1000"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "直播间新增1名舰长", "task_id": "6ERAcwloghvasy00", "award": "星轨通票*3"},
    # 直播里程碑 - 下半
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积3天开播", "task_id": "18ERA1wloghv1ch00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积5天开播", "task_id": "18ERA1wloghv1nd00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积10天开播", "task_id": "18ERA1wloghvcsq00", "award": "星琼*800"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积15天开播", "task_id": "18ERA1wloghvcva00", "award": "星琼*1000"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "直播间新增1名舰长", "task_id": "6ERAcwloghvp7x00", "award": "星轨通票*3"},

    # ===== 绝区零3.3 =====
    # 全版本 - 观看互动任务
    {"version": "绝区零3.3", "period": "全版本", "type": "观看互动", "name": "观看挽昼实机PV一分钟，并一键三连", "task_id": "6ERAcwloghvop400", "award": "菲林*30"},
    {"version": "绝区零3.3", "period": "全版本", "type": "观看互动", "name": "每日观看活动视频时长≥10min", "task_id": "6ERAcwloghvpz000", "award": "丁尼*1000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "观看互动", "name": "每日给活动视频投币≥1", "task_id": "6ERAcwloghvp6b00", "award": "资深调查员记录*2"},
    # 全版本 - 投稿任务
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "投稿≥4，单稿点赞≥10且累计播放≥400", "task_id": "6ERAcwloghvaeu00", "award": "菲林*80"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "投稿≥5，单稿点赞≥10且累计播放≥500", "task_id": "6ERAcwloghvpar00", "award": "原装母带*1"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "累计播放≥15万且累计点赞≥1000", "task_id": "6ERAcwloghvasq00", "award": "菲林*1000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "累计播放≥70万且累计点赞≥10000", "task_id": "6ERAcwloghvoo900", "award": "菲林*1600"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "单稿播放≥100且单稿点赞≥10", "task_id": "6ERAcwloghvpf500", "award": "菲林*30"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "单稿播放≥10000且单稿点赞≥500", "task_id": "6ERAcwloghvosw00", "award": "菲林*300"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "单稿播放≥10000且单稿点赞≥500的有效稿件≥3个", "task_id": "6ERAcwloghvp1000", "award": "菲林*800"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "累计投稿3天，单稿点赞≥10且累计视频播放≥500", "task_id": "6ERAcwloghvp5r00", "award": "菲林*150"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "累计投稿10天，单稿点赞≥10且累计视频播放≥1000", "task_id": "6ERAcwloghvp1900", "award": "菲林*300"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "累计投稿20天，累计点赞≥300且累计视频播放≥3000", "task_id": "6ERAcwloghvpl100", "award": "菲林*500"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "累计投稿30天，累计点赞≥600且累计视频播放≥6000", "task_id": "6ERAcwloghvoh200", "award": "菲林*1000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "投稿", "name": "累计投稿35天，累计点赞≥1000且累计视频播放≥50000", "task_id": "6ERAcwloghvaa200", "award": "菲林*1000"},
    # 全版本 - 每日直播任务
    {"version": "绝区零3.3", "period": "全版本", "type": "直播", "name": "当日开播60分钟", "task_id": "6ERAcwloghvpv900", "award": "丁尼*1000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播", "name": "当日直播间收到电池≥2", "task_id": "6ERAcwloghvpr400", "award": "音擎能源模块*2"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播", "name": "当日直播间弹幕≥10条", "task_id": "6ERAcwloghvpsl00", "award": "资深调查员记录*2"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播", "name": "当日至少1名用户观看时长≥10分钟", "task_id": "6ERAcwloghvpz300", "award": "丁尼*5000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播", "name": "直播收获1名舰长", "task_id": "6ERAcwloghvaix00", "award": "菲林*480"},
    # 全版本 - 直播里程碑任务
    {"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑", "name": "直播里程碑任务（任务主体）", "task_id": "6ERAcwloghvpd800", "award": "菲林*360~1000（6档累计）"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑", "name": "累计3天完成开播及互动任务", "task_id": "18ERA1wloghvcrj00", "award": "菲林*360"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑", "name": "累计5天完成开播及互动任务", "task_id": "18ERA1wloghvccb00", "award": "菲林*660"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑", "name": "累计10天完成开播及互动任务", "task_id": "18ERA1wloghvcvp00", "award": "菲林*1000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑", "name": "累计20天完成开播及互动任务", "task_id": "18ERA1wloghvcj100", "award": "菲林*1000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑", "name": "累计30天完成开播及互动任务", "task_id": "18ERA1wloghvcfb00", "award": "菲林*1000"},
    {"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑", "name": "累计35天完成开播及互动任务", "task_id": "18ERA1wloghvc3e00", "award": "菲林*1000"},
]

# 兼容旧代码
MINGCHAO_TASKS = [t for t in ALL_TASKS if t["version"] == "鸣潮3.7"]

# 版本默认act_id（同一版本的所有任务共享同一个act_id）
VERSION_DEFAULT_ACT_ID = {
    "鸣潮3.7": "1ERAzwloghv32n00",
    "原神7.1": "1ERA3wloghv6q200",
    "崩坏星穹铁道4.6": "1ERAzwloghv3q100",
    "绝区零3.3": "1ERAzwloghv2ai00",
}

TASK_ACT_ID_CACHE = {}



def load_act_id_cache():
    """从文件加载act_id缓存"""
    global TASK_ACT_ID_CACHE
    try:
        if ACT_ID_CACHE_FILE.exists():
            with open(ACT_ID_CACHE_FILE, "r", encoding="utf-8") as f:
                saved_cache = json.load(f)
                if isinstance(saved_cache, dict):
                    TASK_ACT_ID_CACHE.update(saved_cache)
                    print(f"已加载 {len(saved_cache)} 条act_id缓存")
    except Exception as e:
        print(f"加载act_id缓存失败: {e}")

def save_act_id_cache():
    """保存act_id缓存到文件"""
    try:
        atomic_write_json(ACT_ID_CACHE_FILE, TASK_ACT_ID_CACHE)
    except Exception as e:
        print(f"保存act_id缓存失败: {e}")


# 启动时加载 act_id 缓存（原 main_gui_pro.py:571）
load_act_id_cache()
