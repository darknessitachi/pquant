# -*- coding: utf-8 -*-
import os
import cx_Oracle


# 创建数据库连接
def connect(url):
    os.environ['NLS_LANG'] = "SIMPLIFIED CHINESE_CHINA.ZHS16GBK"
    db = cx_Oracle.connect(url)
    return db


# 查询结果集
def select(db, sql):
    cursor = db.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    return result

def __dml_db(db, sql, param=None):
    cursor = db.cursor()
    if param:
        cursor.execute(sql, param)
    else:
        cursor.execute(sql)
    cursor.close()
    db.commit()


def ddl_db(db, sql):
    cursor = db.cursor()
    cursor.execute(sql)
    cursor.close()


def batch_insert(db, sql, bulk_list):
    cursor = db.cursor()
    for item in bulk_list:
        cursor.execute(sql, item)
    cursor.close()
    db.commit()


def insert(db, sql):
    __dml_db(db, sql)


def update(db, sql):
    __dml_db(db, sql)
