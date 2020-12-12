from smbus2 import SMBus
from bitstring import BitArray, CreationError

class q48sc12050:
	def __init__(self, device_address, smbus_instance):
		self.device_address = device_address
		self.smbus_instance = smbus_instance

	def get_linear_mode_write_bytes(self, value, exponent):
		exponent_bit_array = self.calculate_exponent_bit_array(exponent)
		mantissa_bit_array = self.calculate_mantissa_bit_array(value, exponent)
		two_byte_bit_array = exponent_bit_array + mantissa_bit_array

		lower_byte = two_byte_bit_array[8:16]
		print("Lower Byte: " + lower_byte.bin)
		upper_byte = two_byte_bit_array[0:8]
		print("Upper Byte: " + upper_byte.bin)
		return [upper_byte.int, lower_byte.int];

	def calculate_exponent_bit_array(self, exponent):
		NUM_EXPONENT_BITS = 5
		try:
			exponent_bit_array = BitArray(int=exponent, length=NUM_EXPONENT_BITS)
		except bitstring.CreationError:
			print("Error creating Bit Array for exponent component")
			raise
		return exponent_bit_array

	def calculate_mantissa_bit_array(self, value, exponent):
		assert(value >= 0)
		NUM_MANTISSA_BITS = 11

		# Calculate number of decimals places for the int and 
		# decimal porttions of the numbers
		num_decimal_binary_places = -exponent
		num_int_binary_places = NUM_MANTISSA_BITS - num_decimal_binary_places

		# Generate Bit Array for int portion of number
		int_value = int(value)
		try:
			int_bit_array = BitArray(uint=int_value, length=num_int_binary_places)
		except bitstring.CreationError:
			print("Error creating Bit Array for mantissa int component")
			raise

		# Generate Bit Array for decimal portion of number
		decimal_value = value - int_value
		decimal_bit_array = self.generate_bit_array_from_decimals(decimal_value, num_decimal_binary_places)

		# Concatenate int and decimal components of value
		# and ensure mantissa is 11 bits
		value_bit_array = int_bit_array + decimal_bit_array
		assert(len(value_bit_array.bin) == NUM_MANTISSA_BITS)

		return value_bit_array


	def generate_bit_array_from_decimals(self, decimal_value, num_bits):
		bit_string = "0b";
		binary_increment = .5
		for i in range(num_bits):
			if (decimal_value - binary_increment) > 0:
				bit_string += "1"
				decimal_value = decimal_value - binary_increment
			else:
				bit_string += "0"
			binary_increment /= 2
		return BitArray(bit_string)

if __name__ == "__main__":
	# Testing...
	test = q48sc12050(0x32, 0x33)
	value = 34
	exponent = -3
	[upper_byte, lower_byte] = test.get_linear_mode_write_bytes(value, exponent)
	print("Lower Byte Int: " + str(lower_byte))
	print("Upper Byte Int: " + str(upper_byte))




