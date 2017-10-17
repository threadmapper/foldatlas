
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy.ext.declarative import declarative_base
# from flask_sqlalchemy import SQLAlchemy

import settings

engine = create_engine( settings.database_uri, convert_unicode=True )

# Autoflush = true is important to prevent errors on EC2
db_session = scoped_session( sessionmaker( autocommit=False, autoflush=True, bind=engine ) )

# from app import sqla
# Base = sqla.Model # declarative_base()
Base = declarative_base()
# Base.query = db_session.query_property()
