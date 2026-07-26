import unittest
from unittest.mock import patch

from action import Action
from item import defaultItemDict, findItemObjByName
from main import parseInput
from outcome import Outcome
from solver import fairApproximateResult, immediateItemCost
from state import State, applyAction


def state_with_shells(live, blank):
    state = State()
    state.live_left = live
    state.blank_left = blank
    state.total_left = live + blank
    state.player_hp = 4
    state.dealer_hp = 4
    state.max_hp = 4
    state.player_knowledge = ["Unknown"] * state.total_left
    state.dealer_knowledge = ["Unknown"] * state.total_left
    return state


class ShellTransitionTests(unittest.TestCase):
    def test_beer_ejects_physical_blank_after_inverter(self):
        state = state_with_shells(3, 4)
        state.shell_inverted = True
        state.player_items["Beer"] = 1

        result = applyAction(
            state,
            Action("Use Item", "Player", "Beer"),
            Outcome(item="Beer", shell="Blank"),
        )

        self.assertEqual((result.live_left, result.blank_left), (3, 3))
        self.assertEqual(result.player_knowledge[0], "Blank")
        self.assertFalse(result.shell_inverted)

    def test_solver_beer_branches_use_physical_shell_probabilities(self):
        state = state_with_shells(3, 4)
        state.shell_inverted = True
        state.player_items["Beer"] = 1
        action = next(
            action
            for action in state.listLegalActions()
            if action.type == "Use Item" and action.item.name == "Beer"
        )

        branches = state.listAllNextStates(action)
        by_shell = {branch.player_knowledge[0]: branch for branch in branches}

        self.assertAlmostEqual(by_shell["Blank"].chance, 4 / 7)
        self.assertEqual(
            (by_shell["Blank"].live_left, by_shell["Blank"].blank_left),
            (3, 3),
        )
        self.assertAlmostEqual(by_shell["Live"].chance, 3 / 7)
        self.assertEqual(
            (by_shell["Live"].live_left, by_shell["Live"].blank_left),
            (2, 4),
        )

    def test_saw_damage_survives_items_and_applies_to_next_live_shot(self):
        state = state_with_shells(1, 1)
        state.player_turn = False
        state.damage = 2

        result = applyAction(
            state,
            Action("Shoot Opponent", "Dealer"),
            Outcome(shell="Live"),
        )

        self.assertEqual(result.player_hp, 2)
        self.assertEqual(result.damage, 1)

    def test_dealer_sequence_keeps_prior_actions_when_shot_ends_turn(self):
        state = state_with_shells(1, 1)
        state.player_turn = False
        state.dealer_items = defaultItemDict.copy()
        state.dealer_items["Hand Saw"] = 1

        with patch("builtins.input", side_effect=AssertionError("must not re-prompt")):
            result = parseInput("Action", "s so1 m1", state)

        self.assertTrue(result.player_turn)
        self.assertEqual(result.player_hp, 2)
        self.assertEqual(result.total_left, 1)
        self.assertEqual(result.dealer_items["Hand Saw"], 0)

    def test_handcuffs_cannot_be_reused_during_retained_turn(self):
        state = state_with_shells(2, 1)
        state.player_items["Handcuffs"] = 2
        cuffed = applyAction(
            state,
            Action("Use Item", "Player", "Handcuffs"),
            Outcome(item="Handcuffs"),
        )
        retained = applyAction(
            cuffed,
            Action("Shoot Opponent", "Player"),
            Outcome(shell="Live"),
        )

        legal_items = {
            action.item.name
            for action in retained.listLegalActions()
            if action.type == "Use Item"
        }
        self.assertTrue(retained.player_turn)
        self.assertNotIn("Handcuffs", legal_items)

        passed = applyAction(
            retained,
            Action("Shoot Opponent", "Player"),
            Outcome(shell="Blank"),
        )
        self.assertFalse(passed.player_turn)
        self.assertFalse(passed.handcuffs_reuse_blocked)

    def test_beer_cost_includes_wasted_active_inverter(self):
        state = state_with_shells(1, 1)
        state.shell_inverted = True
        action = Action("Use Item", "Player", "Beer")
        self.assertEqual(immediateItemCost(action, state), 2)

    def test_approximate_ranking_does_not_replace_higher_value_with_info(self):
        beer = Action(
            "Use Item", "Player", findItemObjByName("Beer")
        )
        glass = Action(
            "Use Item", "Player", findItemObjByName("Magnifying Glass")
        )
        state = state_with_shells(4, 4)
        state.listLegalActions = lambda: [beer, glass]
        estimates = {
            id(beer): (0.5862, 1.0),
            id(glass): (0.5714, 1.0),
        }

        with patch(
            "solver.evaluateRootActionFairly",
            side_effect=lambda _, action: estimates[id(action)],
        ):
            result = fairApproximateResult(state)

        self.assertIs(result.best_action, beer)
        self.assertAlmostEqual(result.state_value, 0.5862)


if __name__ == "__main__":
    unittest.main()
