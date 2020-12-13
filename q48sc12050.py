from smbus2 import SMBus
from bitstring import BitArray, CreationError
import copy
from q48sc12050_pmbus_commands import *

class Q48SC12050:

	DEFAULT_NUM_MANTISSA_BITS = 11
	DEFAULT_NUM_EXPONENT_BITS = 5
	DEFAULT_WRITE_BYTES_SIGNED = True

	VOUT_NUM_MANTISSA_BITS = 16
	VOUT_NUM_EXPONENT_BITS = 0
	VOUT_WRITE_BYTES_SIGNED = False
	VOUT_EXPONENT = -12
	a = 5 + 4
	b = a - 6

	def __init__(self, device_address, smbus_instance, command_table):
		self.device_address = device_address
		self.smbus_instance = smbus_instance
		self.command_table = command_table

	# TODO
	def write_data(self, command, data):
		command_entry = self.command_table[command]

		if command_entry.is_linear_data_format():
			bytes_to_write = get_linear_write_bytes(
				value=data,
				exponent=command_entry.get_exponent(),
				num_mantissa_bits=command_entry.get_num_mantissa_bits(),
				num_exponent_bits=command_entry.get_num_exponent_bits(),
				signed=command_entry.is_data_signed())
		else:
			bytes_to_write = data

	def get_linear_write_bytes(self, 
				value, 
				exponent, 
				num_mantissa_bits=DEFAULT_NUM_MANTISSA_BITS,
				num_exponent_bits=DEFAULT_NUM_EXPONENT_BITS,
				signed=DEFAULT_WRITE_BYTES_SIGNED):

		exponent_bit_array = self.calculate_exponent_bit_array(exponent, num_exponent_bits)
		mantissa_bit_array = self.calculate_mantissa_bit_array(value, exponent, num_mantissa_bits, signed)
		two_byte_bit_array = exponent_bit_array + mantissa_bit_array

		lower_byte = two_byte_bit_array[8:16]
		upper_byte = two_byte_bit_array[0:8]
		return [upper_byte.int, lower_byte.int];

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
	# Testing...
	test = Q48SC12050(0x32, 0x33)
	value = 34
	exponent = -3
	test.test_class_variables()
	#[upper_byte, lower_byte] = test.get_linear_mode_write_bytes(value, exponent)
	#print("Lower Byte Int: " + str(lower_byte))
	#print("Upper Byte Int: " + str(upper_byte))




