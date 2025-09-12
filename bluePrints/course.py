import json
from datetime import date, datetime
from dateutil import parser
from robyn import SubRouter, jsonify
from sqlalchemy import or_

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority, checkUserVisibleClient

courseRouter = SubRouter(__file__, prefix="/course")


@courseRouter.post("/getCourses")
async def getCourses(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    pageIndex = data.get("pageIndex", 1)
    pageSize = data.get("pageSize", 10000)

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
    finally:
        session.close()


@courseRouter.post("/getCoursesByIds")
async def getCoursesByIds(request):
    session = Session()
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
    finally:
        session.close()


@courseRouter.post("/addCourse")
async def addCourse(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 21):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    try:
        # 检查必填字段
        required_fields = ['name', 'category', 'schoolId', 'duration', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "status": 400,
                    "message": f"请填写{field}"
                })

        # 检查课程名称是否重复
        existing = session.query(Course).filter(Course.name == data['name'],
                                                Course.schoolId == data["schoolId"]).first()
        if existing:
            return jsonify({
                "status": 400,
                "message": "同一校区不能有两门相同的课程"
            })

        # 创建新课程
        new_course = Course(
            name=data['name'],
            category=data['category'],
            schoolId=data['schoolId'],
            duration=data['duration'],
            price=data['price'],
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
    finally:
        session.close()


@courseRouter.post("/updateCourse")
async def updateCourse(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 22):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
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
                Course.schoolId == course.schoolId,
                Course.id != courseId
            ).first()
            if existing:
                return jsonify({
                    "status": 400,
                    "message": "同一校区不能有两门相同的课程"
                })

        # 更新课程信息
        update_fields = [
            'name', 'category', 'schoolId', 'duration', 'price', 'info'
        ]
        for field in update_fields:
            if field in data:
                if data[field] == "null" or not data[field]:
                    if field == "info":
                        setattr(course, field, "")
                    else:
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
    finally:
        session.close()


@courseRouter.post("/deleteCourse")
async def deleteCourse(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 23):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
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
    finally:
        session.close()


@courseRouter.post("/getAllCombos")
async def getAllCombos(request):
    session = Session()
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
    finally:
        session.close()


@courseRouter.post("/addCombo")
async def addCombo(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 24):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
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
    finally:
        session.close()


@courseRouter.post("/updateCombo")
async def updateCombo(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 25):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
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
    finally:
        session.close()


@courseRouter.post("/deleteCombo")
async def deleteCombo(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 26):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
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
    finally:
        session.close()


@courseRouter.post("/getCourseClients")
async def getCourseClients(request):
    session = Session()
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
    finally:
        session.close()


@courseRouter.post("/getLessons")
async def getLessons(request):
    session = Session()
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

    # 获取筛选条件
    name = data.get("name")
    courseName = data.get("courseName")
    schoolId = data.get("schoolId")
    category = data.get("category")
    chiefTeacherName = data.get("chiefTeacherName")
    classTeacherName = data.get("classTeacherName")
    teachingAssistantName = data.get("teachingAssistantName")
    startDate = data.get("startDate")
    endDate = data.get("endDate")

    try:
        query = session.query(Lesson)

        # 添加筛选条件
        if name:
            query = query.filter(Lesson.name.like(f"%{name}%"))
        if courseName:
            query = query.join(Lesson.course).filter(Course.name.like(f"%{courseName}%"))
        if schoolId:
            query = query.join(Lesson.course).filter(Course.schoolId == schoolId)
        if category:
            query = query.join(Lesson.course).filter(Course.category == category)
        if chiefTeacherName:
            query = query.filter(Lesson.chiefTeacherName.like(f"%{chiefTeacherName}%"))
            # chiefTeacher = session.query(User).filter(User.username.like(f"%{chiefTeacherName}%")).first()
            # if chiefTeacher:
            #     query = query.filter(Lesson.chiefTeacherId == chiefTeacher.id)
        if classTeacherName:
            classTeacher = session.query(User).filter(User.username.like(f"%{classTeacherName}%")).first()
            if classTeacher:
                query = query.filter(Lesson.classTeacherId == classTeacher.id)
        if teachingAssistantName:
            query = query.filter(Lesson.teachingAssistantName.like(f"%{teachingAssistantName}%"))
        if startDate:
            query = query.filter(Lesson.startDate >= startDate)
        if endDate:
            query = query.filter(Lesson.startDate <= endDate)

        total = query.count()
        lessons = query.order_by(Lesson.startDate, Lesson.id.desc()) \
            .offset((int(pageIndex) - 1) * int(pageSize)) \
            .limit(pageSize) \
            .all()

        return jsonify({
            "status": 200,
            "lessons": [lesson.to_json() for lesson in lessons],
            "total": total
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取班级列表失败：{str(e)}"
        })
    finally:
        session.close()


@courseRouter.post("/getLessonsByIds")
async def getLessonsByIds(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    lessonIds = data.get("lessonIds", "[]")
    lessonIds = json.loads(lessonIds)

    try:
        lessons = session.query(Lesson).filter(Lesson.id.in_(lessonIds)).all()
        return jsonify({
            "status": 200,
            "courses": [lesson.to_json() for lesson in lessons]
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取班级信息失败：{str(e)}"
        })
    finally:
        session.close()


@courseRouter.post("/getLessonClients")
async def getLessonClients(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    lessonId = data.get("lessonId")
    if lessonId is None:
        return jsonify({
            "status": -2,
            "message": "缺少 lessonId 参数"
        })

    try:
        lessonId = int(lessonId)
        # 使用数据库函数直接过滤，提高性能
        clients_data = []
        clientsCooperated = session.query(Client).filter(
            Client.processStatus == 2  # 已成单
        ).all()

        for client in clientsCooperated:
            # 检查课程ID是否在客户的课程列表中
            if client.lessonIds and lessonId in client.lessonIds:
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
            "message": "班级ID格式错误"
        })
    except Exception as e:
        print(f"获取班级学员失败: {str(e)}")
        return jsonify({
            "status": 500,
            "message": f"查询失败：{str(e)}"
        })
    finally:
        session.close()


@courseRouter.post("/getLessonGraduatedClients")
async def getLessonGraduatedClients(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    lessonId = data.get("lessonId")
    if lessonId is None:
        return jsonify({
            "status": -2,
            "message": "缺少 lessonId 参数"
        })

    try:
        lessonId = int(lessonId)
        # 使用数据库函数直接过滤，提高性能
        clients_data = []
        clientsCooperated = session.query(Client).filter(
            Client.processStatus == 2  # 已成单
        ).all()

        for client in clientsCooperated:
            # 检查课程ID是否在客户的课程列表中
            if client.graduatedLessonIds and lessonId in client.graduatedLessonIds:
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
            "message": "班级ID格式错误"
        })
    except Exception as e:
        print(f"获取班级学员失败: {str(e)}")
        return jsonify({
            "status": 500,
            "message": f"查询失败：{str(e)}"
        })
    finally:
        session.close()


@courseRouter.post("/addLesson")
async def addLesson(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 27):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    try:
        # 检查必填字段
        required_fields = ['name', 'courseId', 'schoolId', 'chiefTeacherName', 'startDate']  # 添加开课日期为必填
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "status": 400,
                    "message": f"请填写{field}"
                })

        # 创建新班级
        # 安全处理：如果没有传值就设 None
        start_date = parser.parse(data['startDate']) if data.get('startDate') else None
        end_date = parser.parse(data['endDate']) if data.get('endDate') else None
        
        new_lesson = Lesson(
            name=data['name'],
            courseId=data['courseId'],
            chiefTeacherName=data['chiefTeacherName'],
            classTeacherId=data.get('classTeacherId') or None,
            teachingAssistantName=data.get('teachingAssistantName'),
            startDate=start_date,   # 转换后的日期
            endDate=end_date,       # 转换后的日期
            info=data.get('info', ''),
            createdTime=datetime.now()  # 添加创建时间
        )
        session.add(new_lesson)
        log = Log(
            operatorId=userId,
            operation=f"添加班级：{data['name']}"
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
    finally:
        session.close()


@courseRouter.post("/updateLesson")
async def updateLesson(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 28):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    lessonId = data.get("id")
    if not lessonId:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查班级是否存在
        lesson = session.query(Lesson).filter(Lesson.id == lessonId).first()
        if not lesson:
            return jsonify({
                "status": 404,
                "message": "班级不存在"
            })

        # 更新班级信息
        update_fields = [
            'name', 'courseId', 'schoolId', 'chiefTeacherName',
            'classTeacherId', 'teachingAssistantName', 'info',
            'startDate', 'endDate'  # 添加开课和结课日期字段
        ]
        for field in update_fields:
            if field in data:
                if data[field] == "null" or not data[field]:
                    if field == "info":
                        setattr(lesson, field, "")
                    else:
                        continue
                try:
                    if field in ['startDate', 'endDate']:
                        # 使用parser.parse处理日期字段
                        parsed_date = parser.parse(data[field])
                        setattr(lesson, field, parsed_date)
                    else:
                        setattr(lesson, field, data[field])
                except Exception:
                    continue
        log = Log(
            operatorId=userId,
            operation=f"更新班级：{lesson.name}"
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
    finally:
        session.close()


@courseRouter.post("/deleteLesson")
async def deleteLesson(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 29):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    lessonId = data.get("id")
    if not lessonId:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查班级是否存在
        lesson = session.query(Lesson).filter(Lesson.id == lessonId).first()
        if not lesson:
            return jsonify({
                "status": 404,
                "message": "班级不存在"
            })

        # TODO：检查班级是否有关联的学员

        # 删除班级
        session.delete(lesson)
        log = Log(
            operatorId=userId,
            operation=f"删除班级：{lesson.name}"
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
    finally:
        session.close()


# 获取可加入班级的学员
@courseRouter.post("/getQualifiedStudents")
async def getQualifiedStudents(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    # 当前班级所属课程
    lessonCourseId = data.get("lessonCourseId")
    if not lessonCourseId:
        return jsonify({
            "status": 400,
            "message": "参数不完整"
        })
    lessonCourseId = int(lessonCourseId)
    query = session.query(Client).filter(Client.processStatus == 2,
                                         Client.courseIds.contains(lessonCourseId))
    # 权限分割
    tag, schoolId, deptId = checkUserVisibleClient(userId)
    match tag:
        case 1:  # 本人相关
            query = query.filter(
                or_(Client.affiliatedUserId == userId, Client.creatorId == userId, Client.appointerId == userId))
        case 2:  # 本校区
            teacher_ids = [tid for (tid,) in session.query(User.id).filter(User.schoolId == schoolId)]
            query = query.filter(
                or_(Client.affiliatedUserId.in_(teacher_ids), Client.creatorId.in_(teacher_ids),
                    Client.appointerId.in_(teacher_ids)))
        case 3:  # 本部门
            teacher_ids = [tid for (tid,) in session.query(User.id).filter(User.departmentId == deptId)]
            query = query.filter(
                or_(Client.affiliatedUserId.in_(teacher_ids), Client.creatorId.in_(teacher_ids),
                    Client.appointerId.in_(teacher_ids)))
        case 4:  # 全部
            pass
        case _:
            return jsonify({
                "status": -2,
                "message": "未限定范围"
            })
    # 获取分页数据
    clients = query.order_by(Client.clientStatus, Client.createdTime.desc()).all()

    clients = [Client.to_json(client) for client in clients]
    session.close()
    return jsonify({
        "status": 200,
        "message": "可加入班级学员获取成功",
        "clients": clients
    })


# 班级添加学员
@courseRouter.post("/addStudent")
async def addStudent(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 30):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    lessonId = data.get("courseId")
    studentId = data.get("studentId")

    if not all([lessonId, studentId]):
        return jsonify({
            "status": -2,
            "message": "参数不完整"
        })

    try:
        lessonId = int(lessonId)
        studentId = int(studentId)
        # 获取课程信息
        lesson = session.query(Lesson).get(lessonId)
        if not lesson:
            return jsonify({
                "status": -3,
                "message": "班级不存在"
            })

        # 获取学员信息
        client = session.query(Client).get(studentId)
        if not client:
            return jsonify({
                "status": -4,
                "message": "学员不存在"
            })

        # 检查学员是否已经在课程中
        if lessonId in (client.lessonIds or []):
            return jsonify({
                "status": -5,
                "message": "该学员已在班级中"
            })

        # 添加课程ID到学员的课程列表中
        if not client.lessonIds:
            client.lessonIds = []
        client.lessonIds.append(lessonId)

        logContent = f"班级：{lesson.name}添加学员"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
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
    finally:
        session.close()


# 班级移除学员
@courseRouter.post("/removeStudent")
async def removeStudent(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 31):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    stuId = data.get("stuId")
    lessonId = data.get("lessonId")

    if not all([stuId, lessonId]):
        return jsonify({
            "status": -2,
            "message": "参数不完整"
        })

    try:
        lessonId = int(lessonId)
        # 获取学员信息
        client = session.query(Client).get(stuId)
        if not client:
            return jsonify({
                "status": -3,
                "message": "学员不存在"
            })
        # 店长可以移除本校区数据，其他人只能移除自己所属的数据
        user = session.query(User).get(userId)
        if user.usertype == 1:
            if user.vocationId == 2:
                if client.schoolId != user.schoolId:
                    return jsonify({
                        "status": -5,
                        "message": "您只能移除您所在校区的学员"
                    })
            else:
                if client.creatorId != userId and client.affiliatedUserId != userId and client.appointerId != userId:
                    return jsonify({
                        "status": -6,
                        "message": "您只能移除所属于您的学员"
                    })

        # 从学员的课程列表中移除该课程
        if client.lessonIds and lessonId in client.lessonIds:
            client.lessonIds.remove(lessonId)
            logContent = f"课程：{session.query(Lesson).get(lessonId).name}移除学员"
            clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
            session.add(clientLog)
            session.commit()
            return jsonify({
                "status": 200,
                "message": "移除成功"
            })
        else:
            return jsonify({
                "status": -4,
                "message": "该学员未参加此课程"
            })

    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"移除失败：{str(e)}"
        })
    finally:
        session.close()


# 班级学员毕业
@courseRouter.post("/graduateClient")
async def graduateClient(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 15):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    stuId = data.get("clientId")
    lessonId = data.get("lessonId")

    if not all([stuId, lessonId]):
        return jsonify({
            "status": -2,
            "message": "参数不完整"
        })

    try:
        lessonId = int(lessonId)
        # 获取学员信息
        client = session.query(Client).get(stuId)
        if not client:
            return jsonify({
                "status": -3,
                "message": "学员不存在"
            })

        if not client.graduatedLessonIds:
            client.graduatedLessonIds = []
        if lessonId in client.graduatedLessonIds:
            return jsonify({
                "status": -4,
                "message": "该学员在该课程已毕业，无法重复操作"
            })
        client.graduatedLessonIds.append(lessonId)

        logContent = f"课程：{session.query(Lesson).get(lessonId).name}毕业"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "毕业成功"
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"毕业失败：{str(e)}"
        })
    finally:
        session.close()


# 班级学员取消毕业
@courseRouter.post("/ungraduateClient")
async def ungraduateClient(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    if not checkUserAuthority(userId, 15):
        return jsonify({
            "status": -2,
            "message": "无权限进行该操作"
        })
    data = request.json()
    stuId = data.get("clientId")
    lessonId = data.get("lessonId")

    if not all([stuId, lessonId]):
        return jsonify({
            "status": -2,
            "message": "参数不完整"
        })

    try:
        lessonId = int(lessonId)
        # 获取学员信息
        client = session.query(Client).get(stuId)
        if not client:
            return jsonify({
                "status": -3,
                "message": "学员不存在"
            })

        if not client.graduatedLessonIds:
            client.graduatedLessonIds = []
        if lessonId not in client.graduatedLessonIds:
            return jsonify({
                "status": -4,
                "message": "该学员尚未毕业，无法取消"
            })
        client.graduatedLessonIds.remove(lessonId)

        logContent = f"课程：{session.query(Lesson).get(lessonId).name}取消毕业"
        clientLog = ClientLog(clientId=client.id, operatorId=userId, operation=logContent)
        session.add(clientLog)
        session.commit()
        return jsonify({
            "status": 200,
            "message": "取消毕业成功"
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"取消毕业失败：{str(e)}"
        })
    finally:
        session.close()


# 获取学生课程信息
@courseRouter.post("/getStudentCourses")
async def getStudentCourses(request):
    session = Session()
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    stuId = data.get("stuId")
    try:
        student = session.query(Client).get(stuId)
        # 提取课程和课程记录
        courseIds = set(student.courseIds or [])
        lessonIds = student.lessonIds or []
        lessons = session.query(Lesson).filter(Lesson.id.in_(lessonIds)).all()

        lessonCourseMap = {lesson.courseId: lesson for lesson in lessons}
        lessonCourseIds = set(lessonCourseMap.keys())
        today = date.today()

        # 分类
        ongoingCourseIds = {
            cid for cid, lesson in lessonCourseMap.items()
            if (lesson.endDate and lesson.startDate <= today <= lesson.endDate) or (
                    not lesson.endDate and lesson.startDate <= today)
        }

        notStartedCourseIds = courseIds - lessonCourseIds
        finishedCourseIds = courseIds - ongoingCourseIds - notStartedCourseIds

        # 一次性查出所有涉及的课程
        allRelatedCourseIds = courseIds
        courses = session.query(Course).filter(Course.id.in_(allRelatedCourseIds)).all()
        courseIdNameMap = {c.id: c.name for c in courses}

        # 构造结果
        finishedCourseNames = "，".join([courseIdNameMap[cid] for cid in finishedCourseIds if cid in courseIdNameMap])
        ongoingCourseNames = "，".join([courseIdNameMap[cid] for cid in ongoingCourseIds if cid in courseIdNameMap])
        notStartedCourseNames = "，".join(
            [courseIdNameMap[cid] for cid in notStartedCourseIds if cid in courseIdNameMap])

        return jsonify({
            "status": 200,
            "message": "学生课程信息获取成功",
            "finishedCourseNames": finishedCourseNames,
            "ongoingCourseNames": ongoingCourseNames,
            "notStartedCourseNames": notStartedCourseNames
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": "学生课程信息获取失败"
        })
    finally:
        session.close()
