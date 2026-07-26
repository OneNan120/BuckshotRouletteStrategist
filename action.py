from item import Item
class Action:
    type: str # Shoot Self, Shoot Opponent, Use Item, Select Item
    actor: str # Player, Dealer
    item: Item | None 

    def __init__(self, type, actor, item=None):
        self.type = type
        self.actor = actor
        self.item = item

    def __str__(self):
        if self.type == "Cancel Adrenaline":
            return "Let Adrenaline expire"
        if self.item:
            if self.type == "Select Item":
                return f"Steal and use {self.item.name}"
            return f"Use {self.item.name}"
        return self.type
