def generate_crc8_table():
    poly = 0x31
    table = []
    for crc in range(256):
        for _ in range(8):
            crc = (crc << 1) ^ poly if (crc & 0x80) else crc << 1
            crc &= 0xFF
        table.append(crc)
    return table


CRC8_TABLE = generate_crc8_table()


def crc8_dallas(data):
    crc = 0xFF
    for byte in data:
        crc = CRC8_TABLE[crc ^ byte]
    return crc


def generate_crc16_table():
    table = []
    for byte in range(256):
        crc = byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
        table.append(crc)
    return table


CRC16_CCITT_TABLE = generate_crc16_table()


def crc16_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc = (crc << 8) ^ CRC16_CCITT_TABLE[(crc >> 8) ^ byte]
        crc &= 0xFFFF
    return crc