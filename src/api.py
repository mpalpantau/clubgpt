#!/usr/bin/env python3
"""
ClubGPT Web API
Simple HTTP server with chat interface.
"""

import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
from anthropic import Anthropic

# Load data
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'matches.json')
UI_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'index.html')

with open(DATA_PATH, 'r') as f:
    MATCH_DATA = json.load(f)

def build_context(data):
    """Convert match data into readable context for the LLM."""

    context = f"""# {data['team']} - {data['season']} Season Data
Competition: {data['competition']}
Data Source: {data.get('data_source', 'Impect')}
Last Sync: {data.get('last_sync', 'Unknown')}

## Season Summary
- Total Matches: {data['summary']['total_matches']}

"""
    # Add summary stats if available (old format)
    summary = data.get('summary', {})
    if 'record' in summary:
        r = summary['record']
        context += f"- Record: {r['wins']}W - {r['draws']}D - {r['losses']}L\n"
    if 'goals_for' in summary:
        context += f"- Goals: {summary['goals_for']} scored, {summary['goals_against']} conceded\n"
    if 'avg_xg' in summary:
        context += f"- Average xG: {summary['avg_xg']}\n"

    context += "\n## Match Data\n\n"

    for match in data['matches']:
        m = match['metrics']
        xg = m.get('expected_goals', {})
        poss = m.get('possession', {})
        shots = m.get('shots', {})
        press = m.get('pressing', {})
        buildup = m.get('buildup', {})
        opp = m.get('opponent', {})
        duels = m.get('duels', {})
        ratios = m.get('ratios', {})

        # Header line
        result = match.get('result', '')
        venue = match.get('venue', '')
        date = match.get('date', '')
        header = f"### MD{match['matchday']}: vs {match['opponent']}"
        if result:
            header += f" - {result}"
        if venue:
            header += f" ({venue})"
        if date:
            header += f" - {date}"
        context += header + "\n"

        # xG
        packing_xg = xg.get('packing_xg', xg.get('shot_based_xg', ''))
        nsxg = xg.get('shot_based_xg', '')
        postshot = xg.get('post_shot_xg', '')
        threat = xg.get('developed_goal_threat', '')
        context += f"xG: {nsxg} (packing: {packing_xg}, post-shot: {postshot})"
        if threat:
            context += f" | Threat: {threat}"
        context += "\n"

        # Possession & passing
        poss_rate = poss.get('ball_possession_rate', 0)
        pass_acc = poss.get('passing_accuracy', 0)
        context += f"Possession: {poss_rate:.0%} | Pass Accuracy: {pass_acc:.0%} | Passes: {poss.get('successful_passes', 0)} successful, {poss.get('unsuccessful_passes', 0)} failed\n"

        # Shots
        context += f"Shots: {shots.get('total_shots', 0)} ({shots.get('shots_on_target', 0)} on target)\n"

        # Ball progression
        bp = buildup.get('ball_progression', 0)
        bod = buildup.get('breaking_opponent_defence', 0)
        cbl = buildup.get('critical_ball_loss', 0)
        dbc = buildup.get('defensive_ball_control', 0)
        oi = buildup.get('offensive_interventions', 0)
        context += f"Ball Progression: {bp} | Breaking Defence: {bod} | Critical Ball Loss: {cbl} | Def Ball Control: {dbc} | Off. Interventions: {oi}\n"

        # Opponent
        obp = opp.get('opponent_ball_progression', 0)
        obd = opp.get('opponent_breaking_defence', opp.get('own_defence_broken', 0))
        context += f"Opponent Ball Progression: {obp} | Opponent Breaking Defence: {obd}\n"

        # Pressing
        ph = press.get('avg_pressure_height_m', 0)
        cp = press.get('avg_pressure_counter_press', press.get('avg_pressure_buildup', 0))
        gk = press.get('pressuring_gk_pct', 0)
        fhp = press.get('forced_high_passes_pct', 0)
        context += f"Pressing: Height {ph:.0f}m | Counter-press: {cp:.1f} | GK pressure: {gk:.0%} | Forced high passes: {fhp:.0%}\n"

        # Duels
        dr = duels.get('duel_rate', 0)
        gd = duels.get('ground_duel_success', 0)
        ad = duels.get('aerial_duel_success', 0)
        context += f"Duels: {dr:.0%} win rate | Ground: {gd:.0%} | Aerial: {ad:.0%}\n"

        # Ratios (new data)
        if ratios:
            context += f"Ratios: Reverse play {ratios.get('reverse_play', 0):.1%} | Remove opponents {ratios.get('remove_opponents', 0):.1%}\n"

        context += "\n"

    # Players section
    if 'players' in data and data['players']:
        context += "## Squad\n\n"
        for p in data['players']:
            context += f"- {p['name']}"
            if p.get('birth_date'):
                context += f" (born {p['birth_date']})"
            if p.get('height'):
                context += f", {p['height']}m"
            if p.get('preferred_foot'):
                context += f", {p['preferred_foot'].lower()} foot"
            context += "\n"

    return context

def query_clubgpt(question: str) -> str:
    """Query Claude with the match data."""

    client = Anthropic()
    context = build_context(MATCH_DATA)

    system_prompt = """You are ClubGPT, an AI assistant for Brisbane Roar Football Club coaching staff.
You have access to detailed match data from the current A-League Men 2025-26 season, sourced from Impect analytics.

IMPORTANT RULES:
- You ONLY have data for the current 2025-26 season. If asked about previous seasons or historical data, clearly state that you don't have that data.
- The player list comes from Impect's squad registry and may include players no longer contracted. Do NOT make claims about specific player performances (goals scored, assists, ratings) — you do not have individual player match stats, only team-level KPIs.
- You DO have: team xG, possession, pressing, buildup, duels, shots, and ball progression data per match.
- When asked about players or goalscorers, explain that you have team-level analytics but not individual player stats for this season.

Answer questions about team performance, tactics, trends, and patterns.
Be concise. Reference specific matches and numbers. Identify patterns.
When comparing matches, use the KPI data to support your analysis."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"DATA:\n{context}\n\nQUESTION: {question}"
            }
        ]
    )

    return message.content[0].text

class ClubGPTHandler(SimpleHTTPRequestHandler):
    """Handle HTTP requests for ClubGPT."""

    def do_GET(self):
        global MATCH_DATA
        if self.path == '/' or self.path == '/index.html':
            # Serve the UI
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open(UI_PATH, 'rb') as f:
                self.wfile.write(f.read())
        elif self.path.startswith('/api/query'):
            # Handle API query
            query_string = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query_string)
            question = params.get('q', [''])[0]

            if question:
                try:
                    answer = query_clubgpt(question)
                    response = json.dumps({'answer': answer})
                except Exception as e:
                    response = json.dumps({'error': str(e)})
            else:
                response = json.dumps({'error': 'No question provided'})

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode())
        elif self.path == '/api/data':
            # Return raw data
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(MATCH_DATA).encode())
        elif self.path == '/api/sync':
            # Trigger data sync
            try:
                from impect_sync import sync
                username = os.environ.get('IMPECT_USERNAME')
                password = os.environ.get('IMPECT_PASSWORD')
                if not username or not password:
                    response = json.dumps({'error': 'IMPECT_USERNAME and IMPECT_PASSWORD not set'})
                else:
                    sync(username, password)
                    # Reload data
                    with open(DATA_PATH, 'r') as f:
                        MATCH_DATA = json.load(f)
                    response = json.dumps({'status': 'synced', 'matches': MATCH_DATA['summary']['total_matches']})
            except Exception as e:
                response = json.dumps({'error': str(e)})

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[ClubGPT] {args[0]}")

def main():
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), ClubGPTHandler)
    print(f"""
╔═══════════════════════════════════════════╗
║            ClubGPT                        ║
║         AI Chief of Staff                 ║
╠═══════════════════════════════════════════╣
║  Server running at http://localhost:{port}  ║
║                                           ║
║  Endpoints:                               ║
║    /           - Chat UI                  ║
║    /api/query  - Query API                ║
║    /api/data   - Raw data                 ║
║    /api/sync   - Trigger Impect sync      ║
╚═══════════════════════════════════════════╝
""")
    server.serve_forever()

if __name__ == "__main__":
    main()
