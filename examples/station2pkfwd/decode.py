#---------------------ENCABEZADO--------------------
#| 0x01 | DevEUI | 0x41 | 1 byte| 8 bytes | FCnt  |

#---------------------GNSS--------------------
#+------+-------+-------------+-------------+-------------------+
#| 0x61 | Len   | Timestamp   | Status      | Payload           |
#| 1B   | 1B    | 4B (inv)    | 4B          | N bytes (varía)   |
#+------+-------+-------------+-------------+-------------------+
#| gnss | Cant  | Timestamp   | Estado GNSS | Datos GNSS

#---------------------WIFI--------------------
#+------+-------+-------------+-------------------------------+
#| 0x62 | Len   | Timestamp   | Beacons (cada uno 8 bytes)    |
#| 1B   | 1B    | 4B (inv)    | N x 8B                        |
#+------+-------+-------------+-------------------------------+
#| wifi | Cant  | Timestamp   | Lista de balizas WiFi

def parse_trama(hex_string):
    index = 0
    trama = bytes.fromhex(hex_string)

    def read_bytes(n):
        nonlocal index
        data = trama[index:index + n]
        index += n
        return data

    def parse_timestamp(raw_bytes):
        return int.from_bytes(raw_bytes[::-1], byteorder='big')

    result = {}

    # ENCABEZADO
    if trama[index] == 0x01:
        index += 1
        result['DevEUI'] = read_bytes(8).hex().upper()

    if trama[index] == 0x41:
        index += 1
        result['FCnt'] = int.from_bytes(read_bytes(4), byteorder='big')

    # GNSS y/o WiFi
    while index < len(trama):
        code = trama[index]
        index += 1

        if index >= len(trama):
            break

        length = trama[index]
        index += 1

        frame_data = read_bytes(length)

        if code == 0x61:  # GNSS
            ts_raw = frame_data[0:4]
            status_raw = frame_data[4:8]
            payload = frame_data[8:]
            result['GNSS'] = {
                'Scan Timestamp': parse_timestamp(ts_raw),
                'Status': status_raw.hex().upper(),
                'Payload': payload.hex().upper()
            }

        elif code == 0x62:  # WiFi
            ts_raw = frame_data[0:4]
            beacons_raw = frame_data[4:]

            beacons = []
            for i in range(0, len(beacons_raw), 8):
                beacon = beacons_raw[i:i+8]
                if len(beacon) == 8:
                    cleaned = beacon[0:1] + beacon[2:]
                    beacons.append(cleaned.hex().upper())

            result['WiFi'] = {
                'Scan Timestamp': parse_timestamp(ts_raw),
                'Beacons': beacons
            }

        else:
            result[f"Unknown_{code:02X}"] = frame_data.hex().upper()

    return result

def parse_estado(data):
    index = 0
    result = {}

    # Leer encabezado DevEUI (0x01)
    if data[index] == 0x01:
        index += 1
        result['DevEUI'] = int.from_bytes(data[index:index+8], byteorder='big')
        index += 8

    # Leer encabezado FCnt (0x41)
    if data[index] == 0x41:
        index += 1
        result['FCnt'] = int.from_bytes(data[index:index+4], byteorder='big')
        index += 4

    # Leer el resto como trama de estado
    while index < len(data):
        code = data[index]
        index += 1

        if code == 0x10:
            valor = int.from_bytes(data[index:index+2], byteorder='big')
            result['Bateria_mV'] = valor
            index += 2
        elif code == 0x11:
            valor = int.from_bytes(data[index:index+4], byteorder='big')
            result['Energia_mJ'] = valor
            index += 4
        elif code == 0x12:
            valor = int.from_bytes(data[index:index+4], byteorder='big')
            result['Carga_ms'] = valor
            index += 4
        elif code == 0x30:
            result['Flags'] = f"{data[index]:08b}"
            index += 1
        elif code == 0x40:
            valor = int.from_bytes(data[index:index+3], byteorder='big')
            result['Resets'] = valor
            index += 3
        elif code == 0x50:
            result['Temperatura_C'] = data[index]
            index += 1
        else:
            result[f"Desconocido_{code:02X}"] = "??"
            break

    return result


# Ejemplo de uso:
trama_hex = "010016C001F01A33384100002F9E613479A22B6718090101AB454168F50D4C9F9A5A6D52DCEEF8E7EE38A1797816F4E3A3C431476880316F923D83A919F45734AA72B522622C79A22B67BC113AA65920ABEFB911C04A0059B02AB911484BD444DA70B311B0BBE540D6E2B311D0579473483D"
decodificado = parse_trama(trama_hex)

from pprint import pprint
pprint(decodificado)


trama_estado_hex = "100EB611000000E91201040280300040000000503D"
estado_bytes = bytes.fromhex(trama_estado_hex)

from pprint import pprint
pprint(parse_estado(estado_bytes))