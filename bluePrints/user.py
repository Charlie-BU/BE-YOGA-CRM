import json
import time

from robyn import SubRouter, jsonify

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

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
    log = Log(operatorId=user.id, operation="用户登录")
    try:
        session.add(log)
        session.commit()
    except Exception:
        session.rollback()
    return jsonify({
        "status": 200,
        "message": "登录成功",
        "sessionid": sessionid,
    })


@userRouter.post("/loginCheck")
async def loginCheck(request):
    sessionid = request.headers["sessionid"]
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
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    user = session.query(User).get(userId)
    return jsonify({
        "status": 200,
        "message": "用户信息获取成功",
        "user": User.to_json(user)
    })


@userRouter.post("/register")
async def register(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    if not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -1,
            "message": "权限不足"
        })
    form = request.json()["form"]
    form = json.loads(form)
    username = form["username"]
    gender = form["gender"]
    phone = form["phone"]
    address = form["address"]
    department = form["department"]
    vocation = form["vocation"]
    status = form["status"]
    usertype = form["usertype"]
    password = form["password"]
    user = User(username=username, gender=gender, phone=phone, address=address, departmentId=department,
                vocation=vocation, status=status, usertype=usertype, hashedPassword=User.hashPassword(password))
    log = Log(operatorId=userId, operation=f"添加用户：{username}")
    try:
        session.add(user)
        session.add(log)
        session.commit()
    except Exception:
        session.rollback()
    return jsonify({
        "status": 200,
        "message": "用户添加成功"
    })


@userRouter.post("/modifyPwd")
async def modifyPwd(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    user = session.query(User).get(userId)
    if not user:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    form = request.json()["form"]
    form = json.loads(form)
    oldPwd = form["oldPwd"]
    if not user.checkPassword(oldPwd):
        return jsonify({
            "status": -2,
            "message": "旧密码输入错误"
        })
    newPwd = form["newPwd"]
    user.hashedPassword = User.hashPassword(newPwd)
    log = Log(operatorId=user.id, operation="修改密码")
    try:
        session.add(log)
        session.commit()
    except Exception:
        session.rollback()
    return jsonify({
        "status": 200,
        "message": "密码修改成功"
    })
