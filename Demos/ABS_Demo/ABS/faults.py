"""
Fault bitfield helpers.
bit0: Timeout, bit1: ChkFail, bit2: Range, bit3: BusOff
"""
TIMEOUT = 1 << 0
CHKFAIL = 1 << 1
RANGE   = 1 << 2
BUSOFF  = 1 << 3
