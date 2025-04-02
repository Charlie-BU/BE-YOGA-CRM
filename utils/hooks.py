import base64
import hashlib
import hmac
import re
import string
import time
import yagmail
import random

from config import LOGIN_SECRET
from models import session, User


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
        return None
    pattern = rf"^userId=(\d+)&timestamp=(\d+)&signature=(.+)&algorithm=sha256$"  # 必须用()包含住捕获组才能被match.group捕获
    match = re.match(pattern, decodedSessionid)
    if not match:
        return None
    userId = match.group(1)
    timestamp = match.group(2)
    signature = match.group(3)
    if not checkSignature(signature, userId):  # 签名无效
        return None
    if time.time() - float(timestamp) > 10800:  # 3小时有效
        return None
    return {
        "userId": int(userId),
        "timestamp": timestamp
    }


def checkUserAuthority(userId, operationLevel="adminOnly"):
    user = session.query(User).get(userId)
    usertype = user.usertype
    if operationLevel == "adminOnly":
        return usertype == 2 or usertype == 6
    elif operationLevel == "superAdminOnly":
        return usertype == 6
    else:
        return True


def generateCaptcha():
    source = string.digits * 6
    captcha = random.sample(source, 6)
    captcha = "".join(captcha)
    return captcha
