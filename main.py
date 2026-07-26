from state import State, applyAction
from action import Action
from solver import solver, cache
from outcome import Outcome
from item import itemKeyMap, defaultItemDict, findItemObjByName
import sys
import copy
import textwrap
import difflib

state = State()
state_history = []
itemInputMap = {
    **itemKeyMap,
    "phone": "Burner Phone",
    "inverter": "Inverter",
    "medicine": "Expired Medicine",
    "beer": "Beer",
    "adrenaline": "Adrenaline",
    "saw": "Hand Saw",
    "handsaw": "Hand Saw",
    "cuffs": "Handcuffs",
    "handcuffs": "Handcuffs",
    "glass": "Magnifying Glass",
    "cigarette": "Cigarette Pack",
}

ACTION_INPUTS = [
    "ss", "so", "ui", "si", "ss1", "ss2", "ssu", "so1", "so2", "sou",
    "phone", "inverter", "medicine", "beer", "adrenaline", "saw",
    "handsaw", "cuffs", "handcuffs", "glass", "cigarette",
    "q", "k", "v", "r", "z", "exit",
]

def resolveUnknownConsumedShell(state: State) -> str:
    print("Shell unknown. Enter the remaining shell counts to keep the state exact.")
    while True:
        try:
            print("Remaining live shells: ")
            live_left = int(input())
            print("Remaining blank shells: ")
            blank_left = int(input())
        except ValueError:
            print("** Counts must be integers; try again **")
            continue

        live_used = state.live_left - live_left
        blank_used = state.blank_left - blank_left
        if (
            live_left < 0
            or blank_left < 0
            or live_left + blank_left != state.total_left - 1
            or (live_used, blank_used) not in ((1, 0), (0, 1))
        ):
            print("** Counts must remove exactly one shell; try again **")
            continue

        return "Live" if live_used == 1 else "Blank"


def readItemOutcome(item: str, state: State, actor: str) -> Outcome:
    outcome = Outcome(item=item)
    if actor == "Dealer" and item in ("Burner Phone", "Magnifying Glass"):
        outcome.hidden = True
        return outcome
    if item == "Burner Phone":
        print("Input shell position (2 = next shell, 3 = third shell): ")
        outcome.idx = int(parseInput("Idx", input(), state))
        print("Input shell: ")
        outcome.shell = parseInput("Shell", input(), state)
    elif item == "Expired Medicine":
        print("Input Gain (0 for False, 1 for True): ")
        outcome.gain = parseInput("Gain", input(), state) is True
    elif item in ("Beer", "Magnifying Glass"):
        if item == "Beer":
            print("Input ejected shell: ")
        else:
            print("Input shell: ")
        outcome.shell = parseInput("Shell", input(), state)
        if item == "Beer" and outcome.shell == "Unknown":
            outcome.shell = resolveUnknownConsumedShell(state)
    return outcome


def applyItemInput(state: State, actor: str, item: str) -> State:
    actor_items = state.player_items if actor == "Player" else state.dealer_items
    if actor_items.get(item, 0) < 1:
        print(f"** {actor} does not have {item}; try again **")
        return state

    legal_items = {
        action.item.name
        for action in state.listLegalActions()
        if action.type == "Use Item"
    }
    if item not in legal_items:
        print("** That item cannot be used in the current state **")
        return state

    print(f"** Using: {item} **")
    outcome = readItemOutcome(item, state, actor)
    next_state = applyAction(state, Action("Use Item", actor, item), outcome)
    return next_state


def applySelectInput(
    state: State, actor: str, item: str, outcome: Outcome | None = None
) -> State:
    legal_items = {
        action.item.name
        for action in state.listLegalActions()
        if action.type == "Select Item"
    }
    if item not in legal_items:
        print("** That item cannot be selected with Adrenaline **")
        return state
    print(f"** Adrenaline selection: {item} **")
    if outcome is None:
        outcome = readItemOutcome(item, state, actor)
    return applyAction(
        state,
        Action("Select Item", actor, item),
        outcome,
    )


def applyCompactSelectInput(state: State, actor: str, shortcut: str) -> State:
    """Apply an Adrenaline selection such as b2, g1, m0, or p42."""
    if not shortcut:
        return state
    item = itemKeyMap.get(shortcut[0])
    if item is None or item == "Adrenaline":
        print("** Invalid Adrenaline item shortcut **")
        return state

    suffix = shortcut[1:]
    if not suffix:
        return applySelectInput(state, actor, item)

    outcome = Outcome(item=item)
    if (
        item == "Burner Phone"
        and len(suffix) >= 2
        and suffix[:-1].isdigit()
        and suffix[-1] in ("0", "1", "2", "u")
    ):
        if actor == "Dealer":
            print("** Dealer Burner Phone result is private; use p **")
            return state
        position = int(suffix[:-1])
        if position < 2 or position > state.total_left:
            print("** Phone position must be from 2 through the shells remaining **")
            return state
        outcome.idx = position
        outcome.shell = {
            "0": "Unknown",
            "u": "Unknown",
            "1": "Live",
            "2": "Blank",
        }[suffix[-1]]
    elif item == "Beer" and suffix in ("0", "1", "2", "u"):
        outcome.shell = (
            resolveUnknownConsumedShell(state)
            if suffix in ("0", "u")
            else ("Live" if suffix == "1" else "Blank")
        )
    elif item == "Magnifying Glass" and suffix in ("0", "1", "2", "u"):
        if actor == "Dealer":
            if suffix not in ("0", "u"):
                print("** Dealer Magnifying Glass result is private; use g or gu **")
                return state
            outcome.hidden = True
        else:
            outcome.shell = {
                "0": "Unknown",
                "u": "Unknown",
                "1": "Live",
                "2": "Blank",
            }[suffix]
    elif item == "Expired Medicine" and suffix in ("0", "1"):
        outcome.gain = suffix == "1"
    else:
        print("** Invalid outcome for selected item; try again **")
        return state
    return applySelectInput(state, actor, item, outcome)


def applyOrUndoAction(state: State, action_input: str) -> State:
    if action_input == "e":
        if state_history:
            print("** Previous action restored **")
            return state_history.pop()
        print("** No previous action to restore **")
        return state

    previous_state = state
    next_state = parseInput("Action", action_input, state)
    state_history.append(previous_state)
    return next_state

def showMain():
    print("============================================================")
    print("Welcome to Buckshot Roulette Helper!")
    print("  r     Start a new game/load")
    print("  q     Open the instruction manual")
    print("  k     Open the item catalog")
    print("  v     View the current game state")
    print("  z     Return to this menu")
    print("  exit  Quit")
    print("============================================================")

    parseInput("Main", input(), state)
    showMain()

def showManual():
    print("\n====================== MANUAL ======================")
    print("PURPOSE")
    print("  Enter the real match state. The helper evaluates every")
    print("  legal move and prints a recommended action route.")
    print("\n1. SET UP A GAME")
    print("  Load: enter shells using 1 (live) and 2 (blank).")
    print("        Example: 112212")
    print("  HP: enter the shared starting/max health.")
    print("  Items: enter each item's key once per copy.")
    print("         Example: bmmi = 1 Beer, 2 Medicine, 1 Inverter.")
    print("\n2. RECORD EACH ACTION")
    print("  ss / so       Shoot self / opponent, then enter the result. Example: ss 1")
    print("  ui <key>      Use an item. Example: ui b")
    print("  <item key>    Fast item use. Example: i")
    print("  e             Undo the previous action.")
    print("\n3. SHELL RESULT KEYS")
    print("  1 = live     2 = blank     u or 0 = unknown")
    print("  Fast shots: ss1, ss2, ssu, so1, so2, sou")
    print("\n4. ITEM OUTCOME SHORTCUTS")
    print("  b1 / b2 / bu        Beer ejected live / blank / unknown")
    print("  g1 / g2 / gu        Glass saw live / blank / unknown")
    print("  m1 / m0             Medicine succeeded / failed")
    print("  p21                 Phone: position 2 is live")
    print("  p42                 Phone: position 4 is blank")
    print("\n5. ADRENALINE")
    print("  si <key>             Select the stolen item after Adrenaline")
    print("  b2                   While selecting: steal Beer, eject blank")
    print("  ab2                  Use Adrenaline + steal/use Beer in one entry")
    print("  ap42                 Use Adrenaline + Phone; position 4 is blank")
    print("  0 / si 0 / si skip   Let Adrenaline expire")
    print("\n6. DEALER INPUT")
    print("  Dealer actions may be entered as a space-separated sequence.")
    print("  Example: h so1 i p ss2 so1")
    print("  Player actions must be entered one at a time.")
    print("\nGLOBAL COMMANDS")
    print("  q manual | k item catalog | v current state")
    print("  r restart | z menu | exit quit")
    print("====================================================\n")


def showItemCatalog():
    print("\n=================== ITEM CATALOG ===================")
    for key, name in itemKeyMap.items():
        item = findItemObjByName(name)
        print(f"[{key}] {item.name}")
        for line in textwrap.wrap(item.description, width=54):
            print(f"    {line}")
        if item.legals:
            print(f"    Use when: {'; '.join(item.legals)}")
        print()
    print("Press an item's key during a turn to use it.")
    print("====================================================\n")


def showCurrentState(state: State):
    print("\nCurrent game state:")
    print(state)
    print()


def showTypoPrompt(usr_input: str, input_type: str):
    candidates = ACTION_INPUTS if input_type == "Action" else [
        "q", "k", "v", "r", "z", "exit"
    ]
    matches = difflib.get_close_matches(usr_input, candidates, n=1, cutoff=0.6)
    if matches and matches[0] != usr_input:
        print(f"** Unrecognized input '{usr_input}'. Did you mean '{matches[0]}'? **")
    else:
        print(f"** Unrecognized input '{usr_input}'. Please try again. **")
    print("Help: q = manual | k = item catalog | v = current state")
    print(f"Enter {input_type.lower()} input again:")


def showResumePrompt(input_type: str):
    labels = {
        "Main": "main-menu command",
        "Load": "load",
        "HP": "maximum HP",
        "Player Items": "player items",
        "Dealer Items": "dealer items",
        "Action": "action",
        "Shell": "shell result",
        "Idx": "shell position",
        "Gain": "medicine result",
        "Item": "item",
    }
    print(f"Enter {labels.get(input_type, 'input')}:")


def start():
    state = State()
    print("============================================================")
    print("Input the load (example: 112212): ")
    parseInput("Load", input(), state)
    print("============================================================")
    print("Input max hp: ")
    parseInput("HP", input(), state)
    print("============================================================")
    print("Input player items (example: bmmi): ")
    parseInput("Player Items", input(), state)
    print("============================================================")
    print("Input Dealer items (example: bmmi): ")
    parseInput("Dealer Items", input(), state)
    print("============================================================")
    print("Running...")
    updateLoad(state)
    showMain()
    

def updateLoad(state: State):
    if state.winner:
        print("** ", state.winner, "Win! **")
        print("============================================================")
        start()
    elif state.total_left < 1:
        print("** Load Ended! **")
        print("============================================================")
        print("Input the load (example: 112212): ")
        parseInput("Load", input(), state)
        print("Input player items (example: bmmi): ")
        parseInput("Player Items", input(), state)
        print("============================================================")
        print("Input Dealer items (example: bmmi): ")
        parseInput("Dealer Items", input(), state)
        print("============================================================")
        print("Running...")
        updateLoad(state)
    else:
        print("============================================================")
        print(str(state))
        print("============================================================")
        solver.solve(state)
        print("============================================================")
        actor = "Player" if state.player_turn else "Dealer"
        print(f"[{actor} Round] Input action: ")
        if actor == "Dealer":
            print("Dealer shortcuts: ss1/ss2, so1/so2, or item key (p/i/m/b/a/s/h/g/c)")
        print("Help: q = manual | k = item catalog | v = state | e = undo")
        action_input = input().strip().lower()
        state = applyOrUndoAction(state, action_input)
        print("============================================================")
        updateLoad(state)

def parseInput(type: str, usr_input: str, state: State) -> State | str | None:
    usr_input = usr_input.strip().lower()
    if usr_input == "q":
        showManual()
        showResumePrompt(type)
        return parseInput(type, input(), state)
    if usr_input == "k":
        showItemCatalog()
        showResumePrompt(type)
        return parseInput(type, input(), state)
    if usr_input == "v":
        showCurrentState(state)
        showResumePrompt(type)
        return parseInput(type, input(), state)

    if type == "Main":
        match usr_input:
            case "q":
                showManual()
                parseInput(type, input(), state)
                return
            case "r":
                start()
                return
            case "z":
                return
            case "exit":
                sys.exit()
            case _:
                showTypoPrompt(usr_input, type)
                showMain()
                return
    elif type == "Load":
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()
            case "z":
                showMain()
                return
            case "exit":
                sys.exit()
            case "":
                print("** Invalid input, try again **")
                return parseInput(type, input(), state)
        live_cnt = 0
        blank_cnt = 0
        for c in usr_input:
            if c == '1':
                live_cnt += 1
            elif c == '2':
                blank_cnt += 1
            else:
                print("** Invalid input, try again **")
                return parseInput(type, input(), state)
        state.live_left = live_cnt
        state.blank_left = blank_cnt
        state.total_left = live_cnt + blank_cnt
        state.player_turn = True
        state.damage = 1
        state.shell_inverted = False
        state.opponent_cuffed = False
        state.handcuffs_reuse_blocked = False
        state.in_Adrenaline = False
        state.player_knowledge = []
        state.dealer_knowledge = []
        state.cur_shell_idx = 0
        for _ in range(state.total_left):
            state.player_knowledge.append("Unknown")
            state.dealer_knowledge.append("Unknown")
        cache.clear()
        state_history.clear()
        return None
    elif type == "HP":
            match usr_input:
                case "q":
                    showManual()
                    return parseInput(type, input(), state)
                case "r":
                    return start()
                case "z":
                    return showMain()
                case "exit":
                    sys.exit()
            try:
                hp = int(usr_input)
            except ValueError:
                print("** Invalid input, try again **")
                return parseInput(type, input(), state)
            state.max_hp = hp
            state.player_hp = hp
            state.dealer_hp = hp
            return None
    elif type == "Player Items":
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()
            case "z":
                return showMain()
            case "":
                return None
            case "exit":
                sys.exit()
        m = copy.deepcopy(defaultItemDict)
        for key in usr_input:
            if key not in itemKeyMap:
                print("** Invalid input, try again **")
                parseInput(type, input(), state)
                return
            else: m[itemKeyMap[key]] += 1
        state.player_items = copy.deepcopy(m)
        return state
    elif type == "Dealer Items":
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()    
            case "z":
                return showMain() 
            case "":
                return
            case "exit":
                sys.exit()
        m = copy.deepcopy(defaultItemDict)
        for key in usr_input:
            if key not in itemKeyMap:
                print("** Invalid input, try again **")
                return parseInput(type, input(), state)
            else: m[itemKeyMap[key]] += 1
        state.dealer_items = copy.deepcopy(m)
        return state
    elif type == "Action":
        actor = "Player" if state.player_turn else "Dealer"
        parts = usr_input.strip().lower().split()
        if state.in_Adrenaline and usr_input in ("0", "n", "none", "skip"):
            return applyAction(
                state,
                Action("Cancel Adrenaline", actor),
                Outcome(),
            )
        if (
            state.in_Adrenaline
            and len(parts) == 1
            and len(usr_input) > 1
            and usr_input[0] in itemKeyMap
        ):
            next_state = applyCompactSelectInput(state, actor, usr_input)
            if next_state is state:
                return parseInput(type, input(), state)
            return next_state
        if (
            not state.in_Adrenaline
            and len(parts) == 1
            and len(usr_input) > 1
            and usr_input[0] == "a"
        ):
            after_adrenaline = applyItemInput(
                state, actor, "Adrenaline"
            )
            if after_adrenaline is state:
                return parseInput(type, input(), state)
            next_state = applyCompactSelectInput(
                after_adrenaline, actor, usr_input[1:]
            )
            if next_state is after_adrenaline:
                print("** Combined Adrenaline shortcut was not applied; try again **")
                return parseInput(type, input(), state)
            return next_state
        if len(parts) > 1 and parts[0] not in ("ui", "si"):
            if state.player_turn:
                print("** Player actions must be entered one at a time **")
                return parseInput(type, input(), state)
            next_state = state
            for index, token in enumerate(parts):
                previous_step = next_state
                next_state = parseInput("Action", token, next_state)
                if next_state is previous_step:
                    print(f"** Invalid dealer action in sequence: {token} **")
                    return parseInput(type, input(), state)
                if index < len(parts) - 1 and next_state.player_turn:
                    print(
                        "** Dealer turn ended; remaining sequence actions were ignored **"
                    )
                    return next_state
            return next_state
        if len(parts) == 2 and parts[0] in ("ui", "si"):
            if parts[0] == "si" and parts[1] in ("0", "n", "none", "skip"):
                if not state.in_Adrenaline:
                    print("** No active Adrenaline selection to cancel; try again **")
                    return parseInput(type, input(), state)
                return applyAction(
                    state,
                    Action("Cancel Adrenaline", actor),
                    Outcome(),
                )
            item = itemInputMap.get(parts[1])
            if item is None:
                if parts[0] == "si":
                    print("** Invalid steal selection; try again or enter si 0 to let Adrenaline expire **")
                else:
                    print("** Invalid item key; try again **")
                return parseInput(type, input(), state)
            if parts[0] == "ui":
                next_state = applyItemInput(state, actor, item)
            else:
                next_state = applySelectInput(state, actor, item)
            if next_state is state:
                return parseInput(type, input(), state)
            return next_state
        if (
            len(usr_input) >= 3
            and usr_input[0] == "p"
            and usr_input[1:-1].isdigit()
            and usr_input[-1] in ("0", "1", "2", "u")
        ):
            if actor == "Dealer":
                print("** Dealer Burner Phone result is private; use p **")
                return parseInput(type, input(), state)
            position = int(usr_input[1:-1])
            if position < 2 or position > state.total_left:
                print("** Phone position must be from 2 through the shells remaining **")
                return parseInput(type, input(), state)
            legal_items = {
                action.item.name
                for action in state.listLegalActions()
                if action.type == "Use Item"
            }
            if "Burner Phone" not in legal_items:
                print(f"** {actor} cannot use Burner Phone in the current state **")
                return parseInput(type, input(), state)
            shell = {
                "0": "Unknown",
                "u": "Unknown",
                "1": "Live",
                "2": "Blank",
            }[usr_input[-1]]
            return applyAction(
                state,
                Action("Use Item", actor, "Burner Phone"),
                Outcome(item="Burner Phone", idx=position, shell=shell),
            )
        if len(usr_input) == 2 and usr_input[0] == "g" and usr_input[1] in ("0", "1", "2", "u"):
            if actor == "Dealer":
                if usr_input[1] in ("0", "u"):
                    return applyItemInput(
                        state, actor, "Magnifying Glass"
                    )
                print("** Dealer Magnifying Glass result is private; use g or gu **")
                return state
            legal_items = {
                action.item.name
                for action in state.listLegalActions()
                if action.type == "Use Item"
            }
            if "Magnifying Glass" not in legal_items:
                print("** Player cannot use Magnifying Glass in the current state **")
                return parseInput(type, input(), state)
            shell = {
                "1": "Live",
                "2": "Blank",
                "0": "Unknown",
                "u": "Unknown",
            }[usr_input[1]]
            return applyAction(
                state,
                Action("Use Item", actor, "Magnifying Glass"),
                Outcome(item="Magnifying Glass", shell=shell),
            )
        if len(usr_input) == 2 and usr_input[0] == "m" and usr_input[1] in ("0", "1"):
            legal_items = {
                action.item.name
                for action in state.listLegalActions()
                if action.type == "Use Item"
            }
            if "Expired Medicine" not in legal_items:
                print(f"** {actor} cannot use Expired Medicine in the current state **")
                return parseInput(type, input(), state)
            return applyAction(
                state,
                Action("Use Item", actor, "Expired Medicine"),
                Outcome(item="Expired Medicine", gain=usr_input[1] == "1"),
            )
        if (
            len(usr_input) == 2
            and usr_input[0] == "b"
            and usr_input[1] in ("0", "1", "2", "u")
        ):
            legal_items = {
                action.item.name
                for action in state.listLegalActions()
                if action.type == "Use Item"
            }
            if "Beer" not in legal_items:
                print(f"** {actor} cannot use Beer in the current state **")
                return parseInput(type, input(), state)
            shell_key = usr_input[1]
            if shell_key in ("0", "u"):
                shell = resolveUnknownConsumedShell(state)
            else:
                shell = "Live" if shell_key == "1" else "Blank"
            return applyAction(
                state,
                Action("Use Item", actor, "Beer"),
                Outcome(item="Beer", shell=shell),
            )
        shortcut_item = itemInputMap.get(usr_input)
        if shortcut_item is not None:
            if state.in_Adrenaline:
                next_state = applySelectInput(state, actor, shortcut_item)
            else:
                next_state = applyItemInput(state, actor, shortcut_item)
            if next_state is state:
                return parseInput(type, input(), state)
            return next_state
        if len(usr_input) == 3 and usr_input[:2] in ("ss", "so"):
            shell_key = usr_input[2]
            if shell_key in ("0", "u"):
                shell = resolveUnknownConsumedShell(state)
            elif shell_key in ("1", "2"):
                shell = "Live" if shell_key == "1" else "Blank"
            else:
                print("** Invalid dealer shortcut **")
                return parseInput(type, input(), state)
            action_type = "Shoot Self" if usr_input[:2] == "ss" else "Shoot Opponent"
            return applyAction(state, Action(action_type, actor), Outcome(shell=shell))
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()
            case "z":
                return showMain()
            case "exit":
                sys.exit()
            case "ss":
                print("Input shell: ")
                shell = parseInput("Shell", input(), state)
                if shell == "Unknown":
                    shell = resolveUnknownConsumedShell(state)
                return applyAction(state, Action("Shoot Self", actor), Outcome(shell=shell))
            case "so":
                print("Input shell: ")
                shell = parseInput("Shell", input(), state)
                if shell == "Unknown":
                    shell = resolveUnknownConsumedShell(state)
                return applyAction(state, Action("Shoot Opponent", actor), Outcome(shell=shell))
            case "ui":
                print("** Use one line, for example: ui b **")
                return parseInput(type, input(), state)
            case "si":
                print("** Use one line, for example: si b **")
                return parseInput(type, input(), state)
            case _:
                showTypoPrompt(usr_input, type)
                return parseInput(type, input(), state)
    elif type == "Shell":
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()
            case "z":
                return showMain()
            case "exit":
                sys.exit()
            case "1":
                return "Live"
            case "2":
                return "Blank"
            case "0" | "u":
                return "Unknown"
            case _:
                print("** Invalid input, try again **")
                return parseInput(type, input(), state)
    elif type == "Idx":
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()
            case "z":
                return showMain()
            case "exit":
                sys.exit()
            case _:
                try:
                    n = int(usr_input)
                except ValueError:
                    print("** Invalid input, try again **")
                    return parseInput(type, input(), state)
                if n < 2 or n > state.total_left:
                    print("** Invalid input, try again **")
                    return parseInput(type, input(), state)
                return usr_input
    elif type == "Gain":
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()
            case "z":
                return showMain()
            case "exit":
                sys.exit()
            case "0":
                return "False"
            case "1":
                return True
            case _:
                print("** Invalid input, try again **")
                return parseInput(type, input(), state)
    elif type == "Item":
        match usr_input:
            case "q":
                showManual()
                return parseInput(type, input(), state)
            case "r":
                return start()
            case "z":
                return showMain()
            case "exit":
                sys.exit()
            case _:
                if len(usr_input) != 1:
                    print("** Invalid input, try again **")
                    return parseInput(type, input(), state)
                key = usr_input[0]
                if key not in itemKeyMap:
                    print("** Invalid input, try again **")
                    return parseInput(type, input(), state)
                return itemKeyMap[key]
            
if __name__ == "__main__":
    showMain()
