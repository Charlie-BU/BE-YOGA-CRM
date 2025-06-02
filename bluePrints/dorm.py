import json
import time
from datetime import timedelta

from robyn import SubRouter, jsonify
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

dormRouter = SubRouter(__file__, prefix="/dorm")


# 公寓相关
@dormRouter.post("/getDormInfoByBedId")
async def getDormInfoByBedId(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    bed_id = data.get("bedId")

    try:
        # 获取床位信息，包括关联的房间和公寓信息
        bed = session.query(Bed).get(bed_id)
        if not bed:
            return jsonify({
                "status": 404,
                "message": "床位不存在"
            })

        room = session.query(Room).get(bed.roomId)
        if not room:
            return jsonify({
                "status": 404,
                "message": "房间不存在"
            })
        dormitory = session.query(Dormitory).get(room.dormitoryId)

        return jsonify({
            "status": 200,
            "dorm": dormitory.to_json(),
            "room": room.to_json(),
            "bed": bed.to_json()
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"获取住宿信息失败：{str(e)}"
        })


@dormRouter.post("/getDormitories")
async def getDormitories(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    pageIndex = data.get("pageIndex", 1)
    pageSize = data.get("pageSize", 10)
    schoolId = data.get("schoolId")

    try:
        # 构建查询
        if schoolId:
            query = session.query(Dormitory).filter(Dormitory.schoolId == schoolId)
        else:
            query = session.query(Dormitory)

        # 权限分割
        user = session.query(User).get(userId)
        if user.usertype == 1:
            query = session.query(Dormitory).filter(Dormitory.schoolId == user.schoolId)
        # 获取总数
        total = query.count()
        # 获取分页数据
        dormitories = query.order_by(Dormitory.id) \
            .offset((int(pageIndex) - 1) * int(pageSize)) \
            .limit(pageSize) \
            .all()

        return jsonify({
            "status": 200,
            "dormitories": [dorm.to_json() for dorm in dormitories],
            "total": total
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"获取公寓列表失败：{str(e)}"
        })


@dormRouter.post("/addDormitory")
async def addDormitory(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 38):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    name = data.get("name")
    category = data.get("category")
    schoolId = data.get("schoolId")

    try:
        # 创建新公寓
        new_dormitory = Dormitory(
            name=name,
            category=category,
            schoolId=schoolId
        )
        session.add(new_dormitory)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "添加公寓成功",
            "id": new_dormitory.id
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"添加公寓失败：{str(e)}"
        })


@dormRouter.post("/updateDormitory")
async def updateDormitory(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 39):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    dormitory_id = data.get("id")
    name = data.get("name")
    category = data.get("category")
    schoolId = data.get("schoolId")

    try:
        dormitory = session.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
        if not dormitory:
            return jsonify({
                "status": 404,
                "message": "公寓不存在"
            })

        # 更新公寓信息
        dormitory.name = name
        dormitory.category = category
        dormitory.schoolId = schoolId
        session.commit()

        return jsonify({
            "status": 200,
            "message": "更新公寓成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"更新公寓失败：{str(e)}"
        })


@dormRouter.post("/deleteDormitory")
async def deleteDormitory(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 40):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    dormitory_id = data.get("id")

    try:
        # 查找关联的房间
        rooms = session.query(Room).filter(Room.dormitoryId == dormitory_id).all()

        # 删除关联的床位
        for room in rooms:
            session.query(Bed).filter(Bed.roomId == room.id).delete()

        # 删除房间
        session.query(Room).filter(Room.dormitoryId == dormitory_id).delete()

        # 删除公寓
        session.query(Dormitory).filter(Dormitory.id == dormitory_id).delete()

        session.commit()
        return jsonify({
            "status": 200,
            "message": "删除公寓成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"删除公寓失败：{str(e)}"
        })


# 房间相关
@dormRouter.post("/getRooms")
async def getRooms(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    dormitoryId = data.get("dormitoryId")

    try:
        # 获取指定公寓的所有房间
        rooms = session.query(Room).filter(Room.dormitoryId == dormitoryId).all()
        return jsonify({
            "status": 200,
            "rooms": [room.to_json() for room in rooms]
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"获取房间列表失败：{str(e)}"
        })


@dormRouter.post("/addRoom")
async def addRoom(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 41):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    dormitoryId = data.get("dormitoryId")
    roomNumber = data.get("roomNumber")
    building = data.get("building")
    maxBeds = data.get("maxBeds", 0)

    try:
        # 创建新房间
        new_room = Room(
            dormitoryId=dormitoryId,
            roomNumber=roomNumber,
            building=building,
            maxBeds=maxBeds
        )
        session.add(new_room)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "添加房间成功",
            "id": new_room.id
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"添加房间失败：{str(e)}"
        })


@dormRouter.post("/updateRoom")
async def updateRoom(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 42):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    room_id = data.get("id")
    roomNumber = data.get("roomNumber")
    building = data.get("building")
    maxBeds = data.get("maxBeds")

    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return jsonify({
                "status": 404,
                "message": "房间不存在"
            })

        # 更新房间信息
        room.roomNumber = roomNumber
        room.building = building
        room.maxBeds = maxBeds
        session.commit()

        return jsonify({
            "status": 200,
            "message": "更新房间成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"更新房间失败：{str(e)}"
        })


@dormRouter.post("/deleteRoom")
async def deleteRoom(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 43):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    room_id = data.get("id")

    try:
        # 删除关联的床位
        session.query(Bed).filter(Bed.roomId == room_id).delete()

        # 删除房间
        session.query(Room).filter(Room.id == room_id).delete()

        session.commit()
        return jsonify({
            "status": 200,
            "message": "删除房间成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"当前房间存在床位有人入住，无法删除"
        })


# 床位相关
@dormRouter.post("/getBeds")
async def getBeds(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    roomId = data.get("roomId")

    try:
        # 获取指定房间的所有床位
        beds = session.query(Bed).filter(Bed.roomId == roomId).all()
        return jsonify({
            "status": 200,
            "beds": [bed.to_json() for bed in beds]
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"获取床位列表失败：{str(e)}"
        })


@dormRouter.post("/addBed")
async def addBed(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 44):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    roomId = data.get("roomId")
    bedNumber = data.get("bedNumber")
    category = data.get("category")
    duration = data.get("duration")

    try:
        room = session.query(Room).get(roomId)
        if not room:
            return jsonify({
                "status": 404,
                "message": "房间不存在"
            })
        if room.beds and len(room.beds) >= room.maxBeds:
            return jsonify({
                "status": -2,
                "message": "当前房间床位数已达最大床位数"
            })
        # 创建新床位
        new_bed = Bed(
            roomId=roomId,
            bedNumber=bedNumber,
            category=category,
            duration=duration
        )
        session.add(new_bed)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "添加床位成功",
            "id": new_bed.id
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"添加床位失败：{str(e)}"
        })


@dormRouter.post("/updateBed")
async def updateBed(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 45):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    bed_id = data.get("id")
    bedNumber = data.get("bedNumber")
    category = data.get("category")
    duration = data.get("duration")

    try:
        bed = session.query(Bed).filter(Bed.id == bed_id).first()
        if not bed:
            return jsonify({
                "status": 404,
                "message": "床位不存在"
            })

        # 更新床位信息
        bed.bedNumber = bedNumber
        bed.category = category
        bed.duration = duration
        session.commit()

        return jsonify({
            "status": 200,
            "message": "更新床位成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"更新床位失败：{str(e)}"
        })


@dormRouter.post("/deleteBed")
async def deleteBed(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 46):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    bed_id = data.get("id")

    try:
        bed = session.query(Bed).get(bed_id)
        if not bed:
            return jsonify({
                "status": 404,
                "message": "床位不存在"
            })
        if bed.clients:
            return jsonify({
                "status": -2,
                "message": "当前房间有人入住，无法删除"
            })
        # 删除床位
        session.delete(bed)
        log = Log(operatorId=userId, operation="删除床位")
        session.add(log)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "删除床位成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"删除床位失败：{str(e)}"
        })


# 获取未入住的成单客户
@dormRouter.post("/getUncheckedDealedClients")
async def getUncheckedDealedClients(request):
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
    try:
        # 获取分页数据
        query = session.query(Client).filter(
            Client.processStatus == 2,
            Client.bedId.is_(None)
        ).order_by(
            Client.clientStatus,
            Client.createdTime.desc()
        )

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
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "错误"
        })


@dormRouter.post("/assignBed")
async def assignBed(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 47):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    bed_id = data.get("bedId")
    student_id = data.get("studentId")

    try:
        bed = session.query(Bed).filter(Bed.id == bed_id).first()
        if not bed or not student_id:
            return jsonify({
                "status": 404,
                "message": "参数错误"
            })

        student = session.query(Client).get(student_id)
        if not student:
            return jsonify({
                "status": 404,
                "message": "学生不存在"
            })

        # 分配床位
        student.bedId = bed_id
        student.bedCheckInDate = datetime.now().date()
        log = Log(operatorId=userId, operation=f"学员：{student.name}入住")
        session.add(log)
        logContent = "学员入住宿舍"
        clientLog = ClientLog(clientId=student.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "床位分配成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"床位分配失败：{str(e)}"
        })


@dormRouter.post("/checkOut")
async def checkOut(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 48):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    bed_id = data.get("bedId")

    try:
        # 获取床位信息
        bed = session.query(Bed).filter(Bed.id == bed_id).first()
        if not bed:
            return jsonify({
                "status": 404,
                "message": "床位不存在"
            })

        # 获取当前入住的学员信息
        student = session.query(Client).filter(Client.bedId == bed_id).first()
        if not student:
            return jsonify({
                "status": 404,
                "message": "该床位没有入住学员"
            })

        # 记录学员姓名用于日志
        student_name = student.name

        # 清除学员的床位信息
        student.bedId = None
        student.bedCheckInDate = None

        # 添加操作日志
        log = Log(operatorId=userId, operation=f"学员：{student_name}离住")
        session.add(log)
        logContent = "学员离住"
        clientLog = ClientLog(clientId=student.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "离住成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"离住失败：{str(e)}"
        })


# 获取已超期的床位和学员
@dormRouter.post("/getOverdueBeds")
async def getOverdueBeds(request):
    sessionid = request.headers.get("sessionid")
    user_info = checkSessionid(sessionid)
    userId = user_info.get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    try:
        today = datetime.now().date()
        # 预加载 clients，防止 lazy load
        beds = session.query(Bed).options(joinedload(Bed.clients)).filter(Bed.clients is not None).all()
        result = []
        for bed in beds:
            if not bed.clients:
                continue  # 安全检查
            client = bed.clients[-1]  # 默认取最后入住者
            check_in_date = client.bedCheckInDate
            duration_weeks = bed.duration or 0
            expected_checkout = check_in_date + timedelta(weeks=duration_weeks)

            if today > expected_checkout:
                overdue_days = (today - expected_checkout).days
                result.append({
                    "bedId": bed.id,
                    "clientId": client.id,
                    "clientName": client.name,
                    "dormName": bed.room.dormitory.name,
                    "roomNumber": bed.room.roomNumber,
                    "bedNumber": bed.bedNumber,
                    "bedCheckInDate": check_in_date,
                    "overdueDays": overdue_days
                })
        return jsonify({
            "status": 200,
            "result": result
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"获取失败：{str(e)}"
        })