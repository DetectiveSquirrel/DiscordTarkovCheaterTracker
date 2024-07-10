from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    BigInteger,
    func,
    distinct,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
import settings
import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger("database")


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
    __tablename__ = DatabaseEnum.TABLE_CHEATERS_KILLED.value
    id = Column(Integer, primary_key=True, autoincrement=True)
    fromUserid = Column(BigInteger)
    serverIdLoggedIn = Column(BigInteger)
    cheatersgamename = Column(String(255))
    cheaterprofileid = Column(BigInteger)
    timereported = Column(BigInteger)


class CheaterDeaths(Base):
    __tablename__ = DatabaseEnum.TABLE_CHEATER_DEATHS.value
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
            if table in [DatabaseEnum.TABLE_CHEATER_DEATHS, DatabaseEnum.BOTH]:
                query = session.query(CheaterDeaths)
                if user_id:
                    query = query.filter_by(fromUserid=user_id)
                results.extend(query.all())
            if table in [DatabaseEnum.TABLE_CHEATERS_KILLED, DatabaseEnum.BOTH]:
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
                    DatabaseEnum.TABLE.value: (
                        DatabaseEnum.TABLE_CHEATER_DEATHS.value
                        if isinstance(report, CheatersKilled)
                        else DatabaseEnum.TABLE_CHEATERS_KILLED.value
                    ),
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

    @classmethod
    def get_comprehensive_cheater_details(
        cls, cheater_id: int
    ) -> Optional[Dict[str, Any]]:
        def op(session):
            try:
                logger.debug(f"Fetching basic info for cheater ID: {cheater_id}")
                cheater = cls.get_cheater_basic_info(session, cheater_id)
                logger.debug(f"Basic info fetched: {cheater}")

                if not cheater:
                    logger.debug("Cheater not found.")
                    return None

                logger.debug(f"Counting death reports for cheater ID: {cheater_id}")
                cheater["total_death_reports"] = cls.count_death_reports(
                    session, cheater_id
                )
                logger.debug(f"Total death reports: {cheater['total_death_reports']}")

                logger.debug(f"Counting kill reports for cheater ID: {cheater_id}")
                cheater["total_kill_reports"] = cls.count_kill_reports(
                    session, cheater_id
                )
                logger.debug(f"Total kill reports: {cheater['total_kill_reports']}")

                logger.debug(
                    f"Fetching most killed by info for cheater ID: {cheater_id}"
                )
                cheater["most_killed_by"] = cls.get_most_killed_by(session, cheater_id)
                logger.debug(f"Most killed by: {cheater['most_killed_by']}")

                logger.debug(
                    f"Fetching most deaths to info for cheater ID: {cheater_id}"
                )
                cheater["most_deaths_to"] = cls.get_most_deaths_to(session, cheater_id)
                logger.debug(f"Most deaths to: {cheater['most_deaths_to']}")

                logger.debug(
                    f"Fetching most reported server info for cheater ID: {cheater_id}"
                )
                cheater["most_reported_server"] = cls.get_most_reported_server(
                    session, cheater_id
                )
                logger.debug(f"Most reported server: {cheater['most_reported_server']}")

                # Get the last report time and reporter for kills from CheatersKilled
                logger.debug(
                    f"Fetching last kill report from CheatersKilled for cheater ID: {cheater_id}"
                )
                last_kill_report = (
                    session.query(
                        CheatersKilled.timereported, CheatersKilled.fromUserid
                    )
                    .filter_by(cheaterprofileid=cheater_id)
                    .order_by(CheatersKilled.timereported.desc())
                    .first()
                )
                logger.debug(
                    f"Last kill report from CheatersKilled: {last_kill_report}"
                )

                # Get the last report time and reporter for deaths from CheaterDeaths
                logger.debug(
                    f"Fetching last death report from CheaterDeaths for cheater ID: {cheater_id}"
                )
                last_death_report = (
                    session.query(CheaterDeaths.timereported, CheaterDeaths.fromUserid)
                    .filter_by(cheaterprofileid=cheater_id)
                    .order_by(CheaterDeaths.timereported.desc())
                    .first()
                )
                logger.debug(
                    f"Last death report from CheaterDeaths: {last_death_report}"
                )

                if last_kill_report:
                    cheater["last_kill_report_time"] = last_kill_report.timereported
                    cheater["last_kill_reported_by"] = last_kill_report.fromUserid

                if last_death_report:
                    cheater["last_death_report_time"] = last_death_report.timereported
                    cheater["last_death_reported_by"] = last_death_report.fromUserid

                logger.debug(f"Final cheater details: {cheater}")
                return cheater
            except Exception as e:
                logger.error(f"Error in get_comprehensive_cheater_details: {e}")
                logger.error(f"Cheater ID: {cheater_id}")
                logger.error(f"Current session state: {session}")
                return None

        return cls._execute_db_operation(op)

    @staticmethod
    def get_cheater_basic_info(session, cheater_id: int) -> Optional[Dict[str, Any]]:
        cheater_killed = (
            session.query(CheatersKilled)
            .filter_by(cheaterprofileid=cheater_id)
            .order_by(CheatersKilled.timereported.desc())
            .first()
        )
        cheater_death = (
            session.query(CheaterDeaths)
            .filter_by(cheaterprofileid=cheater_id)
            .order_by(CheaterDeaths.timereported.desc())
            .first()
        )

        if cheater_killed and cheater_death:
            if cheater_killed.timereported >= cheater_death.timereported:
                return {
                    "id": cheater_killed.cheaterprofileid,
                    "name": cheater_killed.cheatersgamename,
                }
            else:
                return {
                    "id": cheater_death.cheaterprofileid,
                    "name": cheater_death.cheatersgamename,
                }
        elif cheater_killed:
            return {
                "id": cheater_killed.cheaterprofileid,
                "name": cheater_killed.cheatersgamename,
            }
        elif cheater_death:
            return {
                "id": cheater_death.cheaterprofileid,
                "name": cheater_death.cheatersgamename,
            }
        else:
            return None

    @staticmethod
    def count_death_reports(session, cheater_id: int) -> int:
        return (
            session.query(CheaterDeaths).filter_by(cheaterprofileid=cheater_id).count()
        )

    @staticmethod
    def count_kill_reports(session, cheater_id: int) -> int:
        return (
            session.query(CheatersKilled).filter_by(cheaterprofileid=cheater_id).count()
        )

    @staticmethod
    def get_most_killed_by(session, cheater_id: int) -> Optional[Dict[str, Any]]:
        result = (
            session.query(CheatersKilled.fromUserid, func.count().label("kill_count"))
            .filter_by(cheaterprofileid=cheater_id)
            .group_by(CheatersKilled.fromUserid)
            .order_by(func.count().desc())
            .first()
        )

        return {"user_id": result[0], "count": result[1]} if result else None

    @staticmethod
    def get_most_deaths_to(session, cheater_id: int) -> Optional[Dict[str, Any]]:
        result = (
            session.query(CheaterDeaths.fromUserid, func.count().label("death_count"))
            .filter_by(cheaterprofileid=cheater_id)
            .group_by(CheaterDeaths.fromUserid)
            .order_by(func.count().desc())
            .first()
        )

        return {"user_id": result[0], "count": result[1]} if result else None

    @staticmethod
    def get_most_reported_server(session, cheater_id: int) -> Optional[Dict[str, Any]]:
        try:
            logger.debug(f"Fetching death reports for cheater ID: {cheater_id}")
            deaths_query = (
                session.query(
                    CheaterDeaths.serverIdLoggedIn.label("server_id"),
                    func.count().label("report_count"),
                )
                .filter_by(cheaterprofileid=cheater_id)
                .group_by(CheaterDeaths.serverIdLoggedIn)
            )
            logger.debug(f"Deaths query: {deaths_query}")

            logger.debug(f"Fetching kill reports for cheater ID: {cheater_id}")
            kills_query = (
                session.query(
                    CheatersKilled.serverIdLoggedIn.label("server_id"),
                    func.count().label("report_count"),
                )
                .filter_by(cheaterprofileid=cheater_id)
                .group_by(CheatersKilled.serverIdLoggedIn)
            )
            logger.debug(f"Kills query: {kills_query}")

            combined_query = deaths_query.union_all(kills_query).subquery()

            final_query = (
                session.query(
                    combined_query.c.server_id,
                    func.sum(combined_query.c.report_count).label("total_count"),
                )
                .group_by(combined_query.c.server_id)
                .order_by(func.sum(combined_query.c.report_count).desc())
            )
            logger.debug(f"Final combined query: {final_query}")

            result = final_query.first()
            logger.debug(f"Final combined query result: {result}")

            return {"server_id": result[0], "count": result[1]} if result else None
        except Exception as e:
            logger.error(f"Error in get_most_reported_server: {e}")
            return None

    @classmethod
    def get_all_cheaters(cls) -> List[Dict[str, Any]]:
        def op(session):
            cheaters_killed = session.query(
                distinct(CheatersKilled.cheaterprofileid),
                CheatersKilled.cheatersgamename,
            ).all()
            cheaters_deaths = session.query(
                distinct(CheaterDeaths.cheaterprofileid), CheaterDeaths.cheatersgamename
            ).all()

            all_cheaters = {(c[0], c[1]) for c in cheaters_killed + cheaters_deaths}
            return [{"id": cheater[0], "name": cheater[1]} for cheater in all_cheaters]

        return cls._execute_db_operation(op)
