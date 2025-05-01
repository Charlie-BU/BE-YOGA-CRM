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
        signature = calcSignature(user.id)
        rawSessionid = f"userId={user.id}&timestamp={int(time.time())}&signature={signature}&algorithm=sha256"
        sessionid = encode(rawSessionid)
        log = Log(operatorId=user.id, operation="用户登录")

        session.add(log)
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
    try:
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
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "错误"
        })


@userRouter.post("/getUserInfo")
async def getUserInfo(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
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
    departmentId = form["department"]
    schoolId = None
    if departmentId:
        department = session.query(Department).get(departmentId)
        schoolId = department.schoolId
    vocation = form["vocation"]
    status = form["status"]
    usertype = form["usertype"]
    password = form["password"]
    user = User(username=username, gender=gender, phone=phone, address=address, departmentId=departmentId,
                schoolId=schoolId,
                vocation=vocation, status=status, usertype=usertype, hashedPassword=User.hashPassword(password))
    log = Log(operatorId=userId, operation=f"添加用户：{username}")
    try:
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


@userRouter.post("/modifyPwd")
async def modifyPwd(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
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
    try:
        # 获取分页数据
        query = session.query(User)
        if name:
            query = query.filter(User.username.like(f"%{name}%")).order_by(User.schoolId)
        if schoolId:
            query = query.filter(User.schoolId == schoolId).order_by(User.schoolId)
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
        return jsonify({
            "status": 500,
            "message": f"获取用户列表失败：{str(e)}"
        })


@userRouter.post("/updateUser")
async def updateUser(request):
    sessionid = request.headers.get("sessionid")
    operatorId = checkSessionid(sessionid).get("userId")
    if not operatorId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    user_id = data.get("id")

    try:
        # 获取操作者信息，检查权限
        operator = session.query(User).get(operatorId)
        if not operator or operator.usertype <= 1:
            return jsonify({
                "status": -2,
                "message": "无权限进行此操作"
            })

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

    data = request.json()
    user_id = data.get("id")

    try:
        # 获取操作者信息，检查权限
        operator = session.query(User).get(operatorId)
        if not operator or operator.usertype <= 1:
            return jsonify({
                "status": -2,
                "message": "无权限进行此操作"
            })

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


@userRouter.post("/initUserPwd")
async def initUserPwd(request):
    sessionid = request.headers.get("sessionid")
    curr_user = checkSessionid(sessionid).get("userId")
    if not curr_user:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    # 检查当前用户权限
    curr_user_info = session.query(User).get(curr_user)
    if not curr_user_info or curr_user_info.usertype <= 1:
        return jsonify({
            "status": 403,
            "message": "无权限执行此操作"
        })

    data = request.json()
    user_id = data.get("id")

    if not user_id:
        return jsonify({
            "status": 400,
            "message": "缺少用户ID"
        })

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

# TODO
# @userRouter.post("/getCustomerServiceSummaryData")
# async def getCustomerServiceSummaryData(request):
#     sessionid = request.headers.get("sessionid")
#     userId = checkSessionid(sessionid).get("userId")
#     if not userId:
#         return jsonify({
#             "status": -1,
#             "message": "用户未登录"
#         })
#
#     data = request.json()
#     startDate = data.get("startDate")
#     endDate = data.get("endDate")
#
#     try:
#         users = session.query(User).order_by(User.schoolId).all()
#
#         # 构建查询条件
#         query = session.query(
#             User.id,
#             User.username,
#             User.schoolName,
#             func.count(case([(Customer.city == '上海', 1)])).label('shanghaiCount'),
#             func.count(case([(Customer.city == '北京', 1)])).label('beijingCount'),
#             func.count(case([(Customer.city == '广州', 1)])).label('guangzhouCount'),
#             func.count(case([(Customer.city == '成都', 1)])).label('chengduCount'),
#             # 总体数据
#             func.count(Customer.id).label('totalWechat'),
#             func.sum(case([(Customer.status == 'signed', 1)], else_=0)).label('totalSignup'),
#             # 商务通数据
#             func.count(case([(Customer.source == 'business', 1)])).label('bwAdd'),
#             func.sum(case([(and_(Customer.source == 'business', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'bwSignup'),
#             # 红推数据
#             func.count(case([(Customer.source == 'red', 1)])).label('redAdd'),
#             func.sum(case([(and_(Customer.source == 'red', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'redSignup'),
#             # 信息流数据
#             func.count(case([(Customer.source == 'info', 1)])).label('infoAdd'),
#             func.sum(case([(and_(Customer.source == 'info', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'infoSignup'),
#             # 点评数据
#             func.count(case([(Customer.source == 'dianping', 1)])).label('dpAdd'),
#             func.sum(case([(and_(Customer.source == 'dianping', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'dpSignup'),
#             # 电话数据
#             func.count(case([(Customer.source == 'phone', 1)])).label('phoneAdd'),
#             func.sum(case([(and_(Customer.source == 'phone', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'phoneSignup'),
#             # 小红书数据
#             func.count(case([(Customer.source == 'xiaohongshu', 1)])).label('xhsAdd'),
#             func.sum(case([(and_(Customer.source == 'xiaohongshu', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'xhsSignup'),
#             # 抖音数据
#             func.count(case([(Customer.source == 'douyin', 1)])).label('dyAdd'),
#             func.sum(case([(and_(Customer.source == 'douyin', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'dySignup'),
#             # 推荐/介绍数据
#             func.count(case([(Customer.source == 'referral', 1)])).label('referAdd'),
#             func.sum(case([(and_(Customer.source == 'referral', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'referSignup'),
#             # 自己进店数据
#             func.count(case([(Customer.source == 'self', 1)])).label('selfAdd'),
#             func.sum(case([(and_(Customer.source == 'self', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'selfSignup'),
#             # 公众号数据
#             func.count(case([(Customer.source == 'wechat', 1)])).label('mpAdd'),
#             func.sum(case([(and_(Customer.source == 'wechat', Customer.status == 'signed'), 1)], else_=0)).label(
#                 'mpSignup'),
#             # 视频号数据
#             func.count(case([(Customer.source == 'video', 1)])).label('videoAdd'),
#             func.count(case([(Customer.source == 'video2', 1)])).label('videoAdd2')
#         ).join(Customer, User.id == Customer.userId)
#
#         # 添加时间筛选条件
#         if startDate and endDate:
#             query = query.filter(and_(
#                 Customer.createTime >= startDate,
#                 Customer.createTime <= endDate
#             ))
#
#         # 按用户分组
#         query = query.group_by(User.id)
#
#         # 执行查询
#         results = query.all()
#
#         # 转换结果为字典列表
#         allData = []
#         for result in results:
#             data_dict = {
#                 'userId': result.id,
#                 'username': result.username,
#                 'schoolName': result.schoolName,
#                 'shanghaiCount': result.shanghaiCount,
#                 'beijingCount': result.beijingCount,
#                 'guangzhouCount': result.guangzhouCount,
#                 'chengduCount': result.chengduCount,
#                 'totalWechat': result.totalWechat,
#                 'totalSignup': result.totalSignup,
#                 'bwAdd': result.bwAdd,
#                 'bwSignup': result.bwSignup,
#                 'redAdd': result.redAdd,
#                 'redSignup': result.redSignup,
#                 'infoAdd': result.infoAdd,
#                 'infoSignup': result.infoSignup,
#                 'dpAdd': result.dpAdd,
#                 'dpSignup': result.dpSignup,
#                 'phoneAdd': result.phoneAdd,
#                 'phoneSignup': result.phoneSignup,
#                 'xhsAdd': result.xhsAdd,
#                 'xhsSignup': result.xhsSignup,
#                 'dyAdd': result.dyAdd,
#                 'dySignup': result.dySignup,
#                 'referAdd': result.referAdd,
#                 'referSignup': result.referSignup,
#                 'selfAdd': result.selfAdd,
#                 'selfSignup': result.selfSignup,
#                 'mpAdd': result.mpAdd,
#                 'mpSignup': result.mpSignup,
#                 'videoAdd': result.videoAdd,
#                 'videoAdd2': result.videoAdd2
#             }
#             allData.append(data_dict)
#
#         return jsonify({
#             "status": 200,
#             "message": "获取数据成功",
#             "allData": allData
#         })
#
#     except Exception as e:
#         return jsonify({
#             "status": 500,
#             "message": f"获取数据失败：{str(e)}"
#         })
