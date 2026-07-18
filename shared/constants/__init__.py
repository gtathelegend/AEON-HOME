# shared/constants/__init__.py

# Protocol Constants
AEON_MAGIC_0 = 0xAE
AEON_MAGIC_1 = 0x01
AEON_MAGIC = (AEON_MAGIC_0, AEON_MAGIC_1)

# Frame Types
AEON_TYPE_FEATURE_FRAME = 0x01
AEON_TYPE_EVENT         = 0x02
AEON_TYPE_COMMAND       = 0x10
AEON_TYPE_ACK           = 0xFF

# Default configurations
DEFAULT_BAUD_RATE = 115200
DEFAULT_DEVICE_ID = "aeon-home-001"
