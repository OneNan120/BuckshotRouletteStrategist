from item import findItemObjByName, adrenaline, defaultItemDict
from action import Action
from outcome import Outcome
ITEM_NAMES = tuple(defaultItemDict)

class State:
    live_left: int
    blank_left: int
    total_left: int

    player_hp: int
    dealer_hp: int
    max_hp: int

    player_turn: bool
    cur_shell_idx: int

    player_items: dict # item:quantity
    dealer_items: dict

    damage: int # 2 if using Hand Saw
    shell_inverted: bool
    opponent_cuffed: bool
    handcuffs_reuse_blocked: bool
    in_Adrenaline: bool

    player_knowledge: list
    dealer_knowledge: list

    winner: str | None # Dealer, Player
    chance: float

    def __init__(self):
        self.live_left = 0
        self.blank_left = 0
        self.total_left = 0
        self.player_hp = 0
        self.dealer_hp = 0
        self.max_hp = 0
        self.player_turn = True
        self.cur_shell_idx = 0
        self.player_items = defaultItemDict.copy()
        self.dealer_items = defaultItemDict.copy()
        self.damage = 1
        self.shell_inverted = False
        self.opponent_cuffed = False
        self.handcuffs_reuse_blocked = False
        self.in_Adrenaline = False
        self.player_knowledge = []
        self.dealer_knowledge = []
        self.winner = None
        self.chance = 1.0

    def clone(self):
        """Fast copy for solver branches."""
        result = object.__new__(type(self))
        result.__dict__ = self.__dict__.copy()
        result.player_items = self.player_items.copy()
        result.dealer_items = self.dealer_items.copy()
        result.player_knowledge = self.player_knowledge.copy()
        result.dealer_knowledge = self.dealer_knowledge.copy()
        return result

    def __deepcopy__(self, memo):
        result = self.clone()
        memo[id(self)] = result
        return result

    def cache_key(self):
        """Return the future-relevant, immutable representation of this state."""
        return (
            self.live_left,
            self.blank_left,
            self.total_left,
            self.player_hp,
            self.dealer_hp,
            self.max_hp,
            self.player_turn,
            tuple(self.player_items[name] for name in ITEM_NAMES),
            tuple(self.dealer_items[name] for name in ITEM_NAMES),
            self.damage,
            self.shell_inverted,
            self.opponent_cuffed,
            self.handcuffs_reuse_blocked,
            self.in_Adrenaline,
            tuple(self.player_knowledge[self.cur_shell_idx:]),
            tuple(self.dealer_knowledge[self.cur_shell_idx:]),
            self.winner,
        )

    def __str__(self):
        actor = "Player" if self.player_turn else "Dealer"
        winner = self.winner if self.winner is not None else "None"

        player_items = ", ".join(
            f"{name}: {quantity}"
            for name, quantity in self.player_items.items()
            if quantity > 0
        ) or "None"

        dealer_items = ", ".join(
            f"{name}: {quantity}"
            for name, quantity in self.dealer_items.items()
            if quantity > 0
        ) or "None"

        player_knowledge = ", ".join(
            f"{index}:{shell}"
            for index, shell in enumerate(self.player_knowledge, start=1)
        ) or "None"

        dealer_knowledge = ", ".join(
            f"{index}:{shell}"
            for index, shell in enumerate(self.dealer_knowledge, start=1)
        ) or "None"

        return (
            "\n"
            "==================== GAME STATE ====================\n"
            f"Turn:               {actor}\n"
            f"Winner:             {winner}\n"
            f"State Chance:       {self.chance:.2%}\n"
            "----------------------------------------------------\n"
            f"Player HP:          {self.player_hp}/{self.max_hp}\n"
            f"Dealer HP:          {self.dealer_hp}/{self.max_hp}\n"
            "----------------------------------------------------\n"
            f"Live Shells Left:   {self.live_left}\n"
            f"Blank Shells Left:  {self.blank_left}\n"
            f"Total Shells Left:  {self.total_left}\n"
            f"Current Shell Index:{self.cur_shell_idx + 1}\n"
            "----------------------------------------------------\n"
            f"Damage:             {self.damage}\n"
            f"Shell Inverted:     {self.shell_inverted}\n"
            f"Opponent Cuffed:    {self.opponent_cuffed}\n"
            f"Handcuffs Reuse:    {'Blocked' if self.handcuffs_reuse_blocked else 'Ready'}\n"
            f"In Adrenaline:      {self.in_Adrenaline}\n"
            "----------------------------------------------------\n"
            f"Player Items:       {player_items}\n"
            f"Dealer Items:       {dealer_items}\n"
            "----------------------------------------------------\n"
            f"Player Knowledge:   {player_knowledge}\n"
            f"Dealer Knowledge:   {dealer_knowledge}\n"
            "===================================================="
        )

    def listLegalActions(self):
        actor = "Dealer"
        opponent = "Player"
        if self.player_turn:
            actor = "Player"
            opponent = "Dealer"
        
        lst = []

        if self.total_left < 1:
            return lst

        # Select Item actions
        if self.in_Adrenaline:
            if opponent == "Dealer":
                for item in self.dealer_items:
                    item_obj = findItemObjByName(item)
                    if (
                        self.dealer_items[item] < 1
                        or item == adrenaline.name
                        or (
                            item == "Handcuffs"
                            and (
                                self.opponent_cuffed
                                or self.handcuffs_reuse_blocked
                            )
                        )
                        or not self.checkLegals(item_obj.legals, actor, opponent)
                    ):
                        continue
                    lst.append(Action(type="Select Item", actor=actor, item=item_obj))
            elif opponent == "Player":
                for item in self.player_items:
                    item_obj = findItemObjByName(item)
                    if (
                        self.player_items[item] < 1
                        or item == adrenaline.name
                        or (
                            item == "Handcuffs"
                            and (
                                self.opponent_cuffed
                                or self.handcuffs_reuse_blocked
                            )
                        )
                        or not self.checkLegals(item_obj.legals, actor, opponent)
                    ):
                        continue
                    lst.append(Action(type="Select Item", actor=actor, item=item_obj))
            lst.append(Action(type="Cancel Adrenaline", actor=actor))
            return lst

        # use item actions
        opponent_items = self.dealer_items if self.player_turn else self.player_items
        opponent_has_adrenaline = opponent_items.get("Adrenaline", 0) > 0
        actor_hp = self.player_hp if self.player_turn else self.dealer_hp
        actor_knowledge = self.player_knowledge if self.player_turn else self.dealer_knowledge
        if self.player_turn: 
            for item in self.player_items:
                if self.player_items[item] < 1: continue
                obj = findItemObjByName(item)
                if (
                    not opponent_has_adrenaline
                    and item == "Cigarette Pack"
                    and actor_hp >= self.max_hp
                ):
                    continue
                if (
                    not opponent_has_adrenaline
                    and item == "Magnifying Glass"
                    and actor_knowledge[self.cur_shell_idx] != "Unknown"
                ):
                    continue
                if not opponent_has_adrenaline and item == "Burner Phone" and all(
                    shell != "Unknown"
                    for shell in actor_knowledge[self.cur_shell_idx + 1:]
                ):
                    continue
                if (self.checkLegals(obj.legals, actor, opponent)):
                    lst.append(Action(type="Use Item", actor=actor, item=obj))
        else:
            for item in self.dealer_items:
                if self.dealer_items[item] < 1: continue
                obj = findItemObjByName(item)
                if (
                    not opponent_has_adrenaline
                    and item == "Cigarette Pack"
                    and actor_hp >= self.max_hp
                ):
                    continue
                if (
                    not opponent_has_adrenaline
                    and item == "Magnifying Glass"
                    and actor_knowledge[self.cur_shell_idx] != "Unknown"
                ):
                    continue
                if not opponent_has_adrenaline and item == "Burner Phone" and all(
                    shell != "Unknown"
                    for shell in actor_knowledge[self.cur_shell_idx + 1:]
                ):
                    continue
                if (self.checkLegals(obj.legals, actor, opponent)):
                    lst.append(Action(type="Use Item", actor=actor, item=obj))
        # shoot actions
        lst.append(Action(type="Shoot Self", actor=actor))
        lst.append(Action(type="Shoot Opponent", actor=actor))
        return lst

    def checkLegals(self, legals, actor, opponent) -> bool:
        for legal in legals:
            match legal:
                case "At least two shells remaining":
                    if self.total_left < 2:
                        return False
                case "opponent owns at least one non-Adrenaline item":
                    items = self.dealer_items if opponent == "Dealer" else self.player_items
                    if not any(quantity > 0 and name != adrenaline.name for name, quantity in items.items()):
                        return False
                case "Shotgun is not sawed":
                    if self.damage > 1: return False
                case "Opponent is not cuffed":
                    if self.opponent_cuffed or self.handcuffs_reuse_blocked:
                        return False
                case "User health is not full":
                    hp = self.player_hp if actor == "Player" else self.dealer_hp
                    if hp >= self.max_hp: return False
        return True

    def listAllNextStates(self, action: Action) -> list:
        lst = []

        if self.in_Adrenaline and action.type != "Select Item":
            recovered_state = self.clone()
            recovered_state.in_Adrenaline = False
            return recovered_state.listAllNextStates(action)

        if action.type in ("Shoot Self", "Shoot Opponent"):
            physical_probabilities = shellProbabilities(
                self, action.actor, self.cur_shell_idx
            )
            for shell in ("Blank", "Live"):
                physical_shell = (
                    ("Live" if shell == "Blank" else "Blank")
                    if self.shell_inverted
                    else shell
                )
                probability = physical_probabilities[physical_shell]
                if probability > 0.0:
                    next_state = applyAction(self, action, Outcome(shell=shell))
                    next_state.chance = probability
                    lst.append(next_state)
            return lst
        
        match action.type:
            case "Shoot Self":
                # Outcome 1: blank shell
                next_state = self.clone()
                
                # update shell status
                next_state.total_left -= 1

                # update shell idx
                next_state.cur_shell_idx = self.cur_shell_idx + 1

                # Reset damage
                next_state.damage = 1

                if self.shell_inverted:
                    next_state.chance = self.live_left / self.total_left
                    # update shell status
                    next_state.live_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Live"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Live"
                    updateKnowledge(next_state)
                else: 
                    next_state.chance = self.blank_left / self.total_left
                    next_state.blank_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Blank"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Blank"
                    updateKnowledge(next_state)
                if next_state.chance > 0.0: lst.append(next_state)

                # Outcome 2: live shell
                next_state = self.clone()
                
                # update shell status
                next_state.total_left -= 1

                # update shell idx
                next_state.cur_shell_idx = self.cur_shell_idx + 1

                # Reset damage
                next_state.damage = 1

                # update hp, turn, and winner
                if self.player_turn: next_state.player_hp = self.player_hp - self.damage
                else: next_state.dealer_hp = self.dealer_hp - self.damage
                if self.opponent_cuffed: 
                    next_state.player_turn = self.player_turn
                    next_state.opponent_cuffed = False
                else: next_state.player_turn = not self.player_turn
                if next_state.player_hp < 1: next_state.winner = "Dealer"
                elif next_state.dealer_hp < 1: next_state.winner = "Player"
                if not self.shell_inverted:
                    next_state.chance = self.live_left / self.total_left
                    # update shell status
                    next_state.live_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Live"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Live"
                    updateKnowledge(next_state)
                else:
                    next_state.chance = self.blank_left / self.total_left
                    # update shell status
                    next_state.blank_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Blank"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Blank"
                    updateKnowledge(next_state)

                if next_state.chance > 0.0: lst.append(next_state)
            case "Shoot Opponent":
                # Outcome 1: blank shell
                next_state = self.clone()
                
                # update shell status
                next_state.total_left -= 1

                # update shell idx
                next_state.cur_shell_idx = self.cur_shell_idx + 1

                # Reset damage
                next_state.damage = 1

                # update turn
                if self.opponent_cuffed: 
                    next_state.player_turn = self.player_turn
                    next_state.opponent_cuffed = False
                else: next_state.player_turn = not self.player_turn

                if self.shell_inverted:
                    next_state.chance = self.live_left / self.total_left
                    # update shell status
                    next_state.live_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Live"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Live"
                    updateKnowledge(next_state)
                else:
                    next_state.chance = self.blank_left / self.total_left
                    # update shell status
                    next_state.blank_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Blank"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Blank"
                    updateKnowledge(next_state)
                if next_state.chance > 0.0: lst.append(next_state)

                # Outcome 2: live shell
                next_state = self.clone()

                # update shell status
                next_state.total_left -= 1

                # update shell idx
                next_state.cur_shell_idx = self.cur_shell_idx + 1

                # Reset damage
                next_state.damage = 1

                # update turn
                if self.opponent_cuffed: next_state.player_turn = self.player_turn
                else: next_state.player_turn = not self.player_turn

                # update hp
                if self.player_turn: next_state.dealer_hp = self.dealer_hp - self.damage 
                else: next_state.player_hp = self.player_hp - self.damage
                # update winner
                if next_state.player_hp < 1: next_state.winner = "Dealer"
                elif next_state.dealer_hp < 1: next_state.winner = "Player"

                if not self.shell_inverted:
                    next_state.chance = self.live_left / self.total_left
                    # update shell status
                    next_state.live_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Live"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Live"
                    updateKnowledge(next_state)
                else:
                    next_state.chance = self.blank_left / self.total_left
                    # update shell status
                    next_state.blank_left -= 1
                    next_state.player_knowledge[self.cur_shell_idx] = "Blank"
                    next_state.dealer_knowledge[self.cur_shell_idx] = "Blank"
                    updateKnowledge(next_state)
                if next_state.chance > 0.0: lst.append(next_state)
            case "Use Item":
                lst.extend(getAllNextStates(action.item.name, self, action.actor))
            case "Select Item":
                item = action.item.name
                tmp_state = self.clone()
                if action.actor == "Player":
                    tmp_state.player_items[item] += 1
                    tmp_state.dealer_items[item] -= 1
                else:
                    tmp_state.dealer_items[item] += 1
                    tmp_state.player_items[item] -= 1
                tmp_state.in_Adrenaline = False
                lst.extend(getAllNextStates(item, tmp_state, action.actor))
            case "Cancel Adrenaline":
                next_state = self.clone()
                next_state.in_Adrenaline = False
                next_state.chance = 1.0
                lst.append(next_state)
        return lst

def shellProbabilities(state: State, actor: str, index: int) -> dict:
    """Conditional physical-shell probabilities from one actor's knowledge."""
    knowledge = (
        state.player_knowledge if actor == "Player" else state.dealer_knowledge
    )
    known = knowledge[index]
    if known != "Unknown":
        return {
            "Live": 1.0 if known == "Live" else 0.0,
            "Blank": 1.0 if known == "Blank" else 0.0,
        }

    remaining = knowledge[state.cur_shell_idx:]
    unknown_count = remaining.count("Unknown")
    unknown_live = state.live_left - remaining.count("Live")
    unknown_blank = state.blank_left - remaining.count("Blank")
    if unknown_count <= 0:
        return {"Live": 0.0, "Blank": 0.0}
    return {
        "Live": max(0, unknown_live) / unknown_count,
        "Blank": max(0, unknown_blank) / unknown_count,
    }


def updateKnowledge(state: State):
    if state.total_left < 1: 
        return
    for knowledge in (state.player_knowledge, state.dealer_knowledge):
        remaining = knowledge[state.cur_shell_idx:]
        unknown_indices = [
            index
            for index in range(state.cur_shell_idx, len(knowledge))
            if knowledge[index] == "Unknown"
        ]
        unknown_live = state.live_left - remaining.count("Live")
        unknown_blank = state.blank_left - remaining.count("Blank")
        if unknown_live == 0:
            for index in unknown_indices:
                knowledge[index] = "Blank"
        elif unknown_blank == 0:
            for index in unknown_indices:
                knowledge[index] = "Live"

def getAllNextStates(item: str, cur_state: State, actor: str) -> list:
    if item == "Beer":
        lst = []
        for physical_shell in ("Blank", "Live"):
            probability = shellProbabilities(
                cur_state, actor, cur_state.cur_shell_idx
            )[physical_shell]
            if probability == 0:
                continue
            next_state = _consume_physical_shell(cur_state, physical_shell)
            items = next_state.player_items if actor == "Player" else next_state.dealer_items
            items[item] -= 1
            if next_state.total_left == 0:
                if cur_state.opponent_cuffed:
                    next_state.opponent_cuffed = False
                else:
                    next_state.player_turn = not cur_state.player_turn
            next_state.chance = probability
            lst.append(next_state)
        return lst

    match item:
        case "Burner Phone": 
            chance = 1.0 / (cur_state.total_left - 1)
            lst = []
            for i in range(1, cur_state.total_left):
                target_shell = cur_state.cur_shell_idx + i
                probabilities = shellProbabilities(cur_state, actor, target_shell)
                for shell in ("Blank", "Live"):
                    if probabilities[shell] <= 0.0:
                        continue
                    next_state = cur_state.clone()
                    next_state.chance = chance * probabilities[shell]
                    if actor == "Player":
                        next_state.player_items[item] -= 1
                        next_state.player_knowledge[target_shell] = shell
                    else:
                        next_state.dealer_items[item] -= 1
                        next_state.dealer_knowledge[target_shell] = shell
                    updateKnowledge(next_state)
                    lst.append(next_state)

            return lst
        case "Inverter":
            next_state = cur_state.clone()
            if actor == "Player": next_state.player_items[item] -= 1
            elif actor == "Dealer": next_state.dealer_items[item] -= 1
            next_state.chance = 1.0
            next_state.shell_inverted = not cur_state.shell_inverted
            
            return [next_state]
        case "Expired Medicine": 
            lst = []
            # Outcome 1: regain two charges
            next_state = cur_state.clone()
            next_state.chance = 0.5
            if actor == "Player": 
                next_state.player_hp = min(cur_state.max_hp, cur_state.player_hp + 2)
                next_state.player_items[item] -= 1
            elif actor == "Dealer": 
                next_state.dealer_hp = min(cur_state.max_hp, cur_state.dealer_hp + 2)
                next_state.dealer_items[item] -= 1
            if next_state.chance > 0.0: lst.append(next_state)

            # Outcome 2: lose one charge
            next_state = cur_state.clone()
            next_state.chance = 0.5
            if actor == "Player": 
                next_state.player_hp -= 1
                next_state.player_items[item] -= 1
                if next_state.player_hp < 1: next_state.winner = "Dealer"
            elif actor == "Dealer": 
                next_state.dealer_hp -= 1
                next_state.dealer_items[item] -= 1
                if next_state.dealer_hp < 1: next_state.winner = "Player"
            if next_state.chance > 0.0: lst.append(next_state)

            return lst
        case "Beer":
            lst = []
            # Outcome 1: blank shell
            next_state = cur_state.clone()
            next_state.chance = cur_state.blank_left / cur_state.total_left
            if actor == "Player": next_state.player_items[item] -= 1
            elif actor == "Dealer": next_state.dealer_items[item] -= 1
            next_state.cur_shell_idx += 1
            next_state.total_left -= 1
            if cur_state.shell_inverted:
                # upate shell status
                next_state.live_left -= 1
                next_state.player_knowledge[cur_state.cur_shell_idx] = "Live"
                next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Live"
            else:
                next_state.blank_left -= 1
                next_state.player_knowledge[cur_state.cur_shell_idx] = "Blank"
                next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Blank"
            updateKnowledge(next_state)
            if next_state.chance > 0.0: lst.append(next_state)

            # Outcome 2: live shell
            next_state = cur_state.clone()
            next_state.chance = cur_state.live_left / cur_state.total_left
            if actor == "Player": next_state.player_items[item] -= 1
            elif actor == "Dealer": next_state.dealer_items[item] -= 1
            next_state.cur_shell_idx += 1
            next_state.total_left -= 1
            if cur_state.shell_inverted:
                # upate shell status
                next_state.live_left -= 1
                next_state.player_knowledge[cur_state.cur_shell_idx] = "Blank"
                next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Blank"
            else:
                next_state.blank_left -= 1
                next_state.player_knowledge[cur_state.cur_shell_idx] = "Live"
                next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Live"
            updateKnowledge(next_state)
            if next_state.chance > 0.0: lst.append(next_state)

            return lst
        case "Adrenaline": 
            next_state = cur_state.clone()
            next_state.chance = 1.0
            next_state.in_Adrenaline = True
            if actor == "Player":
                next_state.player_items[item] -= 1
            elif actor == "Dealer":
                next_state.dealer_items[item] -= 1
            return [next_state]
        case "Hand Saw": 
            next_state = cur_state.clone()
            next_state.chance = 1.0
            next_state.damage = 2
            if actor == "Player": next_state.player_items[item] -= 1
            elif actor == "Dealer": next_state.dealer_items[item] -= 1
            return [next_state]
        case "Handcuffs":
            next_state = cur_state.clone()
            next_state.chance = 1.0
            next_state.opponent_cuffed = True
            next_state.handcuffs_reuse_blocked = True
            if actor == "Player": next_state.player_items[item] -= 1
            elif actor == "Dealer": next_state.dealer_items[item] -= 1
            return [next_state]
        case "Magnifying Glass": 
            lst = []
            probabilities = shellProbabilities(
                cur_state, actor, cur_state.cur_shell_idx
            )
            for physical_shell in ("Blank", "Live"):
                if probabilities[physical_shell] <= 0.0:
                    continue
                next_state = cur_state.clone()
                next_state.chance = probabilities[physical_shell]
                if actor == "Player":
                    next_state.player_items[item] -= 1
                    next_state.player_knowledge[cur_state.cur_shell_idx] = physical_shell
                else:
                    next_state.dealer_items[item] -= 1
                    next_state.dealer_knowledge[cur_state.cur_shell_idx] = physical_shell
                updateKnowledge(next_state)
                lst.append(next_state)

            return lst
        case "Cigarette Pack": 
            next_state = cur_state.clone()
            next_state.chance = 1.0
            if actor == "Player": 
                next_state.player_items[item] -= 1
                next_state.player_hp = min(cur_state.max_hp, cur_state.player_hp + 1)
            elif actor == "Dealer": 
                next_state.dealer_items[item] -= 1
                next_state.dealer_hp = min(cur_state.max_hp, cur_state.dealer_hp + 1)
            return [next_state]

def _consume_physical_shell(cur_state: State, physical_shell: str) -> State:
    """Remove a shell by its physical type.

    Shell inventory and knowledge always describe physical shells. Inversion
    only changes what the current shell does when fired; it does not recolor a
    shell ejected by Beer.
    """
    next_state = cur_state.clone()
    index = cur_state.cur_shell_idx
    next_state.total_left -= 1
    next_state.cur_shell_idx += 1
    if physical_shell == "Live":
        next_state.live_left -= 1
    else:
        next_state.blank_left -= 1
    next_state.player_knowledge[index] = physical_shell
    next_state.dealer_knowledge[index] = physical_shell
    next_state.shell_inverted = False
    updateKnowledge(next_state)
    return next_state


def _apply_shot(cur_state: State, action: Action, effective_shell: str) -> State:
    physical_shell = (
        ("Live" if effective_shell == "Blank" else "Blank")
        if cur_state.shell_inverted
        else effective_shell
    )
    next_state = _consume_physical_shell(cur_state, physical_shell)
    next_state.damage = 1

    if effective_shell == "Live":
        target_is_player = (
            action.type == "Shoot Self" and cur_state.player_turn
        ) or (
            action.type == "Shoot Opponent" and not cur_state.player_turn
        )
        if target_is_player:
            next_state.player_hp -= cur_state.damage
        else:
            next_state.dealer_hp -= cur_state.damage

        if next_state.player_hp < 1:
            next_state.winner = "Dealer"
        elif next_state.dealer_hp < 1:
            next_state.winner = "Player"

    # A blank self-shot keeps the turn. Every other shot normally passes it.
    passes_turn = action.type == "Shoot Opponent" or effective_shell == "Live"
    if passes_turn:
        if cur_state.opponent_cuffed:
            next_state.player_turn = cur_state.player_turn
            next_state.opponent_cuffed = False
        else:
            next_state.player_turn = not cur_state.player_turn
            next_state.handcuffs_reuse_blocked = False
    return next_state


def applyAction(cur_state: State, action: Action, outcome: Outcome=None) -> State:
        if cur_state.in_Adrenaline and action.type != "Select Item":
            cur_state = cur_state.clone()
            cur_state.in_Adrenaline = False
        next_state = cur_state.clone()
        next_state.chance = 1.0

        if action.type in ("Shoot Self", "Shoot Opponent"):
            return _apply_shot(cur_state, action, outcome.shell)

        if action.type == "Use Item" and outcome.item == "Beer":
            next_state = _consume_physical_shell(cur_state, outcome.shell)
            items = next_state.player_items if cur_state.player_turn else next_state.dealer_items
            items["Beer"] -= 1
            if next_state.total_left == 0:
                if cur_state.opponent_cuffed:
                    next_state.opponent_cuffed = False
                else:
                    next_state.player_turn = not cur_state.player_turn
                    next_state.handcuffs_reuse_blocked = False
            return next_state

        match action.type:
            case "Shoot Self":
                # Outcome 1: blank shell
                if outcome.shell == "Blank": 
                    # update shell status
                    next_state.total_left -= 1

                    # update shell idx
                    next_state.cur_shell_idx = cur_state.cur_shell_idx + 1

                    # Reset damage
                    next_state.damage = 1

                    if cur_state.shell_inverted:
                        # update shell status
                        next_state.live_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Live"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Live"
                        updateKnowledge(next_state)
                        # update hp
                        if cur_state.player_turn: next_state.player_hp = cur_state.player_hp - cur_state.damage 
                        else: next_state.dealer_hp = cur_state.dealer_hp - cur_state.damage
                        # update turn
                        if cur_state.opponent_cuffed: next_state.player_turn = cur_state.player_turn
                        else: next_state.player_turn = not cur_state.player_turn
                        # update winner
                        if next_state.player_hp < 1: next_state.winner = "Dealer"
                        elif next_state.dealer_hp < 1: next_state.winner = "Player"
                    else: 
                        next_state.blank_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Blank"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Blank"
                        updateKnowledge(next_state)

                # Outcome 2: live shell
                elif outcome.shell == "Live":
                    # update shell status
                    next_state.total_left -= 1

                    # update shell idx
                    next_state.cur_shell_idx = cur_state.cur_shell_idx + 1

                    # Reset damage
                    next_state.damage = 1

                    if cur_state.opponent_cuffed: next_state.player_turn = cur_state.player_turn 
                    else: next_state.player_turn = not cur_state.player_turn

                    # update hp, turn, and winner
                    if not cur_state.shell_inverted:
                        # update shell status
                        next_state.live_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Live"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Live"
                        updateKnowledge(next_state)
                        if cur_state.player_turn: next_state.player_hp = cur_state.player_hp - cur_state.damage
                        else: next_state.dealer_hp = cur_state.dealer_hp - cur_state.damage
                        
                        if next_state.player_hp < 1: next_state.winner = "Dealer"
                        elif next_state.dealer_hp < 1: next_state.winner = "Player"
                    else:
                        # update shell status
                        next_state.blank_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Blank"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Blank"
                        updateKnowledge(next_state)
                    return next_state
            case "Shoot Opponent":
                # Outcome 1: blank shell
                if outcome.shell == "Blank": 
                    # update shell status
                    next_state.total_left -= 1

                    # update shell idx
                    next_state.cur_shell_idx = cur_state.cur_shell_idx + 1

                    # Reset damage
                    next_state.damage = 1

                    # update turn
                    if cur_state.opponent_cuffed: next_state.player_turn = cur_state.player_turn
                    else: next_state.player_turn = not cur_state.player_turn

                    if cur_state.shell_inverted:
                        # update shell status
                        next_state.live_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Live"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Live"
                        updateKnowledge(next_state)
                        # update hp
                        if cur_state.player_turn: next_state.dealer_hp = cur_state.dealer_hp - cur_state.damage 
                        else: next_state.player_hp = cur_state.player_hp - cur_state.damage
                        # update winner
                        if next_state.player_hp < 1: next_state.winner = "Dealer"
                        elif next_state.dealer_hp < 1: next_state.winner = "Player"
                    else:
                        # update shell status
                        next_state.blank_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Blank"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Blank"
                        updateKnowledge(next_state)
                    return next_state

                # Outcome 2: live shell
                if outcome.shell == "Live": 
                    # update shell status
                    next_state.total_left -= 1

                    # update shell idx
                    next_state.cur_shell_idx = cur_state.cur_shell_idx + 1

                    # Reset damage
                    next_state.damage = 1
                    # update hp
                    if cur_state.player_turn: next_state.player_hp = cur_state.player_hp - cur_state.damage
                    else: next_state.dealer_hp = cur_state.dealer_hp - cur_state.damage
                    # update winner
                    if next_state.player_hp < 1: next_state.winner = "Dealer"
                    elif next_state.dealer_hp < 1: next_state.winner = "Player"

                    # update turn
                    if cur_state.opponent_cuffed: next_state.player_turn = cur_state.player_turn
                    else: next_state.player_turn = not cur_state.player_turn

                    if not cur_state.shell_inverted:
                        # update shell status
                        next_state.live_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Live"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Live"
                        updateKnowledge(next_state)
                    else:
                        # update shell status
                        next_state.blank_left -= 1
                        next_state.player_knowledge[cur_state.cur_shell_idx] = "Blank"
                        next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Blank"
                        updateKnowledge(next_state)
                    return next_state
            case "Use Item":
                if cur_state.player_turn: next_state.player_items[outcome.item] -= 1
                else: next_state.dealer_items[outcome.item] -= 1
                match outcome.item:
                    case "Burner Phone":
                        if outcome.hidden:
                            return next_state
                        target_index = (
                            cur_state.cur_shell_idx + outcome.idx - 1
                        )
                        if cur_state.player_turn:
                            next_state.player_knowledge[target_index] = outcome.shell
                        else: 
                            next_state.dealer_knowledge[target_index] = outcome.shell
                        updateKnowledge(next_state)
                    case "Inverter":
                        next_state.shell_inverted = not cur_state.shell_inverted
                    case "Expired Medicine":
                        delta = 2 if outcome.gain else -1
                        if cur_state.player_turn:
                            next_state.player_hp += delta
                            next_state.player_hp = min(next_state.max_hp, next_state.player_hp)
                            if next_state.player_hp < 1: next_state.winner = "Dealer"
                        else: 
                            next_state.dealer_hp += delta
                            next_state.dealer_hp = min(next_state.max_hp, next_state.dealer_hp)
                            if next_state.dealer_hp < 1: next_state.winner = "Player"
                    case "Beer":
                        if outcome.shell == "Blank":
                        # Outcome 1: blank shell
                            next_state.cur_shell_idx += 1
                            next_state.total_left -= 1
                            if cur_state.shell_inverted:
                                # upate shell status
                                next_state.live_left -= 1
                                next_state.player_knowledge[next_state.cur_shell_idx] = "Live"
                                next_state.dealer_knowledge[next_state.cur_shell_idx] = "Live"
                            else:
                                next_state.blank_left -= 1
                                next_state.player_knowledge[next_state.cur_shell_idx] = "Blank"
                                next_state.dealer_knowledge[next_state.cur_shell_idx] = "Blank"
                            updateKnowledge(next_state)

                        elif outcome.shell == "Live":
                        # Outcome 2: live shell
                            next_state.cur_shell_idx += 1
                            next_state.total_left -= 1
                            if cur_state.shell_inverted:
                                # upate shell status
                                next_state.live_left -= 1
                                next_state.player_knowledge[next_state.cur_shell_idx] = "Blank"
                                next_state.dealer_knowledge[next_state.cur_shell_idx] = "Blank"
                            else:
                                next_state.blank_left -= 1
                                next_state.player_knowledge[next_state.cur_shell_idx] = "Live"
                                next_state.dealer_knowledge[next_state.cur_shell_idx] = "Live"
                            updateKnowledge(next_state)
                        return next_state
                    case "Adrenaline":
                        next_state.in_Adrenaline = True
                        return next_state
                    case "Hand Saw": 
                        next_state.damage = 2
                        return next_state
                    case "Handcuffs":
                        next_state.opponent_cuffed = True
                        next_state.handcuffs_reuse_blocked = True
                        return next_state
                    case "Magnifying Glass": 
                        if outcome.hidden:
                            return next_state
                        # Outcome 1: blank shell
                        if outcome.shell == "Blank":
                            if cur_state.player_turn: 
                                next_state.player_knowledge[cur_state.cur_shell_idx] = "Live" if cur_state.shell_inverted else "Blank"
                            else: 
                                next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Live" if cur_state.shell_inverted else "Blank"
                            updateKnowledge(next_state)
                            return next_state
                        
                        # Outcome 2: live shell
                        elif outcome.shell == "Live":
                            if cur_state.player_turn: 
                                next_state.player_knowledge[cur_state.cur_shell_idx] = "Blank" if cur_state.shell_inverted else "Live"
                            else: 
                                next_state.dealer_knowledge[cur_state.cur_shell_idx] = "Blank" if cur_state.shell_inverted else "Live"
                            updateKnowledge(next_state)

                        return next_state
                    case "Cigarette Pack": 
                        if cur_state.player_turn: next_state.player_hp = min(cur_state.max_hp, cur_state.player_hp + 1)
                        else: next_state.dealer_hp = min(cur_state.max_hp, cur_state.dealer_hp + 1)
                        return next_state
            case "Select Item":
                next_state.in_Adrenaline = False
                item = outcome.item if outcome is not None else (
                    action.item.name if hasattr(action.item, "name") else action.item
                )
                if cur_state.player_turn:
                    next_state.dealer_items[item] -= 1
                    next_state.player_items[item] += 1
                else:
                    next_state.player_items[item] -= 1
                    next_state.dealer_items[item] += 1
                return applyAction(
                    next_state,
                    Action("Use Item", "Player" if cur_state.player_turn else "Dealer", findItemObjByName(item)),
                    outcome,
                )
            case "Cancel Adrenaline":
                next_state.in_Adrenaline = False
                return next_state
        return next_state
