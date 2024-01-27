import sqlite3
import time
from contextlib import asynccontextmanager
from statistics import mean

from fastapi import FastAPI, HTTPException

from schemas import Reading, ReadingInDB, LatestReadings


@asynccontextmanager
async def lifespan(app_: FastAPI):
    con = sqlite3.connect("../co2.db")
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS co2(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            co2_ppm INTEGER,
            temp_celsius REAL,
            pressure_mbar REAL
        )
    """)
    app_.state.db = con

    try:
        yield
    finally:
        con.close()


app = FastAPI(title="CO\u2082 sensor API", lifespan=lifespan, debug=True)


@app.get("/api/latest")
async def get_latest_readings() -> LatestReadings:
    con = app.state.db
    with con:
        query = """\
            SELECT
                recorded,
                co2_ppm,
                temp_celsius,
                pressure_mbar
            FROM
                co2
            WHERE
                recorded BETWEEN :time_before AND :time_after
            ORDER BY
                recorded DESC
        """
        now_timestamp = int(time.time())
        hour_ago_timestamp = now_timestamp - (60 * 60)
        params = {"time_before": hour_ago_timestamp, "time_after": now_timestamp}
        result = con.execute(query, params).fetchall()

    if len(result) == 0:
        raise HTTPException(status_code=404, detail="No recent readings.")

    results = {
        "co2_ppm_latest": result[0]["co2_ppm"],
        "co2_ppm_average_1h": round(mean(r["co2_ppm"] for r in result), 2)
    }
    return LatestReadings(**results)


@app.post("/api/submit", status_code=201)
async def submit_reading(reading: Reading) -> ReadingInDB:
    con = app.state.db
    with con:
        cur = con.execute(
            "INSERT INTO co2(co2_ppm, temp_celsius, pressure_mbar) VALUES(:co2_ppm, :temp_celsius, :pressure_mbar)",
            reading.model_dump()
        )
        result = con.execute(
            "SELECT * FROM co2 WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return ReadingInDB(**result)
