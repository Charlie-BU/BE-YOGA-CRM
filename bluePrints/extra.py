import json
import time

from robyn import SubRouter, jsonify

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
    page_index = data.get("pageIndex", 1)  # 当前页码，默认第一页
    page_size = data.get("pageSize", 10)  # 每页数量，默认10条
    offset = (int(page_index) - 1) * int(page_size)
    name = data.get("name", "")
    # 获取分页数据
    # query = session.query(Client).filter(Client.clientStatus.in_([1, 2]))
    query = session.query(Client).order_by(Client.clientStatus, Client.createdTime.desc())  # 定为全部客户
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
    # 3为已转客户，4为已预约到店，默认都有
    clientStatus = data.get("clientStatus")
    page_index = data.get("pageIndex", 1)  # 当前页码，默认第一页
    page_size = data.get("pageSize", 10)  # 每页数量，默认10条
    offset = (int(page_index) - 1) * int(page_size)
    name = data.get("name")
    # 获取分页数据
    query = session.query(Client).filter(Client.clientStatus.in_([3, 4])).order_by(Client.clientStatus,
                                                                                   Client.createdTime.desc())
    if clientStatus:
        query = query.filter(Client.clientStatus == clientStatus)
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
        for key, value in data.items():
            if value == "null" or not value:
                continue
            if hasattr(client, key):
                try:
                    setattr(client, key, value)
                except Exception:
                    continue
        log = Log(operatorId=userId,
                  operation=f"更新客户信息：{client.name}")
        session.add(log)
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
    required_fields = ['name', 'fromSource', 'weixin']
    # 检查必填字段
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                "status": 400,
                "message": f"缺少必填字段：{field}"
            })
    try:
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
        log = Log(operatorId=userId,
                  operation=f"删除客户：{client.name}")
        session.add(log)
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
        assigned_user = session.query(User).filter(User.id == assigned_user_id).first()
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
            # 记录操作日志
            log = Log(operatorId=userId, operation=f"线索：{client.name}转为正式客户")
            session.add(log)

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
    appointDate = data.get("appointDate")
    if appointDate:
        # 日期格式处理
        appointDate = datetime.strptime(appointDate, '%m/%d/%Y')

    useCombo = data.get("useCombo")
    if useCombo:
        client.comboId = data.get("comboId", None)

    courseIds = data.get("courseIds")
    courseIds = json.loads(courseIds)
    nextTalkDate = data.get("nextTalkDate")
    if nextTalkDate:
        nextTalkDate = datetime.strptime(nextTalkDate, '%m/%d/%Y')
    detailedInfo = data.get("detailedInfo")
    try:
        if client.clientStatus == 4:
            return jsonify({
                "status": -2,
                "message": "客户已预约"
            })
        client.clientStatus = 4
        client.appointerId = appointerId
        client.appointDate = appointDate if appointDate else None
        client.courseIds = courseIds
        client.nextTalkDate = nextTalkDate if nextTalkDate else None
        client.detailedInfo = detailedInfo
        client.processStatus = 1
        log = Log(operatorId=userId, operation=f"客户：{client.name}预约到店")
        session.add(log)
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
        client.detailedInfo = None
        client.processStatus = None
        # 记录操作日志
        log = Log(operatorId=userId, operation=f"客户：{client.name}取消预约")
        session.add(log)
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
    cooperateTime = data.get("cooperateTime")

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
        client.cooperateTime = datetime.strptime(cooperateTime, '%m/%d/%Y')

        # 记录操作日志
        log = Log(operatorId=userId, operation=f"客户：{client.name}确认成单，合同编号：{contractNo}")
        session.add(log)
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

        for clue in clues:
            try:
                # 数据转换
                new_clue = {
                    "name": clue.get("姓名", ""),
                    "gender": 1 if clue.get("性别") == "男" else 2 if clue.get("性别") == "女" else None,
                    "age": int(clue.get("年龄", 0)) if clue.get("年龄") else None,
                    "IDNumber": clue.get("身份证", ""),
                    "phone": clue.get("电话", ""),
                    "weixin": clue.get("微信", ""),
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

                # 检查是否已存在（根据姓名和微信号）
                existing = session.query(Client).filter(
                    Client.name == new_clue["name"],
                    Client.weixin == new_clue["weixin"]
                ).first()

                if existing:
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
            "message": f"导入完成：成功{success_count}条，失败{error_count}条",
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
        # 创建支付记录
        payment = Payment(
            clientId=data.get("clientId"),
            teacherId=data.get("teacherId"),
            amount=data.get("amount"),
            category=data.get("category"),  # 1为定金，2为尾款，3为其他
            paymentMethod=data.get("paymentMethod"),
            info=data.get("info")
        )
        session.add(payment)

        # 记录操作日志
        client = session.query(Client).get(data.get("clientId"))
        teacher = session.query(User).get(data.get("teacherId"))
        payType = "交定金" if data.get("category") == 1 else "交尾款" if data.get("category") == 2 else "付款"
        log = Log(
            operatorId=userId,
            operation=f"客户：{client.name}{payType}{data.get('amount')}元，负责老师：{teacher.username}"
        )
        session.add(log)
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
        ).order_by(Payment.paymentTime.desc()).all()
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
    isIncome = data.get("isIncome", "true")
    try:
        if isIncome == "true":
            query = session.query(Payment).filter(Payment.amount > 0)
        else:
            query = session.query(Payment).filter(Payment.amount <= 0)
        total = query.count()
        payments = query.order_by(Payment.paymentTime.desc()).offset(
            (int(page_index) - 1) * int(page_size)).limit(int(page_size)).all()

        return jsonify({
            "status": 200,
            "payments": [Payment.to_json(payment) for payment in payments],
            "total": total
        })
    except Exception as e:
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
        payment.paymentTime = datetime.now()
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
