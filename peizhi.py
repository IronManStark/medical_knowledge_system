import os
from pathlib import Path

XIANGMU_MULU = Path(__file__).resolve().parent

MEIYE_TIAOSHU = 15

class JichuShezhi(object):

    SECRET_KEY = os.environ.get("MKS_SECRET", "mks-cdb-77a2c9e4f1b8d3a6f5e0c2d7b4a1e9f3")

    DB_DIZHI = os.environ.get("MKS_DB_HOST", "10.211.55.4")
    DB_DUANKOU = int(os.environ.get("MKS_DB_PORT", "3306"))
    DB_ZHANGHAO = os.environ.get("MKS_DB_USER", "root")
    DB_KOULING = os.environ.get("MKS_DB_PASSWORD", "Cdb930823")
    DB_KU_MING = os.environ.get("MKS_DB_NAME", "mks")

    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8mb4"
        % (DB_ZHANGHAO, DB_KOULING, DB_DIZHI, DB_DUANKOU, DB_KU_MING)
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False

    PER_PAGE = MEIYE_TIAOSHU
    UPLOAD_FOLDER = str(XIANGMU_MULU / "data" / "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}

    MODEL_API_URL = os.environ.get("MKS_MODEL_URL", "")
    MODEL_API_KEY = os.environ.get("MKS_MODEL_KEY", "")
    MODEL_MODEL_NAME = os.environ.get("MKS_MODEL_NAME", "")
    MODEL_TIMEOUT = 60

    MINIO_DIZHI = os.environ.get("MKS_MINIO_ENDPOINT", "10.211.55.4:9000")
    MINIO_YONGHU = os.environ.get("MKS_MINIO_USER", "admin")
    MINIO_KOULING = os.environ.get("MKS_MINIO_PASSWORD", "Mkb.001@2023")
    MINIO_TONG = os.environ.get("MKS_MINIO_BUCKET", "mks")
    MINIO_ANQUAN = os.environ.get("MKS_MINIO_SECURE", "false").lower() in ("1", "true", "yes")

    SESSION_LIFETIME_HOURS = 8
