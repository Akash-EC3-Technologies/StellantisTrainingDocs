"""
Lightweight 8-bit checksum helpers.
Checksum = 0xFF - ((Level + (Counter & 0x0F)) & 0xFF)
"""
def make_checksum(level: int, counter: int) -> int:
    return (0xFF - ((int(level) + (int(counter) & 0x0F)) & 0xFF)) & 0xFF

def verify_checksum(level: int, counter: int, checksum: int) -> bool:
    return make_checksum(level, counter) == (checksum & 0xFF)
