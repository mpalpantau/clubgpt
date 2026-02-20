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
    # Import the shared build_context from api.py
    from api import build_context as _build_context
    return _build_context(data)

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
        print("  - Who are the tallest players in the squad?")
        sys.exit(1)

    question = ' '.join(sys.argv[1:])

    print(f"\nClubGPT\n")
    print(f"Q: {question}\n")
    print("-" * 50)

    data = load_data()
    answer = query(question, data)

    print(f"\n{answer}\n")

if __name__ == "__main__":
    main()
