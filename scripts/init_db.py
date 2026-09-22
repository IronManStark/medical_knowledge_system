# -*- coding: utf-8 -*-
# 第一次部署时跑的建库脚本

import os
import sys

# 让这脚本在哪儿都能找到项目根
xiangmu_gen = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, xiangmu_gen)

import pymysql

# 连接参数，环境变量没给就用这套默认的
mysql_lianjie = {
    'host': os.environ.get('MKS_DB_HOST', '10.211.55.4'),
    'port': int(os.environ.get('MKS_DB_PORT', 3306)),
    'user': os.environ.get('MKS_DB_USER', 'root'),
    'password': os.environ.get('MKS_DB_PASSWORD', ''),
    'database': os.environ.get('MKS_DB_NAME', 'mks'),
    'charset': 'utf8mb4',
}


def ba_sql_zou_yi_bian(lian, wenjian_lj):
    """把 sql 文件按分号拆开，一句句喂给 mysql"""
    you_biao = lian.cursor()

    with open(wenjian_lj, 'r', encoding='utf-8') as f:
        quan_wen = f.read()

    # 脚本里语句都是分号收尾，直接拆
    yi_ju_ju = quan_wen.split(';')

    zong = 0
    for ju in yi_ju_ju:
        ju = ju.strip()
        # 空行和注释行跳过
        if not ju or ju.startswith('--'):
            continue
        try:
            you_biao.execute(ju)
            zong += 1
        except Exception as cuo:
            # 某句挂了别整个停，打出来继续，多半是表已存在
            print("  这句没跑成: %s ... -> %s" % (ju[:40], cuo))

    lian.commit()
    you_biao.close()
    print("  sql 文件过完了，成功执行 %d 句" % zong)


def kai_shi():
    print("=== 医学知识库系统 数据库初始化 ===")
    print("目标: MySQL (%s:%s/%s)" % (
        mysql_lianjie['host'], mysql_lianjie['port'], mysql_lianjie['database']))
    print("")

    if not mysql_lianjie['password']:
        print("警告: 没设 MKS_DB_PASSWORD 环境变量，连不上，先设了再来")
        return

    # 第一步：连 mysql 服务，把库建出来
    try:
        lian = pymysql.connect(
            host=mysql_lianjie['host'],
            port=mysql_lianjie['port'],
            user=mysql_lianjie['user'],
            password=mysql_lianjie['password'],
            charset=mysql_lianjie['charset'],
        )
        you_biao = lian.cursor()
        you_biao.execute(
            "CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            % mysql_lianjie['database']
        )
        lian.commit()
        you_biao.close()
        lian.close()
        print("OK 库建好了（或本来就有）")
    except Exception as cuo:
        print("连数据库都没连上: %s" % cuo)
        return

    # 第二步：连上具体的库，灌表结构和初始数据
    try:
        lian = pymysql.connect(**mysql_lianjie)
        sql_zai_na = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'init_mysql.sql')
        ba_sql_zou_yi_bian(lian, sql_zai_na)
        lian.close()
        print("OK 表结构和初始数据都齐了")
    except Exception as cuo:
        print("建表阶段出问题了: %s" % cuo)
        return

    print("")
    print("=== 初始化收工，可以启动系统了 ===")


if __name__ == '__main__':
    kai_shi()
