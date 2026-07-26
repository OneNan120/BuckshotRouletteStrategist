# Buckshot Roulette Strategist

An unofficial single-player strategy companion for **Buckshot Roulette**.

Buckshot Roulette Strategist tracks the current load, health, items, shell
knowledge, and temporary effects during a match. It evaluates the legal
decisions available to both sides and recommends the route with the best
estimated chance of winning.

The project was previously called *Buckshot Roulette Helper*. **Buckshot
Roulette Strategist** better reflects its purpose: analyzing the match and
recommending a strategy instead of merely recording the game state.

> This is an independent fan project. It is not affiliated with or endorsed by
> the developers or publishers of Buckshot Roulette.

> **Single-player only:** this project models matches against the Dealer. It
> does not support Buckshot Roulette's multiplayer mode, which has additional
> items and different gameplay considerations.

## Features

- Tracks live and blank shells, health, inventories, turns, and known shell
  positions
- Supports the single-player item set modeled by this project: Burner Phone,
  Inverter, Beer, Adrenaline, Hand Saw, Handcuffs, Magnifying Glass, Expired
  Medicine, and Cigarette Pack
- Models temporary effects such as inverted shells, saw damage, skipped turns,
  Adrenaline selection, and Handcuffs reuse restrictions
- Keeps separate player and dealer knowledge when information is private
- Evaluates shooting, item use, and item-stealing decisions with an
  expectiminimax search
- Uses an exact tactical solver at the frontier when a complete item search is
  too large
- Shows the estimated player win chance for every legal action
- Accepts compact action shortcuts for quick use during a live match
- Supports multi-action dealer input and one-step undo

## Requirements

- Python 3.10 or newer
- No third-party packages are required to run from source
- PyInstaller is optional and only needed to build a standalone executable

## Running from source

Clone or download the project, open a terminal in its directory, and run:

```console
python main.py
```

From the main menu, enter `r` to start a match. Buckshot Roulette Strategist
will ask for:

1. The shell load
2. Maximum health
3. Player items
4. Dealer items

Enter shells as `1` for live and `2` for blank:

```text
112212
```

Enter inventory keys once per copy. For example, `bmmi` means one Beer, two
Expired Medicines, and one Inverter.

## Controls

### Actions

| Input | Action |
|---|---|
| `ss` | Shoot self, then enter the shell result |
| `so` | Shoot opponent, then enter the shell result |
| `ss1` / `ss2` | Shoot self with a live/blank result |
| `so1` / `so2` | Shoot opponent with a live/blank result |
| `ssu` / `sou` | Shoot with an initially unknown result |
| `ui <key>` | Use an item |
| `<item key>` | Use an item directly |
| `e` | Undo the previous action |

Shell-result keys are:

| Key | Meaning |
|---|---|
| `1` | Live |
| `2` | Blank |
| `u` or `0` | Unknown |

When a consumed shell was not observed, Buckshot Roulette Strategist asks for
the new remaining shell counts. This lets it infer what left the chamber
without guessing.

### Item keys

| Key | Item |
|---|---|
| `p` | Burner Phone |
| `i` | Inverter |
| `m` | Expired Medicine |
| `b` | Beer |
| `a` | Adrenaline |
| `s` | Hand Saw |
| `h` | Handcuffs |
| `g` | Magnifying Glass |
| `c` | Cigarette Pack |

Item outcomes can be recorded in the same command:

```text
b1    Beer ejected a live shell
b2    Beer ejected a blank shell
g1    Magnifying Glass revealed a live shell
g2    Magnifying Glass revealed a blank shell
m1    Expired Medicine succeeded
m0    Expired Medicine failed
p21   Burner Phone revealed that position 2 is live
p42   Burner Phone revealed that position 4 is blank
```

### Adrenaline

Use `si <key>` to choose the item stolen with an active Adrenaline. Adrenaline
and its selected item can also be entered together:

```text
ab2    Steal Beer and eject a blank shell
ap42   Steal Burner Phone; position 4 is blank
```

Enter `0`, `si 0`, or `si skip` to let Adrenaline expire without selecting an
item.

### Dealer sequences

Several dealer actions can be entered on one line:

```text
h so1 i p ss2 so1
```

The sequence stops automatically when the dealer's turn ends. Player actions
are entered one at a time.

### Global commands

| Input | Action |
|---|---|
| `q` | Open the manual |
| `k` | Open the item catalog |
| `v` | Show the current state |
| `r` | Start a new match |
| `z` | Return to the main menu |
| `exit` | Quit |

## Understanding recommendations

Buckshot Roulette Strategist reports values as the estimated probability that
the **player** wins. On the player's turn it seeks the highest value; on the
dealer's turn it assumes the dealer chooses the lowest value.

```text
Available actions (value = player win chance):
   1. Use Beer                          58.62%
   2. Use Magnifying Glass              57.14%
   3. Shoot Self                        42.29%
   4. Shoot Opponent                    38.81%
```

Large positions are searched with a fixed state budget. These results are
marked `Estimated State Value` and `Search: approximate`. Equal estimates use
item preservation and information value as tie-breakers; a visibly lower
estimate does not replace the highest one.

The recommendation is decision support, not a prediction of the game's random
outcome. Its accuracy depends on the entered state and observed results.

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Console interface, input parsing, history, and game loop |
| `state.py` | Game state, legal actions, item effects, and transitions |
| `solver.py` | Exact and bounded expectiminimax strategy search |
| `item.py` | Item definitions and rules |
| `action.py` | Action model |
| `outcome.py` | Observed action outcomes |
| `value.py` | Display model for evaluated actions |
| `test_state.py` | State-transition and strategy regression tests |

## Tests

Run the regression suite with:

```console
python -m unittest -v
```

## Building a Windows executable

Install PyInstaller:

```console
python -m pip install pyinstaller
```

Then build from the project directory:

```console
python -m PyInstaller --onefile --console --name BuckshotRouletteStrategist --noconfirm main.py
```

The executable will be written to `dist/BuckshotRouletteStrategist.exe`.