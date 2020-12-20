class PmbusCommandTableBaseError(Exception):
	def __init__(self, error_message):
		super().__init__(error_mesage)
		self.error_message = error_message

class PmbusCommandTableInvalidCommand(Q48SC12050PmbusCommandTableBaseError):
	def __init__(self, command):
		super().__init__(f"{command_name} does not exist in the command table")

class PmbusCommandTable:

	def __init__(self, file_name):
		self.pmbus_command_table = dict()
		self.file_name = file_name
		self.initialize_command_table()

	def initialize_command_table(self):
		# Open File
		try:
			input_file = open(self.file_name, 'r')
		except:
			print("Invalid file name to initialize pmbus dictionary")
			raise

		# Read Headers Line
		read_line = input_file.readline()

		# Read Data Lines
		read_line = input_file.readline()
		while read_line != "":
			if read_line[-1] == "\n":
				read_line = read_line[:-1]
			command_data = read_line.split(",")
			new_command_entry = PmbusCommand(command_data)
			self.add_table_entry(new_command_entry.get_command_name(), new_command_entry)
			self.add_table_entry(new_command_entry.get_command_address(), new_command_entry)
			read_line = input_file.readline()

		# Close File
		input_file.close()

	def __getitem__(self, key):
		try:
			command_entry = self.pmbus_command_table[key]
		except:
			raise Q48SC12050PmbusCommandTableInvalidCommand(command=key)
		return command_entry

	def get_file_name(self):
		return self.table_file_name

	def add_table_entry(self, key, value):
		self.pmbus_command_table.update({key : value})

class PmbusCommand:
	COMMAND_NAME_INDEX = 0
	COMMAND_ADDRESS_INDEX = 1
	READ_EN_INDEX = 2
	WRITE_EN_INDEX = 3
	NUM_DATA_BYTES_INDEX = 4
	LINEAR_COMMAND_INDEX = 5
	EXPONENT_INDEX = 6
	NUM_MANTISSA_BITS_INDEX = 7
	NUM_EXPONENT_BITS_INDEX = 8
	DATA_SIGNED_INDEX = 9

	TRUE_STRING = "T"
	FALSE_STRING = "F"

	def __init__(self, command_data):
		self.command_data = command_data

		command_address_string = self.command_data[PmbusCommand.COMMAND_ADDRESS_INDEX]
		self.command_address_int = convert_byte_string_to_int(command_address_string)

		command_address_unsigned_int = convert_signed_byte_to_unsigned_byte(self.command_address_int)
		self.command_address_hex = hex(command_address_unsigned_int)

	def get_command_name(self):
		return self.command_data[Q48SC12050PmbusCommandEntry.COMMAND_NAME_INDEX]

	def get_command_address_int(self):
		return self.command_address_int

	def get_command_address_hex(self):
		return self.command_address_hex

	def is_read_enabled(self):
		return (self.command_data[Q48SC12050PmbusCommandEntry.READ_EN_INDEX] == Q48SC12050PmbusCommandEntry.TRUE_STRING)

	def is_write_enabled(self):
		return (self.command_data[Q48SC12050PmbusCommandEntry.WRITE_EN_INDEX] == Q48SC12050PmbusCommandEntry.TRUE_STRING)

	def get_num_data_bytes(self):
		return int(self.command_data[Q48SC12050PmbusCommandEntry.NUM_DATA_BYTES_INDEX])

	def is_linear_data_format(self):
		return (self.command_data[Q48SC12050PmbusCommandEntry.LINEAR_COMMAND_INDEX] == Q48SC12050PmbusCommandEntry.TRUE_STRING)

	def get_exponent(self):
		if not self.is_linear_data_format():
			return None
		return int(self.command_data[Q48SC12050PmbusCommandEntry.EXPONENT_INDEX])

	def get_num_mantissa_bits(self):
		if not self.is_linear_data_format():
			return None
		return int(self.command_data[Q48SC12050PmbusCommandEntry.NUM_MANTISSA_BITS_INDEX])

	def get_num_exponent_bits(self):
		if not self.is_linear_data_format():
			return None
		return int(self.command_data[Q48SC12050PmbusCommandEntry.NUM_EXPONENT_BITS_INDEX])

	def is_data_signed(self):
		if not self.is_linear_data_format():
			return None
		return (self.command_data[Q48SC12050PmbusCommandEntry.DATA_SIGNED_INDEX] == Q48SC12050PmbusCommandEntry.TRUE_STRING)

def convert_byte_string_to_int(byte_string):
	"""
	Converts a hex string, binary string, or int/uint
	string that represents a single byte to an integer
	"""
	try:
		if len(byte_string) >= 2:
			if byte_string[0:2] == "0b":
				verify_binary_byte_string_length(byte_string)
				byte_int = int(byte_string, 2)
			elif byte_string[0:2] == "0x":
				verify_hex_byte_string_length(byte_string)
				byte_int = int(byte_string, 16)
			elif byte_string[0] == "-":
				byte_int = int(byte_string)
				verify_int_byte_string(byte_int)
			else:
				byte_int = int(byte_string)
				verify_unsigned_int_byte_string(byte_int)
				byte_int = convert_unsigned_byte_to_signed_byte(byte_int)
		else:
			byte_int = int(byte_string)
			verify_unsigned_int_byte_string(byte_int)
			byte_int = convert_unsigned_byte_to_signed_byte(byte_int)
	except:
		# Raise Error
	return byte_int

def verify_binary_byte_string_length(binary_string):
	NUM_HEADER_BITS = len("0b")
	NUM_BITS_IN_BYTE = 8
	BINARY_STRING_LENGTH = NUM_HEADER_BITS + NUM_BITS_IN_BYTE
	if len(binary_string) != BINARY_STRING_LENGTH:
		# Raise Error

def verify_hex_byte_string_length(hex_string):
	NUM_HEADER_BITS = len("0x")
	NUM_HEX_DIGITS_IN_BYTE = 2
	HEX_STRING_LENGTH = NUM_HEADER_BITS + NUM_HEX_DIGITS_IN_BYTE
	if len(hex_string) != HEX_STRING_LENGTH:
		# Raise Error

def verify_int_byte_string(int_string)
	if not (-128 <= byte_int <= 127):
		# Raise Error

def verify_unsigned_int_byte_string(int_string):
	if not (0 <= byte_int <= 255):
		# Raise Error

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