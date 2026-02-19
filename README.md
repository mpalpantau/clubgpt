# ClubGPT 🏟️

AI Chief of Staff for Football Clubs. Ask questions about your club data in plain English.

## Quick Start

```bash
# 1. Clone/download this folder to your machine

# 2. Install dependencies
pip install anthropic

# 3. Set your API key
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# 4. Run the web UI
cd clubgpt
python src/api.py

# 5. Open http://localhost:8000 in your browser
```

## Command Line Usage

```bash
# Ask a single question
python src/query.py "What was our best xG match this season?"
python src/query.py "How do we perform against Wellington Phoenix?"
python src/query.py "What's our pressing intensity at home vs away?"
```

## Data Sources

- **Impect**: Match & player performance data
- **Contracts**: (Coming soon) Salary & contract terms
- **Medical**: (Coming soon) Injury & fitness data
- **Finance**: (Coming soon) Budget & revenue

## Architecture

```
User Question
     ↓
[Query Engine] → Finds relevant data chunks
     ↓
[Claude API] → Generates answer with context
     ↓
Natural Language Response
```

## Current Data

- 14 A-League matches (Brisbane Roar 2025-26)
- 457 metrics per match from Impect
- Style, xG, pressing, ball progression, zones, etc.

---
Built for Brisbane Roar FC
