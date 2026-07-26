from state import State
from value import Value
from action import Action
import math

class Result:
    turn: str # Player, Dealer
    state_value: float
    action_values: list # Value objs
    best_action: Action
    worst_action: Action

    def __init__(
        self,
        turn,
        state_value,
        action_values,
        best_action,
        worst_action,
        exact=True,
        state_item_cost=0.0,
    ):
        self.turn = turn
        self.state_value = state_value
        self.action_values = action_values
        self.best_action = best_action
        self.worst_action = worst_action
        self.exact = exact
        self.state_item_cost = state_item_cost

cache = {} # canonical state tuple: Result
MAX_SEARCH_STATES = 50_000
APPROX_STATES_PER_ACTION = 8_000
tactical_cache = {}


class SearchContext:
    def __init__(self, max_states=None):
        self.max_states = max_states
        self.expanded_states = 0
        self.truncated = False


def estimate(state: State) -> float:
    """Use an exact no-items tactical solve at the search frontier."""
    return tacticalValue(state)


def tacticalKey(state: State):
    return (
        state.live_left,
        state.blank_left,
        state.total_left,
        state.player_hp,
        state.dealer_hp,
        state.max_hp,
        state.player_turn,
        state.damage,
        state.shell_inverted,
        state.opponent_cuffed,
        state.handcuffs_reuse_blocked,
        tuple(state.player_knowledge[state.cur_shell_idx:]),
        tuple(state.dealer_knowledge[state.cur_shell_idx:]),
        state.winner,
    )


def tacticalValue(state: State) -> float:
    """Exact expectiminimax value when no further items may be used."""
    if state.winner == "Player":
        return 1.0
    if state.winner == "Dealer":
        return 0.0
    if state.total_left < 1:
        total_hp = state.player_hp + state.dealer_hp
        return state.player_hp / total_hp if total_hp > 0 else 0.5

    key = tacticalKey(state)
    if key in tactical_cache:
        return tactical_cache[key]

    actor = "Player" if state.player_turn else "Dealer"
    action_values = []
    for action_type in ("Shoot Self", "Shoot Opponent"):
        value = 0.0
        action = Action(action_type, actor)
        for next_state in state.listAllNextStates(action):
            value += next_state.chance * tacticalValue(next_state)
        action_values.append(value)

    result = max(action_values) if state.player_turn else min(action_values)
    tactical_cache[key] = result
    return result


def healthRatio(state: State) -> float:
    total_hp = state.player_hp + state.dealer_hp
    if total_hp <= 0:
        return 0.5
    return state.player_hp / total_hp


def immediateItemCost(action: Action, state: State = None) -> int:
    """Number of items consumed by taking this action."""
    cost = 1 if action.item is not None else 0
    item_name = getattr(action.item, "name", action.item)
    if state is not None and item_name == "Beer" and state.shell_inverted:
        # Beer consumes both itself and the pending value of the Inverter.
        cost += 1
    return cost


def searchPriority(action: Action) -> int:
    """Explore actions that reveal state before irreversible modifiers.

    This only controls bounded-search order; it never removes an action or
    changes a calculated value.
    """
    item_name = getattr(action.item, "name", action.item)
    if item_name == "Magnifying Glass":
        return 0
    if item_name == "Burner Phone":
        return 1
    if action.type in ("Shoot Self", "Shoot Opponent"):
        return 2
    return 3

class Solver:
    def solve(self, state: State):
        """
        1. Check whether state is terminal
        2. Check cache
        3. Generate all legal actions
        4. For each action:
            generate all possible outcomes
            recursively solve each resulting state
            calculate weighted action value
        5. If human player's turn:
            select maximum action value
        6. If dealer's turn:
            select minimum action value
        7. Store result in cache
        8. Return result
        """
        if state.winner:
            self.showWinner(state.winner)
            return []
        
        if state.total_left < 1:
            self.showLoadEnd()
            return []

        key = state.cache_key()
        if key in cache:
            self.show(cache[key])
            return []
        
        context = SearchContext(MAX_SEARCH_STATES)
        calc(state, context)

        result = cache[key]
        if not result.exact:
            result = fairApproximateResult(state)
            cache.clear()
            cache[key] = result
        self.show(result)
        if not result.exact:
            # Approximate entries depend on where this search hit its budget.
            cache.clear()

    def showLoadEnd(self):
        print("Load Ended, Please input new load")

    def showWinner(self, winner: str):
        print(winner, "Win!")

    def show(self, res: Result):
        print("================== RECOMMENDED ROUTE ==================")
        print(f"Turn: {res.turn}")
        label = "State Value" if res.exact else "Estimated State Value"
        print(f"{label}: {res.state_value:.2%} player win chance")
        if not res.exact:
            print(f"Search: approximate ({MAX_SEARCH_STATES:,}-state limit)")
            print(
                "Equal estimates are ranked to preserve items and favor "
                "information."
            )
        print("-------------------------------------------------------")
        print("Available actions (value = player win chance):")
        for index, av in enumerate(res.action_values, start=1):
            print(f"  {index:>2}. {av.name:<32} {av.val:>7.2%}")
        if res.turn == "Player":
            best_action, worst_action = res.best_action, res.worst_action
        else:
            best_action, worst_action = res.worst_action, res.best_action
        print("-------------------------------------------------------")
        print(f"> RECOMMENDED: {best_action}")
        print(f"  AVOID:       {worst_action}")
        print("=======================================================")
    

def calc(state: State, context=None) -> float:
    if context is None:
        context = SearchContext()

    if state.winner:
        if state.winner == "Player": return 1.0
        elif state.winner == "Dealer": return 0.0
    elif state.total_left < 1:
        total_hp = state.player_hp + state.dealer_hp
        return state.player_hp / total_hp if total_hp > 0 else 0.5
    key = state.cache_key()
    if key in cache:
        return cache[key].state_value
    if context.max_states is not None and context.expanded_states >= context.max_states:
        context.truncated = True
        return estimate(state)
    else:
        context.expanded_states += 1
        # state value = max action value
        action_values = []
        actions = sorted(state.listLegalActions(), key=searchPriority)
        best_action = None
        worst_action = None
        max_action_value = 0.0
        min_action_value = 1.0
        best_item_cost = float("inf")
        worst_item_cost = float("inf")
        for action in actions:
            # action value = sum of outcome probability * next_state value
            action_val = 0.0
            action_item_cost = float(immediateItemCost(action, state))
            next_states = state.listAllNextStates(action)
            merged_states = {}
            for next_state in next_states:
                next_key = next_state.cache_key()
                if next_key in merged_states:
                    merged_states[next_key][1] += next_state.chance
                else:
                    merged_states[next_key] = [next_state, next_state.chance]
            for next_state, probability in merged_states.values():
                child_value = calc(next_state, context)
                action_val += probability * child_value
                child_result = cache.get(next_state.cache_key())
                if child_result is not None:
                    action_item_cost += probability * child_result.state_item_cost
            action_values.append(Value(str(action), action_val))
            if (
                action_val > max_action_value + 1e-12
                or best_action is None
                or (
                    math.isclose(action_val, max_action_value, abs_tol=1e-12)
                    and action_item_cost < best_item_cost
                )
            ):
                max_action_value = action_val
                best_action = action
                best_item_cost = action_item_cost
            if (
                action_val < min_action_value - 1e-12
                or worst_action is None
                or (
                    math.isclose(action_val, min_action_value, abs_tol=1e-12)
                    and action_item_cost < worst_item_cost
                )
            ):
                min_action_value = action_val
                worst_action = action
                worst_item_cost = action_item_cost
        state_value = max_action_value if state.player_turn else min_action_value
        state_item_cost = best_item_cost if state.player_turn else worst_item_cost
        cache[key] = Result(
            "Player" if state.player_turn else "Dealer",
            state_value,
            action_values,
            best_action,
            worst_action,
            exact=not context.truncated,
            state_item_cost=state_item_cost,
        )
        return state_value


def evaluateAction(state: State, action: Action, context: SearchContext):
    action_value = 0.0
    action_item_cost = float(immediateItemCost(action, state))
    merged_states = {}
    for next_state in state.listAllNextStates(action):
        next_key = next_state.cache_key()
        if next_key in merged_states:
            merged_states[next_key][1] += next_state.chance
        else:
            merged_states[next_key] = [next_state, next_state.chance]
    for next_state, probability in merged_states.values():
        child_value = calc(next_state, context)
        action_value += probability * child_value
        child_result = cache.get(next_state.cache_key())
        if child_result is not None:
            action_item_cost += probability * child_result.state_item_cost
    return action_value, action_item_cost


def evaluateRootActionFairly(state: State, action: Action):
    """Give every root outcome an equal, independent search allowance."""
    merged_states = {}
    for next_state in state.listAllNextStates(action):
        next_key = next_state.cache_key()
        if next_key in merged_states:
            merged_states[next_key][1] += next_state.chance
        else:
            merged_states[next_key] = [next_state, next_state.chance]

    if not merged_states:
        return 0.0, float(immediateItemCost(action, state))

    per_outcome_budget = max(
        1, APPROX_STATES_PER_ACTION // len(merged_states)
    )
    action_value = 0.0
    action_item_cost = float(immediateItemCost(action, state))
    for next_state, probability in merged_states.values():
        # Approximate cache entries depend on traversal order. Each observed
        # outcome gets a clean cache and the same allowance.
        cache.clear()
        context = SearchContext(per_outcome_budget)
        child_value = calc(next_state, context)
        action_value += probability * child_value
        child_result = cache.get(next_state.cache_key())
        if child_result is not None:
            action_item_cost += probability * child_result.state_item_cost
    return action_value, action_item_cost


def fairApproximateResult(state: State) -> Result:
    """Evaluate each root action with the same independent node allowance."""
    evaluations = []

    for action in state.listLegalActions():
        cache.clear()
        action_value, item_cost = evaluateRootActionFairly(state, action)
        evaluations.append((action, action_value, item_cost))

    action_values = [
        Value(str(action), action_value)
        for action, action_value, _ in evaluations
    ]
    raw_max = max(value for _, value, _ in evaluations)
    raw_min = min(value for _, value, _ in evaluations)
    # Approximation already introduces uncertainty. Do not compound it by
    # replacing the best displayed value with a visibly worse action merely
    # because it is informative or saves an item. Those are tie-breakers only.
    best_candidates = [
        entry for entry in evaluations
        if math.isclose(entry[1], raw_max, abs_tol=1e-12)
    ]
    worst_candidates = [
        entry for entry in evaluations
        if math.isclose(entry[1], raw_min, abs_tol=1e-12)
    ]

    def preference(entry):
        action, _, item_cost = entry
        return (item_cost, searchPriority(action))

    best_action, selected_max, best_cost = min(
        best_candidates, key=preference
    )
    worst_action, selected_min, worst_cost = min(
        worst_candidates, key=preference
    )
    # If the same action lands in both tolerance bands, keep "avoid" anchored
    # to the actual opposite extreme so the display cannot contradict itself.
    if worst_action is best_action and len(evaluations) > 1:
        worst_action, selected_min, worst_cost = min(
            (entry for entry in evaluations if entry[0] is not best_action),
            key=lambda entry: (entry[1],) + preference(entry),
        )

    state_value = selected_max if state.player_turn else selected_min
    state_cost = best_cost if state.player_turn else worst_cost
    return Result(
        "Player" if state.player_turn else "Dealer",
        state_value,
        action_values,
        best_action,
        worst_action,
        exact=False,
        state_item_cost=state_cost,
    )

solver = Solver()
