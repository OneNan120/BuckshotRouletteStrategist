class Outcome:
    shell: str
    idx: int # one-based Phone position; current shell is position 1
    item: str
    gain: bool # medicine

    def __init__(self, shell=None, idx=None, item=None, gain=None, hidden=False):
        self.shell = shell
        self.idx = idx
        self.item = item
        self.gain = gain
        self.hidden = hidden
