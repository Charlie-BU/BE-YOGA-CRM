from datetime import datetime
from sqlalchemy import create_engine, ForeignKey, Boolean, Column, Integer, Text, DateTime, Date, Float, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.ext.mutable import MutableList
from bcrypt import hashpw, gensalt, checkpw

from config import DATABASE_URI

# 配置连接池参数，增加连接池大小和最大溢出数
engine = create_engine(
    DATABASE_URI, 
    echo=True,
    pool_size=20,  # 默认连接池大小
    max_overflow=30,  # 最大溢出连接数
    pool_timeout=60,  # 连接超时时间
    pool_recycle=3600  # 连接回收时间，防止连接被数据库关闭
)
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


# session = Session()


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
    # 职位
    vocationId = Column(Integer, ForeignKey("role.id"), nullable=True)
    vocation = relationship("Role", backref="users")

    @property
    def vocationName(self):
        if self.vocationId:
            return self.vocation.name
        return ""

    @property
    def authority(self):
        if self.vocationId:
            return self.vocation.authority
        return []

    # 人员状态：1在职 / 2离职
    status = Column(Integer, nullable=True)
    # 可见线索状态：1本人相关 / 2本校区 / 3本部门 / 4全部
    clientVisible = Column(Integer, nullable=True, default=1)

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
            "vocationId": self.vocationId,
            "vocationName": self.vocationName,
            "authority": self.authority,
            "status": self.status,
            "clientVisible": self.clientVisible,
        }
        if self.departmentId:
            data["departmentName"] = self.department.name
        if self.schoolId:
            data["schoolName"] = self.school.name
        return data


# 职位
class Role(Base):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    authority = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "authority": self.authority,
        }
        return data


# 权限
# 注意⚠️：此表内容通常不允许修改
class Authority(Base):
    __tablename__ = "authority"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    module = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "module": self.module,
        }
        return data


class Department(Base):
    __tablename__ = "department"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    # 所属校区
    schoolId = Column(Integer, ForeignKey("school.id"), nullable=True)
    school = relationship("School", backref="departments")
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "schoolId": self.schoolId,
            "info": self.info,
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
    # 状态：1未分配 / 2已分配 / 3转客户 / 4已预约到店 / 5已毕业
    clientStatus = Column(Integer, nullable=True, default=1)
    # 所属人 / 负责人 / 合作老师
    affiliatedUserId = Column(Integer, ForeignKey("user.id"), nullable=True)
    affiliatedUser = relationship("User", backref="cooperateStudents")
    # 创建人
    creatorId = Column(Integer, nullable=True)

    @property
    def creatorName(self):
        session = Session()
        creator = session.query(User).get(self.creatorId)
        if not creator:
            return ""
        session.close()
        return creator.username

    createdTime = Column(DateTime, nullable=True, default=datetime.now)
    # 客户备注
    info = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])

    # 转客户时间
    toClientTime = Column(DateTime, nullable=True)

    # 接待人
    appointerId = Column(Integer, nullable=True)

    @property
    def appointerName(self):
        session = Session()
        appointer = session.query(User).get(self.appointerId)
        if not appointer:
            return ""
        session.close()
        return appointer.username

    # 所在校区
    @property
    def schoolId(self):
        session = Session()
        try:
            affiliatedUser = session.query(User).get(self.affiliatedUserId)
            if affiliatedUser:
                return affiliatedUser.schoolId
            appointer = session.query(User).get(self.appointerId)
            if appointer and appointer.schoolId:
                return appointer.schoolId
            creator = session.query(User).get(self.creatorId)
            if creator and creator.schoolId:
                return creator.schoolId
            return None
        finally:
            session.close()

    @property
    def schoolName(self):
        session = Session()
        try:
            appointer = session.query(User).get(self.appointerId)
            if appointer and appointer.schoolId:
                return appointer.school.name
            affiliatedUser = session.query(User).get(self.affiliatedUserId)
            if affiliatedUser:
                return affiliatedUser.school.name
            creator = session.query(User).get(self.creatorId)
            if creator and creator.schoolId:
                return creator.school.name
            return ""
        finally:
            session.close()

    # 课程（多个）
    courseIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    # 套餐，可有可无
    comboId = Column(Integer, nullable=True)

    @property
    def courseNames(self):
        session = Session()
        if not self.courseIds or len(self.courseIds) == 0:
            return ""
        courses = [session.query(Course).get(id) for id in self.courseIds]
        if courses:
            courseNames = [course.name for course in courses if course is not None]
            return "，".join(courseNames)
        session.close()
        return ""

    # 班级
    lessonIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    # 已毕业的班级
    graduatedLessonIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    # 跟进状态：1未成单 / 2已成单
    processStatus = Column(Integer, nullable=True, default=1)
    # 预约日期
    appointDate = Column(Date, nullable=True)
    # 下次沟通日期
    nextTalkDate = Column(Date, nullable=True)
    # 合同url
    contractUrl = Column(Text, nullable=True)
    # 成单时间
    cooperateTime = Column(DateTime, nullable=True)
    # 已学总课时：周
    learnedWeeks = Column(Float, nullable=True, default=0.0)
    # 入住宿舍床
    bedId = Column(Integer, ForeignKey("bed.id"), nullable=True)
    bed = relationship("Bed", backref="clients")
    # 入住时间
    bedCheckInDate = Column(Date, nullable=True)
    # 离住时间
    bedCheckOutDate = Column(Date, nullable=True)

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
            "creatorId": self.creatorId,
            "creatorName": self.creatorName,
            "createdTime": self.createdTime,
            "toClientTime": self.toClientTime,
            "appointerId": self.appointerId,
            "appointerName": self.appointerName,
            "schoolId": self.schoolId,
            "schoolName": self.schoolName,
            "courseIds": self.courseIds,
            "courseNames": self.courseNames,
            "comboId": self.comboId,
            "lessonIds": self.lessonIds,
            "graduatedLessonIds": self.graduatedLessonIds,
            "processStatus": self.processStatus,
            "appointDate": self.appointDate,
            "nextTalkDate": self.nextTalkDate,
            "cooperateTime": self.cooperateTime,
            "contractUrl": self.contractUrl,
            "learnedWeeks": self.learnedWeeks,
            "bedId": self.bedId,
            "bedCheckInDate": self.bedCheckInDate,
            "bedCheckOutDate": self.bedCheckOutDate,
        }
        if self.info:
            data["info"] = [info for info in self.info if info != ""]
        if self.affiliatedUserId:
            data["affiliatedUserName"] = self.affiliatedUser.username
        if self.comboId:
            session = Session()
            combo = session.query(CourseCombo).get(self.comboId)
            if combo:
                data["comboName"] = combo.showName
                data["comboPrice"] = combo.price
            session.close()
        # 数据过大了
        # if self.bedId:
        #     data["bed"] = self.bed.to_json()
        return data


class School(Base):
    __tablename__ = "school"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "info": self.info,
        }
        return data


class Course(Base):
    __tablename__ = "course"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    # 分类：1全日制 / 2周末班
    category = Column(Integer, nullable=True)
    creatorId = Column(Integer, ForeignKey("user.id"), nullable=True)
    creator = relationship("User", backref="createdCourses")
    # 所属校区
    schoolId = Column(Integer, ForeignKey("school.id"), nullable=True)
    school = relationship("School", backref="courses")
    createdTime = Column(DateTime, nullable=True, default=datetime.now)
    # 课时
    duration = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "schoolId": self.schoolId,
            "creatorId": self.creatorId,
            "createdTime": self.createdTime,
            "duration": self.duration,
            "price": self.price,
            "info": self.info,
        }
        if self.creatorId:
            data["creatorName"] = self.creator.username
        if self.schoolId:
            data["schoolName"] = self.school.name
        return data


# 课程套餐
class CourseCombo(Base):
    __tablename__ = "course_combo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    price = Column(Float, nullable=True)

    @property
    def showName(self):
        return self.name + " - " + str(format(self.price, '.2f')) + "元"

    # 所属校区
    schoolId = Column(Integer, ForeignKey("school.id"), nullable=True)
    school = relationship("School", backref="combos")
    # 包含课程
    courseIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "showName": self.showName,
            "price": self.price,
            "schoolId": self.schoolId,
            "courseIds": self.courseIds,
            "info": self.info,
        }
        if self.schoolId:
            data["schoolName"] = self.school.name
        # 课程名列表
        if self.courseIds and len(self.courseIds) > 0:
            session = Session()
            courses = [session.query(Course).get(courseId) for courseId in self.courseIds]
            data["courseNames"] = [course.name for course in courses]
            session.close()
        return data


# 班级
class Lesson(Base):
    __tablename__ = "lesson"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    courseId = Column(Integer, ForeignKey("course.id"), nullable=True)
    course = relationship("Course", backref="lessons")
    # 开课日期
    startDate = Column(Date, nullable=True)
    # 结课日期
    endDate = Column(Date, nullable=True)

    @property
    def courseName(self):
        if self.courseId:
            return self.course.name
        return None

    @property
    def category(self):
        if self.courseId:
            return self.course.category
        return None

    @property
    def schoolId(self):
        if self.courseId:
            return self.course.schoolId
        return None

    # 主讲人
    chiefTeacherId = Column(Integer, nullable=True)
    chiefTeacherName = Column(Text, nullable=True)
    # @property
    # def chiefTeacherName(self):
    #     chiefTeacher = session.query(User).get(self.chiefTeacherId)
    #     if chiefTeacher:
    #         return chiefTeacher.username
    #     else:
    #         return ""

    # 班主任
    classTeacherId = Column(Integer, nullable=True)

    @property
    def classTeacherName(self):
        session = Session()
        classTeacher = session.query(User).get(self.classTeacherId)
        session.close()
        if classTeacher:
            return classTeacher.username
        else:
            return ""

    # 助教
    teachingAssistantName = Column(Text, nullable=True)

    info = Column(Text, nullable=True)
    createdTime = Column(DateTime, nullable=True, default=datetime.now)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "courseId": self.courseId,
            "courseName": self.courseName,
            "startDate": self.startDate,
            "endDate": self.endDate,
            "category": self.category,
            "schoolId": self.schoolId,
            "chiefTeacherId": self.chiefTeacherId,
            "chiefTeacherName": self.chiefTeacherName,
            "classTeacherId": self.classTeacherId,
            "classTeacherName": self.classTeacherName,
            "teachingAssistantName": self.teachingAssistantName,
            "info": self.info,
            "createdTime": self.createdTime,
        }
        if self.schoolId:
            session = Session()
            school = session.query(School).get(self.schoolId)
            data["schoolName"] = school.name
            session.close()
        return data


class Payment(Base):
    __tablename__ = "payment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 客户：仅收入
    clientId = Column(Integer, ForeignKey("client.id"), nullable=True)
    client = relationship("Client", backref="payments")

    @property
    def clientName(self):
        if self.clientId:
            return self.client.name
        return ""

    @property
    def clientPhone(self):
        if self.clientId:
            return self.client.phone
        return ""

    # 收款方：仅支出
    receiver = Column(Text, nullable=True)
    # 负责老师
    teacherId = Column(Integer, ForeignKey("user.id"), nullable=True)
    teacher = relationship("User", backref="payments")

    # 所属校区（取决于负责老师）
    @property
    def schoolId(self):
        if self.teacherId:
            return self.teacher.schoolId
        return None

    @property
    def schoolName(self):
        if self.teacherId:
            return self.teacher.school.name
        return ""

    # 金额：单位元，正为收入，负为支出
    amount = Column(Integer, nullable=True)
    # 类别：1定金 / 2尾款 / 3住宿费 / 4补差价 / 5其他
    category = Column(Integer, nullable=True)
    # 交易方式：1现金 / 2微信 / 3支付宝 / 4POS / 5对公 / 6其他
    paymentMethod = Column(Integer, nullable=True)
    # 备注
    info = Column(Text, nullable=True)
    paymentDate = Column(Date, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "clientId": self.clientId,
            "clientName": self.clientName,
            "clientPhone": self.clientPhone,
            "receiver": self.receiver,
            "teacherId": self.teacherId,
            "amount": self.amount,
            "category": self.category,
            "paymentMethod": self.paymentMethod,
            "info": self.info,
            "paymentDate": self.paymentDate,
            "schoolId": self.schoolId,
            "schoolName": self.schoolName,
        }
        if self.teacherId:
            data["teacherName"] = self.teacher.username
        return data


class Dormitory(Base):
    __tablename__ = "dormitory"
    id = Column(Integer, primary_key=True)
    # 公寓名或小区名
    name = Column(Text, nullable=True)
    # 类别：1公寓 / 2民房
    category = Column(Integer, nullable=True)
    schoolId = Column(Integer, ForeignKey("school.id"), nullable=True)
    school = relationship("School", backref="dormitories")

    @property
    def roomCount(self):
        session = Session()
        roomCount = session.query(Room).filter(Room.dormitoryId == self.id).count()
        session.close()
        return roomCount

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "schoolId": self.schoolId,
            "roomCount": self.roomCount,
        }
        if self.schoolId:
            data["schoolName"] = self.school.name
        return data


class Room(Base):
    __tablename__ = "room"
    id = Column(Integer, primary_key=True)
    dormitoryId = Column(Integer, ForeignKey("dormitory.id"), nullable=True)
    dormitory = relationship("Dormitory", backref="rooms")

    @property
    def category(self):
        if self.dormitory:
            return self.dormitory.category
        return 1

    # 公寓房间号或民房户号
    roomNumber = Column(Text, nullable=True)
    # 民房楼栋
    building = Column(Text, nullable=True)
    maxBeds = Column(Integer, nullable=True, default=0)  # 统计用，最大床位数

    # 已住的床位数
    # bool(bed.clients) 会把空列表变成 False，非空变成 True，加总起来就是非空床的数量。
    # sum(True, True, False) => 2，因为 True 就是 1，False 是 0。
    @property
    def occupiedBeds(self):
        session = Session()
        beds = session.query(Bed).filter(Bed.roomId == self.id).all()
        if len(beds) != 0:
            return sum(bool(bed.clients) for bed in beds)
        session.close()
        return 0

    def to_json(self):
        data = {
            "id": self.id,
            "dormitoryId": self.dormitoryId,
            "category": self.category,
            "roomNumber": self.roomNumber,
            "building": self.building,
            "maxBeds": self.maxBeds,
            "occupiedBeds": self.occupiedBeds,
        }
        # if self.dormitoryId:
        #     data["dormitory"] = self.dormitory.to_json()
        return data


class Bed(Base):
    __tablename__ = "bed"
    id = Column(Integer, primary_key=True)
    roomId = Column(Integer, ForeignKey("room.id"), nullable=True)
    room = relationship("Room", backref="beds")
    # 床号
    bedNumber = Column(Integer, nullable=True)
    # 类型：1单人床 / 2上铺 / 3下铺
    category = Column(Integer, nullable=True)
    # 时间期限：天
    duration = Column(Integer, nullable=True)

    @property
    def isVacant(self):
        return not self.clients

    def to_json(self):
        data = {
            "id": self.id,
            "roomId": self.roomId,
            "bedNumber": self.bedNumber,
            "category": self.category,
            "duration": self.duration,
            "isVacant": self.isVacant,
            "studentId": None,
            "studentName": None,
        }
        # if self.roomId:
        #     data["room"] = self.room.to_json()
        session = Session()
        client_for_this_bed = session.query(Client).filter(Client.bedId == self.id).first()
        if client_for_this_bed:
            data["studentId"] = client_for_this_bed.id
            data["studentName"] = client_for_this_bed.name
            data["bedCheckInDate"] = client_for_this_bed.bedCheckInDate
            data["bedCheckOutDate"] = client_for_this_bed.bedCheckOutDate
        session.close()
        return data


class ClientLog(Base):
    __tablename__ = "client_log"
    id = Column(Integer, primary_key=True)
    clientId = Column(Integer, ForeignKey("client.id"), nullable=True)
    client = relationship("Client", backref="hisLogs")
    operatorId = Column(Integer, ForeignKey("user.id"), nullable=True)
    operator = relationship("User", backref="hisClientLogs")
    operation = Column(Text, nullable=True)
    time = Column(DateTime, default=datetime.now)

    def to_json(self):
        data = {
            "id": self.id,
            "clientId": self.clientId,
            "clientName": self.client.name,
            "operatorId": self.operatorId,
            "operatorName": self.operator.username,
            "operation": self.operation,
            "time": self.time,
        }
        return data


class Log(Base):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    operatorId = Column(Integer, ForeignKey("user.id"), nullable=True)
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
