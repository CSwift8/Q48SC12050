class ByteConversionBaseError(Exception):
	def __init__(self, error_message):
		super().__init__(error_message)
		self.error_message = error_message

class ByteConversionInvalidBinaryByteString(ByteConversionBaseError):
	def __init__(self, binary_string):
		super().__init__(f"Invalid Binary Byte String {binary_string}; must have 8 bits")

class ByteConversionInvalidHexByteString(ByteConversionBaseError):
	def __init__(self, hex_string):
		super().__init__(f"Invalid Hex Byte String {hex_string}; must have 2 hex digits")

class ByteConversionInvalidSignedIntByteString(ByteConversionBaseError):
	def __init__(self, int_string):
		super().__init__(f"Invalid Signed Int Byte String {int_string}; must be [-128, 127]")

class ByteConversionInvalidUnsignedIntByteString(ByteConversionBaseError):
	def __init__(self, unsigned_int_string):
		super().__init__(f"Invalid Unsigned Int Byte String {unsigned_int_string}; must be [0, 255]")

class ByteConversionNotNumericalByteString(ByteConversionBaseError):
	def __init__(self, byte_string):
		super().__init__(f"Invalid Byte String {byte_string}; must be a binary, hex, int, or uint byte number")

def convert_byte_string_to_int(byte_string):
	"""
	Converts a hex string, binary string, or int/uint
	string that represents a single byte to an integer
	"""
	try:
		if len(byte_string) >= 2:
			if byte_string[0:2] == "0b":
				byte_int = get_and_verify_binary_byte_string_length(byte_string)
			elif byte_string[0:2] == "0x":
				byte_int = get_and_verify_hex_byte_string_length(byte_string)
			elif byte_string[0] == "-":
				byte_int = get_and_verify_int_byte(byte_string)
			else:
				unsigned_byte_int = get_and_verify_unsigned_int_byte(byte_string)
				byte_int = convert_unsigned_byte_to_signed_byte(unsigned_byte_int)
		else:
			unsigned_byte_int = get_and_verify_unsigned_int_byte(byte_string)
			byte_int = convert_unsigned_byte_to_signed_byte(unsigned_byte_int)
	except ValueError:
		raise ByteConversionNotNumericalByteString(byte_string)
	except:
		raise

	return byte_int

def get_and_verify_binary_byte_string_length(binary_string):
	NUM_HEADER_BITS = len("0b")
	NUM_BITS_IN_BYTE = 8
	BINARY_STRING_LENGTH = NUM_HEADER_BITS + NUM_BITS_IN_BYTE
	if len(binary_string) != BINARY_STRING_LENGTH:
		raise ByteConversionInvalidBinaryByteString(binary_string)
	return int(binary_string, 2)

def get_and_verify_hex_byte_string_length(hex_string):
	NUM_HEADER_BITS = len("0x")
	NUM_HEX_DIGITS_IN_BYTE = 2
	HEX_STRING_LENGTH = NUM_HEADER_BITS + NUM_HEX_DIGITS_IN_BYTE
	if len(hex_string) != HEX_STRING_LENGTH:
		raise ByteConversionInvalidHexByteString(hex_string)
	return int(hex_string, 16)

def get_and_verify_int_byte(byte_string):
	byte_int = int(byte_string)
	if not (-128 <= byte_int <= 127):
		raise ByteConversionInvalidSignedIntByteString(byte_int)
	return byte_int

def get_and_verify_unsigned_int_byte(byte_string):
	byte_int = int(byte_string)
	if not (0 <= byte_int <= 255):
		raise ByteConversionInvalidUnsignedIntByteString(byte_int)
	return byte_int

def convert_unsigned_byte_to_signed_byte(unsigned_byte_int):
	if unsigned_byte_int > 127:
		signed_byte_int = unsigned_byte_int - 256
	else:
		signed_byte_int = unsigned_byte_int
	return signed_byte_int

def convert_signed_byte_to_unsigned_byte(signed_byte_int):
	if signed_byte_int < 0:
		unsigned_byte_int = signed_byte_int + 256
	else:
		unsigned_byte_int = signed_byte_int
	return unsigned_byte_int