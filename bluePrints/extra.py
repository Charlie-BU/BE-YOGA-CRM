import datetime
import json
import time

from robyn import SubRouter, jsonify
from sqlalchemy import or_

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

extraRouter = SubRouter(__file__, prefix="/extra")


@extraRouter.post("/getClientById")
async def getClientById(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    clientId = data.get("clientId")
    client = session.query(Client).get(clientId)
    return jsonify({
        "status": 200,
        "message": "客户信息获取成功",
        "client": client.to_json(),
    })


# 获取线索公海（不包括已转客户、已预约到店）
@extraRouter.post("/getClueClients")
async def getClueClients(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    page_index = data.get("pageIndex", 1)
    page_size = data.get("pageSize", 10)
    offset = (int(page_index) - 1) * int(page_size)

    # 构建查询
    query = session.query(Client).order_by(Client.createdTime.desc(), Client.clientStatus)

    # 添加筛选条件
    if data.get("name"):
        query = query.filter(Client.name.like(f"%{data['name']}%"))
    if data.get("fromSource"):
        fromSource = json.loads(data["fromSource"])
        if fromSource:  # 修改为支持多选
            query = query.filter(Client.fromSource.in_(fromSource))
    if data.get("gender"):
        query = query.filter(Client.gender == data["gender"])
    if data.get("age"):
        query = query.filter(Client.age == data["age"])
    if data.get("IDNumber"):
        query = query.filter(Client.IDNumber.like(f"%{data['IDNumber']}%"))
    if data.get("phone"):
        query = query.filter(Client.phone.like(f"%{data['phone']}%"))
    if data.get("weixin"):
        query = query.filter(Client.weixin.like(f"%{data['weixin']}%"))
    if data.get("QQ"):
        query = query.filter(Client.QQ.like(f"%{data['QQ']}%"))
    if data.get("douyin"):
        query = query.filter(Client.douyin.like(f"%{data['douyin']}%"))
    if data.get("rednote"):
        query = query.filter(Client.rednote.like(f"%{data['rednote']}%"))
    if data.get("shangwutong"):
        query = query.filter(Client.shangwutong.like(f"%{data['shangwutong']}%"))
    if data.get("address"):
        query = query.filter(Client.address.like(f"%{data['address']}%"))
    if data.get("clientStatus"):
        clientStatus = json.loads(data["clientStatus"])
        if clientStatus:  # 修改为支持多选
            query = query.filter(Client.clientStatus.in_(clientStatus))
    if data.get("startTime"):
        query = query.filter(Client.createdTime >= data["startTime"])
    if data.get("endTime"):
        query = query.filter(Client.createdTime <= data["endTime"])

    if data.get("creatorId"):
        creatorId = json.loads(data["creatorId"])
        if creatorId:
            query = query.filter(Client.creatorId.in_(creatorId))
    if data.get("affiliatedUserId"):
        affiliatedUserId = json.loads(data["affiliatedUserId"])
        if affiliatedUserId:
            query = query.filter(Client.affiliatedUserId.in_(affiliatedUserId))

    # 获取分页数据
    clients = query.offset(offset).limit(page_size).all()
    clients = [Client.to_json(client) for client in clients]

    # 获取总数
    total = query.count()

    return jsonify({
        "status": 200,
        "message": "分页获取成功",
        "clients": clients,
        "total": total
    })


# 获取已转客户、已预约到店
@extraRouter.post("/getClients")
async def getClients(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientStatus = data.get("clientStatus")
    if clientStatus == "null":
        clientStatus = None
    page_index = data.get("pageIndex", 1)
    page_size = data.get("pageSize", 10)
    offset = (int(page_index) - 1) * int(page_size)

    # 基础查询
    query = session.query(Client).filter(Client.clientStatus.in_([3, 4])).order_by(Client.clientStatus,
                                                                                   Client.createdTime.desc())

    # 添加筛选条件
    filters = {
        'name': lambda x: Client.name.like(f"%{x}%"),
        'fromSource': lambda x: Client.fromSource == x,
        'gender': lambda x: Client.gender == x,
        'age': lambda x: Client.age == x,
        'IDNumber': lambda x: Client.IDNumber.like(f"%{x}%"),
        'phone': lambda x: Client.phone.like(f"%{x}%"),
        'weixin': lambda x: Client.weixin.like(f"%{x}%"),
        'QQ': lambda x: Client.QQ.like(f"%{x}%"),
        'douyin': lambda x: Client.douyin.like(f"%{x}%"),
        'rednote': lambda x: Client.rednote.like(f"%{x}%"),
        'shangwutong': lambda x: Client.shangwutong.like(f"%{x}%"),
        'address': lambda x: Client.address.like(f"%{x}%"),
        'appointerId': lambda x: Client.appointerId == x,
        'affiliatedUserName': lambda x: Client.affiliatedUser.username.like(f"%{x}%"),
        # 'appointerName': lambda x: Client.appointerName.like(f"%{x}%"),
        'processStatus': lambda x: Client.processStatus == x,
    }

    # 处理校区：由于schoolId是@property属性，不是SQL字段，直接filter不执行
    if data.get("schoolId"):
        query = query.join(Client.affiliatedUser).filter(User.schoolId == data["schoolId"])

    # 处理日期范围筛选
    if data.get('startTime') and data.get('endTime'):
        query = query.filter(Client.createdTime.between(data['startTime'], data['endTime']))

    if data.get('appointStartDate') and data.get('appointEndDate'):
        query = query.filter(Client.appointDate.between(data['appointStartDate'], data['appointEndDate']))

    if data.get('nextTalkStartDate') and data.get('nextTalkEndDate'):
        query = query.filter(Client.nextTalkDate.between(data['nextTalkStartDate'], data['nextTalkEndDate']))

    # 应用其他筛选条件
    for field, filter_func in filters.items():
        if data.get(field):
            query = query.filter(filter_func(data[field]))

    if clientStatus:
        query = query.filter(Client.clientStatus == clientStatus)

    # 获取分页数据
    clients = query.offset(offset).limit(page_size).all()
    clients = [Client.to_json(client) for client in clients]

    # 获取总数
    total = query.count()

    return jsonify({
        "status": 200,
        "message": "分页获取成功",
        "clients": clients,
        "total": total
    })


# 获取成单客户
@extraRouter.post("/getDealedClients")
async def getDealedClients(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    page_index = data.get("pageIndex", 1)  # 当前页码，默认第一页
    page_size = data.get("pageSize", 10)  # 每页数量，默认10条
    offset = (int(page_index) - 1) * int(page_size)
    name = data.get("name", "")
    # 获取分页数据
    query = session.query(Client).filter(Client.processStatus == 2).order_by(Client.clientStatus,
                                                                             Client.createdTime.desc())
    if name:
        query = query.filter(Client.name.like(f"%{name}%"))
    clients = query.offset(offset).limit(page_size).all()
    clients = [Client.to_json(client) for client in clients]
    # 获取总数
    total = query.count()
    return jsonify({
        "status": 200,
        "message": "分页获取成功",
        "clients": clients,
        "total": total
    })


@extraRouter.post("/getClassStudents")
async def getClassStudents(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    stuId = data.get("stuId")
    student = session.query(Client).get(stuId)
    stuInfo = {
        "id": stuId,
        "name": student.name,
        "gender": student.gender,
        "phone": student.phone,
        "weixin": student.weixin,
        "cooperateTime": student.cooperateTime,
    }
    return jsonify({
        "status": 200,
        "message": "客户信息获取成功",
        "stuInfo": stuInfo,
    })


@extraRouter.post("/updateClient")
async def updateClient(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    client_id = data.get("id")
    try:
        client = session.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                "status": -2,
                "message": "客户不存在"
            })

        uniqueFields = {
            "phone": "电话",
            "weixin": "微信",
            "QQ": "QQ",
            "douyin": "抖音",
            "rednote": "小红书",
            "shangwutong": "商务通"
        }

        # 检查唯一字段是否已被其他客户使用
        for field, field_name in uniqueFields.items():
            if data.get(field) and data[field] != getattr(client, field):  # 只检查非空且已修改的字段
                # 查询是否已存在该字段值的其他客户
                existing_client = session.query(Client).filter(
                    Client.id != client_id,  # 排除当前客户
                    getattr(Client, field) == data[field]
                ).first()

                if existing_client:
                    return jsonify({
                        "status": 400,
                        "message": f"已存在相同{field_name}的客户"
                    })

        # 更新客户信息
        changes = []
        fieldsToSave = {
            "name": "姓名",
            "gender": "性别",
            "age": "年龄",
            "phone": "电话",
            "QQ": "QQ",
            "douyin": "抖音",
            "rednote": "小红书",
            "shangwutong": "商务通",
            "IDNumber": "身份证",
            "address": "地区"
        }
        for key, value in data.items():
            if value == "null" or not value:
                continue
            if hasattr(client, key):
                try:
                    if key == "info":
                        client.info.append(value)
                        changes.append(f"添加备注: {value}")
                        continue

                    old_value = getattr(client, key)
                    if str(old_value) != str(value):  # 确认真的有改动
                        setattr(client, key, value)
                        if key in fieldsToSave.keys():
                            changes.append(f"{fieldsToSave[key]}: {old_value} -> {value}")
                except Exception as e:
                    continue
        logContent = f"更新客户信息：" + "；".join(changes) if changes else "（无修改）"
        log = Log(operatorId=userId,
                  operation=logContent)
        clientLog = ClientLog(clientId=client_id, operatorId=userId, operation=logContent)
        session.add(log)
        session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "更新成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": -3,
            "message": f"更新失败：{str(e)}"
        })


@extraRouter.post("/addClient")
async def addClient(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    requiredFields = ['name', 'fromSource', 'weixin']
    # 检查必填字段
    for field in requiredFields:
        if not data.get(field):
            return jsonify({
                "status": 400,
                "message": f"缺少必填字段：{field}"
            })
    try:
        uniqueFields = {
            "phone": "电话",
            "weixin": "微信",
            "QQ": "QQ",
            "douyin": "抖音",
            "rednote": "小红书",
            "shangwutong": "商务通"
        }

        # 检查唯一字段是否已被使用
        for field, field_name in uniqueFields.items():
            if data.get(field):  # 只检查非空字段
                # 查询是否已存在该字段值的客户
                existing_client = session.query(Client).filter(getattr(Client, field) == data[field]).first()
                if existing_client:
                    return jsonify({
                        "status": 400,
                        "message": f"已存在相同{field_name}的客户"
                    })

        # 添加创建人和创建时间信息
        data['creatorId'] = userId
        # 创建新客户
        new_client = Client(**data)
        session.add(new_client)
        log = Log(operatorId=userId,
                  operation=f"创建新客户：{data['name']}")
        session.add(log)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "添加成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"添加失败：{str(e)}"
        })


@extraRouter.post("/deleteClient")
async def deleteClient(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    client_id = data.get("id")
    if not client_id:
        return jsonify({
            "status": 400,
            "message": "缺少客户ID"
        })
    try:
        client = session.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({
                "status": 404,
                "message": "客户不存在"
            })
        # 删除客户
        session.delete(client)
        logContent = f"删除客户"
        log = Log(operatorId=userId,
                  operation=logContent)
        session.add(log)
        clientLog = ClientLog(clientId=client_id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "删除成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"删除失败：{str(e)}"
        })


@extraRouter.post("/unassignClients")
async def unassignClients(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    client_ids = data.get("ids")
    client_ids = json.loads(client_ids)
    if not client_ids:
        return jsonify({
            "status": 400,
            "message": "缺少客户ID"
        })

    try:
        # 批量更新客户的所属人为空
        session.query(Client).filter(Client.id.in_(client_ids)).update(
            {
                "clientStatus": 1,
                "affiliatedUserId": None
            },
            synchronize_session=False
        )
        log = Log(operatorId=userId,
                  operation=f"取消分配客户：{[client.name for client in session.query(Client).filter(Client.id.in_(client_ids)).all()]}")
        session.add(log)
        for client_id in client_ids:
            logContent = "取消分配"
            clientLog = ClientLog(clientId=client_id, operatorId=userId, operation=logContent)
            session.add(clientLog)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "取消分配成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"取消分配失败：{str(e)}"
        })


@extraRouter.post("/assignClients")
async def assignClients(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    client_ids = data.get("ids")
    client_ids = json.loads(client_ids)
    assigned_user_id = data.get("userId")

    if not client_ids or not assigned_user_id:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 获取被分配的用户信息
        assigned_user = session.query(User).get(assigned_user_id)
        if not assigned_user:
            return jsonify({
                "status": 404,
                "message": "所属人不存在"
            })

        # 批量更新客户的所属人
        session.query(Client).filter(Client.id.in_(client_ids)).update({
            "clientStatus": 2,
            "affiliatedUserId": assigned_user_id
        }, synchronize_session=False)
        log = Log(operatorId=userId,
                  operation=f"分配客户：{[client.name for client in session.query(Client).filter(Client.id.in_(client_ids)).all()]}")
        session.add(log)
        for client_id in client_ids:
            logContent = f"分配客服：{assigned_user.username}"
            clientLog = ClientLog(clientId=client_id, operatorId=userId, operation=logContent)
            session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "分配成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"分配失败：{str(e)}"
        })


# 转客户
@extraRouter.post("/convertToClients")
async def convertToClients(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    ids = data.get("ids")
    ids = json.loads(ids)
    try:
        # 批量更新客户状态
        clients = session.query(Client).filter(Client.id.in_(ids)).all()
        for client in clients:
            client.clientStatus = 3  # 将状态改为正式客户
            client.toClientTime = datetime.now()
            # 记录操作日志
            log = Log(operatorId=userId, operation=f"线索：{client.name}转为正式客户")
            session.add(log)
            logContent = "线索转为正式客户"
            clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
            session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "转换成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"转换失败：{str(e)}"
        })


@extraRouter.post("/submitReserve")
async def submitReserve(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientId = data.get("clientId")
    client = session.query(Client).get(clientId)
    appointerId = data.get("appointerId")
    try:
        appointerId = int(appointerId)
    except Exception:
        appointerId = None
    appointDate = data.get("appointDate")
    if appointDate:
        # 日期格式处理
        appointDate = datetime.strptime(appointDate, '%m/%d/%Y')

    useCombo = json.loads(data.get("useCombo"))
    if useCombo:
        client.comboId = data.get("comboId", None)

    courseIds = data.get("courseIds")
    courseIds = json.loads(courseIds)
    nextTalkDate = data.get("nextTalkDate")
    if nextTalkDate:
        nextTalkDate = datetime.strptime(nextTalkDate, '%m/%d/%Y')
    info = data.get("info")
    try:
        # 允许重复预约
        # if client.clientStatus == 4:
        #     return jsonify({
        #         "status": -2,
        #         "message": "客户已预约"
        #     })
        client.clientStatus = 4
        client.appointerId = appointerId
        client.appointDate = appointDate if appointDate else None
        client.courseIds = courseIds
        client.nextTalkDate = nextTalkDate if nextTalkDate else None
        client.info.append(info)
        client.processStatus = 1
        log = Log(operatorId=userId, operation=f"客户：{client.name}预约到店")
        session.add(log)
        logContent = "客户预约"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "预约成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"预约失败：{str(e)}"
        })


@extraRouter.post("/cancelReserve")
async def cancelReserve(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientId = data.get("clientId")
    client = session.query(Client).get(clientId)

    try:
        # 重置预约相关字段
        if client.clientStatus == 3:
            return jsonify({
                "status": -2,
                "message": "客户未预约"
            })
        client.clientStatus = 3
        client.appointerId = None
        client.appointDate = None
        client.courseIds = None
        client.nextTalkDate = None
        client.processStatus = None
        # 记录操作日志
        log = Log(operatorId=userId, operation=f"客户：{client.name}取消预约")
        session.add(log)
        logContent = "取消预约"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "取消预约成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"取消预约失败：{str(e)}"
        })


# 确认成单 / 签署合同
@extraRouter.post("/confirmCooperation")
async def confirmCooperation(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientId = data.get("clientId")
    contractNo = data.get("contractNo")

    try:
        client = session.query(Client).get(clientId)
        if not client:
            return jsonify({
                "status": 400,
                "message": "客户不存在"
            })

        # 更新客户状态为已成单
        if client.processStatus == 2:
            return jsonify({
                "status": -2,
                "message": "客户已成单"
            })
        client.processStatus = 2
        client.contractNo = contractNo
        client.cooperateTime = datetime.now()

        # 记录操作日志
        log = Log(operatorId=userId, operation=f"客户：{client.name}确认成单，合同编号：{contractNo}")
        session.add(log)
        logContent = f"确认成单，合同编号：{contractNo}"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "签约成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"签约失败：{str(e)}"
        })


@extraRouter.post("/cancelCooperation")
async def cancelCooperation(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientId = data.get("clientId")

    try:
        client = session.query(Client).get(clientId)
        if not client:
            return jsonify({
                "status": 400,
                "message": "客户不存在"
            })

        # 更新客户状态为未成单
        client.processStatus = 1
        client.contractNo = None
        client.cooperateTime = None

        # 记录操作日志
        log = Log(operatorId=userId, operation=f"客户：{client.name}取消成单")
        session.add(log)
        logContent = "取消成单"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "取消成单成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"取消成单失败：{str(e)}"
        })


# 学员毕业
@extraRouter.post("/graduateClient")
async def graduateClient(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientId = data.get("id")

    try:
        client = session.query(Client).get(clientId)
        if not client:
            return jsonify({
                "status": -2,
                "message": "客户不存在"
            })

        if client.clientStatus == 5:
            return jsonify({
                "status": -3,
                "message": "该学员已毕业"
            })

        # 更新客户状态为已毕业
        client.clientStatus = 5

        # 记录操作日志
        log = Log(operatorId=userId, operation=f"学员：{client.name}已毕业")
        session.add(log)
        logContent = "学员毕业"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "操作成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"操作失败：{str(e)}"
        })


# 取消毕业
@extraRouter.post("/cancelGraduate")
async def cancelGraduate(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientId = data.get("id")

    try:
        client = session.query(Client).get(clientId)
        if not client:
            return jsonify({
                "status": -2,
                "message": "客户不存在"
            })

        if client.clientStatus != 5:
            return jsonify({
                "status": -3,
                "message": "客户不是毕业状态"
            })

        # 更新客户状态为已成单（从毕业状态恢复）
        client.clientStatus = 4

        # 记录操作日志
        log = Log(operatorId=userId, operation=f"客户：{client.name}取消毕业")
        session.add(log)
        logContent = "学员取消毕业"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "操作成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"操作失败：{str(e)}"
        })


# 批量导入线索
@extraRouter.post("/batchImportClues")
async def batchImportClues(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clues = data.get("clues")
    clues = json.loads(clues)

    if not clues or not isinstance(clues, list):
        return jsonify({
            "status": 400,
            "message": "无效的导入数据"
        })

    try:
        success_count = 0
        error_count = 0

        # 定义唯一字段及其中文名称
        uniqueFields = {
            "phone": "电话",
            "weixin": "微信",
            "QQ": "QQ",
            "douyin": "抖音",
            "rednote": "小红书",
            "shangwutong": "商务通"
        }
        error_msg = None
        for clue in clues:
            try:
                # 数据转换
                new_clue = {
                    "name": clue.get("* 姓名", ""),
                    "gender": 1 if clue.get("性别") == "男" else 2 if clue.get("性别") == "女" else None,
                    "age": int(clue.get("年龄", 0)) if clue.get("年龄") else None,
                    "IDNumber": clue.get("身份证", ""),
                    "phone": clue.get("电话", ""),
                    "weixin": clue.get("* 微信", ""),
                    "QQ": clue.get("QQ", ""),
                    "douyin": clue.get("抖音", ""),
                    "rednote": clue.get("小红书", ""),
                    "shangwutong": clue.get("商务通", ""),
                    "address": clue.get("地区", ""),
                    "info": clue.get("备注", ""),
                    "clientStatus": 1,  # 线索状态
                    "creatorId": userId
                }

                # 验证必填字段
                if not new_clue["name"] or not new_clue["weixin"]:
                    error_count += 1
                    continue

                # 检查唯一字段是否已被使用
                field_exists = False
                for field, field_name in uniqueFields.items():
                    if new_clue[field]:  # 只检查非空字段
                        # 查询是否已存在该字段值的客户
                        existing_client = session.query(Client).filter(
                            getattr(Client, field) == new_clue[field]).first()
                        if existing_client:
                            error_msg = f"存在{field_name}相同的客户等"
                            field_exists = True
                            break

                if field_exists:
                    error_count += 1
                    continue

                # 创建新线索
                client = Client(**new_clue)
                session.add(client)
                success_count += 1

            except Exception as e:
                error_count += 1
                continue

        session.commit()

        return jsonify({
            "status": 200,
            "message": f"导入完成：成功{success_count}条，失败{error_count}条" + (
                f"。失败原因：{error_msg}" if error_msg else ""),
            "data": {
                "success": success_count,
                "error": error_count
            }
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"导入失败：{str(e)}"
        })


# 客户付款
@extraRouter.post("/submitPayment")
async def submitPayment(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    try:
        amount = int(data.get("amount"))
        # 创建支付记录
        payment = Payment(
            clientId=data.get("clientId"),
            teacherId=data.get("teacherId"),
            amount=amount,
            category=data.get("category"),  # 1为定金，2为尾款，3为其他
            paymentMethod=data.get("paymentMethod"),
            info=data.get("info"),
            paymentDate=datetime.now().date()
        )
        session.add(payment)

        # 记录操作日志
        client = session.query(Client).get(data.get("clientId"))
        teacher = session.query(User).get(data.get("teacherId"))
        payType = "交定金" if data.get("category") == 1 else "交尾款" if data.get("category") == 2 else "付款"
        log = Log(
            operatorId=userId,
            operation=f"客户：{client.name}{payType}{amount}元，负责老师：{teacher.username}"
        )
        session.add(log)
        if amount > 0:
            logContent = f"{payType}{amount}元，负责老师：{teacher.username}"
        else:
            logContent = f"退款{-1 * amount}元，负责老师：{teacher.username}"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "付款成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"付款失败：{str(e)}"
        })


# 获取客户付款记录
@extraRouter.post("/getClientPayments")
async def getClientPayments(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    client_id = data.get("clientId")

    if not client_id:
        return jsonify({
            "status": 400,
            "message": "缺少客户ID"
        })

    try:
        # 获取该客户的所有交易记录
        payments = session.query(Payment).filter(
            Payment.clientId == client_id
        ).order_by(Payment.paymentDate.desc()).all()
        return jsonify({
            "status": 200,
            "payments": [Payment.to_json(payment) for payment in payments]
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取交易记录失败：{str(e)}"
        })


@extraRouter.post("/getPayments")
async def getPayments(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    page_index = data.get("pageIndex", 1)
    page_size = data.get("pageSize", 10)
    paymentType = data.get("paymentType", "all")

    try:
        query = session.query(Payment)

        # 添加筛选条件
        if data.get("schoolId"):
            query = query.join(Payment.teacher).filter(
                User.schoolId == data["schoolId"]
            )
        if paymentType == "income":
            query = query.filter(Payment.amount > 0)
        elif paymentType == "expense":
            query = query.filter(Payment.amount <= 0)

        if data.get("category"):
            query = query.filter(Payment.category == data["category"])

        if data.get("paymentMethod"):
            query = query.filter(Payment.paymentMethod == data["paymentMethod"])

        if data.get("clientName"):
            # 必须用outerjoin，否则默认innerjoin，当没有Payment.client但存在Payment.receiver时无法找到
            query = query.outerjoin(Payment.client).filter(
                or_(
                    Client.name.contains(data["clientName"]),
                    Payment.receiver.contains(data["clientName"])
                )
            )

        if data.get("clientPhone"):
            query = query.join(Payment.client).filter(
                Client.phone.contains(data["clientPhone"])
            )

        if data.get("startTime"):
            query = query.filter(Payment.paymentDate >= data["startTime"])

        if data.get("endTime"):
            query = query.filter(Payment.paymentDate <= data["endTime"])

        total = query.count()
        payments = query.order_by(Payment.paymentDate.desc(), Payment.id.desc()).offset(
            (int(page_index) - 1) * int(page_size)).limit(int(page_size)).all()

        return jsonify({
            "status": 200,
            "payments": [Payment.to_json(payment) for payment in payments],
            "total": total
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": 500,
            "message": f"获取交易记录失败：{str(e)}"
        })


@extraRouter.post("/addPayment")
async def addPayment(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    amount = float(data.get("amount"))
    if not amount or amount == 0:
        return jsonify({
            "status": -2,
            "message": "金额不能等于0"
        })
    try:
        payment = Payment()
        payment.clientId = data.get("clientId") if data.get("clientId") != "null" else None
        payment.receiver = data.get("receiver")
        payment.teacherId = data.get("teacherId")
        payment.amount = amount
        payment.category = data.get("category")
        payment.paymentMethod = data.get("paymentMethod")
        payment.info = data.get("info")
        payment.paymentDate = datetime.now().date()
        payment.creatorId = userId

        session.add(payment)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "添加成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"添加失败：{str(e)}"
        })


@extraRouter.post("/updatePayment")
async def updatePayment(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    payment_id = data.get("id")
    if not payment_id:
        return jsonify({
            "status": 400,
            "message": "缺少ID"
        })
    amount = float(data.get("amount"))
    if not amount or amount == 0:
        return jsonify({
            "status": -2,
            "message": "金额不能为0"
        })
    try:
        payment = session.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return jsonify({
                "status": 404,
                "message": "记录不存在"
            })

        payment.clientId = data.get("clientId") if data.get("clientId") != "null" else None
        payment.receiver = data.get("receiver")
        payment.teacherId = data.get("teacherId")
        payment.amount = amount
        payment.category = data.get("category")
        payment.paymentMethod = data.get("paymentMethod")
        payment.info = data.get("info")

        session.commit()
        return jsonify({
            "status": 200,
            "message": "更新成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"更新失败：{str(e)}"
        })


@extraRouter.post("/deletePayment")
async def deletePayment(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    payment_id = data.get("id")
    if not payment_id:
        return jsonify({
            "status": 400,
            "message": "缺少ID"
        })

    try:
        payment = session.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return jsonify({
                "status": 404,
                "message": "记录不存在"
            })

        session.delete(payment)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "删除成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"删除失败：{str(e)}"
        })


@extraRouter.post("/getLogs")
async def getLogs(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    page_index = data.get("pageIndex", 1)
    page_size = data.get("pageSize", 10)
    offset = (int(page_index) - 1) * int(page_size)

    # 构建查询
    query = session.query(Log).order_by(Log.time.desc())

    # 添加筛选条件
    if data.get("operatorName"):
        query = query.join(User, Log.operatorId == User.id) \
            .filter(User.username.like(f"%{data['operatorName']}%"))
    if data.get("operation"):
        query = query.filter(Log.operation.like(f"%{data['operation']}%"))
    if data.get("startTime"):
        query = query.filter(Log.time >= data["startTime"])
    if data.get("endTime"):
        query = query.filter(Log.time <= data["endTime"])

    # 获取分页数据
    logs = query.offset(offset).limit(page_size).all()
    logs = [log.to_json() for log in logs]

    # 获取总数
    total = query.count()

    return jsonify({
        "status": 200,
        "message": "获取日志成功",
        "logs": logs,
        "total": total
    })


@extraRouter.post("/getClientLogs")
async def getClientLogs(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    clientId = data.get("clientId")
    page_index = data.get("pageIndex", 1)
    page_size = data.get("pageSize", 10)
    offset = (int(page_index) - 1) * int(page_size)
    try:
        # 构建查询
        query = session.query(ClientLog).filter(ClientLog.clientId == clientId).order_by(ClientLog.time.desc())
        # 获取分页数据
        clientLogs = query.offset(offset).limit(page_size).all()
        logs = [log.to_json() for log in clientLogs]

        # 获取总数
        total = query.count()
        return jsonify({
            "status": 200,
            "message": "获取日志成功",
            "logs": logs,
            "total": total
        })
    except Exception as e:
        print(e)
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "日志获取失败"
        })
