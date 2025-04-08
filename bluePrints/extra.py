import json
import time

from robyn import SubRouter, jsonify

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

extraRouter = SubRouter(__file__, prefix="/extra")


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
    query = session.query(Client).order_by(Client.clientStatus)       # 定为全部客户
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
    # 3为已转客户，4为已预约到店
    clientStatus = data.get("clientStatus", 3)
    page_index = data.get("pageIndex", 1)  # 当前页码，默认第一页
    page_size = data.get("pageSize", 10)  # 每页数量，默认10条
    offset = (int(page_index) - 1) * int(page_size)
    name = data.get("name", "")
    # 获取分页数据
    query = session.query(Client).filter(Client.clientStatus == clientStatus)
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
        data['createdUserId'] = userId
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
            category=data.get("category"),      # 1为定金，2为尾款，3为其他
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