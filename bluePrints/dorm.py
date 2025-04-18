import json
import time

from robyn import SubRouter, jsonify
from sqlalchemy import func, text

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

dormRouter = SubRouter(__file__, prefix="/dorm")


# 公寓相关
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
        print("错误！！！", e)
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
            "message": f"删除房间失败：{str(e)}"
        })

# TODO：床位相关
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

        result_beds = []
        for bed in beds:
            # 获取学生信息
            student_name = None
            if bed.studentId:
                student = session.query(Student).filter(Student.id == bed.studentId).first()
                if student:
                    student_name = student.name

            bed_json = {
                "id": bed.id,
                "roomId": bed.roomId,
                "bedNumber": bed.bedNumber,
                "category": bed.category,
                "duration": bed.duration,
                "studentId": bed.studentId,
                "studentName": student_name
            }
            result_beds.append(bed_json)

        return jsonify({
            "status": 200,
            "beds": result_beds
        })
    except Exception as e:
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

    data = request.json()
    roomId = data.get("roomId")
    bedNumber = data.get("bedNumber")
    category = data.get("category")
    duration = data.get("duration")

    try:
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

    data = request.json()
    bed_id = data.get("id")

    try:
        # 删除床位
        session.query(Bed).filter(Bed.id == bed_id).delete()
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


@dormRouter.post("/assignBed")
async def assignBed(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    bed_id = data.get("bedId")
    student_id = data.get("studentId")

    try:
        bed = session.query(Bed).filter(Bed.id == bed_id).first()
        if not bed:
            return jsonify({
                "status": 404,
                "message": "床位不存在"
            })

        # 检查学生是否存在
        if student_id:
            student = session.query(Student).filter(Student.id == student_id).first()
            if not student:
                return jsonify({
                    "status": 404,
                    "message": "学生不存在"
                })

        # 分配床位
        bed.studentId = student_id
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
