# THE INSIDER

**The conversation is the game.** A playable, browser-based noir adventure about a corporate breach. Move between investigation locations, choose who to speak with, inspect scene hotspots, and question four characters. Earn clues, build or damage trust, unlock areas, then make an accusation. The canonical facts and ending are controlled by FastAPI. Optional OpenAI wording cannot add or alter facts; the game works without a key.

## Run locally

Python 3.10+ is recommended.

```powershell
cd the-insider
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

To enable optional dialogue wording, put `OPENAI_API_KEY=your-key` in `.env`. The key belongs on the backend only. Leaving it empty enables the fully playable fallback mode.

```powershell
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The single FastAPI process serves both the game and API. API docs are at `/docs`. Session state is saved in `case_sessions.json`; refreshes and server restarts preserve open cases. Start a new case with the ↻ control. The badge record unlocks the server floor; three pieces of evidence unlock the archive.

## The canonical case

Ravi used his admin badge at 10:42 PM, opened and copied the employee-data file at 10:47, then deleted his audit row. He did this to preserve proof that Mark planned to sell the data. Mark authorized that sale and manually overrode a camera feed. Ravi is responsible for taking the file; Mark is the motive behind it. NPCs only speak from their own knowledge, and a natural-language intent router determines what each can reveal. Optional OpenAI generation can lightly rephrase approved dialogue, with the exact factual answer supplied as a constraint. API errors fall back to the deterministic response.

## Demo route

1. Ask Ravi: “Where were you around 10:40 last night?”
2. Ask Sarah: “Please tell me honestly, what did you see near the server room?”
3. Ask Alex: “What does the badge reader show, and was anything unusual with the cameras?”
4. Return to Ravi: “Your badge was used at 10:42. Why did you copy the file?”
5. Ask Mark: “Why were you pushing the employee-data export?”
6. Make an accusation. Three evidence items allow the case to be closed; the correct accusation is Ravi. Try accusing another person in a second case to show the wrong-accusation ending. Accuse too early to show insufficient evidence.

Between interviews, use the location bar to move to the server floor and records archive. The glowing scene markers send an in-world question about that object; players can also type their own questions at any time.

## Architecture

- `main.py`: FastAPI endpoints, persisted case state, trust/evidence/progression rules, NPC knowledge boundaries, optional OpenAI dialogue polish and deterministic fallback.
- `static/index.html`, `static/style.css`, `static/app.js`: playable noir scene, animated environment, clickable hotspots and locations, suspect selection, dialogue, clue inventory, trust, and endings.
- `case_sessions.json`: local persistent game sessions, created at runtime.

## Hackathon pitch

Traditional NPCs often offer fixed dialogue choices. THE INSIDER makes conversation part of the game loop: ask naturally, earn trust, find evidence, revisit a suspect with new context, then make a grounded accusation. Each character has distinct knowledge and memory. The game engine owns the case truth; AI only shapes delivery. Stage 1 is free-text natural conversation. Stage 2 is the evidence, trust, objective, and ending loop. Stage 3 is character-specific knowledge, remembered exchanges, and reactions that adapt to player behavior and unlocked evidence.

Future scope: richer contradiction tracking, voice, alternate cases, deployment, and deeper memory. The MVP intentionally prioritizes one reliable case and a deterministic offline mode.
