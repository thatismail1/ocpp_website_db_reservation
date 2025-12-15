# backend/db.py

from pathlib import Path
from datetime import datetime, timezone



from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
)

from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'ocpp_cms.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class MeterLog(Base):
    __tablename__ = "meter_logs"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(64), index=True)

    group_id = Column(String(64))
    group_name = Column(String(128))
    device_type = Column(String(64))

    timestamp = Column(DateTime(timezone=True), index=True)

    user_name = Column(String(128), index=True)
    charger_name = Column(String(128), index=True)

    total_power = Column(Float)
    phase1_power = Column(Float)
    phase2_power = Column(Float)
    phase3_power = Column(Float)

    total_reactive_power = Column(Float)
    phase1_reactive_power = Column(Float)
    phase2_reactive_power = Column(Float)
    phase3_reactive_power = Column(Float)

    total_power_factor = Column(Float)
    phase1_power_factor = Column(Float)
    phase2_power_factor = Column(Float)
    phase3_power_factor = Column(Float)

    phase1_voltage = Column(Float)
    phase2_voltage = Column(Float)
    phase3_voltage = Column(Float)

    frequency = Column(Float)

    delivered_energy = Column(Float)
    supplied_energy = Column(Float)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def meter_log_to_dict(row: MeterLog):
    ts = row.timestamp
    ts_str = None
    if ts:
        ts_str = ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "ID": row.record_id,
        "groupId": row.group_id,
        "groupName": row.group_name,
        "deviceType": row.device_type,
        "timestamp": ts_str,
        "userName": row.user_name,
        "totalPower": row.total_power,
        "phase1Power": row.phase1_power,
        "phase2Power": row.phase2_power,
        "phase3Power": row.phase3_power,
        "totalReactivePower": row.total_reactive_power,
        "phase1ReactivePower": row.phase1_reactive_power,
        "phase2ReactivePower": row.phase2_reactive_power,
        "phase3ReactivePower": row.phase3_reactive_power,
        "totalPowerFactor": row.total_power_factor,
        "phase1PowerFactor": row.phase1_power_factor,
        "phase2PowerFactor": row.phase2_power_factor,
        "phase3PowerFactor": row.phase3_power_factor,
        "phase1Voltage": row.phase1_voltage,
        "phase2Voltage": row.phase2_voltage,
        "phase3Voltage": row.phase3_voltage,
        "frequency": row.frequency,
        "deliveredEnergy": row.delivered_energy,
        "suppliedEnergy": row.supplied_energy,
        "chargerName": row.charger_name,
    }
