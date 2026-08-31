from sqlalchemy import BigInteger, Column, Integer, String
from .database import Base

class FoodPlace(Base):
    __tablename__ = "food_places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    note = Column(String)
    image = Column(String, default="")      # link ảnh (URL)
    rating = Column(Integer, default=0)     # 0-5 sao
    status = Column(String)  # da_an | chua_an | muon_an


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

class Transaction(Base):
    """Một giao dịch tiền — nhập tay hoặc import từ sao kê MoMo."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(BigInteger, default=0)   # VND, luôn là số dương
    kind = Column(String, default="out")     # out = chi | in = thu
    category = Column(String, default="khac")
    note = Column(String, default="")
    date = Column(String, default="")        # "YYYY-MM-DD", như deadline của Plan
    source = Column(String, default="momo")  # momo | tien_mat | bank
    ref = Column(String, default="", index=True)  # mã GD MoMo — để import 2 lần không bị nhân đôi


class Budget(Base):
    """Hạn mức chi cho một tháng."""

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(String, index=True)   # "YYYY-MM"
    amount = Column(BigInteger, default=0)
