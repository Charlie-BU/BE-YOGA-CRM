import time

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
