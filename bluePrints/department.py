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
