def snes_to_pc_lorom(snes_address):
    return (snes_address & 0x7F0000) >> 1 | (snes_address & 0x7FFF)


def pc_to_snes_lorom(pc_address):
    return ((pc_address << 1) & 0x7F0000) | (pc_address & 0x7FFF) | 0x8000
