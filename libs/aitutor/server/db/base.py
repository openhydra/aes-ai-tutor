import json

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker

from aitutor.settings import Settings

db_uri = Settings.basic_settings.SQLALCHEMY_DATABASE_URI
database_name = "aes-ai-tutor"

base_db_uri = db_uri.rsplit("/", 1)[0]
engine = create_engine(
    base_db_uri, json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
)

try:
    with engine.connect() as connection:
        connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}`"))
except ProgrammingError as e:
    print(f"Error creating database: {e}")

# 创建带数据库名的引擎
engine_with_db = create_engine(
    db_uri, json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_with_db)

Base: DeclarativeMeta = declarative_base()
