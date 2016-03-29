import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class Category(Base):
    __tablename__ = 'category'
    id = Column(
        Integer, primary_key=True
    )
    name = Column(
        String(80), nullable=False
    )

class Item(Base):
    __tablename__ = 'item'
    id = Column(
        Integer, primary_key=True
    )
    title = Column(
        String(80), nullable=False
    )
    description = Column(
        String, nullable=False
    )
    image_url = Column(
        String, nullable=True
    )
    category_id = Column(
        Integer, ForeignKey('category.id')
    )
    category = relationship(Category)



db_url = "postgresql:///catalog"

engine = create_engine(db_url)
Base.metadata.create_all(engine)