#!/usr/bin/env python3
"""
ClubGPT Query Engine
Ask questions about your club data in natural language.
"""

import os
import json
import sys
from anthropic import Anthropic

# Load data
def load_data():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'matches.json')
    with open(data_path, 'r') as f:
        return json.load(f)

# Build context from data
def build_context(data):
    """Convert match data into readable context for the LLM."""
    
    context = f"""# {data['team']} - {data['season']} Season Data
Competition: {data['competition']}
Data Source: {data['data_source']}

## Season Summary
- Record: {data['summary']['record']['wins']}W - {data['summary']['record']['draws']}D - {data['summary']['record']['losses']}L
- Goals: {data['summary']['goals_for']} scored, {data['summary']['goals_against']} conceded
- Average xG: {data['summary']['avg_xg']}
- Average Possession: {data['summary']['avg_possession']:.0%}
- Average Pass Accuracy: {data['summary']['avg_pass_accuracy']:.0%}

## Match-by-Match Data

"""
    
    for match in data['matches']:
        m = match['metrics']
        context += f"""### Matchday {match['matchday']}: vs {match['opponent']} ({match['venue'].upper()})
Date: {match['date']} | Result: {match['result']}

**Style Profile:**
- Possession Control: {m['style']['possession_control']:.0%}
- Heavy Metal: {m['style']['heavy_metal']:.0%}
- Counter Attacking: {m['style']['counter_attacking']:.0%}
- Direct & Aerial: {m['style']['direct_aerial']:.0%}

**Expected Goals:**
- Shot-based xG: {m['expected_goals']['shot_based_xg']}
- Post-shot xG: {m['expected_goals']['post_shot_xg']}

**Ball Progression:**
- Ball Progression: {m['buildup']['ball_progression']}
- Breaking Opponent Defence: {m['efficiency']['breaking_opponent_defence']}
- Critical Ball Losses: {m['buildup']['critical_ball_loss']}

**Possession & Passing:**
- Possession: {m['possession']['ball_possession_rate']:.0%}
- Pass Accuracy: {m['possession']['passing_accuracy']:.0%}
- Successful Passes: {m['possession']['successful_passes']}

**Pressing:**
- Pressing GK: {m['pressing']['pressuring_gk_pct']:.0%}
- Avg Pressure Height: {m['pressing']['avg_pressure_height_m']:.1f}m
- Counter-Press Intensity: {m['pressing']['avg_pressure_counter_press']:.1f}

**Shots:**
- Total: {m['shots']['total_shots']}
- On Target: {m['shots']['shots_on_target']}

**Duels:**
- Ground Duel Win Rate: {m['duels']['ground_duel_success']:.0%}
- Aerial Duel Win Rate: {m['duels']['aerial_duel_success']:.0%}

---
"""
    
    return context

# Query the LLM
def query(question: str, data: dict) -> str:
    """Send a question to Claude with the match data context."""
    
    client = Anthropic()
    
    context = build_context(data)
    
    system_prompt = """You are ClubGPT, an AI assistant for Brisbane Roar Football Club. 
You have access to detailed match data from the current season.

Your role:
- Answer questions about team performance, tactics, and trends
- Provide data-driven insights
- Compare matches and identify patterns
- Be concise but thorough

When answering:
- Reference specific matches and metrics
- Highlight trends across multiple matches
- Provide actionable insights when relevant
- Use the exact numbers from the data

If asked about something not in the data, say so clearly."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""Here is the team's match data:

{context}

---

Question: {question}"""
            }
        ]
    )
    
    return message.content[0].text

def main():
    if len(sys.argv) < 2:
        print("Usage: python query.py 'Your question here'")
        print("\nExample questions:")
        print("  - What was our best xG match?")
        print("  - How do we perform at home vs away?")
        print("  - What's our pressing profile?")
        print("  - Which matches had the most ball progression?")
        sys.exit(1)
    
    question = ' '.join(sys.argv[1:])
    
    print(f"\n🏟️  ClubGPT\n")
    print(f"Q: {question}\n")
    print("-" * 50)
    
    data = load_data()
    answer = query(question, data)
    
    print(f"\n{answer}\n")

if __name__ == "__main__":
    main()
