import time

from robyn import SubRouter, jsonify

from models import *
from utils.hooks import calcSignature, encode, checkSessionid

userRouter = SubRouter(__file__, prefix="/user")


@userRouter.post("/login")
async def login(request):
    data = request.json()
    username = data["username"]
    user = session.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({
            "status": -1,
            "message": "用户不存在",
        })
    password = data["password"]
    if not user.checkPassword(password):
        return jsonify({
            "status": -2,
            "message": "密码错误"
        })
    signature = calcSignature(user.id)
    rawSessionid = f"userId={user.id}&timestamp={int(time.time())}&signature={signature}&algorithm=sha256"
    sessionid = encode(rawSessionid)
    return jsonify({
        "status": 200,
        "message": "登录成功",
        "sessionid": sessionid,
    })


@userRouter.post("/loginCheck")
async def loginCheck(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId, timestamp = res["userId"], res["timestamp"]
    if time.time() - float(timestamp) > 10800:  # 3小时
        return jsonify({
            "status": -2,
            "message": "登录已过期，请重新登录"
        })
    user = session.query(User).get(userId)
    return jsonify({
        "status": 200,
        "message": "用户已登录",
        "data": {
            "id": user.id,
            "username": user.username,
            "usertype": user.usertype,
        }
    })


@userRouter.post("/getUserInfo")
async def getUserInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    user = session.query(User).get(userId)
    return jsonify({
        "status": 200,
        "message": "用户信息获取成功",
        "user": User.to_json(user)
    })
