from robyn import Robyn, ALLOW_CORS, jsonify

from bluePrints.user import userRouter
from models import User, session

app = Robyn(__file__)
ALLOW_CORS(app, origins=["*"])

# 注册蓝图
app.include_router(userRouter)


@app.get("/")
async def index():
    return "Welcome to YOGA CRM"


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8052)
