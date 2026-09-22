# -*- coding: utf-8 -*-
# 通用工具函数

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import request, has_request_context

from mks_models import AccessLog, shujuku

# 写日志文件
_wenjian_logger = logging.getLogger("mks_rizhi")
if not _wenjian_logger.handlers:
    # logs 目录跟项目根同级，没有就建
    _rizhi_mulu = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    if not os.path.exists(_rizhi_mulu):
        os.makedirs(_rizhi_mulu, exist_ok=True)
    _chuliqi = RotatingFileHandler(
        os.path.join(_rizhi_mulu, "mks.log"),
        maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8",
    )
    _chuliqi.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    _wenjian_logger.addHandler(_chuliqi)
    _wenjian_logger.setLevel(logging.INFO)


def xie_wenben_rizhi(neirong, jibie="info"):
    """往 logs/mks.log 里顺手写一行，出问题时靠它回忆现场"""
    if jibie == "error":
        _wenjian_logger.error(neirong)
    else:
        _wenjian_logger.info(neirong)


def jilu_caozuo(caozuoren, dongzuo, mokuai, duixiang="", xiangqing=""):
    # 往操作流水表里加一条
    # 系统自己干的活，人传 None
    benji_ip = ""
    if has_request_context():
        # 反代优先取 X-Forwarded-For，取不到再用直连地址
        fanyi = request.environ.get("HTTP_X_FORWARDED_FOR", "")
        benji_ip = fanyi if fanyi else (request.remote_addr or "")

    if caozuoren is not None:
        rid = caozuoren.id
        rname = caozuoren.username
    else:
        rid = None
        rname = "system"

    yi_tiao = AccessLog(
        user_id=rid,
        username=rname,
        action=dongzuo,
        module=mokuai,
        target=duixiang,
        ip_address=benji_ip,
        detail=xiangqing,
    )
    shujuku.session.add(yi_tiao)
    try:
        shujuku.session.commit()
    except Exception as cuowu:
        # 写库失败不影响主流程，回滚后记到文件日志
        shujuku.session.rollback()
        xie_wenben_rizhi("操作日志写库失败: %s" % cuowu, "error")
