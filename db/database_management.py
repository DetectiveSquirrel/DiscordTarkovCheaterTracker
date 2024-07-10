from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
import settings
import logging
import time

logger = logging.getLogger(__name__)

class DatabaseConnectionError(Exception):
    pass

# Create the SQLAlchemy engine with error handling
try:
    engine = create_engine(
        f'postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}',
        pool_recycle=3600,  # Recycle connections every hour
        pool_pre_ping=True,  # Test connections before using them
        connect_args={'connect_timeout': 10}  # Increase the connect timeout
    )
    logger.info("Database connection established successfully.")
except SQLAlchemyError as e:
    logger.error(f"Error connecting to the database: {e}")
    engine = None

Base = declarative_base()

# Define schemas
class ServerSettings(Base):
    __tablename__ = 'server_settings'
    serverid = Column(BigInteger, primary_key=True)
    channelid = Column(BigInteger)

class CheatersKilled(Base):
    __tablename__ = 'cheaters_killed_by'
    id = Column(Integer, primary_key=True, autoincrement=True)
    fromUserid = Column(BigInteger)
    serverIdLoggedIn = Column(BigInteger)
    cheatersgamename = Column(String(255))
    cheaterprofileid = Column(BigInteger)
    timereported = Column(BigInteger)

class KilledByCheaters(Base):
    __tablename__ = 'killed_by_cheaters'
    id = Column(Integer, primary_key=True, autoincrement=True)
    fromUserid = Column(BigInteger)
    serverIdLoggedIn = Column(BigInteger)
    cheatersgamename = Column(String(255))
    cheaterprofileid = Column(BigInteger)
    timereported = Column(BigInteger)

# Create tables
if engine:
    try:
        Base.metadata.create_all(engine)
        logger.info("Database schema created successfully.")
    except SQLAlchemyError as e:
        logger.error(f"Error creating database schema: {e}")

# Create session factory
Session = sessionmaker(bind=engine) if engine else None

class DatabaseManager:
    @staticmethod
    def _get_session():
        if Session is None:
            raise DatabaseConnectionError("Database connection is not available")
        return Session()

    @staticmethod
    def _execute_db_operation(operation):
        try:
            with DatabaseManager._get_session() as session:
                return operation(session)
        except DatabaseConnectionError as e:
            logger.error(f"Database connection error: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Database operation error: {e}")

    @classmethod
    def add_server_settings(cls, serverid: int, channelid: int) -> None:
        def op(session):
            session.add(ServerSettings(serverid=serverid, channelid=channelid))
            session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def get_server_settings(cls, serverid: Optional[int] = None) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(ServerSettings)
            if serverid:
                query = query.filter_by(serverid=serverid)
            return [item.__dict__ for item in query.all()]
        return cls._execute_db_operation(op)

    @classmethod
    def update_server_settings(cls, serverid: int, channelid: int) -> None:
        def op(session):
            item = session.query(ServerSettings).get(serverid)
            if item:
                item.channelid = channelid
                session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def delete_server_settings(cls, serverid: int) -> None:
        def op(session):
            item = session.query(ServerSettings).get(serverid)
            if item:
                session.delete(item)
                session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def add_cheater_killed(cls, fromUserid: int, serverIdLoggedIn: int, cheatersgamename: str, cheaterprofileid: int, timereported: int) -> None:
        def op(session):
            session.add(CheatersKilled(fromUserid=fromUserid, serverIdLoggedIn=serverIdLoggedIn, 
                                       cheatersgamename=cheatersgamename, cheaterprofileid=cheaterprofileid,
                                       timereported=timereported))
            session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def get_cheaters_killed(cls, fromUserid: Optional[int] = None, serverIdLoggedIn: Optional[int] = None) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(CheatersKilled)
            if fromUserid:
                query = query.filter_by(fromUserid=fromUserid)
            if serverIdLoggedIn:
                query = query.filter_by(serverIdLoggedIn=serverIdLoggedIn)
            return [item.__dict__ for item in query.all()]
        return cls._execute_db_operation(op)

    @classmethod
    def update_cheater_killed(cls, id: int, updates: Dict[str, Any]) -> None:
        def op(session):
            item = session.query(CheatersKilled).get(id)
            if item:
                for key, value in updates.items():
                    setattr(item, key, value)
                session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def delete_cheater_killed(cls, id: int) -> None:
        def op(session):
            item = session.query(CheatersKilled).get(id)
            if item:
                session.delete(item)
                session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def add_killed_by_cheater(cls, fromUserid: int, serverIdLoggedIn: int, cheatersgamename: str, cheaterprofileid: int, timereported: int) -> None:
        def op(session):
            session.add(KilledByCheaters(fromUserid=fromUserid, serverIdLoggedIn=serverIdLoggedIn, 
                                         cheatersgamename=cheatersgamename, cheaterprofileid=cheaterprofileid,
                                         timereported=timereported))
            session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def get_killed_by_cheaters(cls, fromUserid: Optional[int] = None, serverIdLoggedIn: Optional[int] = None) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(KilledByCheaters)
            if fromUserid:
                query = query.filter_by(fromUserid=fromUserid)
            if serverIdLoggedIn:
                query = query.filter_by(serverIdLoggedIn=serverIdLoggedIn)
            return [item.__dict__ for item in query.all()]
        return cls._execute_db_operation(op)

    @classmethod
    def update_killed_by_cheater(cls, id: int, updates: Dict[str, Any]) -> None:
        def op(session):
            item = session.query(KilledByCheaters).get(id)
            if item:
                for key, value in updates.items():
                    setattr(item, key, value)
                session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def delete_killed_by_cheater(cls, id: int) -> None:
        def op(session):
            item = session.query(KilledByCheaters).get(id)
            if item:
                session.delete(item)
                session.commit()
        cls._execute_db_operation(op)

    @classmethod
    def get_cheaters_killed_report_summary(cls) -> List[Dict[str, Any]]:
        def op(session):
            cheater_reports = {}
            results = session.query(CheatersKilled).all()

            for report in results:
                cheater_id = report.cheaterprofileid
                if cheater_id not in cheater_reports:
                    cheater_reports[cheater_id] = {
                        'count': 0,
                        'latest_name': ''
                    }
                cheater_reports[cheater_id]['count'] += 1
                if report.timereported > cheater_reports[cheater_id].get('latest_time', 0):
                    cheater_reports[cheater_id]['latest_time'] = report.timereported
                    cheater_reports[cheater_id]['latest_name'] = report.cheatersgamename

            # Convert to list of dictionaries
            summary = [{'cheater_id': k, 'count': v['count'], 'latest_name': v['latest_name']} for k, v in cheater_reports.items()]
            return summary

        return cls._execute_db_operation(op)

    @classmethod
    def get_killed_by_cheaters_report_summary(cls) -> List[Dict[str, Any]]:
        def op(session):
            cheater_reports = {}
            results = session.query(KilledByCheaters).all()

            for report in results:
                cheater_id = report.cheaterprofileid
                if cheater_id not in cheater_reports:
                    cheater_reports[cheater_id] = {
                        'count': 0,
                        'latest_name': ''
                    }
                cheater_reports[cheater_id]['count'] += 1
                if report.timereported > cheater_reports[cheater_id].get('latest_time', 0):
                    cheater_reports[cheater_id]['latest_time'] = report.timereported
                    cheater_reports[cheater_id]['latest_name'] = report.cheatersgamename

            # Convert to list of dictionaries
            summary = [{'cheater_id': k, 'count': v['count'], 'latest_name': v['latest_name']} for k, v in cheater_reports.items()]
            return summary

        return cls._execute_db_operation(op)
    
    @classmethod
    def get_kills_by_cheater_report_for_user(cls, user_id: int) -> List[Dict[str, Any]]:
        def op(session):
            kill_reports = {}
            results = session.query(KilledByCheaters).filter_by(fromUserid=user_id).all()

            for report in results:
                cheater_id = report.cheaterprofileid
                if cheater_id not in kill_reports:
                    kill_reports[cheater_id] = {
                        'count': 0,
                        'latest_name': ''
                    }
                kill_reports[cheater_id]['count'] += 1
                if report.timereported > kill_reports[cheater_id].get('latest_time', 0):
                    kill_reports[cheater_id]['latest_time'] = report.timereported
                    kill_reports[cheater_id]['latest_name'] = report.cheatersgamename

            # Convert to list of dictionaries
            summary = [{'cheater_id': k, 'count': v['count'], 'latest_name': v['latest_name']} for k, v in kill_reports.items()]
            return summary

        return cls._execute_db_operation(op)