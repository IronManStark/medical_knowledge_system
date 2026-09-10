# -*- coding: utf-8 -*-
"""医学知识库系统 - 配置模块"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class AppConfig:
    SECRET_KEY = os.environ.get("MKS_SECRET", "mks-9f2a7c4e1b8d3a6f5e0c2d7b4a1e9f3c")

    DB_TYPE = os.environ.get("MKS_DB_TYPE", "sqlite").lower()
    DB_HOST = os.environ.get("MKS_DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("MKS_DB_PORT", "3306"))
    DB_USER = os.environ.get("MKS_DB_USER", "root")
    DB_PASSWORD = os.environ.get("MKS_DB_PASSWORD", "")
    DB_NAME = os.environ.get("MKS_DB_NAME", "mks")

    if DB_TYPE == "mysql":
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(BASE_DIR / "data" / "mks.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PER_PAGE = 15
    UPLOAD_FOLDER = str(BASE_DIR / "data" / "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}

    MODEL_API_URL = os.environ.get("MKS_MODEL_URL", "")
    MODEL_API_KEY = os.environ.get("MKS_MODEL_KEY", "")
    MODEL_MODEL_NAME = os.environ.get("MKS_MODEL_NAME", "")
    MODEL_TIMEOUT = 60

    SESSION_LIFETIME_HOURS = 8


class DevelopmentConfig(AppConfig):
    DEBUG = True


class ProductionConfig(AppConfig):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
