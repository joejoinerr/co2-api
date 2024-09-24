"""CO2 API main app."""

import os
import sqlite3
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from statistics import mean

from fastapi import FastAPI, HTTPException, BackgroundTasks, status

from schemas import LatestReadings, Reading, ReadingInDB


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncGenerator[None, None]:
    """Sets up the application, including DB connection."""
    con = sqlite3.connect(os.environ["DB_PATH"])
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS co2(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            co2_ppm INTEGER,
            temp_celsius REAL,
            pressure_mbar REAL
        )
    """
    )
    app_.state.db = con

    try:
        yield
    finally:
        con.close()


app = FastAPI(
    title="CO\u2082 sensor API", lifespan=lifespan, debug=True, redoc_url=None
)


@app.get("/api/latest")
async def get_latest_readings() -> LatestReadings:
    """Fetches the latest and past 1h average readings."""
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
    hour_params = {"time_before": hour_ago_timestamp, "time_after": now_timestamp}
    week_ago_timestamp = now_timestamp - 604800
    week_params = {"time_before": week_ago_timestamp, "time_after": now_timestamp}

    con = app.state.db
    with con:
        hour_result = con.execute(query, hour_params).fetchall()
        week_result = con.execute(query, week_params)

    if len(hour_result) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No recent readings."
        )

    results = {
        "co2_ppm_latest": hour_result[0]["co2_ppm"],
        "co2_ppm_average_1h": round(mean(r["co2_ppm"] for r in hour_result), 2),
        "co2_ppm_average_1w": round(mean(r["co2_ppm"] for r in week_result), 2)
        "last_reading_time": hour_result[0]["recorded"]
    }
    return LatestReadings(**results)


@app.post("/api/submit", status_code=status.HTTP_201_CREATED)
async def submit_reading(reading: Reading, background_tasks: BackgroundTasks) -> ReadingInDB:
    """Creates a new reading in the database."""
    con = app.state.db
    with con:
        cur = con.execute(
            "INSERT INTO co2(co2_ppm, temp_celsius, pressure_mbar) VALUES(:co2_ppm, :temp_celsius, :pressure_mbar)",
            reading.model_dump(),
        )
        result = con.execute(
            "SELECT * FROM co2 WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    background_tasks.add_task(delete_old_entries)
    return ReadingInDB(**result)


def delete_old_entries():
    con = sqlite3.connect(os.environ["DB_PATH"])
    now_timestamp = int(time.time())
    week_ago = now_timestamp - 604800
    with con:
        con.execute("DELETE FROM co2 WHERE recorded < ?", (week_ago,))
