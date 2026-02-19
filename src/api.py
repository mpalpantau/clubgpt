#!/usr/bin/env python3
"""
ClubGPT Web API
Simple FastAPI server with chat interface.
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

## Season Summary
- Record: {data['summary']['record']['wins']}W - {data['summary']['record']['draws']}D - {data['summary']['record']['losses']}L
- Goals: {data['summary']['goals_for']} scored, {data['summary']['goals_against']} conceded
- Average xG: {data['summary']['avg_xg']}

## Match Data

"""
    
    for match in data['matches']:
        m = match['metrics']
        context += f"""### MD{match['matchday']}: {match['result']} vs {match['opponent']} ({match['venue']}) - {match['date']}
xG: {m['expected_goals']['shot_based_xg']} | Possession: {m['possession']['ball_possession_rate']:.0%} | Shots: {m['shots']['total_shots']} ({m['shots']['shots_on_target']} on target)
Ball Progression: {m['buildup']['ball_progression']} | Breaking Defence: {m['efficiency']['breaking_opponent_defence']}
Style: Possession {m['style']['possession_control']:.0%}, Counter {m['style']['counter_attacking']:.0%}, Heavy Metal {m['style']['heavy_metal']:.0%}
Pressing: Height {m['pressing']['avg_pressure_height_m']:.0f}m, Counter-press {m['pressing']['avg_pressure_counter_press']:.0f}

"""
    
    return context

def query_clubgpt(question: str) -> str:
    """Query Claude with the match data."""
    
    client = Anthropic()
    context = build_context(MATCH_DATA)
    
    system_prompt = """You are ClubGPT, an AI assistant for Brisbane Roar Football Club.
You have access to detailed match data from the current season.
Answer questions about team performance, tactics, and trends.
Be concise. Reference specific matches and numbers. Identify patterns."""

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
║            🏟️  ClubGPT                    ║
║         AI Chief of Staff                 ║
╠═══════════════════════════════════════════╣
║  Server running at http://localhost:{port}  ║
║                                           ║
║  Endpoints:                               ║
║    /           - Chat UI                  ║
║    /api/query  - Query API                ║
║    /api/data   - Raw data                 ║
╚═══════════════════════════════════════════╝
""")
    server.serve_forever()

if __name__ == "__main__":
    main()
