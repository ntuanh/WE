from sqlalchemy import Column, Integer, String
from .database import Base

class FoodPlace(Base):
    __tablename__ = "food_places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    note = Column(String)
    status = Column(String)  # da_an | chua_an | muon_an


class StudyPlace(Base):
    __tablename__ = "study_places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    note = Column(String)