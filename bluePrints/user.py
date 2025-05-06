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


@userRouter.post("/getCustomerServiceSummaryData")
async def getCustomerServiceSummaryData(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    startDate = data.get("startDate")
    endDate = data.get("endDate")

    try:
        users = session.query(User).order_by(User.schoolId).all()
        allData = []
        for user in users:
            # 分配给当前客服的客户
            hisClients = user.cooperateStudents
            # 已转客户的（加）- 修改日期比较逻辑
            convertedToClients = [
                hisClient for hisClient in hisClients
                if hisClient.clientStatus >= 3
                   and (startDate <= hisClient.toClientTime.strftime(
                    '%Y-%m-%d') <= endDate if startDate and endDate else True)
            ]
            # 已成单的（报）- 修改日期比较逻辑
            dealedClients = [
                hisClient for hisClient in hisClients
                if hisClient.processStatus == 2
                   and (startDate <= hisClient.cooperateTime.strftime(
                    '%Y-%m-%d') <= endDate if startDate and endDate else True)
            ]

            shanghaiCount = len([client for client in dealedClients if client.schoolId == 2])
            beijingCount = len([client for client in dealedClients if client.schoolId == 4])
            guangzhouCount = len([client for client in dealedClients if client.schoolId == 3])
            chengduCount = len([client for client in dealedClients if client.schoolId == 1])
            totalToClient = len(convertedToClients)
            totalDealed = len(dealedClients)

            bwAdd = len([client for client in convertedToClients if client.fromSource == 1])
            bwSignup = len([client for client in dealedClients if client.fromSource == 1])
            redAdd = len([client for client in convertedToClients if client.fromSource in [10, 20]])
            redSignup = len([client for client in dealedClients if client.fromSource in [10, 20]])
            infoAdd = len([client for client in convertedToClients if client.fromSource in [14, 16, 17, 18, 19, 22]])
            infoSignup = len([client for client in dealedClients if client.fromSource in [14, 16, 17, 18, 19, 22]])
            dpAdd = len([client for client in convertedToClients if client.fromSource == 7])
            dpSignup = len([client for client in dealedClients if client.fromSource == 7])
            phoneAdd = len([client for client in convertedToClients if client.fromSource == 2])
            phoneSignup = len([client for client in dealedClients if client.fromSource == 2])
            xhsAdd = len([client for client in convertedToClients if client.fromSource == 8])
            xhsSignup = len([client for client in dealedClients if client.fromSource == 8])
            dyAdd = len([client for client in convertedToClients if client.fromSource in [9, 14]])
            dySignup = len([client for client in dealedClients if client.fromSource in [9, 14]])
            referAdd = len([client for client in convertedToClients if client.fromSource == 3])
            referSignup = len([client for client in dealedClients if client.fromSource == 3])
            selfAdd = len([client for client in convertedToClients if client.fromSource == 4])
            selfSignup = len([client for client in dealedClients if client.fromSource == 4])
            mpAdd = len([client for client in convertedToClients if client.fromSource == 11])
            mpSignup = len([client for client in dealedClients if client.fromSource == 11])
            videoAdd = len([client for client in convertedToClients if client.fromSource == 12])
            videoSignup = len([client for client in dealedClients if client.fromSource == 12])

            allData.append({
                "userId": user.id,
                "username": user.username,
                "schoolName": user.school.name,
                "shanghaiCount": shanghaiCount,
                "beijingCount": beijingCount,
                "guangzhouCount": guangzhouCount,
                "chengduCount": chengduCount,
                "totalToClient": totalToClient,
                "totalDealed": totalDealed,
                "bwAdd": bwAdd,
                "bwSignup": bwSignup,
                "redAdd": redAdd,
                "redSignup": redSignup,
                "infoAdd": infoAdd,
                "infoSignup": infoSignup,
                "dpAdd": dpAdd,
                "dpSignup": dpSignup,
                "phoneAdd": phoneAdd,
                "phoneSignup": phoneSignup,
                "xhsAdd": xhsAdd,
                "xhsSignup": xhsSignup,
                "dyAdd": dyAdd,
                "dySignup": dySignup,
                "referAdd": referAdd,
                "referSignup": referSignup,
                "selfAdd": selfAdd,
                "selfSignup": selfSignup,
                "mpAdd": mpAdd,
                "mpSignup": mpSignup,
                "videoAdd": videoAdd,
                "videoSignup": videoSignup,
            })
        return jsonify({
            "status": 200,
            "message": "数据获取成功",
            "allData": allData
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取数据失败：{str(e)}"
        })


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
#         # 构建基础查询
#         base_query = session.query(
#             User.id,
#             User.username,
#             School.name.label('schoolName')
#         ).join(School, User.schoolId == School.id)
#
#         # 构建时间过滤条件
#         date_filter = and_(
#             Client.cooperateTime >= startDate if startDate else text('1=1'),
#             Client.cooperateTime <= endDate if endDate else text('1=1')
#         )
#
#         # 修改 case 语句语法
#         base_query = base_query.add_columns(
#             # 城市报名统计
#             func.count(case((Client.schoolId == 2, 1))).label('shanghaiCount'),
#             func.count(case((Client.schoolId == 4, 1))).label('beijingCount'),
#             func.count(case((Client.schoolId == 3, 1))).label('guangzhouCount'),
#             func.count(case((Client.schoolId == 1, 1))).label('chengduCount'),
#
#             # 总体统计
#             func.count(Client.id).label('totalToClient'),
#             func.sum(case((Client.processStatus == 2, 1))).label('totalDealed'),
#
#             # 各渠道统计
#             func.count(case((Client.fromSource == 1, 1))).label('bwAdd'),
#             func.sum(case((and_(Client.fromSource == 1, Client.processStatus == 2), 1))).label('bwSignup'),
#
#             func.count(case((Client.fromSource.in_([10, 20]), 1))).label('redAdd'),
#             func.sum(case((and_(Client.fromSource.in_([10, 20]), Client.processStatus == 2), 1))).label('redSignup'),
#
#             func.count(case((Client.fromSource.in_([14, 16, 17, 18, 19, 22]), 1))).label('infoAdd'),
#             func.sum(case((and_(Client.fromSource.in_([14, 16, 17, 18, 19, 22]), Client.processStatus == 2), 1))).label('infoSignup'),
#
#             func.count(case((Client.fromSource == 7, 1))).label('dpAdd'),
#             func.sum(case((and_(Client.fromSource == 7, Client.processStatus == 2), 1))).label('dpSignup'),
#
#             func.count(case((Client.fromSource == 2, 1))).label('phoneAdd'),
#             func.sum(case((and_(Client.fromSource == 2, Client.processStatus == 2), 1))).label('phoneSignup'),
#
#             func.count(case((Client.fromSource == 8, 1))).label('xhsAdd'),
#             func.sum(case((and_(Client.fromSource == 8, Client.processStatus == 2), 1))).label('xhsSignup'),
#
#             func.count(case((Client.fromSource.in_([9, 14]), 1))).label('dyAdd'),
#             func.sum(case((and_(Client.fromSource.in_([9, 14]), Client.processStatus == 2), 1))).label('dySignup'),
#
#             func.count(case((Client.fromSource == 3, 1))).label('referAdd'),
#             func.sum(case((and_(Client.fromSource == 3, Client.processStatus == 2), 1))).label('referSignup'),
#
#             func.count(case((Client.fromSource == 4, 1))).label('selfAdd'),
#             func.sum(case((and_(Client.fromSource == 4, Client.processStatus == 2), 1))).label('selfSignup'),
#
#             func.count(case((Client.fromSource == 11, 1))).label('mpAdd'),
#             func.sum(case((and_(Client.fromSource == 11, Client.processStatus == 2), 1))).label('mpSignup'),
#
#             func.count(case((Client.fromSource == 12, 1))).label('videoAdd'),
#             func.sum(case((and_(Client.fromSource == 12, Client.processStatus == 2), 1))).label('videoSignup')
#         )
#
#         # 应用过滤条件并分组
#         final_query = base_query.outerjoin(
#             Client,
#             and_(
#                 User.id == Client.id,
#                 date_filter
#             )
#         ).group_by(
#             User.id,
#             User.username,
#             School.name
#         )
#
#         # 执行查询
#         results = final_query.all()
#
#         # 转换结果为字典列表
#         allData = []
#         for row in results:
#             data = row._asdict()
#             # 将 None 值转换为 0
#             for key in data:
#                 if data[key] is None:
#                     data[key] = 0
#             allData.append(data)
#
#         return jsonify({
#             "status": 200,
#             "message": "数据获取成功",
#             "allData": allData
#         })
#
#     except Exception as e:
#         return jsonify({
#             "status": 500,
#             "message": f"获取数据失败：{str(e)}"
#         })


@userRouter.post("/getDateSummaryDataPerDay")
async def getDateSummaryDataPerDay(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    date = data.get("date")
    try:
        # 获取当天的数据
        day_start = f"{date} 00:00:00"
        day_end = f"{date} 23:59:59"

        # 查询当天转化的客户
        convertedToClients = session.query(Client).filter(
            Client.clientStatus >= 3,
            Client.toClientTime.between(day_start, day_end)
        ).all()

        # 查询当天成单的客户
        dealedClients = session.query(Client).filter(
            Client.processStatus == 2,
            Client.cooperateTime.between(day_start, day_end)
        ).all()

        # 统计各城市数据
        shanghaiCount = len([client for client in dealedClients if client.schoolId == 2])
        beijingCount = len([client for client in dealedClients if client.schoolId == 4])
        guangzhouCount = len([client for client in dealedClients if client.schoolId == 3])
        chengduCount = len([client for client in dealedClients if client.schoolId == 1])

        # 统计总数
        totalToClient = len(convertedToClients)
        totalDealed = len(dealedClients)

        # 统计各渠道数据
        bwAdd = len([client for client in convertedToClients if client.fromSource == 1])
        bwSignup = len([client for client in dealedClients if client.fromSource == 1])
        redAdd = len([client for client in convertedToClients if client.fromSource in [10, 20]])
        redSignup = len([client for client in dealedClients if client.fromSource in [10, 20]])
        infoAdd = len([client for client in convertedToClients if client.fromSource in [14, 16, 17, 18, 19, 22]])
        infoSignup = len([client for client in dealedClients if client.fromSource in [14, 16, 17, 18, 19, 22]])
        dpAdd = len([client for client in convertedToClients if client.fromSource == 7])
        dpSignup = len([client for client in dealedClients if client.fromSource == 7])
        phoneAdd = len([client for client in convertedToClients if client.fromSource == 2])
        phoneSignup = len([client for client in dealedClients if client.fromSource == 2])
        xhsAdd = len([client for client in convertedToClients if client.fromSource == 8])
        xhsSignup = len([client for client in dealedClients if client.fromSource == 8])
        dyAdd = len([client for client in convertedToClients if client.fromSource in [9, 14]])
        dySignup = len([client for client in dealedClients if client.fromSource in [9, 14]])
        referAdd = len([client for client in convertedToClients if client.fromSource == 3])
        referSignup = len([client for client in dealedClients if client.fromSource == 3])
        selfAdd = len([client for client in convertedToClients if client.fromSource == 4])
        selfSignup = len([client for client in dealedClients if client.fromSource == 4])
        mpAdd = len([client for client in convertedToClients if client.fromSource == 11])
        mpSignup = len([client for client in dealedClients if client.fromSource == 11])
        videoAdd = len([client for client in convertedToClients if client.fromSource == 12])
        videoSignup = len([client for client in dealedClients if client.fromSource == 12])

        data = {
            "date": date,
            "shanghaiCount": shanghaiCount,
            "beijingCount": beijingCount,
            "guangzhouCount": guangzhouCount,
            "chengduCount": chengduCount,
            "totalToClient": totalToClient,
            "totalDealed": totalDealed,
            "bwAdd": bwAdd,
            "bwSignup": bwSignup,
            "redAdd": redAdd,
            "redSignup": redSignup,
            "infoAdd": infoAdd,
            "infoSignup": infoSignup,
            "dpAdd": dpAdd,
            "dpSignup": dpSignup,
            "phoneAdd": phoneAdd,
            "phoneSignup": phoneSignup,
            "xhsAdd": xhsAdd,
            "xhsSignup": xhsSignup,
            "dyAdd": dyAdd,
            "dySignup": dySignup,
            "referAdd": referAdd,
            "referSignup": referSignup,
            "selfAdd": selfAdd,
            "selfSignup": selfSignup,
            "mpAdd": mpAdd,
            "mpSignup": mpSignup,
            "videoAdd": videoAdd,
            "videoSignup": videoSignup,
        }

        return jsonify({
            "status": 200,
            "message": "数据获取成功",
            "data": data
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": 500,
            "message": f"获取数据失败：{str(e)}"
        })