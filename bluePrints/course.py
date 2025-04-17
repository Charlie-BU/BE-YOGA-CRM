import json
import time

from robyn import SubRouter, jsonify
from sqlalchemy import func, text

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

courseRouter = SubRouter(__file__, prefix="/course")


@courseRouter.post("/getCourses")
async def getCourses(request):
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
        if schoolId:
            query = session.query(Course).filter(Course.schoolId == schoolId)
        else:
            query = session.query(Course)
        # 获取总数
        total = query.count()

        # 获取分页数据
        courses = query.order_by(Course.schoolId, Course.createdTime.desc()) \
            .offset((int(pageIndex) - 1) * int(pageSize)) \
            .limit(pageSize) \
            .all()

        return jsonify({
            "status": 200,
            "courses": [Course.to_json(course) for course in courses],
            "total": total
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取课程列表失败：{str(e)}"
        })


@courseRouter.post("/getCoursesByIds")
async def getCoursesByIds(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    courseIds = data.get("courseIds", [])
    courseIds = json.loads(courseIds)

    try:
        courses = session.query(Course).filter(Course.id.in_(courseIds)).all()
        return jsonify({
            "status": 200,
            "courses": [course.to_json() for course in courses]
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取课程信息失败：{str(e)}"
        })


@courseRouter.post("/addCourse")
async def addCourse(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    try:
        # 检查必填字段
        required_fields = ['name', 'category', 'schoolId', 'duration', 'price', 'chiefTeacherId']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "status": 400,
                    "message": f"请填写{field}"
                })

        # 检查课程名称是否重复
        existing = session.query(Course).filter(Course.name == data['name']).first()
        if existing:
            return jsonify({
                "status": 400,
                "message": "课程名称已存在"
            })

        # 创建新课程
        new_course = Course(
            name=data['name'],
            category=data['category'],
            schoolId=data['schoolId'],
            duration=data['duration'],
            price=data['price'],
            chiefTeacherId=data['chiefTeacherId'],
            classTeacherId=data.get('classTeacherId') if data.get('classTeacherId') else None,
            teachingAssistantId=data.get('teachingAssistantId') if data.get('teachingAssistantId') else None,
            info=data.get('info', ''),
            creatorId=userId,
            createdTime=datetime.now()
        )
        session.add(new_course)
        log = Log(
            operatorId=userId,
            operation=f"添加课程：{data['name']}"
        )
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


@courseRouter.post("/updateCourse")
async def updateCourse(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    courseId = data.get("id")
    if not courseId:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查课程是否存在
        course = session.query(Course).filter(Course.id == courseId).first()
        if not course:
            return jsonify({
                "status": 404,
                "message": "课程不存在"
            })

        # 检查课程名称是否与其他课程重复
        if data.get('name') and data['name'] != course.name:
            existing = session.query(Course).filter(
                Course.name == data['name'],
                Course.id != courseId
            ).first()
            if existing:
                return jsonify({
                    "status": 400,
                    "message": "课程名称已存在"
                })

        # 更新课程信息
        update_fields = [
            'name', 'category', 'schoolId', 'duration', 'price',
            'chiefTeacherId', 'chiefTeacherName',
            'classTeacherId', 'classTeacherName',
            'teachingAssistantId', 'teachingAssistantName',
            'info'
        ]
        for field in update_fields:
            if field in data:
                if data[field] == "null" or not data[field]:
                    continue
                try:
                    setattr(course, field, data[field])
                except Exception:
                    continue
        log = Log(
            operatorId=userId,
            operation=f"更新课程：{course.name}"
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
            "status": 500,
            "message": f"更新失败：{str(e)}"
        })


@courseRouter.post("/deleteCourse")
async def deleteCourse(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    courseId = data.get("id")
    if not courseId:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查课程是否存在
        course = session.query(Course).filter(Course.id == courseId).first()
        if not course:
            return jsonify({
                "status": 404,
                "message": "课程不存在"
            })

        # TODO: 检查课程是否有关联数据（如学员报名等）

        # 删除课程
        session.delete(course)
        log = Log(
            operatorId=userId,
            operation=f"删除课程：{course.name}"
        )
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


@courseRouter.post("/getAllCombos")
async def getAllCombos(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    try:
        data = request.json()
        pageIndex = data.get('pageIndex', 1)
        pageSize = data.get('pageSize', 10)

        schoolId = data.get('schoolId')
        # 计算分页
        offset = (int(pageIndex) - 1) * int(pageSize)

        if schoolId:
            query = session.query(CourseCombo).filter(CourseCombo.schoolId == schoolId)
        else:
            query = session.query(CourseCombo)
        # 获取总数
        total = query.count()

        # 获取分页数据
        combos = query.offset(offset).limit(pageSize).all()

        return jsonify({
            "status": 200,
            "combos": [combo.to_json() for combo in combos],
            "total": total
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": 500,
            "message": f"获取套餐列表失败：{str(e)}"
        })


@courseRouter.post("/addCombo")
async def addCombo(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    try:
        data = request.json()
        courseIds = data.get('courseIds', [])
        courseIds = json.loads(courseIds)
        new_combo = CourseCombo(
            name=data.get('name'),
            courseIds=courseIds,
            schoolId=data.get('schoolId'),
            price=data.get('price'),
            info=data.get('info'),
        )
        session.add(new_combo)

        # 获取校区名称用于日志
        school = session.query(School).filter(School.id == data.get('schoolId')).first()
        school_name = school.name if school else "未知校区"

        # 记录操作日志
        log = Log(
            operatorId=userId,
            operation=f"新增套餐：{data.get('name')}，所属校区：{school_name}",
        )
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
            "message": f"添加套餐失败：{str(e)}"
        })


@courseRouter.post("/updateCombo")
async def updateCombo(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    try:
        data = request.json()
        combo = session.query(CourseCombo).filter(CourseCombo.id == data.get('id')).first()
        if not combo:
            return jsonify({
                "status": 404,
                "message": "套餐不存在"
            })

        # 记录原始数据用于日志
        old_name = combo.name
        old_school = session.query(School).filter(School.id == combo.schoolId).first()
        old_school_name = old_school.name if old_school else "未知校区"

        courseIds = data.get('courseIds', [])
        courseIds = json.loads(courseIds)
        # 更新数据
        combo.name = data.get('name')
        combo.courseIds = courseIds
        combo.schoolId = data.get('schoolId')
        combo.price = data.get('price')
        combo.info = data.get('info')

        # 获取新校区名称用于日志
        new_school = session.query(School).filter(School.id == data.get('schoolId')).first()
        new_school_name = new_school.name if new_school else "未知校区"

        # 记录操作日志
        log = Log(
            operatorId=userId,
            operation=f"更新套餐：{old_name} -> {data.get('name')}，校区：{old_school_name} -> {new_school_name}",
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
            "status": 500,
            "message": f"更新套餐失败：{str(e)}"
        })


@courseRouter.post("/deleteCombo")
async def deleteCombo(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    try:
        data = request.json()
        combo = session.query(CourseCombo).filter(CourseCombo.id == data.get('id')).first()
        if not combo:
            return jsonify({
                "status": 404,
                "message": "套餐不存在"
            })

        # 记录操作日志
        log = Log(
            operatorId=userId,
            operation=f"删除套餐：{combo.name}"
        )
        session.add(log)

        # 删除套餐
        session.delete(combo)
        session.commit()

        return jsonify({
            "status": 200,
            "message": "删除成功"
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"删除套餐失败：{str(e)}"
        })


@courseRouter.post("/getCourseClients")
async def getCourseClients(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    courseId = data.get("courseId")
    if courseId is None:
        return jsonify({
            "status": -2,
            "message": "缺少 courseId 参数"
        })

    try:
        courseId = int(courseId)

        # 使用数据库函数直接过滤，提高性能
        clients_data = []
        clientsCooperated = session.query(Client).filter(
            Client.processStatus == 2  # 已成单
        ).all()

        for client in clientsCooperated:
            # 检查课程ID是否在客户的课程列表中
            if client.courseIds and courseId in client.courseIds:
                clients_data.append({
                    "id": client.id,
                })
        return jsonify({
            "status": 200,
            "message": "查询成功",
            "total": len(clients_data),
            "clients": clients_data
        })
    except ValueError:
        return jsonify({
            "status": 400,
            "message": "课程ID格式错误"
        })
    except Exception as e:
        print(f"获取课程学员失败: {str(e)}")
        return jsonify({
            "status": 500,
            "message": f"查询失败：{str(e)}"
        })
