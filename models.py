from datetime import datetime
from sqlalchemy import create_engine, ForeignKey, Boolean, Column, Integer, String, Text, DateTime, Date, Float, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.ext.mutable import MutableList
from bcrypt import hashpw, gensalt, checkpw

from config import DATABASE_URI

engine = create_engine(DATABASE_URI, echo=True)
# 数据库表基类
Base = declarative_base()
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
Base.metadata.naming_convention = naming_convention
# 会话，用于通过ORM操作数据库
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = Session()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, nullable=True)
    hashedPassword = Column(Text, nullable=True)
    # 性别：1男 / 2女
    gender = Column(Integer, nullable=True)
    phone = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    # 用户权限级：普通用户1/普通管理员2/超级管理员6
    usertype = Column(Integer, nullable=True, default=1)
    workNum = Column(Text, nullable=True)
    avatarUrl = Column(Text, nullable=True)
    # 所在部门
    departmentId = Column(Integer, ForeignKey("department.id"), nullable=True)
    department = relationship("Department", backref="users")
    # 所在学校
    schoolId = Column(Integer, ForeignKey("school.id"), nullable=True)
    school = relationship("School", backref="users")
    # 职位：1总经理 / 2店长 / 3总监 / 4校长 / 5咨询 / 6老师 / 7助理 / 8员工 / 9新媒体
    vocation = Column(Integer, nullable=True)
    # 人员状态：1在职 / 2离职
    status = Column(Integer, nullable=True)

    @staticmethod  # 静态方法归属于类的命名空间，同时能够在不依赖类的实例的情况下调用
    def hashPassword(password):
        hashedPwd = hashpw(password.encode("utf-8"), gensalt())
        return hashedPwd.decode("utf-8")

    def checkPassword(self, password):
        return checkpw(password.encode("utf-8"), self.hashedPassword.encode("utf-8"))

    def to_json(self):
        data = {
            "id": self.id,
            "username": self.username,
            "gender": self.gender,
            "phone": self.phone,
            "address": self.address,
            "usertype": self.usertype,
            "workNum": self.workNum,
            "avatarUrl": self.avatarUrl,
            "departmentId": self.departmentId,
            "schoolId": self.schoolId,
            "vocation": self.vocation,
            "status": self.status,
        }
        if self.departmentId:
            data["departmentName"] = self.department.name
        if self.schoolId:
            data["schoolName"] = self.school.name
        return data


class Department(Base):
    __tablename__ = "department"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
        }
        return data


class Client(Base):
    __tablename__ = "client"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    #  * 渠道来源：
    #  * 1传统 - 竞价商务通 / 2传统 - 电话 / 3传统 - 推荐 / 4传统 - 进店 / 5传统 - 优化站 /
    #  * 6新电 - 美团 / 7新电 - 点评 / 8新电 - 小红书 / 9新电 - 抖音 / 10新电 - 红推 /
    #  * 11新电 - 公众号 / 12新电 - 视频号 / 13新电 - 快手 / 14新电 - 抖音信息流 / 15新电 - 其他 /
    #  * 16新电 - 北京信息流 / 17新电 - 上海信息流 / 18新电 - 成都信息流 / 19新电 - 广州信息流 /
    #  * 20新电 - 成都红推 / 21新电 - 高德 / 22新电 - 快手信息流 / 23新电 - 上海广点通 /
    #  * 24新电 - 成都广点通 / 25新电 - 小程序 / 26新电 - 电商 / 27会员介绍 / 28合作 /
    #  * 29其他 / 30漏登记
    #  */
    fromSource = Column(Integer, nullable=True)
    gender = Column(Integer, nullable=True)
    age = Column(Integer, nullable=True)
    # 身份证
    IDNumber = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    weixin = Column(Text, nullable=True)
    QQ = Column(Text, nullable=True)
    douyin = Column(Text, nullable=True)
    rednote = Column(Text, nullable=True)
    shangwutong = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    # 状态：1未分配 / 2已分配 / 3转客户
    clientStatus = Column(Integer, nullable=True, default=1)
    # 所属人 / 负责人 / 合作老师
    affiliatedUserId = Column(Integer, ForeignKey("user.id"), nullable=True)
    affiliatedUser = relationship("User", backref="cooperateStudents")
    # 创建人id
    createdUserId = Column(Integer, nullable=True)
    createdTime = Column(DateTime, nullable=True, default=datetime.now)
    # 备注（公海时用）
    info = Column(Text, nullable=True)
    # 预约备注（客户时用）
    detailedInfo = Column(Text, nullable=True)

    # 预约人
    appointerId = Column(Integer, nullable=True)
    # 课程（多个）
    courseIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    # 跟进状态：1未成单 / 2已成单
    processStatus = Column(Integer, nullable=True, default=1)
    # 预约日期
    appointDate = Column(Date, nullable=True)
    # 下次沟通日期
    nextTalkDate = Column(Date, nullable=True)
    # 成单时间
    cooperateTime = Column(DateTime, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "fromSource": self.fromSource,
            "gender": self.gender,
            "age": self.age,
            "IDNumber": self.IDNumber,
            "phone": self.phone,
            "weixin": self.weixin,
            "QQ": self.QQ,
            "douyin": self.douyin,
            "rednote": self.rednote,
            "shangwutong": self.shangwutong,
            "address": self.address,
            "clientStatus": self.clientStatus,
            "affiliatedUserId": self.affiliatedUserId,
            "createdUserId": self.createdUserId,
            "createdTime": self.createdTime,
            "info": self.info,
            "detailedInfo": self.detailedInfo,
            "appointerId": self.appointerId,
            "courseIds": self.courseIds,
            "processStatus": self.processStatus,
            "appointDate": self.appointDate,
            "nextTalkDate": self.nextTalkDate,
            "cooperateTime": self.cooperateTime,
        }
        if self.affiliatedUserId:
            data["affiliatedUserName"] = self.affiliatedUser.username
        return data


class School(Base):
    __tablename__ = "school"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "info": self.info,
        }
        return data


class Course(Base):
    __tablename__ = "course"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    # 分类：1瑜伽课
    category = Column(Text, nullable=True)
    creatorId = Column(Integer, ForeignKey("user.id"), nullable=True)
    # 所属校区
    schoolId = Column(Integer, ForeignKey("school.id"), nullable=True)
    school = relationship("School", backref="courses")
    creator = relationship("User", backref="createdCourses")
    createdTime = Column(DateTime, nullable=True, default=datetime.now)
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "schoolId": self.schoolId,
            "creatorId": self.creatorId,
            "createdTime": self.createdTime,
            "info": self.info,
        }
        if self.creatorId:
            data["creatorName"] = self.creator.username
        if self.schoolId:
            data["schoolName"] = self.school.name
        return data


class Log(Base):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    operatorId = Column(Integer, ForeignKey("user.id"), nullable=False)
    operator = relationship("User", backref="logs")
    operation = Column(Text, nullable=True)
    time = Column(DateTime, default=datetime.now)

    def to_json(self):
        data = {
            "id": self.id,
            "operatorId": self.operatorId,
            "operatorName": self.operator.username,
            "operation": self.operation,
            "time": self.time,
        }
        return data


# 创建所有表（被alembic替代）
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
