# -*- coding: utf-8 -*-
"""游戏活动任务表与 act_id 缓存。"""

import json
import time

from config import (ACT_ID_CACHE_FILE, MANUAL_TASKS_FILE, HIDDEN_TASKS_FILE,
                     TASKS_FILE, CUSTOM_VERSIONS_FILE, CUSTOM_VERSION_TASKS_FILE)
from storage import atomic_write_json, safe_load_json

# 活动任务列表（按版本+期数+类型分类）
ALL_TASKS = [
    # ===== 鸣潮3.8（30 个可用码：视频10 + 通用1 + 直播19）=====
    # 来源：官方激励计划页 9rAamKbtgtpKvFWv，activity_id 1ERAzwloghv5wv00
    # 说明：里程碑/累计型按档拆开（新人限定5档 + 累计每日任务6档），每档独立码；
    #       抽奖类任务（每日看视频/投稿/观看直播/开播/关注官号×3）已按要求剔除。
    # 校验：30 个码全部经 x/task/mission/info 实测 code=0，任务名与文档一致。
    # ========== 视频赛道·第一期 ==========
    {"version": "鸣潮3.8", "period": "上半", "type": "投稿", "name": "【第一期】累计1天投稿≥100播放", "task_id": "6ERAvwloghvy3t00", "award": "60星声"},
    {"version": "鸣潮3.8", "period": "上半", "type": "投稿", "name": "【第一期】累计2天投稿≥300播放≥3币", "task_id": "6ERAvwloghvt1l00", "award": "120星声"},
    {"version": "鸣潮3.8", "period": "上半", "type": "投稿", "name": "【第一期】累计3天投稿≥1000播放≥10币", "task_id": "6ERAvwloghvyns00", "award": "180星声"},
    {"version": "鸣潮3.8", "period": "上半", "type": "投稿", "name": "【第一期】累计7天投稿≥2000播放≥20币", "task_id": "6ERAvwloghvu5z00", "award": "300星声"},
    {"version": "鸣潮3.8", "period": "上半", "type": "投稿", "name": "【第一期】累计14天投稿≥3000播放≥40币", "task_id": "6ERAvwloghvutd00", "award": "500星声"},
    # ========== 视频赛道·第二期 ==========
    {"version": "鸣潮3.8", "period": "下半", "type": "投稿", "name": "【第二期】累计1天投稿≥100播放", "task_id": "6ERAvwloghvy9h00", "award": "60星声"},
    {"version": "鸣潮3.8", "period": "下半", "type": "投稿", "name": "【第二期】累计2天投稿≥300播放≥3币", "task_id": "6ERAvwloghvtbj00", "award": "120星声"},
    {"version": "鸣潮3.8", "period": "下半", "type": "投稿", "name": "【第二期】累计3天投稿≥1000播放≥10币", "task_id": "6ERAvwloghvy6h00", "award": "180星声"},
    {"version": "鸣潮3.8", "period": "下半", "type": "投稿", "name": "【第二期】累计7天投稿≥2000播放≥20币", "task_id": "6ERAvwloghvtbi00", "award": "300星声"},
    {"version": "鸣潮3.8", "period": "下半", "type": "投稿", "name": "【第二期】累计14天投稿≥3000播放≥40币", "task_id": "6ERAvwloghviqd00", "award": "500星声"},
    # ========== 通用 ==========
    {"version": "鸣潮3.8", "period": "全版本", "type": "投稿", "name": "关注官号", "task_id": "6ERAvwloghvu5l00", "award": "20星声"},
    # ========== 新人限定（5 档分档码）==========
    {"version": "鸣潮3.8", "period": "新人限定", "type": "新人开播", "name": "累计1天开播", "task_id": "18ERA1wloghvmbe00", "award": "50星声"},
    {"version": "鸣潮3.8", "period": "新人限定", "type": "新人开播", "name": "累计2天开播", "task_id": "18ERA1wloghv1gd00", "award": "80星声"},
    {"version": "鸣潮3.8", "period": "新人限定", "type": "新人开播", "name": "累计3天开播", "task_id": "18ERA1wloghvmb100", "award": "120星声"},
    {"version": "鸣潮3.8", "period": "新人限定", "type": "新人开播", "name": "累计7天开播", "task_id": "18ERA1wloghvmpn00", "award": "180星声"},
    {"version": "鸣潮3.8", "period": "新人限定", "type": "新人开播", "name": "累计14天开播", "task_id": "18ERA1wloghv1i700", "award": "唤声涡纹*2"},
    # ========== 每日任务·第一期 ==========
    {"version": "鸣潮3.8", "period": "上半", "type": "直播", "name": "【第一期】开播时长60min", "task_id": "6ERAvwloghvt6y00", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.8", "period": "上半", "type": "直播", "name": "【第一期】开播时长120min", "task_id": "6ERAvwloghvylq00", "award": "中级能源核心*2"},
    {"version": "鸣潮3.8", "period": "上半", "type": "直播", "name": "【第一期】直播间弹幕20条", "task_id": "6ERAvwloghvuu300", "award": "贝币*10000"},
    {"version": "鸣潮3.8", "period": "上半", "type": "直播", "name": "【第一期】观看人数≥5人", "task_id": "6ERAvwloghvy1300", "award": "中级复苏吸雾*2"},
    # ========== 每日任务·第二期 ==========
    {"version": "鸣潮3.8", "period": "下半", "type": "直播", "name": "【第二期】开播时长60min", "task_id": "6ERAvwloghvt4g00", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.8", "period": "下半", "type": "直播", "name": "【第二期】开播时长120min", "task_id": "6ERAvwloghvt6t00", "award": "中级能源核心*2"},
    {"version": "鸣潮3.8", "period": "下半", "type": "直播", "name": "【第二期】直播间弹幕20条", "task_id": "6ERAvwloghvyvz00", "award": "贝币*10000"},
    {"version": "鸣潮3.8", "period": "下半", "type": "直播", "name": "【第二期】观看人数≥5人", "task_id": "6ERAvwloghvylv00", "award": "中级复苏吸雾*2"},
    # ========== 累计每日任务·第一期（3 档分档码）==========
    {"version": "鸣潮3.8", "period": "上半", "type": "直播里程碑", "name": "【第一期】累计完成每日任务3天", "task_id": "18ERA1wloghvm1f00", "award": "180星声"},
    {"version": "鸣潮3.8", "period": "上半", "type": "直播里程碑", "name": "【第一期】累计完成每日任务5天", "task_id": "18ERA1wloghvmma00", "award": "300星声"},
    {"version": "鸣潮3.8", "period": "上半", "type": "直播里程碑", "name": "【第一期】累计完成每日任务10天", "task_id": "18ERA1wloghvmtd00", "award": "唤声涡纹*3"},
    # ========== 累计每日任务·第二期（3 档分档码）==========
    {"version": "鸣潮3.8", "period": "下半", "type": "直播里程碑", "name": "【第二期】累计完成每日任务3天", "task_id": "18ERA1wloghvmfw00", "award": "180星声"},
    {"version": "鸣潮3.8", "period": "下半", "type": "直播里程碑", "name": "【第二期】累计完成每日任务5天", "task_id": "18ERA1wloghvmhw00", "award": "300星声"},
    {"version": "鸣潮3.8", "period": "下半", "type": "直播里程碑", "name": "【第二期】累计完成每日任务10天", "task_id": "18ERA1wloghvmm900", "award": "唤声涡纹*3"},

    # ===== 原神7.2 =====
    # act_id: 1ERAzwloghv3vb00（原神7.2UP主激励计划）
    # 投稿任务（5 个）
    {"version": "原神7.2", "period": "全版本", "type": "投稿", "name": "投稿3播放3", "task_id": "6ERAvwloghvylw00", "award": "投稿1：摩拉*20000"},
    {"version": "原神7.2", "period": "全版本", "type": "投稿", "name": "投稿4播放400", "task_id": "6ERAvwloghvuu500", "award": "投稿2：原石*50"},
    {"version": "原神7.2", "period": "全版本", "type": "投稿", "name": "投稿5播放500", "task_id": "6ERAvwloghvycw00", "award": "投稿3：相遇之缘*1"},
    {"version": "原神7.2", "period": "全版本", "type": "投稿", "name": "累计播放15w", "task_id": "6ERAvwloghvyq200", "award": "投稿4：原石*1000"},
    {"version": "原神7.2", "period": "全版本", "type": "投稿", "name": "累计播放70w", "task_id": "6ERAvwloghvy1m00", "award": "投稿5：相遇之缘*10"},
    # 直播-限定任务（1 个）
    {"version": "原神7.2", "period": "全版本", "type": "直播", "name": "分区开播满60分钟且直播间发送弹幕2人", "task_id": "6ERAvwloghvuum00", "award": "原石*50"},
    # 直播-每日任务（4 个）
    {"version": "原神7.2", "period": "每日", "type": "直播", "name": "当日开播满60分钟", "task_id": "6ERAvwloghvy9q00", "award": "精锻用魔矿*5"},
    {"version": "原神7.2", "period": "每日", "type": "直播", "name": "当日直播间累计收到≥10电池价值的礼物", "task_id": "6ERAvwloghvuy800", "award": "大英雄的经验*2"},
    {"version": "原神7.2", "period": "每日", "type": "直播", "name": "当日直播间弹幕数满6条", "task_id": "6ERAvwloghvuis00", "award": "冒险家的经验*6"},
    {"version": "原神7.2", "period": "每日", "type": "直播", "name": "当日直播间至少有1名用户观看满10分钟", "task_id": "6ERAvwloghvuts00", "award": "摩拉*11111"},
    # 直播里程碑任务（1 主体 + 6 分档）
    {"version": "原神7.2", "period": "全版本", "type": "直播里程碑", "name": "直播里程碑（任务主体）", "task_id": "6ERAvwloghvy4600", "award": "6档累计：原石*200~原石*1000"},
    {"version": "原神7.2", "period": "全版本", "type": "直播里程碑", "name": "累计1天开播", "task_id": "18ERA1wloghv1sm00", "award": "原石*200"},
    {"version": "原神7.2", "period": "全版本", "type": "直播里程碑", "name": "累计5天开播", "task_id": "18ERA1wloghv1qf00", "award": "原石*600"},
    {"version": "原神7.2", "period": "全版本", "type": "直播里程碑", "name": "累计10天开播", "task_id": "18ERA1wloghv1za00", "award": "原石*1000"},
    {"version": "原神7.2", "period": "全版本", "type": "直播里程碑", "name": "累计20天开播", "task_id": "18ERA1wloghv1of00", "award": "原石*1000"},
    {"version": "原神7.2", "period": "全版本", "type": "直播里程碑", "name": "累计30天开播", "task_id": "18ERA1wloghv1z900", "award": "原石*1000"},
    {"version": "原神7.2", "period": "全版本", "type": "直播里程碑", "name": "累计40天开播", "task_id": "18ERA1wloghv1ke00", "award": "原石*1000"},
    # 看播里程碑任务（1 主体 + 6 分档）
    {"version": "原神7.2", "period": "全版本", "type": "看播里程碑", "name": "看播里程碑（任务主体）", "task_id": "6ERAvwloghvyzm00", "award": "6档累计：原石*50~原石*200"},
    {"version": "原神7.2", "period": "全版本", "type": "看播里程碑", "name": "累计1天看播", "task_id": "18ERA1wloghv1s100", "award": "原石*50"},
    {"version": "原神7.2", "period": "全版本", "type": "看播里程碑", "name": "累计5天看播", "task_id": "18ERA1wloghv1av00", "award": "原石*50"},
    {"version": "原神7.2", "period": "全版本", "type": "看播里程碑", "name": "累计10天看播", "task_id": "18ERA1wloghv1sa00", "award": "原石*100"},
    {"version": "原神7.2", "period": "全版本", "type": "看播里程碑", "name": "累计20天看播", "task_id": "18ERA1wloghv1og00", "award": "原石*100"},
    {"version": "原神7.2", "period": "全版本", "type": "看播里程碑", "name": "累计30天看播", "task_id": "18ERA1wloghv1pe00", "award": "原石*200"},
    {"version": "原神7.2", "period": "全版本", "type": "看播里程碑", "name": "累计40天看播", "task_id": "18ERA1wloghv1i900", "award": "原石*200"},


    # ===== 崩坏星穹铁道4.7（30 个可用码：12 视频 + 18 直播）=====
    # 来源：官方激励计划页 mruXBu0dRTHxDRgf，activity_id 1ERAxwloghvmpq00
    # 说明：里程碑类任务按档拆开，每档一个独立码（18ERA1wlog…）；
    #       抽奖类任务（每日看视频/看直播/投稿/开播/关注官号）已按最新要求剔除。
    # 校验：全部 30 个码经 x/task/mission/info 实测，code=0 且任务名一致。
    # ========== 视频奖励（12）==========
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAvwloghvymv00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "投稿", "name": "累计3天投稿，且收到三连2", "task_id": "6ERAvwloghvyrf00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "投稿", "name": "累计5天投稿，总播≥1000且收到三连10", "task_id": "6ERAvwloghvyrd00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "投稿", "name": "累计7天投稿，总播≥2000且收到三连30", "task_id": "6ERAvwloghvt3900", "award": "星琼*500"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAvwloghvuyc00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "投稿", "name": "累计3天投稿，且收到三连2", "task_id": "6ERAvwloghvy9o00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "投稿", "name": "累计5天投稿，总播≥1000且收到三连10", "task_id": "6ERAvwloghvt5200", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "投稿", "name": "累计7天投稿，总播≥2000且收到三连30", "task_id": "6ERAvwloghvtbg00", "award": "星琼*500"},
    # 视频奖励·播放量档位
    {"version": "崩坏星穹铁道4.7", "period": "全版本", "type": "投稿", "name": "累计播放量3万", "task_id": "6ERAvwloghvyhk00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.7", "period": "全版本", "type": "投稿", "name": "累计播放量5万", "task_id": "6ERAvwloghvyss00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.7", "period": "全版本", "type": "投稿", "name": "累计播放量10万", "task_id": "6ERAvwloghvyhj00", "award": "星琼*1000"},
    {"version": "崩坏星穹铁道4.7", "period": "全版本", "type": "投稿", "name": "累计播放量30万", "task_id": "6ERAvwloghvu7000", "award": "星轨通票*10"},
    # ========== 新人限定（4 档分档码）==========
    {"version": "崩坏星穹铁道4.7", "period": "新人限定", "type": "直播", "name": "【新人】累计1天开播", "task_id": "18ERA1wloghv1h700", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.7", "period": "新人限定", "type": "直播", "name": "【新人】累计3天开播", "task_id": "18ERA1wloghv1qq00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.7", "period": "新人限定", "type": "直播", "name": "【新人】累计5天开播", "task_id": "18ERA1wloghv1fh00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.7", "period": "新人限定", "type": "直播", "name": "【新人】累计10天开播", "task_id": "18ERA1wloghvnag00", "award": "星琼*200"},
    # ========== 每日 / 限时 ==========
    {"version": "崩坏星穹铁道4.7", "period": "每日", "type": "直播", "name": "【每日】开播满60分钟且累计有效观看≥15分钟", "task_id": "6ERAvwloghvu2h00", "award": "冒险记录*6+遗失碎金*5"},
    {"version": "崩坏星穹铁道4.7", "period": "每日", "type": "直播", "name": "【每日】获得礼物≥10电池且弹幕人数≥4人", "task_id": "6ERAvwloghvu7900", "award": "漫游指南*2+信用点*11111"},
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "直播", "name": "【限时】开播（11.11-11.17）", "task_id": "6ERAvwloghvyot00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "直播", "name": "【限时】开播（12.2-12.8）", "task_id": "6ERAvwloghvyp900", "award": "星琼*50"},
    # ========== 直播里程碑·上半（4 档分档码）==========
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "直播里程碑", "name": "【里程碑·上半】累计3天开播", "task_id": "18ERA1wloghvmdd00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "直播里程碑", "name": "【里程碑·上半】累计5天开播", "task_id": "18ERA1wloghvm1d00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "直播里程碑", "name": "【里程碑·上半】累计10天开播", "task_id": "18ERA1wloghvmu400", "award": "星琼*800"},
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "直播里程碑", "name": "【里程碑·上半】累计15天开播", "task_id": "18ERA1wloghvme900", "award": "星琼*1000"},
    # ========== 直播里程碑·下半（4 档分档码）==========
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "直播里程碑", "name": "【里程碑·下半】累计3天开播", "task_id": "18ERA1wloghvmvc00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "直播里程碑", "name": "【里程碑·下半】累计5天开播", "task_id": "18ERA1wloghvna500", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "直播里程碑", "name": "【里程碑·下半】累计10天开播", "task_id": "18ERA1wloghvmbw00", "award": "星琼*800"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "直播里程碑", "name": "【里程碑·下半】累计15天开播", "task_id": "18ERA1wloghvnp100", "award": "星琼*1000"},
    # ========== 舰长任务 ==========
    {"version": "崩坏星穹铁道4.7", "period": "上半", "type": "直播", "name": "直播间新增1名舰长（11.11-12.1）", "task_id": "6ERAvwloghvtbd00", "award": "星轨通票*3"},
    {"version": "崩坏星穹铁道4.7", "period": "下半", "type": "直播", "name": "直播间新增1名舰长（12.2-12.22）", "task_id": "6ERAvwloghvyih00", "award": "星轨通票*3"},

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

# v6.7.14: 保存内置官方任务基线快照，供 rebuild_all_tasks() 使用。
# 说明：ALL_TASKS 在运行期会被 load_official_tasks() / rebuild_all_tasks() 原地修改，
#       这里在模块加载时立刻深拷贝一份原始内置表，作为重建时的稳定基线。
import copy as _copy
_BUILTIN_TASKS = _copy.deepcopy(ALL_TASKS)


# ========== O9：任务表外置 ==========
# 优先从 data/tasks_official.json 加载官方任务表；文件不存在或损坏时回退到
# 代码内置的 ALL_TASKS。这样更新游戏活动只需替换 JSON，不必重新打包 exe。

def load_official_tasks():
    """从 data/tasks_official.json 加载官方任务表。

    返回 (tasks, versions, source)：
      source = "json" / "builtin" / "json_fallback_builtin"
    """
    global ALL_TASKS, VERSION_DEFAULT_ACT_ID
    try:
        data = safe_load_json(TASKS_FILE, None)
        if not data or not isinstance(data, dict):
            return None, None, "builtin"

        tasks = data.get("tasks")
        versions = data.get("versions")
        if not isinstance(tasks, list) or not tasks:
            return None, None, "builtin"

        # 校验每条任务的必需字段
        cleaned = []
        for t in tasks:
            if not isinstance(t, dict):
                continue
            if not t.get("task_id"):
                continue
            cleaned.append({
                "version": str(t.get("version") or ""),
                "period": str(t.get("period") or ""),
                "type": str(t.get("type") or ""),
                "name": str(t.get("name") or t["task_id"]),
                "task_id": str(t["task_id"]),
                "award": str(t.get("award") or ""),
            })
        if not cleaned:
            return None, None, "builtin"

        if not isinstance(versions, dict) or not versions:
            versions = None

        ALL_TASKS[:] = cleaned
        if versions:
            VERSION_DEFAULT_ACT_ID.clear() if isinstance(VERSION_DEFAULT_ACT_ID, dict) else None
            for k, v in versions.items():
                VERSION_DEFAULT_ACT_ID[k] = v
        return cleaned, versions, "json"
    except Exception as e:
        print(f"加载外置任务表失败，回退内置: {e}")
        return None, None, "json_fallback_builtin"


TASKS_SOURCE = "builtin"

# 官方任务完整快照（不可变基准）
# ALL_TASKS 会被「删除任务」「手动任务」等操作修改，重建时必须基于这份原始快照，
# 否则用户删掉的任务一旦从 ALL_TASKS 移除就再也恢复不了。
OFFICIAL_TASKS = []

# 兼容旧代码
MINGCHAO_TASKS = [t for t in ALL_TASKS if t["version"] == "鸣潮3.7"]

# ========== 手动任务库 ==========
# 用户手动添加（task_id / 活动网址解析而来）的任务，持久化在 data/manual_tasks.json，
# 统一以「手动任务」版本挂到 ALL_TASKS 末尾，因此两套抢码界面的动态下拉框会自动出现。
MANUAL_VERSION = "手动任务"
MANUAL_PERIOD = "手动"
MANUAL_TYPE = "手动"

MANUAL_TASKS = []


def load_manual_tasks():
    """从 data/manual_tasks.json 载入手动任务（失败返回空列表，不抛异常）。"""
    global MANUAL_TASKS
    data = safe_load_json(MANUAL_TASKS_FILE, [])
    if not isinstance(data, list):
        data = []
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id", "")).strip()
        if not task_id:
            continue
        cleaned.append({
            # 允许归入已有游戏版本（如 鸣潮3.7），也允许新建版本名
            "version": str(item.get("version") or MANUAL_VERSION),
            "period": item.get("period") or MANUAL_PERIOD,
            "type": item.get("type") or MANUAL_TYPE,
            "name": str(item.get("name") or task_id),
            "task_id": task_id,
            "award": str(item.get("award") or ""),
            "act_id": str(item.get("act_id") or ""),
            "act_name": str(item.get("act_name") or ""),
            "added_at": str(item.get("added_at") or ""),
        })
    MANUAL_TASKS = cleaned
    return MANUAL_TASKS


def save_manual_tasks():
    """写回 data/manual_tasks.json（原子写，断电不损坏）。"""
    try:
        atomic_write_json(MANUAL_TASKS_FILE, MANUAL_TASKS)
        return True
    except Exception as e:
        print(f"保存手动任务失败: {e}")
        return False


def add_manual_task(entry):
    """新增一条手动任务。返回 (是否成功, 说明)。task_id 重复时拒绝。"""
    task_id = str((entry or {}).get("task_id", "")).strip()
    if not task_id:
        return False, "task_id 为空"
    if any(t.get("task_id") == task_id for t in MANUAL_TASKS):
        return False, "该 task_id 已存在（手动任务库）"
    if any(t.get("task_id") == task_id for t in ALL_TASKS):
        return False, "该 task_id 已在官方任务表中，无需手动添加"
    item = {
        # 允许归入已有版本/期数/类型，便于和官方任务混排；留空则落到「手动任务」
        "version": str(entry.get("version") or MANUAL_VERSION),
        "period": str(entry.get("period") or MANUAL_PERIOD),
        "type": str(entry.get("type") or MANUAL_TYPE),
        "name": str(entry.get("name") or task_id),
        "task_id": task_id,
        "award": str(entry.get("award") or ""),
        "act_id": str(entry.get("act_id") or ""),
        "act_name": str(entry.get("act_name") or ""),
        "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    MANUAL_TASKS.append(item)
    ALL_TASKS.append(item)
    save_manual_tasks()
    return True, "已添加"


def remove_manual_task(task_id):
    """删除一条手动任务（同时从 ALL_TASKS 摘除）。返回是否删除成功。"""
    task_id = str(task_id or "").strip()
    before = len(MANUAL_TASKS)
    MANUAL_TASKS[:] = [t for t in MANUAL_TASKS if t.get("task_id") != task_id]
    # 手动任务可能被归入任意版本，不能只按 version 判断，改为按「手动任务集合」差集摘除
    _manual_ids = {t.get("task_id") for t in MANUAL_TASKS}
    ALL_TASKS[:] = [t for t in ALL_TASKS
                    if t.get("task_id") != task_id or t.get("task_id") in _manual_ids]
    if len(MANUAL_TASKS) != before:
        save_manual_tasks()
        return True
    return False


def get_manual_task(task_id):
    """按 task_id 查手动任务。"""
    task_id = str(task_id or "").strip()
    return next((t for t in MANUAL_TASKS if t.get("task_id") == task_id), None)


# 版本默认act_id（同一版本的所有任务共享同一个act_id）
VERSION_DEFAULT_ACT_ID = {
    "鸣潮3.8": "1ERAzwloghv5wv00",
    "原神7.2": "1ERAzwloghv3vb00",
    "崩坏星穹铁道4.7": "1ERAxwloghvmpq00",
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


# ========== 已删除官方任务的持久化 ==========
# 用户主动删除的官方任务，task_id 记录在此，重启/更新代码后不会自动复活。
HIDDEN_TASK_IDS = set()


def load_hidden_tasks():
    """从 data/hidden_tasks.json 载入被删除的官方 task_id 集合。"""
    global HIDDEN_TASK_IDS
    data = safe_load_json(HIDDEN_TASKS_FILE, [])
    if not isinstance(data, list):
        data = []
    HIDDEN_TASK_IDS = {str(x) for x in data if x}
    return HIDDEN_TASK_IDS


def save_hidden_tasks():
    """写回 data/hidden_tasks.json（原子写）。"""
    try:
        atomic_write_json(HIDDEN_TASKS_FILE, sorted(HIDDEN_TASK_IDS))
        return True
    except Exception as e:
        print(f"保存已删除任务列表失败: {e}")
        return False


def hide_official_task(task_id):
    """记住"这个官方任务被用户删除了"，之后启动不再显示。"""
    task_id = str(task_id or "").strip()
    if not task_id:
        return False
    HIDDEN_TASK_IDS.add(task_id)
    save_hidden_tasks()
    ALL_TASKS[:] = [t for t in ALL_TASKS if t.get("task_id") != task_id]
    return True


def unhide_official_task(task_id):
    """恢复一个之前被删除的官方任务（需调用 rebuild_all_tasks 生效）。"""
    task_id = str(task_id or "").strip()
    if task_id in HIDDEN_TASK_IDS:
        HIDDEN_TASK_IDS.discard(task_id)
        save_hidden_tasks()
        return True
    return False


# ========== 已完成任务库（v6.4.6 用户需求）==========
# 用户：「查询到的任务加入图二图三这里，版本名称为已完成任务，
#       期数和类型固定为已完成和已完成任务」
#
# 实现：查询到的「已完成且可抢」任务，统一以虚拟分类挂到 ALL_TASKS 末尾：
#   version = "已完成任务"   period = "已完成"   type = "已完成任务"
# 这样两套抢码界面的版本/期数/类型下拉框会自动出现该分类，
# 用户直接选「已完成任务」就能看到所有已完成的可抢任务。
DONE_VERSION = "已完成任务"
DONE_PERIOD = "已完成"
DONE_TYPE = "已完成任务"

DONE_TASKS = []


def load_done_tasks():
    """从 data/task_status_cache.json 载入「已完成且可抢」的任务。

    只取满足以下条件的（与查询模块判定一致）：
      task_finished == True
      stock_available == True
      status 不在 (6, 7)   # 6=已领取过, 7=无资格
    """
    global DONE_TASKS
    try:
        import rush_stats as _rs
        cache = _rs.load_task_status_cache()
        claimables = _rs.claimable_tasks(cache)
    except Exception:
        claimables = []

    cleaned = []
    seen = set()
    for item in claimables:
        task_id = str(item.get("task_id", "")).strip()
        if not task_id or task_id in seen:
            continue
        seen.add(task_id)
        cleaned.append({
            "version": DONE_VERSION,
            "period": DONE_PERIOD,
            "type": DONE_TYPE,
            "name": str(item.get("task_name") or task_id),
            "task_id": task_id,
            "award": str(item.get("award") or ""),
            "act_id": str(item.get("act_id") or ""),
            "act_name": str(item.get("act_name") or ""),
            "account_name": str(item.get("account") or ""),
            "status_text": str(item.get("status_text") or "可抢"),
            "queried_at": str(item.get("queried_at") or ""),
            "added_at": str(item.get("queried_at") or ""),
            "is_done_virtual": True,
        })
    DONE_TASKS = cleaned
    return DONE_TASKS


def done_versions():
    """已完成任务的虚拟版本名（用于下拉框）。无数据时返回空列表。"""
    return [DONE_VERSION] if DONE_TASKS else []


def done_periods():
    return [DONE_PERIOD] if DONE_TASKS else []


def done_types():
    return [DONE_TYPE] if DONE_TASKS else []


def get_done_task(task_id):
    """按 task_id 查已完成任务。"""
    task_id = str(task_id or "").strip()
    for t in DONE_TASKS:
        if t.get("task_id") == task_id:
            return t
    return None


def refresh_done_tasks():
    """重新载入已完成任务并重建 ALL_TASKS（供查询后/打开页面时调用）。"""
    load_done_tasks()
    rebuild_all_tasks()
    return DONE_TASKS


# ============================================================
# v6.4.8：自定义版本集合管理（用户需求确认）
#
# 用户澄清：「这个任务组并不是新模式的任务组，
#           而是跟鸣潮3.7版本的各个任务所有任务的一个集合」
# 即：任务组 == ALL_TASKS 里的 version 这一层。
#
# 所以「手动创建」= 创建一个新的版本集合（自定义 version 名），
# 然后把查询到的任务放进去。
#
# 特性：
#   1. 可自定义名称（默认「已完成任务」）
#   2. 期数=已完成、类型=已完成任务 固定（按用户要求）
#   3. 持久化到 data/custom_versions.json
#   4. 支持删除自己创建的版本集合
# ============================================================

# 新版本集合的固定期数/类型（用户明确要求）
CUSTOM_PERIOD = DONE_PERIOD      # "已完成"
CUSTOM_TYPE = DONE_TYPE          # "已完成任务"

CUSTOM_VERSIONS = []   # [{"version": 名称, "created_at": 时间}]


def load_custom_versions():
    """载入用户自定义版本集合列表。"""
    global CUSTOM_VERSIONS
    data = safe_load_json(CUSTOM_VERSIONS_FILE, [])
    if not isinstance(data, list):
        data = []
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        v = str(item.get("version", "")).strip()
        if not v:
            continue
        # 不允许和官方版本重名
        if any(t.get("version") == v for t in OFFICIAL_TASKS):
            continue
        cleaned.append({
            "version": v,
            "created_at": str(item.get("created_at") or ""),
        })
    CUSTOM_VERSIONS = cleaned
    return CUSTOM_VERSIONS


def save_custom_versions():
    """保存自定义版本集合列表。"""
    try:
        atomic_write_json(CUSTOM_VERSIONS_FILE, CUSTOM_VERSIONS)
        return True
    except Exception as e:
        print(f"保存自定义版本失败: {e}")
        return False


def create_custom_version(name):
    """创建一个新的版本集合（用户需求：查询中心里手动创建）。

    返回 (是否成功, 说明)。
    """
    name = str(name or "").strip()
    if not name:
        return False, "名称不能为空"
    if len(name) > 40:
        return False, "名称不能超过40字符"
    # 与现有版本（官方+手动+已完成+自定义）重名检查
    existing = set()
    for t in OFFICIAL_TASKS:
        existing.add(t.get("version"))
    for v in CUSTOM_VERSIONS:
        existing.add(v.get("version"))
    existing.add(MANUAL_VERSION)
    if name in existing:
        return False, "版本「%s」已存在" % name
    CUSTOM_VERSIONS.append({
        "version": name,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_custom_versions()
    rebuild_all_tasks()
    return True, "已创建"


def delete_custom_version(name):
    """删除一个自定义版本集合（连同该版本下的所有任务）。"""
    name = str(name or "").strip()
    before = len(CUSTOM_VERSIONS)
    CUSTOM_VERSIONS[:] = [v for v in CUSTOM_VERSIONS if v.get("version") != name]
    if len(CUSTOM_VERSIONS) == before:
        return False, "不是自定义版本，无法删除"
    save_custom_versions()
    rebuild_all_tasks()
    return True, "已删除"


def custom_version_tasks(name):
    """取某个自定义版本集合下的全部任务。"""
    return [t for t in ALL_TASKS if t.get("version") == name]


# ============================================================
# v6.5.0：自定义版本集合的任务持久化（修复重启丢失 bug）
#
# 用户报的 bug：「这个新集合每次重启exe就会直接消失，不会进行保存」
#
# 根因（两个叠加）：
#   1. add_tasks_to_version() 只往内存 DONE_TASKS 里 append，从不写盘
#   2. load_done_tasks() 启动时从 task_status_cache 重建 DONE_TASKS，
#      且强制把 version 改回 DONE_VERSION，把用户指定的版本名覆盖掉
#   => 重启后：custom_versions.json 里的版本名还在，
#      但版本下的任务全没了（DONE_TASKS 被重建覆盖）
#
# 修复：
#   新增 CUSTOM_VERSION_TASKS_FILE = data/custom_version_tasks.json
#   结构：{"版本名": [任务, 任务, ...], ...}
#   add_tasks_to_version 写入后立即持久化
#   load_custom_version_tasks 在启动时载入并注入 ALL_TASKS
# ============================================================

# 路径由 config.CUSTOM_VERSION_TASKS_FILE 提供（下面 try 里覆盖）

# 内存：{版本名: [任务dict, ...]}
CUSTOM_VERSION_TASKS = {}




def load_custom_version_tasks():
    """从 data/custom_version_tasks.json 载入自定义版本集合的任务。"""
    global CUSTOM_VERSION_TASKS
    data = safe_load_json(CUSTOM_VERSION_TASKS_FILE, {})
    if not isinstance(data, dict):
        data = {}
    cleaned = {}
    for ver, items in data.items():
        ver = str(ver or "").strip()
        if not ver or not isinstance(items, list):
            continue
        tasks = []
        for it in items:
            if not isinstance(it, dict):
                continue
            tid = str(it.get("task_id", "")).strip()
            if not tid:
                continue
            tasks.append({
                "version": ver,
                "period": str(it.get("period") or CUSTOM_PERIOD),
                "type": str(it.get("type") or CUSTOM_TYPE),
                "name": str(it.get("name") or it.get("task_name") or tid),
                "task_id": tid,
                "award": str(it.get("award") or ""),
                "act_id": str(it.get("act_id") or ""),
                "act_name": str(it.get("act_name") or ""),
                "account_name": str(it.get("account_name")
                                    or it.get("account") or ""),
                "status_text": str(it.get("status_text") or "可抢"),
                "added_at": str(it.get("added_at") or ""),
                "is_custom": True,
            })
        if tasks:
            cleaned[ver] = tasks
    CUSTOM_VERSION_TASKS = cleaned
    return CUSTOM_VERSION_TASKS


def save_custom_version_tasks():
    """保存自定义版本集合的任务到磁盘（原子写）。"""
    try:
        atomic_write_json(CUSTOM_VERSION_TASKS_FILE, CUSTOM_VERSION_TASKS)
        return True
    except Exception as e:
        print(f"保存自定义版本任务失败: {e}")
        return False


def custom_version_all_tasks():
    """把所有自定义版本下的任务摊平成列表（供 rebuild 使用）。"""
    out = []
    for ver, items in CUSTOM_VERSION_TASKS.items():
        out.extend(items)
    return out


def rebuild_all_tasks():
    """重建 ALL_TASKS：官方内置 + 自定义版本任务 + 已完成任务 + 手动任务。

    v6.7.14 新增。此前代码里已有 4 处调用 rebuild_all_tasks() 但函数从未实现，
    导致：新增/删除自定义版本任务后，ALL_TASKS 不会刷新，
    「版本」下拉框选到新集合时读不到任务（表现为集合空着）。

    设计原则：
      · 以模块启动时的内置官方任务为基线（_BUILTIN_TASKS）
      · 叠加当前 CUSTOM_VERSION_TASKS 里的所有自定义任务
      · 叠加 DONE_TASKS（已完成任务集合）
      · 叠加 MANUAL_TASKS（手动添加的任务）
      · 用 ALL_TASKS[:] 原地替换，保持所有外部引用有效
      · 联合键 (task_id, account_name) 去重，同账号覆盖
    """
    global ALL_TASKS
    try:
        base = list(_BUILTIN_TASKS) if _BUILTIN_TASKS else []

        merged = list(base)
        index = {}
        for it in merged:
            k = (str(it.get("task_id", "")).strip(),
                 str(it.get("account_name", "") or "").strip())
            if k[0]:
                index[k] = len(merged) - 1

        def _merge(items):
            for it in (items or []):
                if not isinstance(it, dict):
                    continue
                tid = str(it.get("task_id", "") or "").strip()
                if not tid:
                    continue
                acc = str(it.get("account_name", "") or
                          it.get("account", "") or "").strip()
                k = (tid, acc)
                if k in index:
                    merged[index[k]] = it
                else:
                    index[k] = len(merged)
                    merged.append(it)

        # 自定义版本任务
        try:
            custom = custom_version_all_tasks()
            _merge(custom)
        except Exception:
            pass

        # 已完成任务
        try:
            _merge(DONE_TASKS)
        except Exception:
            pass

        # 手动任务
        try:
            _merge(MANUAL_TASKS)
        except Exception:
            pass

        ALL_TASKS[:] = merged
        return len(ALL_TASKS)
    except Exception as e:
        print("重建 ALL_TASKS 失败: %s" % e)
        return 0


def _add_tasks_to_custom_version(version, tasks):
    """内部：往自定义版本任务表里写入并持久化。

    v6.7.14 重写：修复「按账号覆盖」问题。

    原实现的问题：
      去重键只有 task_id，完全不看 account_name。
      所以同一 task_id 被不同账号抢到时，第二个账号永远加不进去；
      而且已存在的条目只会被【跳过】，状态永远不会刷新
      —— 导致抢领成功后，集合里还是旧的「可抢」状态。

    新实现：
      · 去重键改为 (task_id, account_name) 联合键
      · 已存在则【覆盖更新】字段（状态/奖励/act_id/查询时间）
      · 同一 task_id 不同账号 -> 各自独立一条记录
      · 返回 (新增数, 更新数)
    """
    if version not in CUSTOM_VERSION_TASKS:
        CUSTOM_VERSION_TASKS[version] = []
    bucket = CUSTOM_VERSION_TASKS[version]

    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # 建立联合键索引：{(task_id, account_name): 条目引用}
    existing_index = {}
    for idx, t in enumerate(bucket):
        key = (str(t.get("task_id", "")).strip(),
               str(t.get("account_name", "")).strip())
        existing_index[key] = idx

    added = 0
    updated = 0

    for it in (tasks or []):
        tid = str(it.get("task_id", "") or "").strip()
        if not tid:
            continue
        acc = str(it.get("account") or it.get("account_name") or "").strip()
        key = (tid, acc)

        # 统一整理要写入的字段
        fields = {
            "version": version,
            "period": CUSTOM_PERIOD,
            "type": CUSTOM_TYPE,
            "name": str(it.get("task_name") or it.get("name") or tid),
            "task_id": tid,
            "award": str(it.get("award") or ""),
            "act_id": str(it.get("act_id") or ""),
            "act_name": str(it.get("act_name") or ""),
            "account_name": acc,
            "status_text": str(it.get("status_text") or "可抢"),
            "task_finished": bool(it.get("task_finished")),
            "stock_available": bool(it.get("stock_available")),
            "status": it.get("status"),
            "total_stock": it.get("total_stock", 0),
            "day_stock": it.get("day_stock", 0),
            "queried_at": str(it.get("queried_at") or ""),
            "updated_at": now,
            "is_custom": True,
        }

        if key in existing_index:
            # 覆盖更新已有条目（保留 added_at 原始加入时间）
            idx = existing_index[key]
            keep_added_at = bucket[idx].get("added_at", now)
            bucket[idx] = dict(fields, added_at=keep_added_at)
            updated += 1
        else:
            # 新增条目
            bucket.append(dict(fields, added_at=now))
            existing_index[key] = len(bucket) - 1
            added += 1

    if added or updated:
        save_custom_version_tasks()

    return added, updated

def add_tasks_to_version(version, tasks):
    """把一批任务加入指定版本集合（v6.7.14 重写：按账号独立 + 覆盖更新）。

    修复的问题：
      原实现去重键只有 task_id，不看 account_name。
        · 同一 task_id 被多个账号抢到时，只有第一个账号能进集合
        · 已存在条目只跳过不更新 -> 抢领成功后集合里仍是旧状态

    新行为：
      · 去重键 = (task_id, account_name)
      · 已存在 -> 覆盖更新状态/奖励/库存/查询时间
      · 新组合 -> 新增
      · 返回 (新增数, 更新数)
    """
    version = str(version or "").strip()
    if not version:
        return 0, 0

    now = time.strftime("%Y-%m-%d %H:%M:%S")

    def _key(item):
        return (str(item.get("task_id", "")).strip(),
                str(item.get("account_name", "") or
                    item.get("account") or "").strip())

    existing_index = {}
    for idx, t in enumerate(DONE_TASKS):
        if str(t.get("version", "")) == version:
            k = _key(t)
            if k[0]:
                existing_index[k] = idx

    added = 0
    updated = 0

    for it in (tasks or []):
        tid = str(it.get("task_id", "") or "").strip()
        if not tid:
            continue
        acc = str(it.get("account") or it.get("account_name") or "").strip()
        key = (tid, acc)

        entry = {
            "version": version,
            "period": CUSTOM_PERIOD,
            "type": CUSTOM_TYPE,
            "name": str(it.get("task_name") or it.get("name") or tid),
            "task_id": tid,
            "award": str(it.get("award") or ""),
            "act_id": str(it.get("act_id") or ""),
            "act_name": str(it.get("act_name") or ""),
            "account_name": acc,
            "status_text": str(it.get("status_text") or "可抢"),
            "task_finished": bool(it.get("task_finished")),
            "stock_available": bool(it.get("stock_available")),
            "status": it.get("status"),
            "total_stock": it.get("total_stock", 0),
            "day_stock": it.get("day_stock", 0),
            "queried_at": str(it.get("queried_at") or ""),
            "updated_at": now,
            "is_custom": True,
        }

        if key in existing_index:
            idx = existing_index[key]
            keep_added_at = DONE_TASKS[idx].get("added_at", now)
            DONE_TASKS[idx] = dict(entry, added_at=keep_added_at)
            updated += 1
        else:
            DONE_TASKS.append(dict(entry, added_at=now))
            existing_index[key] = len(DONE_TASKS) - 1
            added += 1

    if added or updated:
        try:
            _add_tasks_to_custom_version(version, tasks)
        except Exception:
            pass
        rebuild_all_tasks()

    return added, updated

