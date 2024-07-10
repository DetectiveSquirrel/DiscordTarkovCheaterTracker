from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
import settings
import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DatabaseEnum(Enum):
    SERVER_SETTINGS = "server_settings"
    TABLE_CHEATER_DEATHS = "cheater_deaths"
    TABLE_CHEATERS_KILLED = "cheaters_killed"
    ID = "id"
    FROM_USER_ID = "fromUserid"
    SERVER_ID_LOGGED_IN = "serverIdLoggedIn"
    CHEATERS_GAME_NAME = "cheatersgamename"
    CHEATER_PROFILE_ID = "cheaterprofileid"
    TIME_REPORTED = "timereported"
    TABLE = "table"
    BOTH = "both"


class DatabaseConnectionError(Exception):
    pass


# Create the SQLAlchemy engine with error handling
try:
    engine = create_engine(
        f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}",
        pool_recycle=3600,  # Recycle connections every hour
        pool_pre_ping=True,  # Test connections before using them
        connect_args={"connect_timeout": 10},  # Increase the connect timeout
    )
    logger.info("Database connection established successfully.")
except SQLAlchemyError as e:
    logger.error(f"Error connecting to the database: {e}")
    engine = None

Base = declarative_base()

# Define schemas
class ServerSettings(Base):
    __tablename__ = DatabaseEnum.SERVER_SETTINGS.value
    serverid = Column(BigInteger, primary_key=True)
    channelid = Column(BigInteger)


class CheatersKilled(Base):
    __tablename__ = DatabaseEnum.TABLE_CHEATER_DEATHS.value
    id = Column(Integer, primary_key=True, autoincrement=True)
    fromUserid = Column(BigInteger)
    serverIdLoggedIn = Column(BigInteger)
    cheatersgamename = Column(String(255))
    cheaterprofileid = Column(BigInteger)
    timereported = Column(BigInteger)


class CheaterDeaths(Base):
    __tablename__ = DatabaseEnum.TABLE_CHEATERS_KILLED.value
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
    def get_server_settings(
        cls, serverid: Optional[int] = None
    ) -> List[Dict[str, Any]]:
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
    def add_cheater_killed(
        cls,
        fromUserid: int,
        serverIdLoggedIn: int,
        cheatersgamename: str,
        cheaterprofileid: int,
        timereported: int,
    ) -> None:
        def op(session):
            session.add(
                CheatersKilled(
                    fromUserid=fromUserid,
                    serverIdLoggedIn=serverIdLoggedIn,
                    cheatersgamename=cheatersgamename,
                    cheaterprofileid=cheaterprofileid,
                    timereported=timereported,
                )
            )
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def get_cheaters_killed(
        cls, fromUserid: Optional[int] = None, serverIdLoggedIn: Optional[int] = None
    ) -> List[Dict[str, Any]]:
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
    def add_killed_by_cheater(
        cls,
        fromUserid: int,
        serverIdLoggedIn: int,
        cheatersgamename: str,
        cheaterprofileid: int,
        timereported: int,
    ) -> None:
        def op(session):
            session.add(
                CheaterDeaths(
                    fromUserid=fromUserid,
                    serverIdLoggedIn=serverIdLoggedIn,
                    cheatersgamename=cheatersgamename,
                    cheaterprofileid=cheaterprofileid,
                    timereported=timereported,
                )
            )
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def get_killed_by_cheaters(
        cls, fromUserid: Optional[int] = None, serverIdLoggedIn: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(CheaterDeaths)
            if fromUserid:
                query = query.filter_by(fromUserid=fromUserid)
            if serverIdLoggedIn:
                query = query.filter_by(serverIdLoggedIn=serverIdLoggedIn)
            return [item.__dict__ for item in query.all()]

        return cls._execute_db_operation(op)

    @classmethod
    def update_killed_by_cheater(cls, id: int, updates: Dict[str, Any]) -> None:
        def op(session):
            item = session.query(CheaterDeaths).get(id)
            if item:
                for key, value in updates.items():
                    setattr(item, key, value)
                session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def delete_killed_by_cheater(cls, id: int) -> None:
        def op(session):
            item = session.query(CheaterDeaths).get(id)
            if item:
                session.delete(item)
                session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def get_cheater_reports(
        cls, table: DatabaseEnum = DatabaseEnum.BOTH, user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        def op(session):
            results = []
            if table in [DatabaseEnum.TABLE_CHEATERS_KILLED, DatabaseEnum.BOTH]:
                query = session.query(CheaterDeaths)
                if user_id:
                    query = query.filter_by(fromUserid=user_id)
                results.extend(query.all())
            if table in [DatabaseEnum.TABLE_CHEATER_DEATHS, DatabaseEnum.BOTH]:
                query = session.query(CheatersKilled)
                if user_id:
                    query = query.filter_by(fromUserid=user_id)
                results.extend(query.all())

            logger.debug(f"get_cheater_reports: Retrieved {len(results)} results")

            formatted_results = [
                {
                    DatabaseEnum.ID.value: report.id,
                    DatabaseEnum.FROM_USER_ID.value: report.fromUserid,
                    DatabaseEnum.SERVER_ID_LOGGED_IN.value: report.serverIdLoggedIn,
                    DatabaseEnum.CHEATERS_GAME_NAME.value: report.cheatersgamename,
                    DatabaseEnum.CHEATER_PROFILE_ID.value: report.cheaterprofileid,
                    DatabaseEnum.TIME_REPORTED.value: report.timereported,
                    DatabaseEnum.TABLE.value: DatabaseEnum.TABLE_CHEATER_DEATHS.value
                    if isinstance(report, CheatersKilled)
                    else DatabaseEnum.TABLE_CHEATERS_KILLED.value,
                }
                for report in results
            ]

            logger.debug(
                f"get_cheater_reports: Formatted {len(formatted_results)} results"
            )
            if formatted_results:
                logger.debug(f"Sample result: {formatted_results[0]}")

            return formatted_results

        return cls._execute_db_operation(op)
