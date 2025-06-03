import base64
import hashlib
import hmac
import re
import string
import time
import yagmail
import random

from config import LOGIN_SECRET, MAX_LOG_LENGTH
from models import User, Log, Session


# from models import *


def encode(inputString):
    byteString = inputString.encode('utf-8')
    base64_bytes = base64.b64encode(byteString)
    encodedString = base64_bytes.decode()
    return encodedString


def decode(encodedString):
    try:
        base64_bytes = encodedString.encode('utf-8')
        byteString = base64.b64decode(base64_bytes)
        decodedString = byteString.decode()
    except Exception:
        return None
    return decodedString


# 计算sessionid携带签名
def calcSignature(message):
    secret = LOGIN_SECRET.encode('utf-8')
    message = str(message).encode('utf-8')
    signature = hmac.new(secret, message, hashlib.sha512).hexdigest()
    return signature


def checkSignature(signature, message):
    secret = LOGIN_SECRET.encode('utf-8')
    message = str(message).encode('utf-8')
    correctSig = hmac.new(secret, message, hashlib.sha512).hexdigest()
    return hmac.compare_digest(signature, correctSig)


def checkSessionid(sessionid):
    decodedSessionid = decode(sessionid)
    if not decodedSessionid:
        return {}
    pattern = rf"^userId=(\d+)&timestamp=(\d+)&signature=(.+)&algorithm=sha256$"  # 必须用()包含住捕获组才能被match.group捕获
    match = re.match(pattern, decodedSessionid)
    if not match:
        return {}
    userId = match.group(1)
    timestamp = match.group(2)
    signature = match.group(3)
    if not checkSignature(signature, userId):  # 签名无效
        return {}
    if time.time() - float(timestamp) > 10800:  # 3小时有效
        return {}
    return {
        "userId": int(userId),
        "timestamp": timestamp
    }


def checkAdminOnly(userId, operationLevel="adminOnly"):
    session = Session()
    try:
        user = session.query(User).get(userId)
        if not user:
            return False
        usertype = user.usertype
        if operationLevel == "adminOnly":
            return usertype == 2 or usertype == 6
        elif operationLevel == "superAdminOnly":
            return usertype == 6
        else:
            return True
    finally:
        session.close()


def checkUserAuthority(userId, authorityId):
    session = Session()
    try:
        user = session.query(User).get(userId)
        if not user:
            return False
        # admin豁免
        if user.usertype >= 2:
            return True
        authority = user.authority
        if authorityId in authority:
            return True
        return False
    finally:
        session.close()


def checkUserVisibleClient(userId):
    session = Session()
    try:
        user = session.query(User).get(userId)
        if not user or not user.clientVisible:
            return [0, None, None]
        res = [user.clientVisible, user.schoolId, user.departmentId]
        # admin豁免
        if user.usertype >= 2:
            res[0] = 4
            return res
        return res
    finally:
        session.close()


def generateCaptcha():
    source = string.digits * 6
    captcha = random.sample(source, 6)
    captcha = "".join(captcha)
    return captcha


def clearLogs():
    session = Session()
    try:
        log_count = session.query(Log).count()
        if log_count > MAX_LOG_LENGTH:
            delete_count = log_count - MAX_LOG_LENGTH
            subquery = (
                session.query(Log.id)
                .order_by(Log.time.asc())
                .limit(delete_count)
                .subquery()
            )
            session.query(Log).filter(Log.id.in_(subquery)).delete(synchronize_session=False)
            # session.commit()
    finally:
        session.close()
