import logging
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, Boolean, Column
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Integer, String, Text, create_engine, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import settings

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
    ABSOLVED = "absolved"


class VerifiedLegitFields(Enum):
    TABLE_NAME = "verified_legit"
    ID = "id"
    VERIFIER_USER_ID = "verifier_user_id"
    SERVER_ID = "server_id"
    VERIFIED_TIME = "verified_time"
    TARKOV_GAME_NAME = "tarkov_game_name"
    TARKOV_PROFILE_ID = "tarkov_profile_id"
    TWITCH_NAME = "twitch_name"
    NOTES = "notes"


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
    report_type = Column(SQLAlchemyEnum(ReportType, create_type=True))
    absolved = Column(Boolean, default=False)


class VerifiedLegit(Base):
    __tablename__ = VerifiedLegitFields.TABLE_NAME.value
    id = Column(Integer, primary_key=True, autoincrement=True)
    verifier_user_id = Column(BigInteger)
    server_id = Column(BigInteger)
    verified_time = Column(BigInteger)
    tarkov_game_name = Column(String(255))
    tarkov_profile_id = Column(BigInteger)
    twitch_name = Column(String(255))
    notes = Column(Text)


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
    def add_guild_server_settings(cls, server_id: int, channel_id: int) -> None:
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
    def get_server_settings(cls, server_id: Optional[int] = None) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(ServerSettings)
            if server_id:
                query = query.filter_by(**{ServerSettingsFields.SERVER_ID.value: server_id})
            return [item.__dict__ for item in query.all()]

        return cls._execute_db_operation(op)

    @classmethod
    def update_guild_server_settings(cls, server_id: int, channel_id: int) -> None:
        def op(session):
            session.query(ServerSettings).filter(ServerSettings.server_id == server_id).update(
                {ServerSettingsFields.CHANNEL_ID.value: channel_id},
                synchronize_session=False,
            )
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def delete_server_settings(cls, server_id: int) -> None:
        def op(session):
            session.query(ServerSettings).filter(ServerSettings.server_id == server_id).delete(synchronize_session=False)
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
        absolved: Boolean,
    ) -> None:
        def op(session):
            session.add(
                CheaterReport(
                    **{
                        CheaterReportFields.REPORTER_USER_ID.value: reporter_user_id,
                        CheaterReportFields.SERVER_ID.value: server_id,
                        CheaterReportFields.CHEATER_GAME_NAME.value: cheater_game_name,
                        CheaterReportFields.CHEATER_PROFILE_ID.value: cheater_profile_id,
                        CheaterReportFields.REPORT_TIME.value: report_time,
                        CheaterReportFields.REPORT_TYPE.value: report_type,
                        CheaterReportFields.ABSOLVED.value: absolved,
                    }
                )
            )
            session.commit()

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
                query = query.filter_by(**{CheaterReportFields.REPORT_TYPE.value: report_type})
            if reporter_user_id:
                query = query.filter_by(**{CheaterReportFields.REPORTER_USER_ID.value: reporter_user_id})
            if server_id:
                query = query.filter_by(**{CheaterReportFields.SERVER_ID.value: server_id})
            return [item.__dict__ for item in query.all()]

        return cls._execute_db_operation(op)

    @classmethod
    def update_cheater_report(cls, id: int, updates: Dict[str, Any]) -> None:
        def op(session):
            session.query(CheaterReport).filter(CheaterReport.id == id).update(updates, synchronize_session=False)
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def delete_cheater_report(cls, id: int) -> None:
        def op(session):
            session.query(CheaterReport).filter(CheaterReport.id == id).delete(synchronize_session=False)
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def get_comprehensive_cheater_details(cls, cheater_id: int) -> Optional[Dict[str, Any]]:
        def op(session):
            cheater = cls.get_cheater_basic_info(session, cheater_id)
            verified_status = cls.check_verified_legit_status(cheater_id)

            if not cheater or verified_status["is_verified"]:
                return None

            for report_type in ReportType:
                total_reports_key = f"total_{report_type.name.lower()}_reports"
                last_reported_by_key = f"last_{report_type.name.lower()}_reported_by"
                last_report_time_key = f"last_{report_type.name.lower()}_report_time"
                most_reported_by_key = f"most_{report_type.name.lower()}_reported_by"

                cheater[total_reports_key] = cls.count_reports(session, cheater_id, report_type, absolved=False)

                last_report = cls.get_last_report(session, cheater_id, report_type, absolved=False)
                if last_report:
                    cheater[last_reported_by_key] = last_report.reporter_user_id
                    cheater[last_report_time_key] = last_report.report_time
                else:
                    cheater[last_reported_by_key] = None
                    cheater[last_report_time_key] = None

                most_reported_by = cls.get_most_reported_by(session, cheater_id, report_type, absolved=False)
                cheater[most_reported_by_key] = most_reported_by

            cheater["most_reported_server"] = cls.get_most_reported_server(session, cheater_id, absolved=False)
            cheater["top_reported_servers"] = cls.get_top_reported_servers(session, cheater_id, absolved=False)

            return cheater

        return cls._execute_db_operation(op)

    @staticmethod
    def get_cheater_basic_info(session, cheater_id: int) -> Optional[Dict[str, Any]]:
        cheater = session.query(CheaterReport).filter_by(cheater_profile_id=cheater_id).order_by(CheaterReport.report_time.desc()).first()
        return {"id": cheater.cheater_profile_id, "name": cheater.cheater_game_name} if cheater else None

    @staticmethod
    def count_reports(session, cheater_id: int, report_type: ReportType, absolved: bool = False) -> int:
        return (
            session.query(CheaterReport)
            .filter_by(
                cheater_profile_id=cheater_id,
                report_type=report_type,
                absolved=absolved,
            )
            .count()
        )

    @staticmethod
    def get_most_reported_by(session, cheater_id: int, report_type: ReportType, absolved: bool = False) -> Optional[Dict[str, Any]]:
        result = (
            session.query(CheaterReport.reporter_user_id, func.count().label("report_count"))
            .filter_by(
                cheater_profile_id=cheater_id,
                report_type=report_type,
                absolved=absolved,
            )
            .group_by(CheaterReport.reporter_user_id)
            .order_by(func.count().desc())
            .first()
        )
        return {"user_id": result[0], "count": result[1]} if result else None

    @staticmethod
    def get_most_reported_server(session, cheater_id: int, absolved: bool = False) -> Optional[Dict[str, Any]]:
        result = (
            session.query(CheaterReport.server_id, func.count().label("report_count"))
            .filter_by(cheater_profile_id=cheater_id, absolved=absolved)
            .group_by(CheaterReport.server_id)
            .order_by(func.count().desc())
            .first()
        )
        return {"server_id": result[0], "count": result[1]} if result else None

    @staticmethod
    def get_last_report(session, cheater_id: int, report_type: ReportType, absolved: bool = False):
        return (
            session.query(CheaterReport)
            .filter_by(
                cheater_profile_id=cheater_id,
                report_type=report_type,
                absolved=absolved,
            )
            .order_by(CheaterReport.report_time.desc())
            .first()
        )

    @classmethod
    def get_cheater_reports_by_type(cls, report_type: ReportType, absolved: bool = False) -> List[Dict[str, Any]]:
        def op(session):
            query = session.query(CheaterReport).filter_by(
                **{
                    CheaterReportFields.REPORT_TYPE.value: report_type,
                    CheaterReportFields.ABSOLVED.value: absolved,
                }
            )
            return [item.__dict__ for item in query.all()]

        return cls._execute_db_operation(op)

    @classmethod
    def get_all_cheaters(cls) -> List[Dict[str, Any]]:
        def op(session):
            all_cheaters = (
                session.query(
                    CheaterReport.cheater_profile_id,
                    CheaterReport.cheater_game_name,
                    CheaterReport.report_time,
                    CheaterReport.report_type,
                )
                .filter(CheaterReport.absolved == False)
                .all()
            )

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
    def get_top_reported_servers(session, cheater_id: int, absolved: bool = False, limit: int = 3) -> List[Dict[str, Any]]:
        results = (
            session.query(CheaterReport.server_id, func.count().label("report_count"))
            .filter_by(cheater_profile_id=cheater_id, absolved=absolved)
            .group_by(CheaterReport.server_id)
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )
        return [{"server_id": result[0], "count": result[1]} for result in results]

    @classmethod
    def get_cheater_reports_by_user(cls, user_id: int, absolved: bool = False) -> List[Dict[str, Any]]:
        def op(session):
            reports = (
                session.query(CheaterReport)
                .filter(CheaterReport.reporter_user_id == user_id)
                .filter(CheaterReport.absolved == absolved)
                .order_by(CheaterReport.report_time.desc())
                .all()
            )
            return [item.__dict__ for item in reports]

        return cls._execute_db_operation(op)

    @classmethod
    def get_cheater_reports_by_type_and_user(cls, report_type: ReportType, user_id: int, absolved: bool = False) -> List[Dict[str, Any]]:
        def op(session):
            reports = (
                session.query(CheaterReport)
                .filter(CheaterReport.report_type == report_type)
                .filter(CheaterReport.reporter_user_id == user_id)
                .filter(CheaterReport.absolved == absolved)
                .order_by(CheaterReport.report_time.desc())
                .all()
            )
            return [item.__dict__ for item in reports]

        return cls._execute_db_operation(op)

    @classmethod
    def add_verified_legit(
        cls,
        verifier_user_id: int,
        server_id: int,
        verified_time: int,
        tarkov_game_name: str,
        tarkov_profile_id: int,
        twitch_name: str,
        notes: str,
    ) -> None:
        def op(session):
            session.add(
                VerifiedLegit(
                    **{
                        VerifiedLegitFields.VERIFIER_USER_ID.value: verifier_user_id,
                        VerifiedLegitFields.SERVER_ID.value: server_id,
                        VerifiedLegitFields.VERIFIED_TIME.value: verified_time,
                        VerifiedLegitFields.TARKOV_GAME_NAME.value: tarkov_game_name,
                        VerifiedLegitFields.TARKOV_PROFILE_ID.value: tarkov_profile_id,
                        VerifiedLegitFields.TWITCH_NAME.value: twitch_name,
                        VerifiedLegitFields.NOTES.value: notes,
                    }
                )
            )
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def mark_cheater_reports_as_absolved(cls, tarkov_profile_id: int) -> None:
        def op(session):
            session.query(CheaterReport).filter(CheaterReport.cheater_profile_id == tarkov_profile_id).update(
                {CheaterReportFields.ABSOLVED.value: True}, synchronize_session=False
            )
            session.commit()

        cls._execute_db_operation(op)

    @classmethod
    def add_and_mark_verified_legit(
        cls,
        verifier_user_id: int,
        server_id: int,
        verified_time: int,
        tarkov_game_name: str,
        tarkov_profile_id: int,
        twitch_name: str,
        notes: str,
    ) -> None:
        def op(session):
            cls.add_verified_legit(
                verifier_user_id,
                server_id,
                verified_time,
                tarkov_game_name,
                tarkov_profile_id,
                twitch_name,
                notes,
            )
            cls.mark_cheater_reports_as_absolved(tarkov_profile_id)

        cls._execute_db_operation(op)

    @classmethod
    def check_verified_legit_status(cls, tarkov_profile_id: int) -> Dict[str, Any]:
        def op(session):
            query = session.query(VerifiedLegit).filter(VerifiedLegit.tarkov_profile_id == tarkov_profile_id)
            results = query.all()
            is_verified = len(results) > 0
            verifier_ids = [result.verifier_user_id for result in results]
            verification_times = [result.verified_time for result in results]
            tarkov_game_names = [result.tarkov_game_name for result in results]

            twitch_name = next((result.twitch_name for result in results if result.twitch_name), None)

            return {
                "is_verified": is_verified,
                "count": len(results),
                "verifier_ids": verifier_ids,
                "verification_times": verification_times,
                "tarkov_game_names": tarkov_game_names,
                "twitch_name": twitch_name,
            }

        return cls._execute_db_operation(op)

    @classmethod
    def get_all_verified_users(cls) -> List[Dict[str, Any]]:
        def op(session):
            verified_users = session.query(VerifiedLegit).order_by(VerifiedLegit.verified_time.desc()).all()
            return [
                {
                    "tarkov_profile_id": user.tarkov_profile_id,
                    "tarkov_game_name": user.tarkov_game_name,
                    "twitch_name": user.twitch_name,
                    "verifier_user_id": user.verifier_user_id,
                    "verified_time": user.verified_time,
                }
                for user in verified_users
            ]

        return cls._execute_db_operation(op)

    @classmethod
    def get_comprehensive_verified_details(cls, verified_user_id: int) -> Optional[Dict[str, Any]]:
        def op(session):
            verified_user = (
                session.query(VerifiedLegit)
                .filter(VerifiedLegit.tarkov_profile_id == verified_user_id)
                .order_by(VerifiedLegit.verified_time.asc())
                .first()
            )

            if not verified_user:
                return None

            details = {
                "tarkov_profile_id": verified_user.tarkov_profile_id,
                "tarkov_game_name": verified_user.tarkov_game_name,
                "twitch_name": verified_user.twitch_name,
                "verifier_user_id": verified_user.verifier_user_id,
                "verified_time": verified_user.verified_time,
            }

            # Get all verifications for this user
            all_verifications = (
                session.query(VerifiedLegit)
                .filter(VerifiedLegit.tarkov_profile_id == verified_user_id)
                .order_by(VerifiedLegit.verified_time.desc())
                .all()
            )

            details["verification_count"] = len(all_verifications)
            details["first_verified_time"] = all_verifications[-1].verified_time if all_verifications else None
            details["unique_verifiers"] = list(set(v.verifier_user_id for v in all_verifications))

            # Collect all notes
            details["notes"] = [
                {
                    "content": v.notes,
                    "verifier_user_id": v.verifier_user_id,
                    "timestamp": v.verified_time,
                }
                for v in all_verifications
                if v.notes
            ]

            return details

        return cls._execute_db_operation(op)
