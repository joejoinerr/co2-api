"""CO2 API main app."""

import os
import sqlite3
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from statistics import mean

from fastapi import FastAPI, HTTPException, status

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No recent readings."
        )

    results = {
        "co2_ppm_latest": result[0]["co2_ppm"],
        "co2_ppm_average_1h": round(mean(r["co2_ppm"] for r in result), 2),
    }
    return LatestReadings(**results)


@app.post("/api/submit", status_code=status.HTTP_201_CREATED)
async def submit_reading(reading: Reading) -> ReadingInDB:
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
    return ReadingInDB(**result)
