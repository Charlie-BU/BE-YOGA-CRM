import json
import time

from robyn import SubRouter, jsonify

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

extraRouter = SubRouter(__file__, prefix="/extra")


# 获取线索公海（不包括已转客户）
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
    query = session.query(Client)
    if name:
        query = query.filter(Client.name.like(f"%{name}%"))
    clients = query.filter(Client.clientStatus != 3).offset(offset).limit(page_size).all()
    clients = [Client.to_json(client) for client in clients]
    # 获取总数
    total = query.count()
    return jsonify({
        "status": 200,
        "message": "分页获取成功",
        "clients": clients,
        "total": total
    })


# 获取已转客户
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
    page_index = data.get("pageIndex", 1)  # 当前页码，默认第一页
    page_size = data.get("pageSize", 10)  # 每页数量，默认10条
    offset = (int(page_index) - 1) * int(page_size)
    name = data.get("name", "")
    # 获取分页数据
    query = session.query(Client)
    if name:
        query = query.filter(Client.name.like(f"%{name}%"))
    clients = query.filter(Client.clientStatus == 3).offset(offset).limit(page_size).all()
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
                setattr(client, key, value)
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
