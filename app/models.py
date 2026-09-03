from sqlalchemy import Column, Integer, String
from .database import Base

class FoodPlace(Base):
    __tablename__ = "food_places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    note = Column(String)
    image = Column(String, default="")      # link ảnh (URL)
    rating = Column(Integer, default=0)     # 0-5 sao
    status = Column(String)  # da_an | muon_an


class StudyPlace(Base):
    __tablename__ = "study_places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    note = Column(String)

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    script = Column(String)

    done = Column(Integer, default=0)      # 0 = chưa xong
    priority = Column(String, default="normal")  # low / normal / high
    deadline = Column(String, default="")


class ScheduleEvent(Base):
    """Một mục trong lịch của một người.

    `owner` là tên đăng nhập — mỗi người một cuốn lịch riêng, nhưng cả hai đứa
    đều xem được lịch của nhau (đó mới là điểm của cái trang này).
    """

    __tablename__ = "schedule_events"

    id = Column(Integer, primary_key=True, index=True)
    owner = Column(String, index=True)       # tên đăng nhập của chủ lịch
    date = Column(String, index=True)        # "YYYY-MM-DD"
    start = Column(String, default="")       # "HH:MM", để trống là cả ngày
    title = Column(String)
    note = Column(String, default="")
