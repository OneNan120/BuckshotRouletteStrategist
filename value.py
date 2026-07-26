class Value:
    name: str
    val: float
    def __init__(self, name, val):
        self.name = name
        self.val = val
    def __str__(self):
        return self.name + ": " + str(self.val)