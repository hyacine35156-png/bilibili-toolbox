#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Supabase连接池不同region"""

import psycopg2

regions = [
    ("aws-0-ap-southeast-1.pooler.supabase.com", "新加坡"),
    ("aws-0-ap-northeast-1.pooler.supabase.com", "东京"),
    ("aws-0-ap-northeast-2.pooler.supabase.com", "首尔"),
    ("aws-1-ap-southeast-1.pooler.supabase.com", "新加坡-1"),
]

for host, name in regions:
    try:
        conn = psycopg2.connect(
            host=host, port=5432,
            user="postgres.ongvfaxymdrhiblxxsbb",
            password="yHdXd6jK86aQu6Oh",
            dbname="postgres", sslmode="require", connect_timeout=8
        )
        cur = conn.cursor()
        cur.execute("SELECT current_database(), version()")
        print(f"✓ {host} ({name}) 连接成功: {cur.fetchone()[0]}")
        cur.close()
        conn.close()
        break
    except Exception as e:
        print(f"✗ {host} ({name}): {str(e)[:120]}")
