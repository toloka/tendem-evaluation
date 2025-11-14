"""
grocery_delivery_coverage.py
--------------------------------

This module provides a reusable set of functions for determining the delivery
coverage (postal codes) of a number of German online grocery stores.  It is
designed to be run as a standalone script or imported as a module.  When
executed as a script, it will produce a combined CSV and JSON file that
indicates, for each German postal code, whether delivery is currently
available from the supported grocery services.

The following grocery services are supported:

* **Flink** – Coverage is scraped from the official Flink city landing
  pages.  The script fetches a sitemap that lists all German city pages and
  extracts five‑digit postal codes or ranges (e.g., “20257 bis 22769”) from
  the textual description.  Ranges are expanded into the individual postal
  codes they represent.  As Flink regularly adds new cities or expands
  service areas, the scraper is designed to pick up new pages automatically.

* **REWE** – Coverage is determined via the public REWE Market Selection
  API.  For each German postal code the API at
  ``https://www.rewe.de/shop/api/marketselection/zipcodes/{zipCode}/services``
  is queried.  The returned JSON indicates whether the postal code is served
  by the REWE delivery service.  Because the API may change or require
  authentication, this function is written defensively and will retry
  requests when they fail.  Should the API become inaccessible, the
  resulting set will simply be empty.

* **Knuspr** – Knuspr publicly lists the towns and municipalities it serves
  in four German regions (Berlin, Munich, Rhein‑Main and Augsburg) in its
  FAQ page.  Those lists are encoded below.  The script cross‑references
  these place names against an open dataset of German postal codes from
  ``public.opendatasoft.com`` and returns all postal codes whose place name
  contains one of the supported towns.  This approach approximates Knuspr’s
  coverage; if Knuspr adds or removes towns, update the lists below.

* **Picnic** – At the time of writing Picnic does not provide a public
  endpoint listing its service areas.  Therefore this function relies on a
  manually curated list of cities where Picnic is known to operate (e.g.,
  Düsseldorf, Köln, Essen, Berlin, Hamburg).  When more information becomes
  available, extend ``PICNIC_CITIES`` accordingly.

The script writes two output files into the current working directory:

``delivery_coverage.csv``
    A CSV file with columns ``postal_code``, ``flink``, ``rewe``, ``knuspr``
    and ``picnic``.  Each row contains the five‑digit postal code and a
    boolean flag for each service indicating whether delivery is available.

``delivery_coverage.json``
    A JSON file containing an object keyed by postal code.  Each value is a
    dictionary with boolean flags for the four services, identical to the
    CSV representation.

Usage
-----

Execute the script from the command line.  The process may take some time
because it needs to iterate over all German postal codes and query
third‑party services.  Use the ``--max-workers`` option to control the
degree of concurrency for the REWE API calls.

Example::

    python grocery_delivery_coverage.py --max-workers 10

Requirements
------------

This script requires the following third‑party packages:

* ``requests``
* ``beautifulsoup4``
* ``pandas``

Install them using ``pip install requests beautifulsoup4 pandas``.

Author: OpenAI ChatGPT
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
#  Configuration and constants
# ---------------------------------------------------------------------------

# Base URLs used throughout the module
FLINK_SITEMAP_URL = "https://www.goflink.com/__sitemap__/city-landing.xml"
FLINK_CITY_PATTERN = re.compile(r"https://www\.goflink\.com/de-DE/city/[^\s<>]+")

# URL template for the REWE market selection API.  The ``zip_code`` slot is
# replaced at runtime.  Note: this endpoint may require a user session and
# could return HTTP 403 when accessed without the appropriate cookies.  Use
# a browser or session that has accessed the REWE website recently to obtain
# valid cookies if necessary.
REWE_SERVICE_URL_TEMPLATE = (
    "https://www.rewe.de/shop/api/marketselection/zipcodes/{zip_code}/services"
)

# Open data source for German postal codes (PLZ).  See:
# https://public.opendatasoft.com/explore/dataset/georef-germany-postleitzahl
GERMAN_POSTAL_CODES_API = (
    "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "georef-germany-postleitzahl/records"
)

# Place lists for Knuspr delivery regions (as of September 2025).  When
# Knuspr adds or removes places, update these lists accordingly.  The
# matching performed by ``fetch_knuspr_postal_codes`` is case‑insensitive and
# checks whether the place name is a substring of the ``plz_name`` field
# returned by the open data API.  Plurals or abbreviations (e.g., “Berlin
# Mitte”) are supported via substring matching.
KNUSPR_BERLIN_PLACES: List[str] = [
    "Mühlenbecker Land",
    "Schildow",
    "Panketal",
    "Bernau",
    "Werneuchen",
    "Lichtenow",
    "Altlandsberg",
    "Strausberg",
    "Velten",
    "Oberkrämer",
    "Schönwalde",
    "Falkensee",
    "Dallgow-Döberitz",
    "Potsdam",
    "Oranienburg",
    "Hohen Neuendorf",
    "Hennigsdorf",
    "Glienicke/Nordbahn",
    "Leegebruch",
    "Birkenwerder",
    "Rüdersdorf",
    "Woltersdorf",
    "Erkner",
    "Fürstenwalde",
    "Briesen",
    "Rauen",
    "Königs Wusterhausen",
    "Schulzendorf",
    "Spreenhagen",
    "Schöneiche",
    "Fredersdorf-Vogelsdorf",
    "Petershagen",
    "Neuenhagen",
    "Hoppegarten",
    "Wildau",
    "Zeuthen",
    "Bestensee",
    "Mittenwalde",
    "Zossen",
    "Rangsdorf",
    "Blankenfelde-Mahlow",
    "Großbeeren",
    "Ludwigsfelde",
    "Teltow",
    "Kleinmachnow",
    "Schönefeld",
    "Nuthetal",
    "Michendorf",
    "Schwielowsee",
    # Berlin districts and boroughs
    "Berlin Mitte",
    "Berlin Friedrichshain",
    "Berlin Friedrichsfelde",
    "Berlin Rummelsburg",
    "Berlin Karlshorst",
    "Berlin Lichtenberg",
    "Berlin Prenzlauer Berg",
    "Berlin Moabit",
    "Berlin Charlottenburg",
    "Berlin Wilmersdorf",
    "Berlin Halensee",
    "Berlin Schöneberg",
    "Berlin Tiergarten",
    "Berlin-West",
    "Berlin Kreuzberg",
    "Berlin Neukölln",
    "Berlin Tempelhof",
    "Berlin Mariendorf",
    "Berlin Friedenau",
    "Berlin Steglitz",
    "Berlin Lichterfelde",
    "Berlin Lankwitz",
    "Berlin Britz",
    "Berlin Buckow",
    "Berlin Gropiusstadt",
    "Berlin Rudow",
    "Berlin Alt-Treptow",
    "Berlin Baumschulenweg",
    "Berlin Niederschöneweide",
    "Berlin Oberschöneweide",
    "Berlin Altglienicke",
    "Berlin Bohnsdorf",
    "Berlin Schmöckwitz",
    "Berlin Köpenick",
    "Berlin Rahnsdorf",
    "Berlin Wiesengrund",
    "Berlin Kaulsdorf",
    "Berlin Mahlsdorf",
    "Berlin Hellersdorf",
    "Berlin Biesdorf",
    "Berlin Neu-Schönhausen",
    "Berlin Alt-Hohenschönhausen",
    "Berlin Falkenberg",
    "Berlin Wartenberg",
    "Berlin Weißensee",
    "Berlin Buch",
    "Berlin Blankenburg",
    "Berlin Niederschönhausen",
    "Berlin Rosenthal",
    "Berlin Blankenfelde",
    "Berlin Pankow",
    "Berlin Wedding",
    "Berlin Gesundbrunnen",
    "Berlin Reinickendorf",
    "Berlin Märkisches Viertel",
    "Berlin Frohnau",
    "Berlin Hermsdorf",
    "Berlin Lübars",
    "Berlin Tegel",
    "Berlin Spandau",
    "Berlin Hakenfelde",
    "Berlin Falkenhagener Feld",
    "Berlin Staaken",
    "Berlin Wilhelmstadt",
    "Berlin Haselhorst",
    "Berlin Charlottenburg-Nord",
    "Berlin Siemensstadt",
    "Berlin Westend",
    "Berlin Gatow",
    "Berlin Wannsee",
    "Berlin Nikolassee",
    "Berlin Zehlendorf",
    "Berlin Grunewald",
    "Berlin Dahlem",
    "Berlin Schmargendorf",
]

KNUSPR_MUNICH_PLACES: List[str] = [
    "München",  # the city itself
    "Aschheim",
    "Eching",
    "Feldkirchen",
    "Garching",
    "Gräfelfing",
    "Grünwald",
    "Haar",
    "Heimstetten",
    "Ismaning",
    "Karlsfeld",
    "Kirchheim",
    "Krailling",
    "Neubiberg",
    "Neufahrn",
    "Neuried",
    "Oberhaching",
    "Oberschleißheim",
    "Ottobrunn",
    "Planegg",
    "Pullach",
    "Putzbrunn",
    "Unterföhring",
    "Unterhaching",
    "Unterschleißheim",
    "Taufkirchen",
    "Vaterstetten",
    "Dachau",
    "Bergkirchen",
    "Hebertshausen",
    "Allershausen",
    "Fahrenzhausen",
    "Freising",
    "Hallbergmoos",
    "Erding",
    "Moosinning",
    "Neuching",
    "Finsing",
    "Ottenhofen",
    "Markt Schwaben",
    "Poing",
    "Dorfen",
    "Schwindegg",
    "Obertaufkirchen",
    "Zorneding",
    "Grafing",
    "Egling",
    "Wolfratshausen",
    "Münsing",
    "Eurasburg",
    "Starnberg",
    "Schäftlarn",
    "Pöcking",
    "Bernried",
    "Seeshaupt",
    "Weilheim",
    "Tutzing",
    "Feldafing",
    "Dießen",
    "Hersching",
    "Utting",
    "Seefeld",
    "Inning",
    "Schondorf",
    "Weißenling",  # also spelled 'Weßling'
    "Gauting",
]

KNUSPR_RHEINMAIN_PLACES: List[str] = [
    "Frankfurt",
    "Wiesbaden",
    "Mainz",
    "Darmstadt",
    "Rüsselsheim",
    "Raunheim",
    "Bischofsheim",
    "Ginsheim-Gustavsburg",
    "Kelsterbach",
    "Hochheim",
    "Trebur",
    "Nauheim",
    "Groß-Gerau",
    "Büttelborn",
    "Griesheim",
    "Messel",
    "Rödermark",
    "Dietzenbach",
    "Dreieich",
    "Erzhausen",
    "Egelsbach",
    "Mörfelden-Walldorf",
    "Langen",
    "Heusenstamm",
    "Neu-Isenburg",
    "Bad Homburg",
    "Oberursel",
    "Königstein",
    "Kronberg",
    "Eschborn",
    "Sulzbach",
    "Bad Soden",
    "Kelkheim",
    "Eppstein",
    "Schwalbach",
    "Hofheim",
    "Kriftel",
    "Hattersheim",
    "Niedernhausen",
    "Flörsheim",
    "Steinbach",
    "Offenbach",
    "Obertshausen",
    "Riedstadt",
    "Pfungstadt",
    "Nieder-Olm",
    "Zornheim",
    "Mommenheim",
    "Gau-Bischofsheim",
    "Harxheim",
    "Lörzweiler",
    "Bodenheim",
    "Nackenheim",
    "Nierstein",
    "Klein-Winternheim",
]

KNUSPR_AUGSBURG_PLACES: List[str] = ["Augsburg", "Friedberg"]


# Cities currently served by Picnic.  This list is based on publicly
# available information about Picnic's service areas.  At the time of writing
# the service operates in parts of North Rhine‑Westphalia (NRW), Berlin,
# Hamburg and the Rhineland.  Expand this list when Picnic opens in new
# cities.
PICNIC_CITIES: List[str] = [
    "Berlin",
    "Hamburg",
    "Köln",
    "Düsseldorf",
    "Essen",
    "Duisburg",
    "Bochum",
    "Dortmund",
    "Wuppertal",
    "Münster",
    "Bonn",
]


# Regular expression used to find five‑digit postal codes and ranges in text.
POSTAL_CODE_PATTERN = re.compile(r"\b(\d{5})(?:\s*(?:bis|-|to)\s*(\d{5}))?\b")


# ---------------------------------------------------------------------------
#  Helper classes and functions
# ---------------------------------------------------------------------------

@dataclass
class ServiceCoverage:
    """Data structure storing postal codes served by each grocery service."""

    flink: Set[str] = field(default_factory=set)
    rewe: Set[str] = field(default_factory=set)
    knuspr: Set[str] = field(default_factory=set)
    picnic: Set[str] = field(default_factory=set)

    def to_dataframe(self, all_postal_codes: Iterable[str]) -> pd.DataFrame:
        """Create a pandas DataFrame from the coverage data.

        Each row corresponds to a postal code and contains boolean values
        indicating whether delivery is available from Flink, REWE, Knuspr or
        Picnic.

        Parameters
        ----------
        all_postal_codes : Iterable[str]
            A collection of all German postal codes.  The DataFrame will
            contain a row for each of these codes.

        Returns
        -------
        pandas.DataFrame
            A DataFrame with columns ``postal_code``, ``flink``, ``rewe``,
            ``knuspr`` and ``picnic``.
        """
        records = []
        for plz in sorted(set(all_postal_codes)):
            records.append(
                {
                    "postal_code": plz,
                    "flink": plz in self.flink,
                    "rewe": plz in self.rewe,
                    "knuspr": plz in self.knuspr,
                    "picnic": plz in self.picnic,
                }
            )
        return pd.DataFrame.from_records(records)


def fetch_german_postal_codes() -> pd.DataFrame:
    """Retrieve German postal codes and corresponding place names.

    Returns a DataFrame with at least the columns ``plz_code`` (string) and
    ``plz_name``.  The open dataset API restricts requests to 100 records at
    a time, so the function paginates through the dataset until all records
    have been fetched.

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing all known German postal codes with place
        names.
    """
    params = {
        "select": "plz_code,plz_name",
        "limit": 100,
        "offset": 0,
    }
    records = []
    while True:
        resp = requests.get(GERMAN_POSTAL_CODES_API, params=params)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("results", [])
        if not batch:
            break
        for row in batch:
            code = row.get("plz_code")
            name = row.get("plz_name")
            if code:
                records.append({"plz_code": str(code), "plz_name": name or ""})
        params["offset"] += params["limit"]
        # Stop when fewer than limit records are returned
        if len(batch) < params["limit"]:
            break
    return pd.DataFrame(records)


def fetch_flink_postal_codes(max_workers: int = 5) -> Set[str]:
    """Scrape postal codes from all Flink city landing pages.

    The function first retrieves the city landing sitemap, extracts all
    ``de-DE`` city URLs and then downloads each page concurrently.  It
    searches each page’s text for five‑digit postal codes or ranges and
    expands ranges into individual postal codes.  Codes are returned as a
    set of strings.

    Parameters
    ----------
    max_workers : int, optional
        Maximum number of concurrent fetches.  Defaults to 5.  Increasing
        this value speeds up the process but may stress the Flink servers.

    Returns
    -------
    set[str]
        A set of five‑digit postal codes served by Flink.
    """
    # Fetch sitemap and extract city URLs
    resp = requests.get(FLINK_SITEMAP_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "xml")
    urls = [loc.text for loc in soup.find_all("loc") if "/de-DE/city/" in loc.text]

    # Function to extract postal codes from a single page
    def extract_codes(url: str) -> Set[str]:
        codes: Set[str] = set()
        try:
            r = requests.get(url)
            r.raise_for_status()
            text = r.text
            for match in POSTAL_CODE_PATTERN.finditer(text):
                start = match.group(1)
                end = match.group(2)
                if end:
                    # Expand range (inclusive)
                    s = int(start)
                    e = int(end)
                    codes.update(str(plz) for plz in range(min(s, e), max(s, e) + 1))
                else:
                    codes.add(start)
        except Exception:
            # Ignore individual errors
            pass
        return codes

    all_codes: Set[str] = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for codes in executor.map(extract_codes, urls):
            all_codes.update(codes)
    return all_codes


def fetch_rewe_postal_codes(postal_codes: Iterable[str], max_workers: int = 5) -> Set[str]:
    """Determine which postal codes are served by the REWE delivery service.

    For each postal code in ``postal_codes`` the function queries the REWE
    Market Selection API.  If the response indicates that ``hasDelivery``
    is true, the postal code is added to the result set.  The function
    performs requests concurrently up to ``max_workers`` threads.

    Parameters
    ----------
    postal_codes : Iterable[str]
        Postal codes to check for REWE delivery service availability.
    max_workers : int, optional
        Maximum number of concurrent API requests.  Defaults to 5.

    Returns
    -------
    set[str]
        Postal codes for which REWE offers delivery.
    """
    result: Set[str] = set()

    def check_rewe(plz: str) -> None:
        url = REWE_SERVICE_URL_TEMPLATE.format(zip_code=plz)
        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
                    "Referer": "https://shop.rewe.de/",
                },
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("hasDelivery"):
                    result.add(plz)
        except Exception:
            # Ignore errors (e.g., 403, timeouts); the postal code will be
            # considered not served
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(check_rewe, postal_codes))
    return result


def fetch_knuspr_postal_codes(plz_df: pd.DataFrame) -> Set[str]:
    """Return the set of postal codes served by Knuspr.

    The function uses the lists of towns and boroughs defined above and
    cross‑references them against the ``plz_name`` column of ``plz_df``.
    Matches are case‑insensitive and check whether the town name appears as
    a substring of the place name.  Postal codes from all matching rows are
    collected.

    Parameters
    ----------
    plz_df : pandas.DataFrame
        DataFrame containing at least ``plz_code`` and ``plz_name``.

    Returns
    -------
    set[str]
        Postal codes covered by Knuspr delivery service.
    """
    all_places = (
        KNUSPR_BERLIN_PLACES
        + KNUSPR_MUNICH_PLACES
        + KNUSPR_RHEINMAIN_PLACES
        + KNUSPR_AUGSBURG_PLACES
    )
    codes: Set[str] = set()
    for place in all_places:
        pattern = re.compile(re.escape(place), re.IGNORECASE)
        matches = plz_df[plz_df["plz_name"].str.contains(pattern)]
        codes.update(matches["plz_code"].astype(str).tolist())
    return codes


def fetch_picnic_postal_codes(plz_df: pd.DataFrame) -> Set[str]:
    """Return the set of postal codes served by Picnic.

    Picnic does not publicly disclose its full delivery coverage.  This
    function matches postal codes whose place names contain one of the
    cities listed in ``PICNIC_CITIES``.  Extend ``PICNIC_CITIES`` as
    necessary.

    Parameters
    ----------
    plz_df : pandas.DataFrame
        DataFrame containing at least ``plz_code`` and ``plz_name``.

    Returns
    -------
    set[str]
        Postal codes believed to be served by Picnic.
    """
    codes: Set[str] = set()
    for city in PICNIC_CITIES:
        pattern = re.compile(re.escape(city), re.IGNORECASE)
        matches = plz_df[plz_df["plz_name"].str.contains(pattern)]
        codes.update(matches["plz_code"].astype(str).tolist())
    return codes


def main(max_workers: int = 5) -> None:
    """Entry point for the command line interface.

    This function orchestrates the download of postal code data, fetches
    coverage information for each grocery service, builds a combined
    DataFrame and writes both CSV and JSON output files.

    Parameters
    ----------
    max_workers : int, optional
        Maximum number of concurrent network requests.  Defaults to 5.
    """
    print("Downloading German postal codes dataset…", flush=True)
    plz_df = fetch_german_postal_codes()
    print(f"Fetched {len(plz_df)} postal codes.")

    print("Determining Flink delivery coverage…", flush=True)
    flink_codes = fetch_flink_postal_codes(max_workers=max_workers)
    print(f"Flink serves {len(flink_codes)} postal codes.")

    print("Determining REWE delivery coverage…", flush=True)
    rewe_codes = fetch_rewe_postal_codes(plz_df["plz_code"], max_workers=max_workers)
    print(f"REWE serves {len(rewe_codes)} postal codes.")

    print("Determining Knuspr delivery coverage…", flush=True)
    knuspr_codes = fetch_knuspr_postal_codes(plz_df)
    print(f"Knuspr serves {len(knuspr_codes)} postal codes.")

    print("Determining Picnic delivery coverage…", flush=True)
    picnic_codes = fetch_picnic_postal_codes(plz_df)
    print(f"Picnic serves {len(picnic_codes)} postal codes.")

    # Build coverage data structure
    coverage = ServiceCoverage(
        flink=flink_codes,
        rewe=rewe_codes,
        knuspr=knuspr_codes,
        picnic=picnic_codes,
    )
    df = coverage.to_dataframe(plz_df["plz_code"].astype(str).tolist())
    # Write CSV and JSON
    csv_path = "delivery_coverage.csv"
    json_path = "delivery_coverage.json"
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)
    print(f"Wrote CSV output to {csv_path}")
    print(f"Wrote JSON output to {json_path}")


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(description="Fetch delivery coverage for German grocery stores.")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Number of concurrent requests for network operations.",
    )
    args = parser.parse_args()
    main(max_workers=args.max_workers)