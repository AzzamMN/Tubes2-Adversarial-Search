SAMURAI DUEL V13.2
===================
Turn-based Samurai Duel + Minimax / Alpha-Beta AI Lab.

RUN
---
1. Open terminal in this folder.
2. Install dependencies:
   pip install -r requirements.txt
3. Start:
   python app.py
4. Open:
   http://127.0.0.1:5000

V13.2 GAME FLOW
---------------
Each round now uses a clearer commitment model:
1. NPC AI searches with Minimax or Alpha-Beta.
2. NPC locks an intent before the Player chooses.
3. Player sees NPC INTENT - LOCKED.
4. Player chooses a response.
5. The locked NPC action is executed; there is no second AI decision after the Player clicks.
6. A new intent is calculated for the next round.

This makes Counter meaningful and prevents the confusing situation where the UI shows an action after the Player has already committed to a move.

DIFFICULTY
----------
Easy   = depth 1 + more behavioral variety.
Normal = depth 2 + mostly best search result, with a controlled telegraphed Heavy opportunity every fourth round when its score is reasonably close.
Hard   = depth 3 + follows the best search result.

The search engine still computes Minimax / Alpha-Beta scores. Difficulty is a gameplay layer applied after scoring.

ACTIONS
-------
Slash        12 damage, 5 stamina
Heavy Attack 25 damage, 15 stamina
Guard        70% damage reduction, 8 stamina
Counter      20 damage vs Heavy, 12 stamina

STAMINA
-------
Action cost is paid immediately.
At the start of each fighter's next turn: +3 stamina, capped at 60.
Safety rule: minimum 5 stamina so the game never reaches a no-legal-action dead end.

EXPERIMENTS
-----------
- Minimax vs Alpha-Beta benchmark
- Evaluation V1/V2/V3
- Action Ordering Default/Aggressive/Defensive
- Depth 1/2/3
- Experiment Matrix
- CSV export
- Self-Test

IMPORTANT AI TRACE
------------------
The NPC Action Analysis panel now represents the NPC's committed intent for the current round.
It is not a prediction made after the Player has already chosen.

SELF-TEST
---------
V13.2 core self-test checks:
- low stamina safety
- +3 recovery
- stamina cap
- Slash cost
- Counter vs Heavy
- Player Counter vs NPC Heavy
- Guard reduction
- Minimax vs Alpha-Beta score consistency across multiple states
- four legal actions at full stamina


V13.3 VISUAL FIX
The previous V13.2 background contained its own HUD, which duplicated the HTML HUD. V13.3 uses arena_clean_v13.jpg as the single arena background and keeps player/NPC cards as HTML overlays.
