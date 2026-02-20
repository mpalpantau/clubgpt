#!/usr/bin/env python3
"""
Impect API Sync for ClubGPT
Pulls match and player performance data from Impect's Analysis Portal API.

Uses /v1/analysis/ endpoints (not /v5/customerapi/ which requires separate API access).
Auth: OAuth2 password grant via Keycloak -> Bearer token.
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

# Impect API config
OIDC_TOKEN_URL = "https://login.impect.com/auth/realms/production/protocol/openid-connect/token"
API_BASE = "https://api.impect.com"
CLIENT_ID = "api"

# Brisbane Roar config
SQUAD_ID = 6375
COMPETITION_ITERATION_ID = 1608  # A-League Men 2025-26
COMPETITION_NAME = "A-League Men"
SEASON = "2025-26"

# Match metadata scraped from portal (matchId -> {matchday, date, venue, score})
MATCH_META = {
    234078: {"matchday": 1,  "date": "2026-01-03", "venue": "home", "goals_for": 0, "goals_against": 3},
    234086: {"matchday": 3,  "date": "2026-01-06", "venue": "away", "goals_for": 1, "goals_against": 0},
    234093: {"matchday": 4,  "date": "2026-01-16", "venue": "away", "goals_for": 1, "goals_against": 2},
    234102: {"matchday": 5,  "date": "2025-10-26", "venue": "away", "goals_for": 2, "goals_against": 1},
    234106: {"matchday": 6,  "date": "2025-12-13", "venue": "away", "goals_for": 0, "goals_against": 0},
    234112: {"matchday": 7,  "date": "2026-01-24", "venue": "home", "goals_for": 2, "goals_against": 3},
    234120: {"matchday": 8,  "date": "2025-11-23", "venue": "away", "goals_for": 1, "goals_against": 1},
    234128: {"matchday": 10, "date": "2025-11-09", "venue": "home", "goals_for": 3, "goals_against": 0},
    234147: {"matchday": 13, "date": "2025-10-17", "venue": "home", "goals_for": 1, "goals_against": 0},
    234164: {"matchday": 16, "date": "2025-11-28", "venue": "home", "goals_for": 1, "goals_against": 0},
    234175: {"matchday": 17, "date": "2025-12-31", "venue": "away", "goals_for": 1, "goals_against": 2},
    234184: {"matchday": 19, "date": "2026-01-31", "venue": "away", "goals_for": 4, "goals_against": 1},
    234194: {"matchday": 21, "date": "2025-10-31", "venue": "home", "goals_for": 0, "goals_against": 0},
    234205: {"matchday": 22, "date": "2025-12-07", "venue": "away", "goals_for": 0, "goals_against": 1},
    234209: {"matchday": 23, "date": "2026-02-07", "venue": "home", "goals_for": 1, "goals_against": 2},
    234212: {"matchday": 24, "date": "2026-01-09", "venue": "home", "goals_for": 0, "goals_against": 2},
    234223: {"matchday": 25, "date": "2025-12-19", "venue": "away", "goals_for": 2, "goals_against": 1},
    234228: {"matchday": 26, "date": "2026-02-14", "venue": "away", "goals_for": 1, "goals_against": 1},
}

MATCH_IDS = sorted(MATCH_META.keys())

# Comprehensive KPI list covering all portal tabs
MATCH_KPIS = [
    # xG / Threat
    "pxtPosSum", "PACKING_NSXG", "PACKING_XG", "POSTSHOT_XG",
    # Ball progression (packing)
    "OFFENSIVE_PLAY_DZ", "OFFENSIVE_PLAY", "REMOVE_OPPONENTS_DZ", "REMOVE_OPPONENTS",
    "CRITICAL_BALL_LOSS_NUMBER", "REMOVE_TEAMMATES",
    # Ratios
    "reversePlayRatio", "addOpponentsRatio", "offensivePlayPerRemovedTeammates",
    "addTeammatesRatio", "addTeammatesDefendersRatio", "removeOpponentsRatio",
    # Opponent data
    "OFFENSIVE_PLAY_DZ:opponent", "OFFENSIVE_PLAY:opponent",
    # Standard data
    "ballPossessionRatio", "passRatio", "successfulPassesClean", "unsuccessfulPassesClean",
    "duelsRatio", "groundDuelsRatio", "WON_GROUND_DUELS",
    "aerialDuelsRatio", "WON_AERIAL_DUELS",
    "SHOT_AT_GOAL_NUMBER", "SHOT_AT_GOAL_NUMBER_ON_TARGET",
    "SECOND_BALL_WIN", "SECOND_BALL_WIN:opponent", "secondBallWinsPercent",
    # Pressing
    "oppGkUnderPressurePercent", "meanPressureHeight", "meanPressureOppDef",
    "forcedHighPassesPercent", "meanPressureBtl",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def get_access_token(username: str, password: str) -> str:
    """Authenticate with Impect via OAuth2 password grant."""
    resp = requests.post(OIDC_TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "grant_type": "password",
        "username": username,
        "password": password,
    })
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise ValueError(f"No access_token in response: {resp.json()}")
    return token


def api_get(token: str, path: str, params: dict = None) -> dict:
    """GET request to Impect API."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}{path}", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


def api_post(token: str, path: str, body: dict) -> dict:
    """POST request to Impect API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(f"{API_BASE}{path}", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


def get_squad_names(token: str) -> dict:
    """Get mapping of squad ID -> name."""
    data = api_get(token, "/v1/analysis/squads")
    squads = data.get("data", [])
    return {s["id"]: s["name"] for s in squads}


def get_players(token: str, squad_id: int = SQUAD_ID) -> list:
    """Get player roster for a squad."""
    data = api_get(token, f"/v1/analysis/squads/{squad_id}/players")
    return data.get("data", [])


def get_match_kpis(token: str, match_id: int, kpis: list = None) -> dict:
    """Get KPI data for a single match."""
    if kpis is None:
        kpis = MATCH_KPIS

    body = {
        "kpisAndScores": kpis,
        "matchId": match_id,
        "squadId": SQUAD_ID,
        "competitionIterationId": COMPETITION_ITERATION_ID,
        "compareWithMode": "OPPONENT",
    }
    data = api_post(token, "/v1/analysis/performances/squads/single-match", body)
    performances = data.get("data", {}).get("performances", [])

    result = {"brisbane": None, "opponent": None}
    for perf in performances:
        kpi_values = {}
        for k, v in perf.get("kpisAndScores", {}).items():
            kpi_values[k] = v.get("value")

        entry = {
            "squad_id": perf["squadId"],
            "opponent_squad_id": perf.get("opponentSquadId"),
            "match_id": perf["matchId"],
            "kpis": kpi_values,
        }
        if perf["squadId"] == SQUAD_ID:
            result["brisbane"] = entry
        else:
            result["opponent"] = entry

    return result


def get_season_kpis(token: str, kpis: list = None) -> dict:
    """Get season-average KPI data."""
    if kpis is None:
        kpis = MATCH_KPIS

    body = {
        "kpisAndScores": kpis,
        "squadId": SQUAD_ID,
        "compareSetSquadId": SQUAD_ID,
        "competitionIterationId": COMPETITION_ITERATION_ID,
        "homeAndAway": "HOME_AND_AWAY",
        "compareSet": "ALL_STEPS",
    }
    data = api_post(token, "/v1/analysis/performances/squads/single-iteration", body)
    performances = data.get("data", {}).get("performances", [])

    for perf in performances:
        if perf.get("squadId") == SQUAD_ID:
            return {k: v.get("value") for k, v in perf.get("kpisAndScores", {}).items()}
    return {}


def build_match_data(token: str, match_ids: list = None) -> dict:
    """Pull all match data and build the matches.json structure."""
    if match_ids is None:
        match_ids = MATCH_IDS

    squad_names = get_squad_names(token)
    players = get_players(token)

    matches = []
    for i, match_id in enumerate(match_ids):
        print(f"  Fetching match {match_id} ({i+1}/{len(match_ids)})...")
        try:
            result = get_match_kpis(token, match_id)
            time.sleep(0.15)  # Rate limit: 10 req/s

            br = result.get("brisbane")
            opp = result.get("opponent")
            if not br:
                print(f"    WARNING: No Brisbane Roar data for match {match_id}")
                continue

            opp_id = br.get("opponent_squad_id")
            opp_name = squad_names.get(opp_id, f"Squad {opp_id}")
            opp_kpis = opp.get("kpis", {}) if opp else {}
            br_kpis = br.get("kpis", {})

            meta = MATCH_META.get(match_id, {})
            gf = meta.get("goals_for", 0)
            ga = meta.get("goals_against", 0)
            result_str = f"{'W' if gf > ga else 'L' if gf < ga else 'D'} {gf}-{ga}"

            match_entry = {
                "match_id": match_id,
                "matchday": meta.get("matchday", i + 1),
                "date": meta.get("date", ""),
                "venue": meta.get("venue", ""),
                "result": result_str,
                "goals_for": gf,
                "goals_against": ga,
                "opponent": opp_name,
                "opponent_squad_id": opp_id,
                "metrics": {
                    "expected_goals": {
                        "packing_xg": round(br_kpis.get("PACKING_XG", 0), 2),
                        "shot_based_xg": round(br_kpis.get("PACKING_NSXG", 0), 2),
                        "post_shot_xg": round(br_kpis.get("POSTSHOT_XG", 0), 2),
                        "developed_goal_threat": round(br_kpis.get("pxtPosSum", 0), 2),
                    },
                    "buildup": {
                        "ball_progression": round(br_kpis.get("OFFENSIVE_PLAY", 0), 1),
                        "breaking_opponent_defence": round(br_kpis.get("OFFENSIVE_PLAY_DZ", 0), 1),
                        "defensive_ball_control": round(br_kpis.get("REMOVE_TEAMMATES", 0), 1),
                        "critical_ball_loss": round(br_kpis.get("CRITICAL_BALL_LOSS_NUMBER", 0)),
                        "offensive_interventions": round(br_kpis.get("REMOVE_OPPONENTS", 0), 1),
                    },
                    "opponent": {
                        "opponent_ball_progression": round(opp_kpis.get("OFFENSIVE_PLAY", br_kpis.get("OFFENSIVE_PLAY:opponent", 0)), 1),
                        "opponent_breaking_defence": round(opp_kpis.get("OFFENSIVE_PLAY_DZ", br_kpis.get("OFFENSIVE_PLAY_DZ:opponent", 0)), 1),
                    },
                    "possession": {
                        "ball_possession_rate": round(br_kpis.get("ballPossessionRatio", 0), 3),
                        "passing_accuracy": round(br_kpis.get("passRatio", 0), 3),
                        "successful_passes": round(br_kpis.get("successfulPassesClean", 0)),
                        "unsuccessful_passes": round(br_kpis.get("unsuccessfulPassesClean", 0)),
                    },
                    "duels": {
                        "duel_rate": round(br_kpis.get("duelsRatio", 0), 3),
                        "ground_duel_success": round(br_kpis.get("groundDuelsRatio", 0), 3),
                        "aerial_duel_success": round(br_kpis.get("aerialDuelsRatio", 0), 3),
                    },
                    "shots": {
                        "total_shots": round(br_kpis.get("SHOT_AT_GOAL_NUMBER", 0)),
                        "shots_on_target": round(br_kpis.get("SHOT_AT_GOAL_NUMBER_ON_TARGET", 0)),
                    },
                    "pressing": {
                        "pressuring_gk_pct": round(br_kpis.get("oppGkUnderPressurePercent", 0), 2),
                        "avg_pressure_height_m": round(br_kpis.get("meanPressureHeight", 0), 1),
                        "avg_pressure_buildup": round(br_kpis.get("meanPressureOppDef", 0), 2),
                        "forced_high_passes_pct": round(br_kpis.get("forcedHighPassesPercent", 0), 2),
                        "avg_pressure_counter_press": round(br_kpis.get("meanPressureBtl", 0), 2),
                    },
                    "ratios": {
                        "reverse_play": round(br_kpis.get("reversePlayRatio", 0), 3),
                        "add_opponents": round(br_kpis.get("addOpponentsRatio", 0), 3),
                        "remove_opponents": round(br_kpis.get("removeOpponentsRatio", 0), 3),
                        "offensive_per_removed_teammates": round(br_kpis.get("offensivePlayPerRemovedTeammates", 0), 3),
                    },
                },
                "raw_kpis": br_kpis,
            }
            matches.append(match_entry)

        except Exception as e:
            print(f"    ERROR fetching match {match_id}: {e}")

    # Build full dataset
    dataset = {
        "team": "Brisbane Roar",
        "team_id": SQUAD_ID,
        "season": SEASON,
        "competition": COMPETITION_NAME,
        "competition_iteration_id": COMPETITION_ITERATION_ID,
        "data_source": "Impect Analysis API",
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "matches": matches,
        "players": [
            {
                "id": p["id"],
                "name": p["name"],
                "short_name": p.get("shortName", ""),
                "birth_date": p.get("birthDate", ""),
                "height": p.get("height"),
                "preferred_foot": p.get("leg", ""),
            }
            for p in players
        ],
        "summary": {
            "total_matches": len(matches),
            "record": {
                "wins": sum(1 for m in matches if m.get("goals_for", 0) > m.get("goals_against", 0)),
                "draws": sum(1 for m in matches if m.get("goals_for", 0) == m.get("goals_against", 0)),
                "losses": sum(1 for m in matches if m.get("goals_for", 0) < m.get("goals_against", 0)),
            },
            "goals_for": sum(m.get("goals_for", 0) for m in matches),
            "goals_against": sum(m.get("goals_against", 0) for m in matches),
        },
    }

    return dataset


def sync(username: str = None, password: str = None, output_path: str = None):
    """Full sync: authenticate, pull data, write to disk."""
    username = username or os.environ.get("IMPECT_USERNAME")
    password = password or os.environ.get("IMPECT_PASSWORD")

    if not username or not password:
        raise ValueError("IMPECT_USERNAME and IMPECT_PASSWORD required (env vars or arguments)")

    if output_path is None:
        output_path = os.path.join(DATA_DIR, "matches.json")

    print("ClubGPT Impect Sync")
    print("=" * 40)

    print("Authenticating with Impect...")
    token = get_access_token(username, password)
    print("  Authenticated successfully")

    print(f"Pulling match data for Brisbane Roar ({len(MATCH_IDS)} matches)...")
    dataset = build_match_data(token)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"\nData written to {output_path}")
    print(f"  {dataset['summary']['total_matches']} matches synced")
    print(f"  {len(dataset['players'])} players")

    return dataset


if __name__ == "__main__":
    sync()
