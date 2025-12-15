from ocpp.db import SessionLocal, MeterLog, init_db, meter_log_to_dict
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import jwt
import os
import json
import csv
from pathlib import Path
from collections import defaultdict


app = FastAPI(title="OCPP CMS Dashboard API")

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

security = HTTPBearer()

# Dynamically resolve data folder based on current file location
# ✅ Always point to the same data folder used by OCPP server
DATA_DIR = Path(__file__).resolve().parent / "data"
if not DATA_DIR.exists():
    fallback = Path(__file__).resolve().parents[1] / "backend" / "data"
    if fallback.exists():
        DATA_DIR = fallback
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

print(f"✅ Unified backend DATA_DIR = {DATA_DIR}")



# Define your data file paths
USERS_CSV = DATA_DIR / "users1.csv"
ENERGY_USAGE_JSON = DATA_DIR / "energy_usage.json"
ACTIVE_TRANSACTIONS_JSON = DATA_DIR / "active_transactions.json"
METER_DATA_LOG_JSON = DATA_DIR / "meter_data_log.json"
CHARGER_STATUS_JSON = DATA_DIR / "charger_status.json"

print(f"✅ Data directory: {DATA_DIR}")

def compute_lifetime_total_energy_kwh(db):
    rows = (
        db.query(MeterLog.charger_name, MeterLog.timestamp, MeterLog.delivered_energy)
        .filter(MeterLog.charger_name.isnot(None))
        .order_by(MeterLog.charger_name.asc(), MeterLog.timestamp.asc())
        .all()
    )

    by_charger = defaultdict(list)
    for charger, ts, val in rows:
        if ts is None:
            continue
        by_charger[charger.upper()].append((ts, float(val or 0)))

    total_kwh = 0.0

    for charger, samples in by_charger.items():
        if len(samples) < 2:
            continue

        samples.sort(key=lambda x: x[0])
        values = [v for _, v in samples]

        # Schneider / EVLink → cumulative Wh register
        if "SCHNEIDER" in charger or "EVLINK" in charger:
            delta_wh = max(0.0, values[-1] - values[0])
            total_kwh += delta_wh / 1000.0

        # Livoltek → incremental kWh
        else:
            kwh = 0.0
            for i in range(1, len(values)):
                if values[i] > values[i - 1]:
                    kwh += values[i] - values[i - 1]
            total_kwh += kwh

    return round(total_kwh, 3)

# Models
class LoginRequest(BaseModel):
    username: str
    password: str
    role: str = "admin"  # "admin" or "user"

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_data: Optional[Dict[str, Any]] = None

class UserQuota(BaseModel):
    id_tag: str
    header_name: str
    surname: str
    full_name: Optional[str] = None
    plan: str  # "limited" or "unlimited"
    quota_kwh: Optional[float] = None
    used_kwh: float = 0
    remaining_kwh: Optional[float] = None
    unlimited: bool = False

class UserCreate(BaseModel):
    id_tag: str
    header_name: str
    surname: str
    plan: str = "limited"
    quota_kwh: Optional[float] = 100.0

class UserUpdate(BaseModel):
    header_name: Optional[str] = None
    surname: Optional[str] = None
    plan: Optional[str] = None
    quota_kwh: Optional[float] = None

class DashboardStats(BaseModel):
    total_energy_today: float
    active_sessions: int
    total_users: int
    total_chargers: int
    active_chargers: int
    total_energy_delivered: float

# Helper functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "admin")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return {"username": username, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

def verify_admin(token_data: dict = Depends(verify_token)):
    if token_data["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return token_data["username"]

def load_json_file(filepath: Path, default=None):
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return default if default is not None else {}

def save_json_file(filepath: Path, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_users_csv():
    users = []
    if not USERS_CSV.exists():
        return users
    
    with open(USERS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append(row)
    return users

def save_users_csv(users):
    if not users:
        return
    
    fieldnames = ['id_tag', 'header name', 'surname', 'quota_kwh', 'unlimited']
    with open(USERS_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)

def get_user_quota_info(id_tag: str):
    users = load_users_csv()
    energy_usage = load_json_file(ENERGY_USAGE_JSON, {})
    
    for user in users:
        if user['id_tag'] == id_tag:
            unlimited = user.get('unlimited', 'FALSE').upper() == 'TRUE'
            quota_kwh = None if unlimited else float(user.get('quota_kwh', 0))
            used_kwh = energy_usage.get(id_tag, 0)
            remaining_kwh = None if unlimited else max(0, quota_kwh - used_kwh)
            
            return UserQuota(
                id_tag=id_tag,
                header_name=user.get('header name', ''),
                surname=user.get('surname', ''),
                full_name=f"{user.get('header name', '')} {user.get('surname', '')}",
                plan="unlimited" if unlimited else "limited",
                quota_kwh=quota_kwh,
                used_kwh=used_kwh,
                remaining_kwh=remaining_kwh,
                unlimited=unlimited
            )
    return None

def update_total_energy_delivered():
    """
    Compute lifetime delivered energy using DB instead of JSON.
    """
    from sqlalchemy import select
    from collections import defaultdict

    chargers = load_json_file(CHARGER_STATUS_JSON, {})
    totals = defaultdict(float)

    db = SessionLocal()

    try:
        rows = db.query(MeterLog.charger_name, MeterLog.delivered_energy).all()

        per_charger = defaultdict(list)

        for name, delivered in rows:
            if not name:
                continue
            per_charger[name.upper()].append(float(delivered or 0))

        for ch, vals in per_charger.items():
            vals.sort()

            if "SCHNEIDER" in ch or "EVLINK" in ch:
                delta_wh = max(0, vals[-1] - vals[0])
                totals[ch] = delta_wh / 1000.0

            elif "LIVOLTEK" in ch:
                delta = 0
                for i in range(1, len(vals)):
                    if vals[i] > vals[i - 1]:
                        delta += vals[i] - vals[i - 1]
                totals[ch] = delta

        for charger_id, ch_data in chargers.items():
            cu = charger_id.upper()
            ch_data["total_energy_delivered"] = totals.get(cu, 0)

        save_json_file(CHARGER_STATUS_JSON, chargers)

    finally:
        db.close()





# API Endpoints

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "OCPP CMS Dashboard"}

@app.post("/api/auth/login", response_model=Token)
async def login(request: LoginRequest):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    if request.role == "admin":
        # Admin authentication
        if request.username == "admin" and request.password == "admin123":
            access_token = create_access_token(
                data={"sub": request.username, "role": "admin"}, 
                expires_delta=access_token_expires
            )
            return {
                "access_token": access_token, 
                "token_type": "bearer",
                "role": "admin",
                "user_data": {"username": "admin"}
            }
    elif request.role == "user":
        # User authentication - username is RFID tag, password is evcharger2025
        if request.password == "evcharger2025":
            users = load_users_csv()
            user_found = None
            for user in users:
                if user['id_tag'] == request.username:
                    user_found = user
                    break
            
            if user_found:
                # Get user quota info
                user_info = get_user_quota_info(request.username)
                if user_info:
                    access_token = create_access_token(
                        data={"sub": request.username, "role": "user"}, 
                        expires_delta=access_token_expires
                    )
                    return {
                        "access_token": access_token, 
                        "token_type": "bearer",
                        "role": "user",
                        "user_data": {
                            "id_tag": user_info.id_tag,
                            "full_name": user_info.full_name,
                            "plan": user_info.plan
                        }
                    }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )

@app.get("/api/auth/verify")
async def verify(token_data: dict = Depends(verify_token)):
    return {
        "username": token_data["username"], 
        "role": token_data["role"],
        "authenticated": True
    }

@app.get("/api/user/dashboard")
async def get_user_dashboard(
    token_data: dict = Depends(verify_token),
    db = Depends(get_db),
):
    """
    User dashboard with:
    - User quota info
    - Charger list
    - Active session info
    - Transaction history (from DB instead of JSON file)
    """

    if token_data["role"] != "user":
        raise HTTPException(status_code=403, detail="User access required")

    id_tag = token_data["username"]
    user_info = get_user_quota_info(id_tag)

    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    # ---------------------------------------------------------
    # 1. Load chargers from charger_status.json (unchanged)
    # ---------------------------------------------------------
    chargers = load_json_file(CHARGER_STATUS_JSON, {})
    chargers_list = []

    for charger_id, cdata in chargers.items():
        cdata["id"] = charger_id
        name_upper = cdata.get("name", "").upper()
        brand = cdata.get("brand", "Unknown")

        if brand == "Unknown":
            if "LIVOLTEK" in name_upper:
                brand = "LIVOLTEK"
            elif "SCHNEIDER" in name_upper or "EVLINK" in name_upper:
                brand = "SCHNEIDER"

        cdata["brand"] = brand
        chargers_list.append(cdata)

    # ---------------------------------------------------------
    # 2. Active Session (unchanged logic)
    # ---------------------------------------------------------
    active_transactions = load_json_file(ACTIVE_TRANSACTIONS_JSON, {})
    user_active_session = None

    for trans_id, trans_data in active_transactions.items():
        if trans_data.get("id_tag") == id_tag:
            user_active_session = {
                "transaction_id": trans_id,
                "charger_id": trans_data.get("charger_id"),
                "start_time": trans_data.get("start_time"),
                "energy_delivered": trans_data.get("meter_start", 0),
            }
            break

    # ---------------------------------------------------------
    # 3. Transaction History (REPLACED — DB instead of JSON)
    # ---------------------------------------------------------
    user_transactions = []

    full_name = user_info.full_name  # match by full name
    rows = (
        db.query(MeterLog)
        .filter(MeterLog.user_name == full_name)
        .order_by(MeterLog.timestamp.desc())
        .limit(200)  # get more rows and collapse to sessions
        .all()
    )

    seen_sessions = set()

    for row in rows:
        d = meter_log_to_dict(row)

        # group multiple readings in one day → a "session"
        session_key = f"{d.get('chargerName')}_{(d.get('timestamp') or '')[:10]}"

        if session_key in seen_sessions:
            continue
        seen_sessions.add(session_key)

        user_transactions.append({
            "charger_name": d.get("chargerName"),
            "timestamp": d.get("timestamp"),
            "energy_delivered": d.get("deliveredEnergy", 0),
            "power": d.get("totalPower", 0),
        })

    user_transactions = user_transactions[:20]

    # ---------------------------------------------------------
    # 4. Final response (unchanged structure)
    # ---------------------------------------------------------
    return {
        "user_info": {
            "id_tag": user_info.id_tag,
            "full_name": user_info.full_name,
            "plan": user_info.plan,
            "quota_kwh": user_info.quota_kwh,
            "used_kwh": user_info.used_kwh,
            "remaining_kwh": user_info.remaining_kwh,
            "unlimited": user_info.unlimited,
        },
        "chargers": chargers_list,
        "active_session": user_active_session,
        "transaction_history": user_transactions,
    }


@app.get("/api/stats", response_model=DashboardStats)
async def get_dashboard_stats(db = Depends(get_db)):
    chargers = load_json_file(CHARGER_STATUS_JSON, {})
    active_transactions = load_json_file(ACTIVE_TRANSACTIONS_JSON, {})
    users = load_users_csv()

    today = datetime.now(timezone.utc).date()

    rows = db.query(MeterLog).filter(
        MeterLog.timestamp >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
        MeterLog.timestamp <= datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
    ).all()

    from collections import defaultdict
    by_charger = defaultdict(list)

    for r in rows:
        by_charger[r.charger_name].append((r.timestamp, r.delivered_energy))

    total_today = 0.0

    for ch, vals in by_charger.items():
        if len(vals) < 2:
            continue
        vals.sort(key=lambda x: x[0])
        first = vals[0][1]
        last = vals[-1][1]

        if "SCHNEIDER" in ch.upper() or "EVLINK" in ch.upper():
            total_today += max(0.0, (last - first) / 1000.0)
        else:
            total_today += max(0.0, last - first)

    # ✅ FIXED: lifetime total from DB
    total_energy = compute_lifetime_total_energy_kwh(db)

    active_chargers = sum(1 for c in chargers.values() if c.get("status") == "Charging")

    return DashboardStats(
        total_energy_today=round(total_today, 3),
        active_sessions=len(active_transactions),
        total_users=len(users),
        total_chargers=len(chargers),
        active_chargers=active_chargers,
        total_energy_delivered=total_energy,
    )







@app.get("/api/chargers")
async def get_charger_status():
    try:
        if CHARGER_STATUS_JSON.exists():
            with open(CHARGER_STATUS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)

            chargers_list = []
            for charger_id, charger_data in data.items():
                charger_data["id"] = charger_id
                brand = charger_data.get("brand", "Unknown")
                name_upper = charger_data["name"].upper()
                if brand == "Unknown":
                    if "LIVOLTEK" in name_upper:
                        brand = "LIVOLTEK"
                    elif "SCHNEIDER" in name_upper or "EVLINK" in name_upper:
                        brand = "SCHNEIDER"
                charger_data["brand"] = brand
                chargers_list.append(charger_data)

            # 👇 Return in a structure your frontend expects
            return {"chargers": chargers_list}
        else:
            print("⚠️ Charger status file missing, returning empty list.")
            return {"chargers": []}
    except Exception as e:
        print(f"Error reading charger_status.json: {e}")
        return {"chargers": []}


@app.get("/api/users", response_model=List[UserQuota])
async def get_users():

    users = load_users_csv()
    energy_usage = load_json_file(ENERGY_USAGE_JSON, {})
    
    result = []
    for user in users:
        id_tag = user['id_tag']
        unlimited = user.get('unlimited', 'FALSE').upper() == 'TRUE'
        quota_kwh = None if unlimited else float(user.get('quota_kwh', 0))
        used_kwh = energy_usage.get(id_tag, 0)
        remaining_kwh = None if unlimited else max(0, quota_kwh - used_kwh) if quota_kwh else 0
        
        result.append(UserQuota(
            id_tag=id_tag,
            header_name=user.get('header name', ''),
            surname=user.get('surname', ''),
            full_name=f"{user.get('header name', '')} {user.get('surname', '')}",
            plan="unlimited" if unlimited else "limited",
            quota_kwh=quota_kwh,
            used_kwh=used_kwh,
            remaining_kwh=remaining_kwh,
            unlimited=unlimited
        ))
    
    return result

@app.post("/api/users", response_model=UserQuota)
async def create_user(user: UserCreate, username: str = Depends(verify_admin)):
    users = load_users_csv()
    
    # Check if user already exists
    if any(u['id_tag'] == user.id_tag for u in users):
        raise HTTPException(status_code=400, detail="User with this ID tag already exists")
    
    unlimited = user.plan == "unlimited"
    new_user = {
        'id_tag': user.id_tag,
        'header name': user.header_name,
        'surname': user.surname,
        'quota_kwh': '0' if unlimited else str(user.quota_kwh),
        'unlimited': 'TRUE' if unlimited else 'FALSE'
    }
    
    users.append(new_user)
    save_users_csv(users)
    
    return get_user_quota_info(user.id_tag)

@app.put("/api/users/{id_tag}", response_model=UserQuota)
async def update_user(id_tag: str, user_update: UserUpdate, username: str = Depends(verify_admin)):
    users = load_users_csv()
    
    user_found = False
    for user in users:
        if user['id_tag'] == id_tag:
            user_found = True
            if user_update.header_name:
                user['header name'] = user_update.header_name
            if user_update.surname:
                user['surname'] = user_update.surname
            if user_update.plan:
                unlimited = user_update.plan == "unlimited"
                user['unlimited'] = 'TRUE' if unlimited else 'FALSE'
                if unlimited:
                    user['quota_kwh'] = '0'
            if user_update.quota_kwh is not None and user_update.plan != "unlimited":
                user['quota_kwh'] = str(user_update.quota_kwh)
            break
    
    if not user_found:
        raise HTTPException(status_code=404, detail="User not found")
    
    save_users_csv(users)
    return get_user_quota_info(id_tag)

@app.delete("/api/users/{id_tag}")
async def delete_user(id_tag: str, username: str = Depends(verify_admin)):
    users = load_users_csv()
    
    users = [u for u in users if u['id_tag'] != id_tag]
    save_users_csv(users)
    
    # Also remove from energy usage
    energy_usage = load_json_file(ENERGY_USAGE_JSON, {})
    if id_tag in energy_usage:
        del energy_usage[id_tag]
        save_json_file(ENERGY_USAGE_JSON, energy_usage)
    
    return {"message": "User deleted successfully"}

@app.post("/api/users/{id_tag}/reset")
async def reset_user_usage(id_tag: str, username: str = Depends(verify_admin)):
    energy_usage = load_json_file(ENERGY_USAGE_JSON, {})
    
    if id_tag in energy_usage:
        energy_usage[id_tag] = 0
        save_json_file(ENERGY_USAGE_JSON, energy_usage)
    
    return {"message": f"Usage reset for user {id_tag}", "user": get_user_quota_info(id_tag)}

@app.get("/api/transactions")
async def get_transactions(username: str = Depends(verify_admin)):
    transactions = load_json_file(ACTIVE_TRANSACTIONS_JSON, {})
    return {"transactions": transactions}

@app.get("/api/logs")
async def get_logs(
    username: str = Depends(verify_admin),
    charger: Optional[str] = None,
    limit: Optional[int] = None,
    db = Depends(get_db)
):
    query = db.query(MeterLog).order_by(MeterLog.timestamp.desc())

    if charger:
        query = query.filter(MeterLog.charger_name == charger)

    if limit:
        query = query.limit(limit)

    rows = query.all()
    logs = [meter_log_to_dict(r) for r in rows]

    return {"logs": logs}

@app.get("/api/usage/history")
async def get_usage_history(days: int = 7, db = Depends(get_db)):
    """
    Daily aggregated energy usage (kWh) for all chargers.
    Correctly computes deltas using timestamp order.
    """

    from collections import defaultdict
    from datetime import datetime, timedelta, timezone

    if days <= 0:
        return {"history": []}

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    # ---------------------------------------------------------
    # Load rows from DB in date range
    # ---------------------------------------------------------
    rows = (
        db.query(MeterLog)
        .filter(
            MeterLog.timestamp >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc),
            MeterLog.timestamp <= datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc),
        )
        .order_by(MeterLog.timestamp.asc())
        .all()
    )

    # ---------------------------------------------------------
    # Group by (date, charger) → store (timestamp, value)
    # ---------------------------------------------------------
    grouped = defaultdict(list)

    for row in rows:
        if not row.timestamp:
            continue

        date_key = row.timestamp.date().isoformat()
        charger = (row.charger_name or "UNKNOWN").upper()
        energy = row.delivered_energy or 0

        grouped[(date_key, charger)].append((row.timestamp, energy))

    # ---------------------------------------------------------
    # Compute daily totals
    # ---------------------------------------------------------
    per_day = defaultdict(float)

    for (date_key, charger), samples in grouped.items():
        if len(samples) < 2:
            continue

        # ✅ IMPORTANT: sort by timestamp, NOT by value
        samples.sort(key=lambda x: x[0])
        values = [v for _, v in samples]

        # Schneider / EVLink → cumulative Wh register
        if "SCHNEIDER" in charger or "EVLINK" in charger:
            delta_wh = max(0, values[-1] - values[0])
            per_day[date_key] += delta_wh / 1000.0  # Wh → kWh

        # Livoltek → incremental kWh values
        elif "LIVOLTEK" in charger:
            kwh = 0.0
            for i in range(1, len(values)):
                if values[i] > values[i - 1]:
                    kwh += values[i] - values[i - 1]
            per_day[date_key] += kwh

    # ---------------------------------------------------------
    # Build response (frontend expects this format)
    # ---------------------------------------------------------
    history = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).isoformat()
        history.append({
            "date": d,
            "energy_kwh": round(per_day.get(d, 0.0), 3)
        })

    return {"history": history}






if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)