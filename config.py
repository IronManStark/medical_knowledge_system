# -*- coding: utf-8 -*-
"""
医学知识库系统 - 全局配置模块
负责加载运行参数、数据库连接、会话密钥等配置项
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class AppConfig:
    """应用运行期配置集合"""

    # 会话加密密钥，用于 Flask session 签名
    SECRET_KEY = os.environ.get("MKS_SECRET", "mks-9f2a7c4e1b8d3a6f5e0c2d7b4a1e9f3c")

    # SQLite 数据库文件存放路径
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(BASE_DIR / "data" / "mks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 分页默认条数
    PER_PAGE = 15

    # 上传附件保存目录
    UPLOAD_FOLDER = str(BASE_DIR / "data" / "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}

    # 默认模型接口配置（运行期可在管理页面动态修改）
    MODEL_API_URL = "https://api.example.com/v1/chat/completions"
    MODEL_API_KEY = ""
    MODEL_MODEL_NAME = "gpt-4o-mini"
    MODEL_TIMEOUT = 60

    # 会话有效期（小时）
    SESSION_LIFETIME_HOURS = 8


class DevelopmentConfig(AppConfig):
    DEBUG = True


class ProductionConfig(AppConfig):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
