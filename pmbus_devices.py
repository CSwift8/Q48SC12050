from bitstring import BitArray, CreationError
import copy

from pmbus_command_table import *

class PmbusDeviceBaseError(Exception):
	def __init__(self, error_message):
		super().__init__(error_message)

class PmbusDeviceWriteEnableError(PmbusDeviceBaseError):
	def __init__(self, command_name):
		super().__init__(f"{command_name} is not write accessible")

class PmbusDeviceReadEnableError(PmbusDeviceBaseError):
	def __init__(self, command_name):
		super().__init__(f"{command_name} is not read accessible")

class PmbusDeviceInvalidNumberOfWriteBytes(PmbusDeviceBaseError):
	def __init__(self, command_name, actual_num, expected_num):
		super().__init__(f"{command_name} expects {expected_num} bytes, but {actual_num} are provided")

class PmbusDeviceInvalidExponentFromReadCommand(PmbusDeviceBaseError):
	def __init__(self, command_name, actual_exponent, expected_exponent):
		super().__init__(f"{command_name} expects exponent = {expected_exponent}, but read exponent = {actual_exponent}")

class PmbusDevice:

	LSBYTE_LIST_INDEX = 0
	MSBYTE_LIST_INDEX = 1

	def __init__(self, device_address, smbus_instance, command_table):
		self.device_address = device_address
		self.smbus_instance = smbus_instance
		self.command_table = command_table

	def write_bytes(self, command, bytes_to_write=[]):
		# command -> Command Name OR Command Address
		command_entry = self.get_command_table_entry(command)

		if not isinstance(bytes_to_write, list):
			bytes_to_write = [bytes_to_write]

		self.verify_command_write_enabled(command_entry)
		self.verify_command_correct_num_data_bytes(len(bytes_to_write), command_entry)
		command_address = command_entry.get_command_address()

		if len(bytes_to_write) > 0:
			self.smbus_instance.write_i2c_block_data(self.device_address, command_address, bytes_to_write)
		else:
			self.smbus_instance.write_byte(self.device_address, command_address)

	def read_bytes(self, command):
		# command -> Command Name or Command Address
		command_entry = self.get_command_table_entry(command)
		self.verify_command_read_enabled(command_entry)
		command_address = command_entry.get_command_address()
		command_num_data_bytes = command_entry.get_num_data_bytes()

		return self.smbus_instance.read_i2c_block_data(self.device_address, command_address, command_num_data_bytes)

	def get_linear_write_bytes(command_entry, value):
		exponent = command_entry.get_exponent()
		num_mantissa_bits = command_entry.get_num_mantissa_bits()
		num_exponent_bits = command_entry.get_num_exponent_bits()
		data_signed = command_entry.is_data_signed()

		exponent_bit_array = calculate_exponent_bit_array(exponent, num_exponent_bits)
		mantissa_bit_array = calculate_mantissa_bit_array(value, exponent, num_mantissa_bits, data_signed)
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

	def calculate_exponent_bit_array(exponent, num_exponent_bits):
		if (num_exponent_bits == 0):
			return BitArray()

		try:
			exponent_bit_array = BitArray(int=exponent, length=num_exponent_bits)
		except bitstring.CreationError:
			print("Error creating Bit Array for exponent component")
			raise
		return exponent_bit_array

	def calculate_mantissa_bit_array(value, exponent, num_mantissa_bits, signed):
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
				copy_decimal_value -= binary_increment
			else:
				bit_string += "0"
			binary_increment /= 2
		return BitArray(bit_string)

	def verify_command_correct_num_data_bytes(self, actual_num, command_entry):
		expected_num  = command_entry.get_num_data_bytes()
		if (actual_num != expected_num):
			raise PmbusDeviceInvalidNumberOfWriteBytes(command_entry.get_command_name(), actual_num, expected_num)

	def verify_correct_exponent(self, actual_exponent, command_entry):
		expected_exponent = command_entry.get_exponent()
		if (actual_exponent != expected_exponent):
			raise PmbusDeviceInvalidExponentFromReadCommand(command_entry.get_command_name(), actual_exponent, expected_exponent)

	def verify_command_write_enabled(self, command_entry):
		if not command_entry.is_write_enabled():
			raise PmbusDeviceWriteEnableError(command_entry.get_command_name())

	def verify_command_read_enabled(self, command_entry):
		if not command_entry.is_read_enabled():
			raise PmbusDeviceReadEnableError(command_entry.get_command_name())

	def get_command_table_entry(self, command):
		return self.command_table[command]

	def get_device_address(self):
		return self.device_address

	def get_command_table_file_path(self, class_name):
		TABLE_DIRECTORY_NAME = "PmbusCommandTables"
		TABLE_FILE_EXTENSION = ".csv"
		file_name = class_name + TABLE_FILE_EXTENSION
		file_path = "./" + TABLE_DIRECTORY_NAME + "/" + file_name
		return file_path

class q48sc12050(PmbusDevice):

	def __init__(self, device_address, smbus_instance):
		command_table_file_path = super().get_command_table_file_path(__class__.__name__)
		command_table = PmbusCommandTable(command_table_file_path)
		super().__init__(device_address, smbus_instance, command_table)

pmbus_devices_dict = dict()
def configure_pmbus_devices():
	for pmbus_device_class in PmbusDevice.__subclasses__():
		class_name = pmbus_device_class.__name__
		pmbus_devices_dict.update({class_name : pmbus_device_class})

def get_pmbus_device_class(class_name):
	return pmbus_devices_dict[class_name]
	

if __name__ == "__main__":
	configure_pmbus_devices()
	power_brick = pmbus_devices_dict["q48sc12050"](0x29, None)