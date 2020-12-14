from smbus2 import SMBus
from bitstring import BitArray, CreationError
import copy
from q48sc12050_pmbus_commands import *

class Q48SC12050BaseError(Exception):
	def __init__(self, error_message):
		super().__init__(error_message)

class Q48SC12050WriteEnableError(Q48SC12050BaseError):
	def __init__(self, command_name):
		super().__init__(f"{command_name} is not write accessible")

class Q48SC12050ReadEnableError(Q48SC12050BaseError):
	def __init__(self, command_name):
		super().__init__(f"{command_name} is not read accessible")

class Q48SC12050InvalidCommandError(Q48SC12050BaseError):
	def __init__(self, command_name):
		super().__init__(f"{command_name} does not exist in the command table")

class Q48SC12050InvalidNumberOfWriteBytesError(Q48SC12050BaseError):
	def __init__(self, command_name, actual_num, expected_num):
		super().__init__(f"{command_name} expects {expected_num} bytes, but {actual_num} are provided")

class Q48SC12050InvalidExponentFromReadCommand(Q48SC12050BaseError):
	def __init__(self, command_name, actual_exponent, expected_exponent):
		super().__init__(f"{command_name} expects exponent = {expected_exponent}, but read exponent = {actual_exponent}")


class Q48SC12050:

	LSBYTE_LIST_INDEX = 0
	MSBYTE_LIST_INDEX = 1

	def __init__(self, device_address, smbus_instance, command_table):
		self.device_address = device_address
		self.smbus_instance = smbus_instance
		self.command_table = command_table

	def write_command(self, command, data=[]):
		command_entry = self.get_command_table_entry(command)
		if command_entry.is_linear_data_format():
			bytes_to_write = self.get_linear_write_bytes(command_entry, data)
		else:
			bytes_to_write = data
		self.write_data(command_entry, bytes_to_write)

	def write_data(self, command_entry, bytes_to_write=[]):
		if not isinstance(bytes_to_write, list):
			bytes_to_write = [bytes_to_write]

		self.verify_command_write_enabled(command_entry)
		self.verify_correct_num_data_bytes(len(bytes_to_write), command_entry)
		command_address = command_entry.get_command_address()

		#if len(bytes_to_write) > 0:
		#	self.smbus_instance.write_i2c_block_data(self.device_address, command_address, bytes_to_write)
		#else:
		#	self.smbus_instance.write_byte(self.device_address, command_address)

	def read_command(self, command):
		command_entry = self.get_command_table_entry(command)
		bytes_read = self.read_data(command_entry)

		if command_entry.is_linear_data_format():
			data = self.get_linear_read_value(command_entry, bytes_read)
		else:
			data = bytes_read
		return data

	def read_data(self, command_entry):
		self.verify_command_read_enabled(command_entry)
		command_address = command_entry.get_command_address()
		command_num_data_bytes = command_entry.get_num_data_bytes()

		#return self.smbus_instance.read_i2c_block_data(self.device_address, command_address, command_num_data_bytes)

	def verify_correct_num_data_bytes(self, actual_num, command_entry):
		expected_num  = command_entry.get_num_data_bytes()
		if (actual_num != expected_num):
			raise Q48SC12050InvalidNumberOfWriteBytesError(command_entry.get_command_name(), actual_num, expected_num)

	def verify_correct_exponent(self, actual_exponent, command_entry):
		expected_exponent = command_entry.get_exponent()
		if (actual_exponent != expected_exponent):
			raise Q48SC12050InvalidExponentFromReadCommand(command_entry.get_command_name(), actual_exponent, expected_exponent)

	def verify_command_write_enabled(self, command_entry):
		if not command_entry.is_write_enabled():
			raise Q48SC12050WriteEnableError(command_entry.get_command_name())

	def verify_command_read_enabled(self, command_entry):
		if not command_entry.is_read_enabled():
			raise Q48SC12050ReadEnableError(command_entry.get_command_name())

	def get_command_table_entry(self, command):
		try:
			command_entry = self.command_table[command]
		except:
			raise Q48SC12050InvalidCommandError(command)
		return command_entry

	def get_linear_write_bytes(self, command_entry, value):
		exponent = command_entry.get_exponent()
		num_mantissa_bits = command_entry.get_num_mantissa_bits()
		num_exponent_bits = command_entry.get_num_exponent_bits()
		data_signed = command_entry.is_data_signed()

		exponent_bit_array = self.calculate_exponent_bit_array(exponent, num_exponent_bits)
		mantissa_bit_array = self.calculate_mantissa_bit_array(value, exponent, num_mantissa_bits, data_signed)
		two_byte_bit_array = exponent_bit_array + mantissa_bit_array

		lower_byte = two_byte_bit_array[8:16]
		upper_byte = two_byte_bit_array[0:8]

		write_bytes = [0, 0]
		write_bytes[Q48SC12050.LSBYTE_LIST_INDEX] = lower_byte.int
		write_bytes[Q48SC12050.MSBYTE_LIST_INDEX] = upper_byte.int

		return write_bytes;

	def get_linear_read_value(self, command_entry, bytes_read):
		num_mantissa_bits = command_entry.get_num_mantissa_bits()
		num_exponent_bits = command_entry.get_num_exponent_bits()

		lower_byte = bytes_read[Q48SC12050.LSBYTE_LIST_INDEX]
		upper_byte = bytes_read[Q48SC12050.MSBYTE_LIST_INDEX]

		lower_byte_bit_array = BitArray(int=lower_byte, length=8)
		upper_byte_bit_array = BitArray(int=upper_byte, length=8)
		value_bit_array = upper_byte_bit_array + lower_byte_bit_array
		mantissa_bit_array = value_bit_array[(16 - num_mantissa_bits):16]
		exponent_bit_array = value_bit_array[0:num_exponent_bits]

		exponent = self.calculate_exponent_value(exponent_bit_array, command_entry)
		mantissa = self.calculate_mantissa_value(mantissa_bit_array, command_entry)
		value = mantissa * (2 ** exponent)
		return value

	def calculate_exponent_value(self, exponent_bit_array, command_entry):
		expected_exponent = command_entry.get_exponent()
		num_exponent_bits = len(exponent_bit_array)
		if num_exponent_bits != 0:
			actual_exponent = exponent_bit_array.int
			self.verify_correct_exponent(actual_exponent, command_entry)
		return expected_exponent

	def calculate_mantissa_value(self, mantissa_bit_array, command_entry):
		data_signed = command_entry.is_data_signed()
		if data_signed:
			mantissa = mantissa_bit_array.int
		else:
			mantissa = mantissa_bit_array.uint
		return mantissa

	def calculate_exponent_bit_array(self, exponent, num_exponent_bits):
		if (num_exponent_bits == 0):
			return BitArray()

		try:
			exponent_bit_array = BitArray(int=exponent, length=num_exponent_bits)
		except bitstring.CreationError:
			print("Error creating Bit Array for exponent component")
			raise
		return exponent_bit_array

	def calculate_mantissa_bit_array(self, value, exponent, num_mantissa_bits, signed):
		if (num_mantissa_bits == 0):
			return BitArray()

		# Calculate number of decimals places for the int and 
		# decimal porttions of the numbers
		num_decimal_binary_places = -exponent
		num_int_binary_places = num_mantissa_bits - num_decimal_binary_places

		# Generate Bit Array for int portion of number
		int_value = int(value)
		try:
			if signed:
				int_bit_array = BitArray(int=int_value, length=num_int_binary_places)
			else:
				int_bit_array = BitArray(uint=int_value, length=num_int_binary_places)
		except bitstring.CreationError:
			print("Error creating Bit Array for mantissa int component")
			raise

		# Generate Bit Array for decimal portion of number
		decimal_value = value - int_value
		decimal_bit_array = self.generate_bit_array_from_decimal(decimal_value, num_decimal_binary_places)

		# Concatenate int and decimal components of value
		value_bit_array = int_bit_array + decimal_bit_array

		return value_bit_array

	def generate_bit_array_from_decimal(self, decimal_value, num_bits):
		bit_string = "0b";
		binary_increment = .5
		copy_decimal_value = copy.copy(decimal_value)
		for i in range(num_bits):
			if (copy_decimal_value - binary_increment) >= 0:
				bit_string += "1"
				copy_decimal_value = copy_decimal_value - binary_increment
			else:
				bit_string += "0"
			binary_increment /= 2
		return BitArray(bit_string)

if __name__ == "__main__":
	#i2c_bus_num = 1;
	#smbus_instance = SMBus(i2c_bus_num)
	#smbus_instance.enable_pec(True)
	smbus_instance = None

	table_input_file = "Q48SC12050_PMBus_Commands.csv"
	command_table = Q48SC12050PmbusCommandTable(table_input_file)
	
	power_brick1 = Q48SC12050(0x7F, smbus_instance, command_table)
	# power_brick2 = Q48SC12050(0x23, smbus_instance, command_table)





