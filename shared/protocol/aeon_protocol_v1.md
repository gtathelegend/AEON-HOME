# AEON Serial Protocol v1

Binary framing protocol between Arduino Sentinel and Snapdragon backend.

## Frame structure

```
Offset  Size  Field
0       2     MAGIC (0xAE 0x01)
2       1     TYPE
3       4     SEQ (uint32 little-endian, monotonic)
7       2     LEN (uint16 little-endian, payload length in bytes)
9       LEN   PAYLOAD
9+LEN   2     CRC16/CCITT-FALSE over bytes [TYPE..PAYLOAD]
```

## Frame types

| Value | Name          | Direction             | Payload                        |
|-------|---------------|-----------------------|--------------------------------|
| 0x01  | FEATURE_FRAME | Arduino → Snapdragon  | FeatureFrame struct (28 bytes) |
| 0x02  | EVENT         | Arduino → Snapdragon  | ASCII string "category:name:arg" |
| 0x10  | COMMAND       | Snapdragon → Arduino  | 1-byte type + 4-byte arg + payload |
| 0xFF  | ACK           | Both directions       | Empty payload                  |

## FeatureFrame payload layout (28 bytes, little-endian)

```
Offset  Size  Type     Field
0       4     float32  temperature   (°C)
4       4     float32  humidity      (%)
8       1     uint8    motion        (0/1)
9       1     uint8    door_open     (0/1)
10      4     float32  mean_temp
14      4     float32  var_temp
18      4     float32  delta_motion  (events/s)
22      4     uint32   timestamp_ms
```

## CRC algorithm

CRC-16/CCITT-FALSE: poly=0x1021, init=0xFFFF, refin=false, refout=false, xorout=0x0000.

## Flow control

- Arduino sends FEATURE_FRAME at ~2 Hz (every SENSOR_SAMPLE_MS × 4 samples).
- Snapdragon sends ACK within 100 ms; if no ACK in 500 ms, Arduino re-transmits once.
- COMMAND frames are sent by Snapdragon for actuation; Arduino responds with ACK.

## Versioning

The MAGIC second byte encodes the protocol version (currently 0x01).
Version negotiation: Arduino sends its version in the first EVENT frame on boot.
