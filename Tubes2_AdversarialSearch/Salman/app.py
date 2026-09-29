from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MAX_HP = 100
MAX_STAMINA = 60
STAMINA_RECOVERY = 3
MIN_ACTION_COST = 5

DIFFICULTIES = {
    "Easy": 1,
    "Normal": 2,
    "Hard": 3,
}

EVAL_NAMES = {
    "v1": "V1 · HP Difference",
    "v2": "V2 · HP + Stamina",
    "v3": "V3 · Tactical",
}

ORDER_NAMES = {
    "default": "Default",
    "aggressive": "Aggressive",
    "defensive": "Defensive",
}

ACTIONS = {
    "slash": {"name": "Slash", "cost": 5, "damage": 12},
    "heavy": {"name": "Heavy Attack", "cost": 15, "damage": 25},
    "guard": {"name": "Guard", "cost": 8, "damage": 0},
    "counter": {"name": "Counter", "cost": 12, "damage": 20},
}

ACTION_ORDERS = {
    "default": ["slash", "heavy", "guard", "counter"],
    "aggressive": ["heavy", "slash", "counter", "guard"],
    "defensive": ["guard", "counter", "slash", "heavy"],
}

game_state = {}


def reset_game():
    global game_state
    game_state = {
        "player_hp": MAX_HP,
        "npc_hp": MAX_HP,
        "player_stamina": MAX_STAMINA,
        "npc_stamina": MAX_STAMINA,
        "player_guard": False,
        "npc_guard": False,
        "turn": 1,
        "phase": "player_turn",
        "game_over": False,
        "winner": None,
        "pending_player_action": None,
        "last_player_action": None,
        "last_npc_action": None,
        "difficulty": "Normal",
        "ai_algorithm": "Alpha-Beta",
        "ai_depth": DIFFICULTIES["Normal"],
        "evaluation": "v2",
        "action_order": "default",
        "ai_nodes": 0,
        "ai_pruned": 0,
        "ai_action_scores": {},
        "ai_chosen_action": None,
        "npc_intent_action": None,
        "combat_log": ["Duel dimulai. Sekarang giliran Player."],
    }


def refresh_npc_intent():
    if game_state.get("game_over"):
        return
    _, scores, debug = root_intent_scores(
        game_state,
        game_state["ai_algorithm"],
        game_state["ai_depth"],
        game_state["evaluation"],
        game_state["action_order"],
    )
    chosen = select_intent_by_difficulty(scores, game_state["difficulty"], game_state["turn"])
    game_state["npc_intent_action"] = chosen
    game_state["ai_chosen_action"] = chosen
    game_state["ai_action_scores"] = scores
    game_state["ai_nodes"] = debug["nodes"]
    game_state["ai_pruned"] = debug["pruned"]


def get_action_order(order_name):
    return ACTION_ORDERS.get(order_name, ACTION_ORDERS["default"])


def get_available_actions(stamina, order_name=None):
    if order_name is None:
        order_name = game_state["action_order"]
    return [
        action
        for action in get_action_order(order_name)
        if stamina >= ACTIONS[action]["cost"]
    ]


def is_terminal(state):
    return state["player_hp"] <= 0 or state["npc_hp"] <= 0


def utility(state):
    # Utility dari sisi NPC sebagai MAX.
    # Terminal value HARUS lebih besar dari evaluasi non-terminal (maks ~100).
    if state["npc_hp"] > 0 and state["player_hp"] <= 0:
        return 10000
    if state["player_hp"] > 0 and state["npc_hp"] <= 0:
        return -10000
    return 0


def evaluation_v1(state):
    return state["npc_hp"] - state["player_hp"]


def evaluation_v2(state):
    hp_difference = state["npc_hp"] - state["player_hp"]
    stamina_difference = state["npc_stamina"] - state["player_stamina"]
    return hp_difference + (0.3 * stamina_difference)


def evaluation_v3(state):
    value = evaluation_v2(state)
    if state.get("npc_guard"):
        value += 8
    if state.get("player_guard"):
        value -= 8
    return value


def evaluate(state, version):
    if version == "v1":
        return evaluation_v1(state)
    if version == "v3":
        return evaluation_v3(state)
    return evaluation_v2(state)


def recover_stamina(stamina):
    value = min(MAX_STAMINA, max(0, stamina + STAMINA_RECOVERY))
    if value < MIN_ACTION_COST:
        value = MIN_ACTION_COST
    return value


def prepare_turn_state(state, actor):
    prepared = state.copy()
    if actor == "player":
        prepared["player_stamina"] = recover_stamina(prepared["player_stamina"])
    else:
        prepared["npc_stamina"] = recover_stamina(prepared["npc_stamina"])
    return prepared


def simulate_exchange(state, player_action, npc_action):
    next_state = {
        "player_hp": state["player_hp"],
        "npc_hp": state["npc_hp"],
        "player_stamina": state["player_stamina"],
        "npc_stamina": state["npc_stamina"],
        "player_guard": player_action == "guard",
        "npc_guard": npc_action == "guard",
        "turn": state.get("turn", 1),
        "game_over": False,
        "winner": None,
    }

    player_damage = 0
    npc_damage = 0

    player_attack = player_action in ("slash", "heavy")
    npc_attack = npc_action in ("slash", "heavy")

    player_counter_success = player_action == "counter" and npc_action == "heavy"
    npc_counter_success = npc_action == "counter" and player_action == "heavy"

    if player_counter_success:
        npc_damage += ACTIONS["counter"]["damage"]

    if npc_counter_success:
        player_damage += ACTIONS["counter"]["damage"]

    if player_attack and not npc_counter_success:
        raw = ACTIONS[player_action]["damage"]
        npc_damage += round(raw * 0.30) if npc_action == "guard" else raw

    if npc_attack and not player_counter_success:
        raw = ACTIONS[npc_action]["damage"]
        player_damage += round(raw * 0.30) if player_action == "guard" else raw

    next_state["player_hp"] = max(0, next_state["player_hp"] - player_damage)
    next_state["npc_hp"] = max(0, next_state["npc_hp"] - npc_damage)
    next_state["player_stamina"] = max(0, next_state["player_stamina"] - ACTIONS[player_action]["cost"])
    next_state["npc_stamina"] = max(0, next_state["npc_stamina"] - ACTIONS[npc_action]["cost"])

    if next_state["npc_hp"] <= 0 and next_state["player_hp"] <= 0:
        next_state["game_over"] = True
        next_state["winner"] = "Draw"
    elif next_state["npc_hp"] <= 0:
        next_state["game_over"] = True
        next_state["winner"] = "Player"
    elif next_state["player_hp"] <= 0:
        next_state["game_over"] = True
        next_state["winner"] = "NPC"

    return next_state, player_damage, npc_damage


def minimax_round(state, depth, counter, eval_version, order_name):
    counter["nodes"] += 1

    if is_terminal(state):
        return utility(state)

    player_state = prepare_turn_state(state, "player")

    if depth <= 0:
        return evaluate(player_state, eval_version)

    player_actions = get_available_actions(player_state["player_stamina"], order_name)
    if not player_actions:
        return evaluate(player_state, eval_version)

    min_value = float("inf")

    for player_action in player_actions:
        npc_state = prepare_turn_state(player_state, "npc")
        npc_actions = get_available_actions(npc_state["npc_stamina"], order_name)

        if not npc_actions:
            player_value = evaluate(npc_state, eval_version)
        else:
            player_value = float("-inf")
            for npc_action in npc_actions:
                next_state, _, _ = simulate_exchange(npc_state, player_action, npc_action)
                value = minimax_round(
                    next_state,
                    depth - 1,
                    counter,
                    eval_version,
                    order_name,
                )
                player_value = max(player_value, value)

        min_value = min(min_value, player_value)

    return min_value


def alpha_beta_round(state, depth, alpha, beta, counter, eval_version, order_name):
    counter["nodes"] += 1

    if is_terminal(state):
        return utility(state)

    player_state = prepare_turn_state(state, "player")

    if depth <= 0:
        return evaluate(player_state, eval_version)

    player_actions = get_available_actions(player_state["player_stamina"], order_name)
    if not player_actions:
        return evaluate(player_state, eval_version)

    min_value = float("inf")

    # Player = MIN. Each child is evaluated by a fresh NPC(MAX) window
    # so alpha values created inside the child do not leak back into MIN.
    for player_action in player_actions:
        npc_state = prepare_turn_state(player_state, "npc")
        npc_actions = get_available_actions(npc_state["npc_stamina"], order_name)

        if not npc_actions:
            player_value = evaluate(npc_state, eval_version)
        else:
            player_value = float("-inf")
            child_alpha = alpha
            child_beta = beta

            for npc_action in npc_actions:
                next_state, _, _ = simulate_exchange(npc_state, player_action, npc_action)
                value = alpha_beta_round(
                    next_state,
                    depth - 1,
                    child_alpha,
                    child_beta,
                    counter,
                    eval_version,
                    order_name,
                )

                player_value = max(player_value, value)
                child_alpha = max(child_alpha, player_value)

                if child_alpha >= child_beta:
                    counter["pruned"] += 1
                    break

        min_value = min(min_value, player_value)
        beta = min(beta, min_value)

        if alpha >= beta:
            counter["pruned"] += 1
            break

    return min_value


def root_scores(state, player_action, algorithm, depth, eval_version, order_name):
    npc_state = prepare_turn_state(state, "npc")
    available = get_available_actions(npc_state["npc_stamina"], order_name)
    scores = {}
    node_total = 0
    prune_total = 0

    for npc_action in available:
        next_state, _, _ = simulate_exchange(npc_state, player_action, npc_action)
        counter = {"nodes": 0, "pruned": 0}
        future_depth = max(0, depth - 1)

        if algorithm == "Minimax":
            score = minimax_round(
                next_state,
                future_depth,
                counter,
                eval_version,
                order_name,
            )
        else:
            score = alpha_beta_round(
                next_state,
                future_depth,
                float("-inf"),
                float("inf"),
                counter,
                eval_version,
                order_name,
            )

        scores[npc_action] = round(score, 2)
        node_total += counter["nodes"]
        prune_total += counter["pruned"]

    return scores, node_total, prune_total


def root_intent_scores(state, algorithm, depth, eval_version, order_name):
    """Choose NPC action before Player responds. NPC is MAX, Player is MIN."""
    npc_state = prepare_turn_state(state, "npc")
    available = get_available_actions(npc_state["npc_stamina"], order_name)
    scores = {}
    node_total = 0
    prune_total = 0

    player_state = prepare_turn_state(npc_state, "player")
    player_actions = get_available_actions(player_state["player_stamina"], order_name)

    for npc_action in available:
        worst_case = float("inf")
        if not player_actions:
            scores[npc_action] = round(evaluate(player_state, eval_version), 2)
            continue

        for player_action in player_actions:
            next_state, _, _ = simulate_exchange(player_state, player_action, npc_action)
            counter = {"nodes": 0, "pruned": 0}
            future_depth = max(0, depth - 1)
            if algorithm == "Minimax":
                value = minimax_round(next_state, future_depth, counter, eval_version, order_name)
            else:
                value = alpha_beta_round(next_state, future_depth, float("-inf"), float("inf"), counter, eval_version, order_name)
            worst_case = min(worst_case, value)
            node_total += counter["nodes"]
            prune_total += counter["pruned"]

        scores[npc_action] = round(worst_case, 2)

    if not scores:
        return None, {}, {"nodes": node_total, "pruned": prune_total}

    chosen = max(scores, key=scores.get)
    return chosen, scores, {"nodes": node_total, "pruned": prune_total}


def select_intent_by_difficulty(scores, difficulty, turn):
    """Keep Minimax/Alpha-Beta as the scorer, but soften NPC behavior for playability.
    Selection is deterministic per turn so the same state is reproducible in tests.
    """
    ranked = sorted(scores, key=scores.get, reverse=True)
    if not ranked:
        return None
    if difficulty == "Hard":
        return ranked[0]
    if difficulty == "Easy":
        # More variety: every third turn intentionally uses the third-ranked option.
        if turn % 3 == 0 and len(ranked) >= 3:
            return ranked[2]
        if turn % 2 == 0 and len(ranked) >= 2:
            return ranked[1]
        return ranked[0]
    # Normal: mostly follows the search result, but intentionally telegraphs a
    # Heavy Attack every fourth round when it is still within a reasonable score
    # margin. This gives the Player a fair Counter opportunity instead of making
    # the NPC either perfectly optimal or perfectly repetitive.
    if turn % 4 == 0 and "heavy" in scores:
        best = scores[ranked[0]]
        if best - scores["heavy"] <= 18:
            return "heavy"
    if turn % 2 == 0 and len(ranked) >= 2:
        best = scores[ranked[0]]
        second = scores[ranked[1]]
        if best - second <= 10:
            return ranked[1]
    return ranked[0]


def choose_npc_action(state, player_action):
    available = get_available_actions(state["npc_stamina"], state["action_order"])

    if not available:
        return None, {}, {"nodes": 0, "pruned": 0}

    scores, total_nodes, total_pruned = root_scores(
        state,
        player_action,
        state["ai_algorithm"],
        state["ai_depth"],
        state["evaluation"],
        state["action_order"],
    )

    chosen = available[0]
    for action in available:
        if scores[action] > scores[chosen]:
            chosen = action

    return chosen, scores, {"nodes": total_nodes, "pruned": total_pruned}


def benchmark_algorithm(state, algorithm, depth, eval_version, order_name):
    # Benchmark mengikuti model game V13.2: NPC mengunci intent lebih dulu,
    # lalu Player memilih respons terhadap intent tersebut.
    prepared = state.copy()
    chosen, scores, debug = root_intent_scores(
        prepared, algorithm, depth, eval_version, order_name
    )
    return {
        "algorithm": algorithm,
        "depth": depth,
        "rows": [{
            "player_action": "Response to NPC intent",
            "npc_action": chosen,
            "score": scores.get(chosen, 0),
            "nodes": debug["nodes"],
            "pruned": debug["pruned"],
            "action_scores": scores,
        }] if chosen else [],
        "total_nodes": debug["nodes"],
        "total_pruned": debug["pruned"],
    }

def compare_configuration(state, depth, eval_version, order_name):
    minimax_result = benchmark_algorithm(state, "Minimax", depth, eval_version, order_name)
    alphabeta_result = benchmark_algorithm(state, "Alpha-Beta", depth, eval_version, order_name)

    reduction = 0
    if minimax_result["total_nodes"]:
        reduction = round(
            (minimax_result["total_nodes"] - alphabeta_result["total_nodes"])
            / minimax_result["total_nodes"]
            * 100,
            2,
        )

    return {
        "depth": depth,
        "evaluation": eval_version,
        "evaluation_name": EVAL_NAMES[eval_version],
        "ordering": order_name,
        "ordering_name": ORDER_NAMES[order_name],
        "minimax_nodes": minimax_result["total_nodes"],
        "alphabeta_nodes": alphabeta_result["total_nodes"],
        "alphabeta_prune_events": alphabeta_result["total_pruned"],
        "node_reduction_percent": reduction,
    }


def set_game_over():
    if game_state["player_hp"] <= 0 and game_state["npc_hp"] <= 0:
        game_state["game_over"] = True
        game_state["winner"] = "Draw"
        game_state["phase"] = "game_over"
        game_state["combat_log"].append("Duel berakhir seri.")
    elif game_state["npc_hp"] <= 0:
        game_state["game_over"] = True
        game_state["winner"] = "Player"
        game_state["phase"] = "game_over"
        game_state["combat_log"].append("Player memenangkan duel!")
    elif game_state["player_hp"] <= 0:
        game_state["game_over"] = True
        game_state["winner"] = "NPC"
        game_state["phase"] = "game_over"
        game_state["combat_log"].append("NPC memenangkan duel!")


def state_for_client():
    return {
        **game_state,
        "available_player_actions": get_available_actions(
            game_state["player_stamina"], game_state["action_order"]
        ),
        "max_hp": MAX_HP,
        "max_stamina": MAX_STAMINA,
        "evaluation_name": EVAL_NAMES[game_state["evaluation"]],
        "order_name": ORDER_NAMES[game_state["action_order"]],
        "ai_role": "MAX · NPC",
        "utility": utility(game_state),
        "stamina_recovery": STAMINA_RECOVERY,
        "min_action_cost": MIN_ACTION_COST,
        "npc_intent_locked": bool(game_state.get("npc_intent_action")),
        "npc_intent_label": ACTIONS.get(game_state.get("npc_intent_action"), {}).get("name", "—"),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(state_for_client())


@app.post("/api/reset")
def api_reset():
    reset_game()
    refresh_npc_intent()
    return jsonify(state_for_client())


@app.post("/api/clear-log")
def api_clear_log():
    game_state["combat_log"] = ["Combat log dibersihkan. Duel tetap berjalan dari state saat ini."]
    return jsonify(state_for_client())


@app.post("/api/settings")
def api_settings():
    data = request.get_json(silent=True) or {}

    if data.get("algorithm") in ("Minimax", "Alpha-Beta"):
        game_state["ai_algorithm"] = data["algorithm"]
    if data.get("difficulty") in DIFFICULTIES:
        game_state["difficulty"] = data["difficulty"]
        game_state["ai_depth"] = DIFFICULTIES[data["difficulty"]]
    if data.get("evaluation") in EVAL_NAMES:
        game_state["evaluation"] = data["evaluation"]
    if data.get("action_order") in ACTION_ORDERS:
        game_state["action_order"] = data["action_order"]

    refresh_npc_intent()
    return jsonify(state_for_client())


@app.post("/api/player-action")
def api_player_action():
    if game_state["game_over"]:
        return jsonify({"error": "Game sudah selesai. Tekan Play Again."}), 400
    if game_state["phase"] != "player_turn":
        return jsonify({"error": "Sekarang bukan giliran Player."}), 400

    # Recovery hanya terjadi saat awal giliran Player.
    before = game_state["player_stamina"]
    game_state["player_stamina"] = recover_stamina(before)

    data = request.get_json(silent=True) or {}
    player_action = data.get("action")
    if player_action not in ACTIONS:
        return jsonify({"error": "Action tidak valid."}), 400

    available = get_available_actions(
        game_state["player_stamina"], game_state["action_order"]
    )
    if player_action not in available:
        return jsonify({"error": "Stamina tidak cukup untuk action ini."}), 400

    game_state["pending_player_action"] = player_action
    game_state["last_player_action"] = player_action
    game_state["phase"] = "npc_resolving"
    game_state["combat_log"].append(
        f"Turn {game_state['turn']}: Player memilih {ACTIONS[player_action]['name']} "
        f"(-{ACTIONS[player_action]['cost']} ST)."
    )
    return jsonify(state_for_client())


@app.post("/api/npc-turn")
def api_npc_turn():
    if game_state["game_over"]:
        return jsonify({"error": "Game sudah selesai."}), 400
    if game_state["phase"] != "npc_resolving":
        return jsonify({"error": "NPC belum mendapat giliran."}), 400

    before = game_state["npc_stamina"]
    game_state["npc_stamina"] = recover_stamina(before)

    player_action = game_state["pending_player_action"]
    if player_action not in ACTIONS:
        game_state["phase"] = "player_turn"
        return jsonify({"error": "Pending action tidak ditemukan."}), 400

    npc_action = game_state.get("npc_intent_action")
    if npc_action not in ACTIONS:
        refresh_npc_intent()
        npc_action = game_state.get("npc_intent_action")
    if npc_action not in get_available_actions(game_state["npc_stamina"], game_state["action_order"]):
        # Emergency fallback only; normal play should never reach this.
        npc_action = get_available_actions(game_state["npc_stamina"], game_state["action_order"])[0]
    debug = {"nodes": game_state.get("ai_nodes", 0), "pruned": game_state.get("ai_pruned", 0)}
    scores = game_state.get("ai_action_scores", {})

    previous_player_hp = game_state["player_hp"]
    previous_npc_hp = game_state["npc_hp"]
    previous_player_stamina = game_state["player_stamina"]
    previous_npc_stamina = game_state["npc_stamina"]

    next_state, player_damage, npc_damage = simulate_exchange(
        game_state, player_action, npc_action
    )

    game_state["player_hp"] = next_state["player_hp"]
    game_state["npc_hp"] = next_state["npc_hp"]
    game_state["player_stamina"] = next_state["player_stamina"]
    game_state["npc_stamina"] = next_state["npc_stamina"]
    game_state["player_guard"] = next_state["player_guard"]
    game_state["npc_guard"] = next_state["npc_guard"]
    game_state["last_npc_action"] = npc_action
    game_state["ai_nodes"] = debug["nodes"]
    game_state["ai_pruned"] = debug["pruned"]
    game_state["ai_action_scores"] = scores
    game_state["ai_chosen_action"] = npc_action

    game_state["combat_log"].append(
        f"Turn {game_state['turn']}: NPC memilih {ACTIONS[npc_action]['name']} "
        f"(-{ACTIONS[npc_action]['cost']} ST)."
    )

    if player_damage > 0:
        game_state["combat_log"].append(f"Player menerima {player_damage} damage.")
    if npc_damage > 0:
        game_state["combat_log"].append(f"NPC menerima {npc_damage} damage.")
    if player_action == "counter" and npc_action != "heavy":
        game_state["combat_log"].append("Counter Player gagal karena NPC bukan Heavy Attack.")
    if npc_action == "counter" and player_action != "heavy":
        game_state["combat_log"].append("Counter NPC gagal karena Player bukan Heavy Attack.")
    if player_action == "guard" and player_damage < ACTIONS[npc_action]["damage"]:
        game_state["combat_log"].append("Guard Player mengurangi damage masuk 70%.")
    if npc_action == "guard" and npc_damage < ACTIONS[player_action]["damage"]:
        game_state["combat_log"].append("Guard NPC mengurangi damage masuk 70%.")

    stamina_message = (
        f"Stamina: Player {previous_player_stamina}→{game_state['player_stamina']}, "
        f"NPC {previous_npc_stamina}→{game_state['npc_stamina']}."
    )
    game_state["combat_log"].append(stamina_message)

    set_game_over()
    if not game_state["game_over"]:
        game_state["turn"] += 1
        game_state["phase"] = "player_turn"
        game_state["pending_player_action"] = None
        refresh_npc_intent()
        game_state["combat_log"].append(
            f"Turn berikutnya siap. NPC mengunci intent {ACTIONS[game_state['npc_intent_action']]['name']}; Player dapat merespons."
        )

    response_state = state_for_client()
    response_state["previous_player_hp"] = previous_player_hp
    response_state["previous_npc_hp"] = previous_npc_hp
    response_state["previous_player_stamina"] = previous_player_stamina
    response_state["previous_npc_stamina"] = previous_npc_stamina
    return jsonify(response_state)


@app.post("/api/benchmark")
def api_benchmark():
    data = request.get_json(silent=True) or {}
    depth = int(data.get("depth", game_state["ai_depth"]))
    depth = max(1, min(3, depth))

    # benchmark_algorithm/ root_scores menyiapkan recovery tepat satu kali
    # untuk actor yang sedang mendapat giliran; jangan recover dua kali di sini.
    benchmark_state = game_state.copy()

    minimax_result = benchmark_algorithm(
        benchmark_state,
        "Minimax",
        depth,
        game_state["evaluation"],
        game_state["action_order"],
    )
    alphabeta_result = benchmark_algorithm(
        benchmark_state,
        "Alpha-Beta",
        depth,
        game_state["evaluation"],
        game_state["action_order"],
    )

    reduction = 0
    if minimax_result["total_nodes"]:
        reduction = round(
            (minimax_result["total_nodes"] - alphabeta_result["total_nodes"])
            / minimax_result["total_nodes"]
            * 100,
            2,
        )

    return jsonify({
        "depth": depth,
        "evaluation_name": EVAL_NAMES[game_state["evaluation"]],
        "ordering_name": ORDER_NAMES[game_state["action_order"]],
        "minimax": minimax_result,
        "alphabeta": alphabeta_result,
        "node_reduction_percent": reduction,
    })


@app.post("/api/experiment-grid")
def api_experiment_grid():
    data = request.get_json(silent=True) or {}
    depth = int(data.get("depth", game_state["ai_depth"]))
    depth = max(1, min(3, depth))

    # Setiap search menyiapkan recovery sendiri agar matriks konsisten dengan game.
    experiment_state = game_state.copy()

    rows = []
    for eval_version in ("v1", "v2", "v3"):
        for order_name in ("default", "aggressive", "defensive"):
            rows.append(
                compare_configuration(
                    experiment_state,
                    depth,
                    eval_version,
                    order_name,
                )
            )

    return jsonify({
        "depth": depth,
        "count": len(rows),
        "total_search_runs": len(rows) * 2,
        "rows": rows,
    })


@app.post("/api/self-test")
def api_self_test():
    tests = []

    def add_test(name, expected, actual, passed):
        tests.append({"name": name, "expected": expected, "actual": actual, "pass": passed})

    def make_state(player_hp=100, npc_hp=100, player_stamina=60, npc_stamina=60):
        return {
            "player_hp": player_hp,
            "npc_hp": npc_hp,
            "player_stamina": player_stamina,
            "npc_stamina": npc_stamina,
            "player_guard": False,
            "npc_guard": False,
        }

    add_test(
        "Low stamina safety rule",
        5,
        recover_stamina(0),
        recover_stamina(0) == 5,
    )
    add_test(
        "Normal recovery +3",
        33,
        recover_stamina(30),
        recover_stamina(30) == 33,
    )
    add_test(
        "Recovery capped at 60",
        60,
        recover_stamina(60),
        recover_stamina(60) == 60,
    )

    initial = make_state()
    slash_state, _, _ = simulate_exchange(initial, "slash", "slash")
    add_test(
        "Slash stamina cost",
        [55, 55],
        [slash_state["player_stamina"], slash_state["npc_stamina"]],
        slash_state["player_stamina"] == 55 and slash_state["npc_stamina"] == 55,
    )

    heavy_state, player_damage, npc_damage = simulate_exchange(initial, "heavy", "counter")
    add_test(
        "Counter vs Heavy",
        [20, 0],
        [player_damage, npc_damage],
        player_damage == 20 and npc_damage == 0,
    )

    reverse_state, player_damage, npc_damage = simulate_exchange(initial, "counter", "heavy")
    add_test(
        "Player Counter vs NPC Heavy",
        [0, 20],
        [player_damage, npc_damage],
        player_damage == 0 and npc_damage == 20,
    )

    guard_state, player_damage, npc_damage = simulate_exchange(initial, "guard", "heavy")
    add_test(
        "Guard reduces Heavy to 30%",
        8,
        player_damage,
        player_damage == 8,
    )

    # Konsistensi keputusan Minimax vs Alpha-Beta pada beberapa state/depth/order.
    consistency_cases = [
        (100, 100, 60, 60, 1, "v1", "default"),
        (82, 65, 45, 50, 2, "v2", "default"),
        (40, 72, 18, 30, 2, "v3", "aggressive"),
        (68, 34, 38, 20, 3, "v2", "defensive"),
        (18, 29, 9, 20, 3, "v3", "aggressive"),
    ]
    consistency_pass = True
    checked = []
    for ph, nh, ps, ns, depth, ev, order in consistency_cases:
        base = make_state(ph, nh, ps, ns)
        mm_choice, mm_scores, _ = root_intent_scores(base, "Minimax", depth, ev, order)
        ab_choice, ab_scores, _ = root_intent_scores(base, "Alpha-Beta", depth, ev, order)
        same_actions = mm_choice == ab_choice and set(mm_scores) == set(ab_scores)
        same_scores = same_actions and all(mm_scores[k] == ab_scores[k] for k in mm_scores)
        consistency_pass = consistency_pass and same_scores
        checked.append({
            "depth": depth, "evaluation": ev, "ordering": order,
            "minimax_choice": mm_choice, "alphabeta_choice": ab_choice, "same_scores": same_scores,
        })
    add_test(
        "Minimax vs Alpha-Beta consistency (5 states)",
        True,
        consistency_pass,
        consistency_pass,
    )

    add_test(
        "Action ordering has 4 legal actions at full stamina",
        4,
        len(get_available_actions(60, "default")),
        len(get_available_actions(60, "default")) == 4,
    )

    all_pass = all(item["pass"] for item in tests)
    return jsonify({
        "all_pass": all_pass,
        "tests": tests,
        "summary": {
            "passed": sum(1 for t in tests if t["pass"]),
            "total": len(tests),
        },
    })


reset_game()
refresh_npc_intent()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
