from robyn import Robyn, ALLOW_CORS, jsonify, Response

from bluePrints.course import courseRouter
from bluePrints.department import deptRouter
from bluePrints.dorm import dormRouter
from bluePrints.extra import extraRouter
from bluePrints.user import userRouter
from models import User, session

app = Robyn(__file__)
# 生产环境需要注释：使用nginx解决跨域
ALLOW_CORS(app, origins=["*"])

# 注册蓝图
app.include_router(userRouter)
app.include_router(deptRouter)
app.include_router(extraRouter)
app.include_router(courseRouter)
app.include_router(dormRouter)


@app.get("/")
async def index():
    return "Welcome to YOGA CRM"


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8052)
