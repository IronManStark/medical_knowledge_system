# -*- coding: utf-8 -*-
# 附件存 minio

import os
import io
import uuid

from minio import Minio
from minio.error import S3Error

from gongju import xie_wenben_rizhi

# 下面这几个默认值只给本地开发用，启动时会被 shezhi_minio() 传进来的配置盖掉
# 注意：9001 是网页控制台端口，S3 API 走 9000
MINIO_DIZHI = "10.211.55.4:9000"
MINIO_YONGHU = "admin"
MINIO_KOULING = "Mkb.001@2023"
MINIO_TONG = "mks"          # 桶名
MINIO_ANQUAN = False        # 走 http，不开 https


_ke_lianjie = None


# 启动时调一次，把配置写进模块级变量
def shezhi_minio(dizhi, yonghu, kouling, tong="mks", anquan=False):
    global MINIO_DIZHI, MINIO_YONGHU, MINIO_KOULING, MINIO_TONG, MINIO_ANQUAN, _ke_lianjie
    MINIO_DIZHI = dizhi
    MINIO_YONGHU = yonghu
    MINIO_KOULING = kouling
    MINIO_TONG = tong
    MINIO_ANQUAN = bool(anquan)
    _ke_lianjie = None  # 强制下次重建连接


def nao_ke_lianjie():
    """客户端单例，复用连接"""
    global _ke_lianjie
    if _ke_lianjie is None:
        _ke_lianjie = Minio(
            MINIO_DIZHI,
            access_key=MINIO_YONGHU,
            secret_key=MINIO_KOULING,
            secure=MINIO_ANQUAN,
        )
    return _ke_lianjie


def que_ren_tong():
    """确认 mks 桶存在，没有就现建"""
    ke = nao_ke_lianjie()
    try:
        if not ke.bucket_exists(MINIO_TONG):
            ke.make_bucket(MINIO_TONG)
            xie_wenben_rizhi("MinIO 桶 %s 不存在，已自动创建" % MINIO_TONG)
    except S3Error as e:
        xie_wenben_rizhi("MinIO 建桶失败: %s" % e, "error")
        raise


def _an_quan_ming(wenjian_ming):
    houzui = ""
    if "." in wenjian_ming:
        houzui = "." + wenjian_ming.rsplit(".", 1)[1].lower()
    return "%s%s" % (uuid.uuid4().hex, houzui)


def pin_dao_minio(fenlei_ming, zhishi_ming, zhishi_id, wenjian_duixiang, yuan_ming, daxiao, leixing):
    """上传文件流，返回对象路径"""
    que_ren_tong()
    ke = nao_ke_lianjie()
    # 知识标题里可能有 / 之类的，替换掉，避免当成路径分隔
    ming_qingxi = (zhishi_ming or "weizhi").replace("/", "_").replace("\\", "_")
    fl_qingxi = (fenlei_ming or "weifenlei").replace("/", "_").replace("\\", "_")
    qianzhui = "%s/%s_%s/" % (fl_qingxi, ming_qingxi, zhishi_id)
    duixiang_ming = qianzhui + _an_quan_ming(yuan_ming)
    try:
        ke.put_object(
            MINIO_TONG, duixiang_ming, wenjian_duixiang, daxiao,
            content_type=leixing or "application/octet-stream",
        )
    except S3Error as e:
        xie_wenben_rizhi("MinIO 上传失败: %s" % e, "error")
        raise
    return duixiang_ming


def qu_liu_cong_minio(duixiang_ming):
    ke = nao_ke_lianjie()
    try:
        xiang = ke.get_object(MINIO_TONG, duixiang_ming)
        return xiang
    except S3Error as e:
        xie_wenben_rizhi("MinIO 取对象失败: %s" % e, "error")
        raise


def shanchu_minio(duixiang_ming):
    """删 minio 上的对象"""
    ke = nao_ke_lianjie()
    try:
        ke.remove_object(MINIO_TONG, duixiang_ming)
    except S3Error as e:
        xie_wenben_rizhi("MinIO 删除对象失败: %s" % e, "error")
