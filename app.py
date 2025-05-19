import json
from math import isnan

from robyn import Robyn, ALLOW_CORS

from bluePrints.course import courseRouter
from bluePrints.department import deptRouter
from bluePrints.dorm import dormRouter
from bluePrints.extra import extraRouter
from bluePrints.user import userRouter
from models import User, session, Client

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


# @app.get("/importClues")
# async def importClues():
#     import pandas as pd
#     from datetime import datetime
#
#     # 读取Excel文件
#     df = pd.read_excel('clues.xlsx')
#
#     # 只处理英文字段的映射
#     field_mapping = {
#         'name': 'name',
#         'gender': 'gender',
#         'age': 'age',
#         'phone': 'phone',
#         'weixin': 'weixin',
#         'IDNumber': 'IDNumber',
#         'QQ': 'QQ',
#         'douyin': 'douyin',
#         'rednote': 'rednote',
#         'shangwutong': 'shangwutong',
#         'address': 'address',
#         'fromSource': 'fromSource',
#         'clientStatus': 'clientStatus',
#         'createdTime': 'createdTime',
#         'processStatus': 'processStatus',
#         'info': 'info',
#         "affiliatedUserId": "affiliatedUserId",
#     }
#
#     success_count = 0
#     error_count = 0
#
#     for _, row in df.iterrows():
#         try:
#             # 创建新的客户记录
#             client_data = {}
#             for excel_field, db_field in field_mapping.items():
#
#                 value = row[excel_field]
#                 if excel_field in df.columns:
#                     if pd.isna(value):
#                         client_data[db_field] = None
#                         continue
#
#                     if excel_field == "gender":
#                         client_data[db_field] = 1 if row[excel_field] == "男" else 2
#                         continue
#                     if excel_field == "info":
#                         client_data[db_field] = [str(row[excel_field])]
#                         continue
#                     if excel_field == "processStatus" and not row[excel_field]:
#                         client_data[db_field] = 1
#                         continue
#                     if excel_field == "createdTime":
#                         from dateutil import parser
#                         client_data[db_field] = parser.parse(row[excel_field])
#                         continue
#                     client_data[db_field] = row[excel_field]
#
#
#             # 创建新的Client对象
#             client = Client(**client_data)
#             session.add(client)
#             success_count += 1
#
#         except Exception as e:
#             print(f'导入失败：{str(e)}')
#             error_count += 1
#             continue
#
#     try:
#         # 提交所有更改
#         session.commit()
#         return f"导入完成：成功 {success_count} 条，失败 {error_count} 条"
#     except Exception as e:
#         session.rollback()
#         return f"导入失败：{str(e)}"


# @app.get("/importTeachers")
# async def importTeachers():
#     def import_teachers_from_json(file_path):
#         with open(file_path, 'r', encoding='utf-8') as f:
#             teachers_data = json.load(f)
#
#         for teacher_data in teachers_data:
#             # 创建新用户
#             teacher = User(
#                 username=teacher_data['username'],
#                 hashedPassword=User.hashPassword('12345'),  # 设置默认密码
#                 departmentId=teacher_data['departmentId'],
#                 vocationId=teacher_data['role'],
#                 phone=teacher_data['phone'],
#                 workNum=teacher_data.get('workNum'),
#                 status=1  # 设置默认状态为1
#             )
#
#             # 添加到会话
#             session.add(teacher)
#         try:
#             # 提交会话
#             session.commit()
#             print(f'{file_path} 导入成功')
#         except Exception as e:
#             session.rollback()
#             print(f'{file_path} 导入失败：{str(e)}')
#
#     import_teachers_from_json('.json')
#
#     return "SUCCESS"


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8052)
