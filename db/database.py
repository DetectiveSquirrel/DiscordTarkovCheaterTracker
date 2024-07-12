from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    BigInteger,
    func,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
import settings
import logging
from enum import Enum, auto

logger = logging.getLogger("database")


class ServerSettingsFields(Enum):
    TABLE_NAME = "server_settings"
    SERVER_ID = "server_id"
    CHANNEL_ID = "channel_id"


class CheaterReportFields(Enum):
    TABLE_NAME = "cheater_reports"
    ID = "id"
    REPORTER_USER_ID = "reporter_user_id"
    SERVER_ID = "server_id"
    CHEATER_GAME_NAME = "cheater_game_name"
    CHEATER_PROFILE_ID = "cheater_profile_id"
    REPORT_TIME = "report_time"
    REPORT_TYPE = "report_type"


class ReportType(Enum):
    KILLED_BY_CHEATER = auto()
    KILLED_A_CHEATER = auto()
    SUS_AS_FUCK = auto()
    STREAM_SNIPER = auto()
    WORD_OF_MOUTH = auto()


REPORT_TYPE_DISPLAY = {
    ReportType.KILLED_BY_CHEATER: "Killed by Cheater",
    ReportType.KILLED_A_CHEATER: "Killed a Cheater",
    ReportType.SUS_AS_FUCK: "Sus as Fuck",
    ReportType.STREAM_SNIPER: "Probable Stream Sniper",
    ReportType.WORD_OF_MOUTH: "Word of Mouth",
}


class DatabaseConnectionError(Exception):
    pass


# Create the SQLAlchemy engine with error handling
try:
    engine = create_engine(
        f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}",
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )
    logger.info("Database connection established successfully.")
except SQLAlchemyError as e:
    logger.error(f"Error connecting to the database: {e}")
    engine = None

Base = declarative_base()


# Define schemas
class ServerSettings(Base):
    __tablename__ = ServerSettingsFields.TABLE_NAME.value
    server_id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger)


class CheaterReport(Base):
    __tablename__ = CheaterReportFields.TABLE_NAME.value
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_user_id = Column(BigInteger)
    server_id = Column(BigInteger)
    cheater_game_name = Column(String(255))
    cheater_profile_id = Column(BigInteger)
    report_time = Column(BigInteger)
    report_type = Column(SQLAlchemyEnum(ReportType))


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

    # Server Settings Operations
    @classmethod
    def add_server_settings(cls, server_id: int, channel_id: int) -> None:
        def op(session):
            session.add(
                ServerSettings(
                    **{
                        ServerSettingsFields.SERVER_ID.value: server_id,
                        ServerSettingsFields.CHANNEL_ID.value: channel_id,
                    }
                )
            )
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def get_server_settings(
        cls, server_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(ServerSettings)
            if server_id:
                query = query.filter_by(
                    **{ServerSettingsFields.SERVER_ID.value: server_id}
                )
            return [item.__dict__ for item in query.all()]

        return cls._execute_db_operation(op)

    @classmethod
    def update_server_settings(cls, server_id: int, channel_id: int) -> None:
        def op(session):
            item = session.query(ServerSettings).get(server_id)
            if item:
                setattr(item, ServerSettingsFields.CHANNEL_ID.value, channel_id)
                session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def delete_server_settings(cls, server_id: int) -> None:
        def op(session):
            item = session.query(ServerSettings).get(server_id)
            if item:
                session.delete(item)
                session.commit()

        cls._execute_db_operation(op)

    # Cheater Report Operations
    @classmethod
    def add_cheater_report(
        cls,
        reporter_user_id: int,
        server_id: int,
        cheater_game_name: str,
        cheater_profile_id: int,
        report_time: int,
        report_type: ReportType,
    ) -> None:
        def op(session):
            logger.debug("Adding cheater report to the session")
            session.add(
                CheaterReport(
                    **{
                        CheaterReportFields.REPORTER_USER_ID.value: reporter_user_id,
                        CheaterReportFields.SERVER_ID.value: server_id,
                        CheaterReportFields.CHEATER_GAME_NAME.value: cheater_game_name,
                        CheaterReportFields.CHEATER_PROFILE_ID.value: cheater_profile_id,
                        CheaterReportFields.REPORT_TIME.value: report_time,
                        CheaterReportFields.REPORT_TYPE.value: report_type,
                    }
                )
            )
            logger.debug("Committing the session to the database")
            session.commit()
            logger.debug("Session committed successfully")

        cls._execute_db_operation(op)

    @classmethod
    def get_cheater_reports(
        cls,
        report_type: Optional[ReportType] = None,
        reporter_user_id: Optional[int] = None,
        server_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(CheaterReport)
            if report_type:
                query = query.filter_by(
                    **{CheaterReportFields.REPORT_TYPE.value: report_type}
                )
            if reporter_user_id:
                query = query.filter_by(
                    **{CheaterReportFields.REPORTER_USER_ID.value: reporter_user_id}
                )
            if server_id:
                query = query.filter_by(
                    **{CheaterReportFields.SERVER_ID.value: server_id}
                )
            return [item.__dict__ for item in query.all()]

        return cls._execute_db_operation(op)

    @classmethod
    def update_cheater_report(cls, id: int, updates: Dict[str, Any]) -> None:
        def op(session):
            item = session.query(CheaterReport).get(id)
            if item:
                for key, value in updates.items():
                    setattr(item, key, value)
                session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def delete_cheater_report(cls, id: int) -> None:
        def op(session):
            item = session.query(CheaterReport).get(id)
            if item:
                session.delete(item)
                session.commit()

        cls._execute_db_operation(op)

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

                for report_type in ReportType:
                    total_reports_key = f"total_{report_type.name.lower()}_reports"
                    last_reported_by_key = (
                        f"last_{report_type.name.lower()}_reported_by"
                    )
                    last_report_time_key = (
                        f"last_{report_type.name.lower()}_report_time"
                    )
                    most_reported_by_key = (
                        f"most_{report_type.name.lower()}_reported_by"
                    )

                    logger.debug(
                        f"Counting {report_type.name.lower()} reports for cheater ID: {cheater_id}"
                    )
                    cheater[total_reports_key] = cls.count_reports(
                        session, cheater_id, report_type
                    )
                    logger.debug(
                        f"Total {report_type.name.lower()} reports: {cheater[total_reports_key]}"
                    )

                    logger.debug(
                        f"Fetching last {report_type.name.lower()} report for cheater ID: {cheater_id}"
                    )
                    last_report = cls.get_last_report(session, cheater_id, report_type)
                    if last_report:
                        cheater[last_reported_by_key] = last_report.reporter_user_id
                        cheater[last_report_time_key] = last_report.report_time
                    else:
                        cheater[last_reported_by_key] = None
                        cheater[last_report_time_key] = None
                    logger.debug(
                        f"Last {report_type.name.lower()} report: {last_report}"
                    )

                    logger.debug(
                        f"Fetching most {report_type.name.lower()} reported by for cheater ID: {cheater_id}"
                    )
                    most_reported_by = cls.get_most_reported_by(
                        session, cheater_id, report_type
                    )
                    cheater[most_reported_by_key] = most_reported_by
                    logger.debug(
                        f"Most {report_type.name.lower()} reported by: {most_reported_by}"
                    )

                logger.debug(
                    f"Fetching most reported server info for cheater ID: {cheater_id}"
                )
                cheater["most_reported_server"] = cls.get_most_reported_server(
                    session, cheater_id
                )
                logger.debug(f"Most reported server: {cheater['most_reported_server']}")

                logger.debug(
                    f"Fetching top reported servers info for cheater ID: {cheater_id}"
                )
                cheater["top_reported_servers"] = cls.get_top_reported_servers(
                    session, cheater_id
                )

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
        cheater = (
            session.query(CheaterReport)
            .filter_by(cheater_profile_id=cheater_id)
            .order_by(CheaterReport.report_time.desc())
            .first()
        )
        return (
            {"id": cheater.cheater_profile_id, "name": cheater.cheater_game_name}
            if cheater
            else None
        )

    @staticmethod
    def count_reports(session, cheater_id: int, report_type: ReportType) -> int:
        return (
            session.query(CheaterReport)
            .filter_by(cheater_profile_id=cheater_id, report_type=report_type)
            .count()
        )

    @staticmethod
    def get_most_reported_by(
        session, cheater_id: int, report_type: ReportType
    ) -> Optional[Dict[str, Any]]:
        result = (
            session.query(
                CheaterReport.reporter_user_id, func.count().label("report_count")
            )
            .filter_by(cheater_profile_id=cheater_id, report_type=report_type)
            .group_by(CheaterReport.reporter_user_id)
            .order_by(func.count().desc())
            .first()
        )
        return {"user_id": result[0], "count": result[1]} if result else None

    @staticmethod
    def get_most_reported_server(session, cheater_id: int) -> Optional[Dict[str, Any]]:
        try:
            result = (
                session.query(
                    CheaterReport.server_id, func.count().label("report_count")
                )
                .filter_by(cheater_profile_id=cheater_id)
                .group_by(CheaterReport.server_id)
                .order_by(func.count().desc())
                .first()
            )
            return {"server_id": result[0], "count": result[1]} if result else None
        except Exception as e:
            logger.error(f"Error in get_most_reported_server: {e}")
            return None

    @staticmethod
    def get_last_report(session, cheater_id: int, report_type: ReportType):
        return (
            session.query(CheaterReport)
            .filter_by(cheater_profile_id=cheater_id, report_type=report_type)
            .order_by(CheaterReport.report_time.desc())
            .first()
        )

    @classmethod
    def get_cheater_reports_by_type(
        cls, report_type: ReportType
    ) -> List[Dict[str, Any]]:
        def op(session):
            query = (
                session.query(CheaterReport)
                .filter_by(**{CheaterReportFields.REPORT_TYPE.value: report_type})
                .all()
            )
            return [item.__dict__ for item in query]

        return cls._execute_db_operation(op)

    @classmethod
    def get_all_cheaters(cls) -> List[Dict[str, Any]]:
        def op(session):
            all_cheaters = session.query(
                getattr(CheaterReport, CheaterReportFields.CHEATER_PROFILE_ID.value),
                getattr(CheaterReport, CheaterReportFields.CHEATER_GAME_NAME.value),
                getattr(CheaterReport, CheaterReportFields.REPORT_TIME.value),
                getattr(CheaterReport, CheaterReportFields.REPORT_TYPE.value),
            ).all()

            return [
                {
                    "id": c[0],
                    "name": c[1],
                    "report_time": c[2],
                    "report_type": c[3].name,
                }
                for c in all_cheaters
            ]

        return cls._execute_db_operation(op)

    @staticmethod
    def get_top_reported_servers(
        session, cheater_id: int, limit: int = 3
    ) -> List[Dict[str, Any]]:
        try:
            results = (
                session.query(
                    CheaterReport.server_id, func.count().label("report_count")
                )
                .filter_by(cheater_profile_id=cheater_id)
                .group_by(CheaterReport.server_id)
                .order_by(func.count().desc())
                .limit(limit)
                .all()
            )
            return [{"server_id": result[0], "count": result[1]} for result in results]
        except Exception as e:
            logger.error(f"Error in get_top_reported_servers: {e}")
            return []

    @classmethod
    def get_cheater_reports_by_user(cls, user_id: int) -> List[Dict[str, Any]]:
        def op(session):
            reports = (
                session.query(CheaterReport)
                .filter(CheaterReport.reporter_user_id == user_id)
                .order_by(CheaterReport.report_time.desc())
                .all()
            )
            return [item.__dict__ for item in reports]

        return cls._execute_db_operation(op)
