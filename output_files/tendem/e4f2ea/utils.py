import time
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import pandas as pd

logger = logging.getLogger("coverage.utils")

@dataclass
class RateLimiter:
    max_per_minute: int
    last_reset_ts: float = time.time()
    count: int = 0

    def wait(self):
        now = time.time()
        window = 60.0
        if now - self.last_reset_ts >= window:
            self.last_reset_ts = now
            self.count = 0
        if self.count >= self.max_per_minute:
            sleep_for = window - (now - self.last_reset_ts)
            if sleep_for > 0:
                logger.debug(f"RateLimiter sleeping for {sleep_for:.2f}s")
                time.sleep(sleep_for)
            self.last_reset_ts = time.time()
            self.count = 0
        self.count += 1


def load_plz_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"zipcode": str}, encoding="utf-8")
    if "zipcode" not in df.columns:
        raise ValueError("Dataset must contain 'zipcode' column")
    df["zipcode"] = df["zipcode"].astype(str).str.zfill(5)
    for col in ("latitude", "longitude"):
        if col not in df.columns:
            raise ValueError(f"Dataset missing required column: {col}")
    df = df.dropna(subset=["latitude", "longitude"])
    df = df.drop_duplicates(subset=["zipcode"], keep='first') 
    df.rename(columns={"place": "city", "state": "state"}, inplace=True)
    return df[["zipcode", "city", "state", "latitude", "longitude"]]


def plz_to_coordinates(plz: str, df: pd.DataFrame) -> Optional[Tuple[float, float]]:
    row = df.loc[df["zipcode"] == plz]
    if row.empty:
        return None
    lat = float(row.iloc[0]["latitude"]) 
    lon = float(row.iloc[0]["longitude"]) 
    return lat, lon


def pick_representative_address(plz: str, df: pd.DataFrame, rep_streets: Dict[str, str], default_house_number: int) -> Optional[Dict[str, str]]:
    row = df.loc[df["zipcode"] == plz]
    if row.empty:
        return None
    city = str(row.iloc[0]["city"]) if pd.notna(row.iloc[0]["city"]) else ""
    street = rep_streets.get(city) or "Hauptstraße"
    return {
        "street": street,
        "house_number": str(default_house_number),
        "postcode": plz,
        "city": city or ""
    }
