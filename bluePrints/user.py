import json
import time
from robyn import SubRouter, jsonify

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkAdminOnly, checkUserAuthority, clearLogs

userRouter = SubRouter(__file__, prefix="/user")


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
    session = Session()
    try:
        user = session.query(User).get(userId)
        return jsonify({
            "status": 200,
            "message": "用户已登录",
            "data": {
                "id": user.id,
                "username": user.username,
                "usertype": user.usertype,
                "authority": user.authority,
            }
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "错误"
        })
    finally:
        session.close()


@userRouter.post("/login")
async def login(request):
    data = request.json()
    username = data["username"]
    session = Session()
    try:
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
        if user.status != 1:
            return jsonify({
                "status": -3,
                "message": "您处于离职状态，暂无法登录"
            })
        signature = calcSignature(user.id)
        rawSessionid = f"userId={user.id}&timestamp={int(time.time())}&signature={signature}&algorithm=sha256"
        sessionid = encode(rawSessionid)
        log = Log(operatorId=user.id, operation="用户登录")
        session.add(log)
        clearLogs()
        session.commit()
        return jsonify({
            "status": 200,
            "message": "登录成功",
            "sessionid": sessionid,
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "错误"
        })
    finally:
        session.close()


@userRouter.post("/getUserInfo")
async def getUserInfo(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    session = Session()
    try:
        user = session.query(User).get(userId)
        return jsonify({
            "status": 200,
            "message": "用户信息获取成功",
            "user": User.to_json(user)
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "错误"
        })
    finally:
        session.close()


@userRouter.post("/register")
async def register(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 1):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    session = Session()
    try:
        form = request.json()["form"]
        form = json.loads(form)
        username = form["username"]
        gender = form["gender"]
        phone = form["phone"]
        address = form["address"]
        departmentId = form["department"]
        schoolId = None
        if departmentId:
            department = session.query(Department).get(departmentId)
            schoolId = department.schoolId
        vocationId = form["vocationId"]
        status = form["status"]
        password = form["password"]
        user = User(username=username, gender=gender, phone=phone, address=address, departmentId=departmentId,
                    schoolId=schoolId,
                    vocationId=vocationId, status=status, usertype=1, clientVisible=1,
                    hashedPassword=User.hashPassword(password))
        log = Log(operatorId=userId, operation=f"添加用户：{username}")

        session.add(user)
        session.add(log)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "用户添加成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "错误"
        })
    finally:
        session.close()


@userRouter.post("/modifyPwd")
async def modifyPwd(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    session = Session()
    try:
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
        session.add(log)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "密码修改成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "错误"
        })
    finally:
        session.close()


@userRouter.post("/getAllUsers")
async def getAllUsers(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    page_index = data.get("pageIndex", 1)  # 当前页码，默认第一页
    page_size = data.get("pageSize", 100000)  # 每页数量，默认全部
    offset = (int(page_index) - 1) * int(page_size)
    name = data.get("name", "")
    schoolId = data.get("schoolId")
    deptId = data.get("deptId")
    session = Session()
    try:
        # 获取分页数据
        query = session.query(User)
        if name:
            query = query.filter(User.username.like(f"%{name}%")).order_by(User.schoolId)
        if schoolId:
            query = query.filter(User.schoolId == schoolId).order_by(User.schoolId)
        if deptId:
            query = query.filter(User.departmentId == deptId).order_by(User.schoolId)
        users = query.offset(offset).limit(page_size).all()
        users = [User.to_json(user) for user in users]
        # 获取总数
        total = query.count()
        return jsonify({
            "status": 200,
            "message": "分页获取成功",
            "users": users,
            "total": total
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"获取用户列表失败：{str(e)}"
        })
    finally:
        session.close()


@userRouter.post("/updateUser")
async def updateUser(request):
    sessionid = request.headers.get("sessionid")
    operatorId = checkSessionid(sessionid).get("userId")
    if not operatorId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(operatorId, 2):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    user_id = data.get("id")

    session = Session()
    try:
        # 查找要更新的用户
        user = session.query(User).get(user_id)
        if not user:
            return jsonify({
                "status": -3,
                "message": "用户不存在"
            })

        # 更新用户信息
        for key, value in data.items():
            if value == "null" or not value:
                continue
            if hasattr(user, key):
                try:
                    setattr(user, key, value)
                except Exception as e:
                    continue

        # 记录操作日志
        log = Log(
            operatorId=operatorId,
            operation=f"更新用户信息：{user.username}"
        )
        session.add(log)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "更新成功"
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            "status": -4,
            "message": f"更新失败：{str(e)}"
        })
    finally:
        session.close()


# 删除用户
@userRouter.post("/deleteUser")
async def deleteUser(request):
    sessionid = request.headers.get("sessionid")
    operatorId = checkSessionid(sessionid).get("userId")
    if not operatorId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(operatorId, 3):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    user_id = data.get("id")

    session = Session()
    try:
        # 查找要删除的用户
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({
                "status": -3,
                "message": "用户不存在"
            })
        if user_id == operatorId:
            return jsonify({
                "status": -6,
                "message": "不能删除自己"
            })
        # 不允许删除超级管理员
        if user.usertype == 6:
            return jsonify({
                "status": -4,
                "message": "不能删除超级管理员"
            })

        # 记录操作日志
        log = Log(
            operatorId=operatorId,
            operation=f"删除用户：{user.username}"
        )
        session.add(log)

        # 删除用户
        session.delete(user)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "删除成功"
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            "status": -5,
            "message": f"删除失败：{str(e)}"
        })
    finally:
        session.close()


@userRouter.post("/initUserPwd")
async def initUserPwd(request):
    sessionid = request.headers.get("sessionid")
    curr_user = checkSessionid(sessionid).get("userId")
    if not curr_user:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(curr_user, 4):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    user_id = data.get("id")

    if not user_id:
        return jsonify({
            "status": 400,
            "message": "缺少用户ID"
        })

    session = Session()
    try:
        # 获取用户信息
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({
                "status": 404,
                "message": "用户不存在"
            })

        user.hashedPassword = User.hashPassword("12345")
        session.commit()

        return jsonify({
            "status": 200,
            "message": "密码初始化成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"密码初始化失败：{str(e)}"
        })
    finally:
        session.close()


@userRouter.post("/getAllVocations")
async def getAllVocations(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    session = Session()
    try:
        vocations = session.query(Role).all()
        vocations = [vocation.to_json() for vocation in vocations]
        return jsonify({
            "status": 200,
            "message": "全部职位获取成功",
            "vocations": vocations,
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "失败"
        })
    finally:
        session.close()


@userRouter.post("/getAllAuthorities")
async def getAllAuthorities(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    session = Session()
    try:
        authorities = session.query(Authority).order_by(Authority.module).all()
        authorities = [authority.to_json() for authority in authorities]
        return jsonify({
            "status": 200,
            "message": "全部权限获取成功",
            "authorities": authorities,
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "失败"
        })
    finally:
        session.close()


# 修改职位权限：限定admin
@userRouter.post("/updateVocationAuthority")
async def updateVocationAuthority(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkAdminOnly(userId, operationLevel="adminOnly"):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    vocationId = data["vocationId"]
    authorities = data["authorities"]
    session = Session()
    try:
        authorities = json.loads(authorities)
        vocation = session.query(Role).get(vocationId)
        vocation.authority = authorities
        session.commit()
        return jsonify({
            "status": 200,
            "message": "职位权限修改成功",
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "messgae": "职位权限修改失败",
        })
    finally:
        session.close()


@userRouter.post("/addVocation")
async def addVocation(request):
    sessionid = request.headers.get("sessionid")
    curr_user = checkSessionid(sessionid).get("userId")
    if not curr_user:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(curr_user, 49):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    name = data.get("name")
    session = Session()
    try:
        vocation = Role(name=name)
        session.add(vocation)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "职位添加成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"密码初始化失败：{str(e)}"
        })
    finally:
        session.close()
