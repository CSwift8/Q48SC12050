
class Q48SC12050PmbusCommandTable:

	def __init__(self, file_name):
		self.pmbus_command_table = dict()
		self.initialize_pmbus_table(file_name)

	def initialize_pmbus_table(self, file_name):
		# Open File
		try:
			input_file = open(file_name, 'r')
		except:
			print("Invalid file name to initialize pmbus dictionary")
			return

		# Read Headers Line
		read_line = input_file.readline()

		# Read Data Lines
		read_line = input_file.readline()
		while read_line != "":
			read_line = read_line.removesuffix("\n")
			command_data = read_line.split(",")
			new_command_entry = Q48SC12050PmbusCommandEntry(command_data)
			pmbus_command_table.update({new_command_entry.get_command_name(), new_command_entry})
			read_line = input_file.readline()

		# Close File
		input_file.close()

	def __getitem__(self, key):
		return self.pmbus_command_table[key]

class Q48SC12050PmbusCommandEntry:
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

	def __init__(self, command_entry_data):
		self.command_entry_data = command_entry_data

	def get_command_name(self):
		return self.command_entry_data[Q48SC12050PmbusCommandEntry.COMMAND_NAME_INDEX]

	def get_command_address(self):
		command_address_string = self.command_entry_data[Q48SC12050PmbusCommandEntry.COMMAND_ADDRESS_INDEX]
		command_address_string = command_address_string.removeprefix("0x")
		command_address_int = int(command_address_string, 16)
		return command_address_int

	def is_read_en(self):
		return (self.command_entry_data[Q48SC12050PmbusCommandEntry.READ_EN_INDEX] == TRUE_STRING)

	def is_write_en(self):
		return (self.command_entry_data[Q48SC12050PmbusCommandEntry.WRITE_EN_INDEX] == TRUE_STRING)

	def get_num_data_bytes(self):
		return int(self.command_entry_data[Q48SC12050PmbusCommandEntry.NUM_DATA_BYTES_INDEX])

	def is_linear_data_format(self):
		return (self.command_entry_data[Q48SC12050PmbusCommandEntry.LINEAR_COMMAND_INDEX] == TRUE_STRING)

	def get_exponent(self):
		return int(self.command_entry_data[Q48SC12050PmbusCommandEntry.EXPONENT_INDEX])

	def get_num_mantissa_bits(self):
		return int(self.command_entry_data[Q48SC12050PmbusCommandEntry.NUM_MANTISSA_BITS_INDEX])

	def get_num_exponents_bits(self):
		return int(self.command_entry_data[Q48SC12050PmbusCommandEntry.NUM_EXPONENT_BITS_INDEX])

	def is_data_signed(self):
		return (self.command_entry_data[Q48SC12050PmbusCommandEntry.DATA_SIGNED_INDEX] == TRUE_STRING)