import byte_conversion

class PmbusCommandTableBaseError(Exception):
	def __init__(self, error_message):
		super().__init__(error_mesage)
		self.error_message = error_message

class PmbusCommandTableCommandDNE(PmbusCommandTableBaseError):
	def __init__(self, command, file_path):
		super().__init__(f"{command} command does not exist in table from {file_path}")

class PmbusCommandTable:

	def __init__(self, file_path):
		self.command_table = dict()
		self.file_path = file_path
		self.initialize_command_table()

	def initialize_command_table(self):
		input_file = open(self.file_path, 'r')

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
			self.add_table_entry(new_command_entry.get_command_address_int(), new_command_entry)
			read_line = input_file.readline()

		input_file.close()

	def add_table_entry(self, key, value):
		self.command_table.update({key : value})

	def get_file_path(self):
		return self.file_path

	def __getitem__(self, key):
		try:
			command = self.command_table[key]
		except:
			raise PmbusCommandTableCommandDNE(key, self.get_file_path())
		return command

class PmbusCommandBaseError(Exception):
	def __init__(self, error_message):
		super().__init__(error_mesage)
		self.error_message = error_message

class PmbusCommandInvalidBooleanParameterError(PmbusCommandBaseError):
	def __init__(self, command_name):
		super().__init__(f"Invalid Boolean Parameter String for {command_name} command; either T or F")

class PmbusCommandInvalidIntParameterError(PmbusCommandBaseError):
	def __init__(self, command_name):
		super().__init__(f"Invalid Integer Parameter String for {command_name} command; must be Base 10 integer")

class PmbusCommandInvalidNumBytesParameterError(PmbusCommandBaseError):
	def __init__(self, command_name):
		super().__init__(f"Invalid Number of Bytes Parameter for {command_name} command; must be positive integer")

class PmbusCommandInvalidExponentParameterError(PmbusCommandBaseError):
	def __init__(self, command_name):
		super().__init__(f"Invalid Exponent Parameter for {command_name} command; must be non-positive integer")

class PmbusCommandInvalidNumberOfBitsParameterError(PmbusCommandBaseError):
	def __init__(self, command_name):
		super().__init__(f"Invalid Number of Mantissa or Exponent Bits for {command_name} command; both must be positive integers that sum to 16")

class PmbusCommandInvalidNumberOfParameters(PmbusCommandBaseError):
	def __init__(self, command_name, actual_num, expected_num):
		super().__init__(f"Invalid Number of parameters for {command_name}; expected {expected_num}, but received {actual_num}")

class PmbusCommand:
	TOTAL_NUM_COMMAND_PARAMETERS = 10

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
		self.command_name = self.command_data[PmbusCommand.COMMAND_NAME_INDEX]
		self.set_and_verify_command_parameters()

	def get_command_name(self):
		return self.command_name

	def get_command_address_int(self):
		return self.command_address_int

	def get_command_address_hex(self):
		return self.command_address_hex

	def is_read_enabled(self):
		return self.read_enabled

	def is_write_enabled(self):
		return self.write_enabled

	def get_num_data_bytes(self):
		return self.num_bytes

	def is_linear_data_format(self):
		return self.linear_data_format

	def get_exponent(self):
		if not self.is_linear_data_format():
			return None
		return self.exponent

	def get_num_mantissa_bits(self):
		if not self.is_linear_data_format():
			return None
		return self.num_mantissa_bits

	def get_num_exponent_bits(self):
		if not self.is_linear_data_format():
			return None
		return self.num_exponent_bits

	def is_data_signed(self):
		if not self.is_linear_data_format():
			return None
		return self.data_signed

	def verify_num_command_parameters(self):
		actual_num_parameters = len(self.command_data)
		if actual_num_parameters != PmbusCommand.TOTAL_NUM_COMMAND_PARAMETERS:
			raise PmbusCommandInvalidNumberOfParameters(self.get_command_name(), actual_num_parameters, PmbusCommand.TOTAL_NUM_COMMAND_PARAMETERS)

	def get_and_verify_boolean_parameter(self, parameter_index):
		parameter = self.command_data[parameter_index]
		if (parameter != PmbusCommand.TRUE_STRING) and (parameter != PmbusCommand.FALSE_STRING):
			raise PmbusCommandInvalidBooleanParameterError(self.get_command_name())
		return (parameter == PmbusCommand.TRUE_STRING)

	def get_and_verify_int_parameter(self, parameter_index):
		parameter_string = self.command_data[parameter_index]
		try:
			parameter_int = int(parameter_string)
		except:
			raise PmbusCommandInvalidIntParameterError(self.get_command_name())
		return parameter_int

	def get_and_verify_num_bytes(self):
		num_bytes = self.get_and_verify_int_parameter(PmbusCommand.NUM_DATA_BYTES_INDEX)
		if num_bytes < 0:
			raise PmbusCommandInvalidNumBytesParameterError(self.get_command_name())
		return num_bytes

	def get_and_verify_exponent(self):
		exponent = self.get_and_verify_int_parameter(PmbusCommand.EXPONENT_INDEX)
		if exponent > 0:
			raise PmbusCommandInvalidExponentParameterError(self.get_command_name())
		return exponent

	def get_and_verify_num_bits(self):
		NUM_BITS_IN_BYTE = 8
		NUM_BITS_IN_TWO_BYTES = 2 * NUM_BITS_IN_BYTE

		num_mantissa_bits = self.get_and_verify_int_parameter(PmbusCommand.NUM_MANTISSA_BITS_INDEX)
		num_exponent_bits = self.get_and_verify_int_parameter(PmbusCommand.NUM_EXPONENT_BITS_INDEX)
		if (num_mantissa_bits < 0) or (num_exponent_bits < 0):
			raise PmbusCommandInvalidNumberOfBitsParameterError(self.get_command_name())
		if num_mantissa_bits + num_exponent_bits != NUM_BITS_IN_TWO_BYTES:
			raise PmbusCommandInvalidNumberOfBitsParameterError(self.get_command_name())
		return num_mantissa_bits, num_exponent_bits

	def set_and_verify_command_parameters(self):
		self.verify_num_command_parameters()

		command_address_string = self.command_data[PmbusCommand.COMMAND_ADDRESS_INDEX]
		self.command_address_int = byte_conversion.convert_byte_string_to_int(command_address_string)

		command_address_unsigned_int = byte_conversion.convert_signed_byte_to_unsigned_byte(self.command_address_int)
		self.command_address_hex = hex(command_address_unsigned_int)

		self.read_enabled = self.get_and_verify_boolean_parameter(PmbusCommand.READ_EN_INDEX)
		self.write_enabled = self.get_and_verify_boolean_parameter(PmbusCommand.WRITE_EN_INDEX)
		self.num_bytes = self.get_and_verify_num_bytes()

		self.linear_data_format = self.get_and_verify_boolean_parameter(PmbusCommand.LINEAR_COMMAND_INDEX)
		if self.linear_data_format:
			self.exponent = self.get_and_verify_exponent()
			self.num_mantissa_bits, self.num_exponent_bits = self.get_and_verify_num_bits()
			self.data_signed = self.get_and_verify_boolean_parameter(PmbusCommand.DATA_SIGNED_INDEX)