# -*- coding: utf-8 -*-
"""
医学知识库系统 - 操作日志工具
统一封装访问日志写入逻辑
作者：陈的斌
"""

from flask import request, has_request_context
from models import AccessLog, db


def log_access(user, action: str, module: str, target: str = "", detail: str = ""):
    """记录一条用户操作日志

    Args:
        user: 当前用户对象（可能为 None）
        action: 操作类型，如 login / create / update / delete / approve
        module: 功能模块名称
        target: 操作对象描述
        detail: 附加详情
    """
    ip_addr = ""
    if has_request_context():
        ip_addr = request.environ.get("HTTP_X_FORWARDED_FOR", "") or request.remote_addr or ""

    entry = AccessLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        module=module,
        target=target,
        ip_address=ip_addr,
        detail=detail,
    )
    db.session.add(entry)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
