import copy
class Item:
    pass

class Phone:
    def __init__(self):
        self.name = "Burner Phone"
        self.description = "Upon use, the user will be told the location and type of a random shell loaded in the Shotgun if there are two or more shells left in the chamber. The phone will state the location of the random shell relative to the current shell (e.g. 'Second shell' means the shell after the one currently in the chamber)."
        self.target = "Shell"
        self.legals = [
            "At least two shells remaining"
        ]
        self.has_random = True
        self.physical_state_change = False
        self.knowledge_state_change = True
        self.turn_consumed_If_last_shell = False

class Inverter:
    def __init__(self):
        self.name = "Inverter"
        self.description = "Upon its use, the current shell in the chamber of the Shotgun will have its polarity reversed; a blank shell becomes a live shell, and a live shell becomes a blank shell."
        self.target = "Shell"
        self.legals = []
        self.has_random = False
        self.physical_state_change = False
        self.knowledge_state_change = True
        self.turn_consumed_If_last_shell = False

class Medicine:
    def __init__(self):
        self.name = "Expired Medicine"
        self.description = "Upon use, the user has a 50% chance of regaining two charges and a 50% chance of losing one."
        self.target = "Self"
        self.legals = [
            "User health is not full"
        ]
        self.has_random = True
        self.physical_state_change = True
        self.knowledge_state_change = False
        self.turn_consumed_If_last_shell = False
class Beer:
    def __init__(self):
        self.name = "Beer"
        self.description = "Upon use, the user will rack the Shotgun, ejecting the current shell without firing it. If a Beer is used on the last round of a load, it ends that player's turn."
        self.target = "Shell"
        self.legals = []
        self.has_random = False
        self.physical_state_change = True
        self.knowledge_state_change = True
        self.turn_consumed_If_last_shell = True
class Adrenaline:
    def __init__(self):
        self.name = "Adrenaline"
        self.description = "Upon use, the user will be able to steal one item from the opposing player's board and use it immediately. Any item can be stolen except for another Adrenaline, or Handcuffs if the opponent being stolen from is already cuffed. If the user does not select an item within 10 seconds, the effect will wear off, barring them from stealing an item."
        self.target = "Opponent"
        self.legals = [
            "opponent owns at least one non-Adrenaline item"
        ]
        self.has_random = False
        self.physical_state_change = True
        self.knowledge_state_change = False
        self.turn_consumed_If_last_shell = False
class HandSaw:
    def __init__(self):
        self.name = "Hand Saw"
        self.description = "Upon being used, the user will saw part of the Shotgun's barrel and magazine off. The Shotgun will then deal double damage for the next turn if a live round is chambered. The barrel will regrow after the turn ends."
        self.target = "Shell"
        self.legals = [
            "Shotgun is not sawed"
        ]
        self.has_random = False
        self.physical_state_change = True
        self.knowledge_state_change = False
        self.turn_consumed_If_last_shell = False
class Handcuffs:
    def __init__(self):
        self.name = "Handcuffs"
        self.description = "Upon use, the opposing player will skip their next turn."
        self.target = "Opponent"
        self.legals = [
            "Opponent is not cuffed"
        ]
        self.has_random = False
        self.physical_state_change = True
        self.knowledge_state_change = False
        self.turn_consumed_If_last_shell = False   
class MagnifyingGlass:
    def __init__(self):
        self.name = "Magnifying Glass"
        self.description = "Upon being used, the user will see what type of round is currently loaded in the Shotgun's chamber."
        self.target = "Shell"
        self.legals = []
        self.has_random = False
        self.physical_state_change = False
        self.knowledge_state_change = True
        self.turn_consumed_If_last_shell = False    
class CigarettePack:
    def __init__(self):
        self.name = "Cigarette Pack"
        self.description = "Upon being used, the user will gain one charge."
        self.target = "Self"
        self.legals = [
            "User health is not full"
        ]
        self.has_random = False
        self.physical_state_change = True
        self.knowledge_state_change = False
        self.turn_consumed_If_last_shell = False

phone = Phone()
inverter = Inverter()
medicine = Medicine()
beer = Beer()
adrenaline = Adrenaline()
handSaw = HandSaw()
handcuffs = Handcuffs()
magnifyingGlass = MagnifyingGlass()
cigarettePack = CigarettePack()

itemKeyMap = {
    'p' : "Burner Phone",
    'i' : "Inverter",
    'm' : "Expired Medicine",
    'b' : "Beer",
    'a' : "Adrenaline",
    's' : "Hand Saw",
    'h' : "Handcuffs",
    'g' : "Magnifying Glass",
    'c' : "Cigarette Pack",
}

defaultItemDict = {}
for name in itemKeyMap.values():
    defaultItemDict[name] = 0

def findItemObjByName(name) -> Item:
    match name:
        case "Burner Phone":
            return phone
        case "Inverter":
            return inverter
        case "Expired Medicine" | "Medicine":
            return medicine
        case "Beer":
            return beer
        case "Adrenaline":
            return adrenaline
        case "Hand Saw":
            return handSaw
        case "Handcuffs":
            return handcuffs
        case "Magnifying Glass":
            return magnifyingGlass
        case "Cigarette Pack":
            return cigarettePack
