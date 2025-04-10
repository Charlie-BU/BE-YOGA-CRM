from robyn import Robyn, ALLOW_CORS, jsonify

from bluePrints.course import courseRouter
from bluePrints.department import deptRouter
from bluePrints.extra import extraRouter
from bluePrints.user import userRouter
from models import User, session

app = Robyn(__file__)
ALLOW_CORS(app, origins=["*"])
# 允许请求头携带自定义标识
app.set_response_header("Access-Control-Allow-Headers", "*")

# 注册蓝图
app.include_router(userRouter)
app.include_router(deptRouter)
app.include_router(extraRouter)
app.include_router(courseRouter)


@app.get("/")
async def index():
    return "Welcome to YOGA CRM"


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8052)
