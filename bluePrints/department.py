from robyn import SubRouter, jsonify

from models import *
from utils.hooks import calcSignature, encode, checkSessionid, checkUserAuthority

deptRouter = SubRouter(__file__, prefix="/dept")


@deptRouter.post("/getAllDepts")
async def getAllDepts(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    if not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -1,
            "message": "权限不足"
        })
    depts = session.query(Department).all()
    depts = [Department.to_json(dept) for dept in depts]
    return jsonify({
        "status": 200,
        "message": "全部部门获取成功",
        "depts": depts,
    })


@deptRouter.post("/getDeptUsers")
async def getDeptUsers(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    branch_id = data.get("branchId")
    try:
        users = session.query(User).filter(User.departmentId == branch_id).all()
        return jsonify({
            "status": 200,
            "users": [User.to_json(user) for user in users]
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取用户列表失败：{str(e)}"
        })


@deptRouter.post("/getAllSchools")
async def getAllSchools(request):
    sessionid = request.headers["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    if not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -1,
            "message": "权限不足"
        })
    schools = session.query(School).all()
    schools = [School.to_json(school) for school in schools]
    return jsonify({
        "status": 200,
        "message": "全部校区获取成功",
        "schools": schools,
    })


@deptRouter.post("/getSchoolUsers")
async def getSchoolUsers(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    data = request.json()
    schoolId = data.get("schoolId")
    try:
        users = session.query(User).filter(User.schoolId == schoolId).all()
        return jsonify({
            "status": 200,
            "users": [User.to_json(user) for user in users]
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取用户列表失败：{str(e)}"
        })


@deptRouter.post("/getSchoolCourses")
async def getSchoolCourses(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    schoolId = data.get("schoolId")

    try:
        courses = session.query(Course).filter(Course.schoolId == schoolId).all()
        return jsonify({
            "status": 200,
            "courses": [Course.to_json(course) for course in courses]
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"获取课程列表失败：{str(e)}"
        })


@deptRouter.post("/addDept")
async def addDept(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    name = data.get("name")
    info = data.get("info", "")
    schoolId = data.get("schoolId")  # 添加校区ID

    if not name or not schoolId:  # 检查必填字段
        return jsonify({
            "status": 400,
            "message": "部门名称和所属校区不能为空"
        })

    try:
        # 检查校区是否存在
        school = session.query(School).filter(School.id == schoolId).first()
        if not school:
            return jsonify({
                "status": 400,
                "message": "所选校区不存在"
            })

        # 检查部门名称是否已存在
        existing = session.query(Department).filter(Department.name == name).first()
        if existing:
            return jsonify({
                "status": 400,
                "message": "部门名称已存在"
            })

        # 创建新部门
        new_dept = Department(
            name=name,
            info=info,
            schoolId=schoolId  # 添加校区ID
        )
        session.add(new_dept)
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


@deptRouter.post("/updateDept")
async def updateDept(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    dept_id = data.get("id")
    name = data.get("name")
    info = data.get("info", "")
    schoolId = data.get("schoolId")  # 添加校区ID

    if not dept_id or not name or not schoolId:  # 检查必填字段
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查部门是否存在
        dept = session.query(Department).filter(Department.id == dept_id).first()
        if not dept:
            return jsonify({
                "status": 404,
                "message": "部门不存在"
            })

        # 检查校区是否存在
        school = session.query(School).filter(School.id == schoolId).first()
        if not school:
            return jsonify({
                "status": 400,
                "message": "所选校区不存在"
            })

        # 检查新名称是否与其他部门重复
        existing = session.query(Department).filter(
            Department.name == name,
            Department.id != dept_id
        ).first()
        if existing:
            return jsonify({
                "status": 400,
                "message": "部门名称已存在"
            })

        # 更新部门信息
        dept.name = name
        dept.info = info
        dept.schoolId = schoolId  # 添加校区ID
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


@deptRouter.post("/deleteDept")
async def deleteDept(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    dept_id = data.get("id")

    if not dept_id:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查部门是否存在
        dept = session.query(Department).filter(Department.id == dept_id).first()
        if not dept:
            return jsonify({
                "status": 404,
                "message": "部门不存在"
            })

        # 检查是否有用户关联此部门
        users = session.query(User).filter(User.departmentId == dept_id).first()
        if users:
            return jsonify({
                "status": 400,
                "message": "该部门下还有用户，无法删除"
            })

        # 删除部门
        session.delete(dept)
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


@deptRouter.post("/addSchool")
async def addSchool(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    name = data.get("name")
    address = data.get("address")
    info = data.get("info", "")

    if not name or not address:
        return jsonify({
            "status": 400,
            "message": "校区名称和地址不能为空"
        })

    try:
        # 检查校区名称是否已存在
        existing = session.query(School).filter(School.name == name).first()
        if existing:
            return jsonify({
                "status": 400,
                "message": "校区名称已存在"
            })

        # 创建新校区
        new_school = School(
            name=name,
            address=address,
            info=info,
        )
        session.add(new_school)
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


@deptRouter.post("/updateSchool")
async def updateSchool(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    schoolId = data.get("id")
    name = data.get("name")
    address = data.get("address")
    info = data.get("info", "")

    if not schoolId or not name or not address:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查校区是否存在
        school = session.query(School).filter(School.id == schoolId).first()
        if not school:
            return jsonify({
                "status": 404,
                "message": "校区不存在"
            })

        # 检查新名称是否与其他校区重复
        existing = session.query(School).filter(
            School.name == name,
            School.id != schoolId
        ).first()
        if existing:
            return jsonify({
                "status": 400,
                "message": "校区名称已存在"
            })

        # 更新校区信息
        school.name = name
        school.address = address
        school.info = info
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


@deptRouter.post("/deleteSchool")
async def deleteSchool(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    schoolId = data.get("id")

    if not schoolId:
        return jsonify({
            "status": 400,
            "message": "参数错误"
        })

    try:
        # 检查校区是否存在
        school = session.query(School).filter(School.id == schoolId).first()
        if not school:
            return jsonify({
                "status": 404,
                "message": "校区不存在"
            })

        # 检查是否有用户关联此校区
        users = session.query(User).filter(User.schoolId == schoolId).first()
        if users:
            return jsonify({
                "status": 400,
                "message": "该校区下还有用户，无法删除"
            })

        # 删除校区
        session.delete(school)
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


@deptRouter.post("/calcSchoolBudget")
async def calcSchoolBudget(request):
    sessionid = request.headers.get("sessionid")
    userId = checkSessionid(sessionid).get("userId")
    if not userId:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })

    data = request.json()
    schoolId = data.get("schoolId")  # 修改参数名
    startDate = data.get("startDate")
    endDate = data.get("endDate")

    try:
        # 获取学校信息
        school = session.query(School).filter(School.id == schoolId).first()
        if not school:
            return jsonify({
                "status": 400,
                "message": "学校不存在"
            })
        query = session.query(Payment).join(Payment.teacher).filter(
            User.schoolId == schoolId
        )
        paymentsBefore = query.filter(Payment.paymentDate < startDate).all()
        inDuring = query.filter(Payment.paymentDate >= startDate, Payment.paymentDate <= endDate,
                                Payment.amount > 0).all()
        exDuring = query.filter(Payment.paymentDate >= startDate, Payment.paymentDate <= endDate,
                                Payment.amount < 0).all()

        budgetBefore = sum(payment.amount for payment in paymentsBefore)
        incomeDuring = sum(payment.amount for payment in inDuring)
        expanseDuring = sum(payment.amount for payment in exDuring)
        budgetAfter = budgetBefore + incomeDuring + expanseDuring

        return jsonify({
            "status": 200,
            "data": {
                "schoolName": school.name,
                "budgetBefore": budgetBefore,
                "incomeDuring": incomeDuring,
                "expanseDuring": expanseDuring,
                "budgetAfter": budgetAfter,
            }
        })
    except Exception as e:
        session.rollback()
        return jsonify({
            "status": 500,
            "message": f"计算失败：{e}"
        })
