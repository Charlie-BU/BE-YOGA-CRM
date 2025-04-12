import json
import time

from robyn import SubRouter, jsonify

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

    try:
        # 获取总数
        total = session.query(Course).count()

        # 获取分页数据
        courses = session.query(Course).order_by(Course.schoolId, Course.createdTime.desc()) \
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


# TODO: 下面三个路由都需要加日志
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
            classTeacherId=data.get('classTeacherId'),
            teachingAssistantId=data.get('teachingAssistantId'),
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
    course_id = data.get("id")
    if not course_id:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查课程是否存在
        course = session.query(Course).filter(Course.id == course_id).first()
        if not course:
            return jsonify({
                "status": 404,
                "message": "课程不存在"
            })

        # 检查课程名称是否与其他课程重复
        if data.get('name') and data['name'] != course.name:
            existing = session.query(Course).filter(
                Course.name == data['name'],
                Course.id != course_id
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
    course_id = data.get("id")
    if not course_id:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查课程是否存在
        course = session.query(Course).filter(Course.id == course_id).first()
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
