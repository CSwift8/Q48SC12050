from smbus2 import SMBus
from bitstring import BitArray, CreationError
import copy
from q48sc12050_pmbus_commands import *
from argparse import ArgumentParser

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
			bytes_to_write = get_linear_write_bytes(command_entry, data)
		else:
			bytes_to_write = data
		self.write_data(command_entry, bytes_to_write)

	def write_data(self, command_entry, bytes_to_write=[]):
		if not isinstance(bytes_to_write, list):
			bytes_to_write = [bytes_to_write]

		self.verify_command_write_enabled(command_entry)
		self.verify_correct_num_data_bytes(len(bytes_to_write), command_entry)
		command_address = command_entry.get_command_address()

		if len(bytes_to_write) > 0:
			self.smbus_instance.write_i2c_block_data(self.device_address, command_address, bytes_to_write)
		else:
			self.smbus_instance.write_byte(self.device_address, command_address)

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
				copy_decimal_value = copy_decimal_value - binary_increment
			else:
				bit_string += "0"
			binary_increment /= 2
		return BitArray(bit_string)

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
		return self.command_table[command]

	def get_device_address(self):
		return self.device_address

class Q48SC12050CLInstructionsBaseError(Exception):
	def __init__(self, error_message):
		super().__init__(error_message)
		self.error_message = error_message

class Q48SC12050CLInstructionsInvalidDeviceAddressInput(Q48SC12050CLInstructionsBaseError):
	def __init__(self, device_address):
		super().__init__(f"{device_address} is not a valid device address")

class Q48SC12050CLInstructionsDeviceAddressAlreadyExists(Q48SC12050CLInstructionsBaseError):
	def __init__(self, device_address):
		super().__init__(f"Device with address {device_address} is already configured")

class Q48SC12050CLInstructionsInvalidPowerBrickSelection(Q48SC12050CLInstructionsBaseError):

class Q48SC12050CLInstructionsInvalidPowerBrickIndexSelection(Q48SC12050CLInstructionsInvalidPowerBrickSelection):
	def __init__(self, index, num_power_bricks_configured):
		super().__init__(f"{index} is not a valid power brick index; valid indices are [0, {num_power_bricks_configured - 1}]")

class Q48SC12050CLInstructionsInvalidPowerBrickDeviceAddressSelection(Q48SC12050CLInstructionsInvalidPowerBrickSelection):
	def __init__(self, device_address, device_address_list):
		super().__init__(f"{device_address} is not a configured device address; choose from {device_address_list} or configure new device")

class Q48SC12050CLInstructions:

	DEVICE_ADDRESS_INDEX = 0
	POWER_BRICK_INSTANCE_INDEX = 1

	def __init__(self, smbus_instance, command_table):
		self.num_power_bricks_configured = 0
		self.power_bricks_list = [[], []]
		self.smbus_instance = smbus_instance
		self.command_table = command_table

	def evoke_device_configuration_prompt(self):
		self.configure_initial_num_power_bricks()
		self.configure_initial_power_bricks()

	def configure_initial_num_power_bricks(self):
		is_valid_input = False
		while not is_valid_input:
			print("Number of Q48SSC12050 Power Bricks:", end=" ")
			try:
				self.num_power_bricks_configured = int(input())
			except:
				print("Invalid input; try again")
			else:
				is_valid_input = True

	def configure_initial_power_bricks(self):
		for i in range(self.num_power_bricks_configured):
			is_valid_input = False
			while not is_valid_input:
				print(f"Power Brick {i} PMBus Device Address:", end=" ");
				device_address_string = str(input())
				try:
					device_address_int = self.convert_address_string_to_int(device_address_string)
					self.verify_device_address(device_address_int)
					self.check_unique_device_address(device_address_int)
				except Q48SC12050CLInstructionsBaseError as err:
					print(err.error_message)
					is_valid_input = False
				else:
					self.add_power_brick(device_address_int)
					is_valid_input = True

	def add_power_brick(self, device_address):
		power_brick = Q48SC12050(device_address, self.smbus_instance, self.command_table)
		self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX].append(device_address)
		self.power_bricks_list[Q48SC12050CLInstructions.POWER_BRICK_INSTANCE_INDEX].append(power_brick)

	def delete_power_brick(self, device_address):
		if device_address in self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX]:
			index = self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX].index(device_address)
			self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX].pop(index)
			self.power_bricks_list[Q48SC12050CLInstructions.POWER_BRICK_INSTANCE_INDEX].pop(index)

	def convert_address_string_to_int(self, address_string):
		try:
			if len(address_string) >= 2:
				if address_string[0:2] == "0b":
					device_address_bit_array = BitArray(bin=address_string)
				elif address_string[0:2] == "0x":
					device_address_bit_array = BitArray(hex=address_string)
				elif address_string[0] == "-":
					device_address_bit_array = BitArray(int=int(address_string), length=8)
				else:
					device_address_bit_array = BitArray(uint=int(address_string), length=8)
			else:
				device_address_bit_array = BitArray(uint=int(address_string), length=8)
		except:
			raise Q48SC12050CLInstructionsInvalidDeviceAddressInput(address_string)
		return device_address_bit_array.int

	def verify_device_address(self, device_address):
		if not (0x00 <= device_address <= 0x7F):
			raise Q48SC12050CLInstructionsInvalidDeviceAddressInput(device_address)

	def check_unique_device_address(self, device_address):
		if device_address in list(self.power_bricks_dict):
			raise Q48SC12050CLInstructionsDeviceAddressAlreadyExists(device_address)

	def execute_instruction(self, command, command_arguments):
		if command == "write":
			self.execute_write_command(command_arguments)
		elif command == "read":
			self.execute_read_command(command_arguments)
		else:
			pass
			# Invalid Command

	def get_power_brick_from_index(self, index):
		try:
			power_brick = self.power_bricks_list[Q48SC12050CLInstructions.POWER_BRICK_INSTANCE_INDEX][arguments.index]
		except:
			raise Q48SC12050CLInstructionsInvalidPowerBrickIndexSelection(index, self.num_power_bricks_configured)
		return power_brick

	def get_power_brick_from_address(self, device_address):
		try:
			index = self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX].index(device_address)
			power_brick = self.power_bricks_list[Q48SC12050CLInstructions.POWER_BRICK_INSTANCE_INDEX][index]
		except:
			raise Q48SC12050CLInstructionsInvalidPowerBrickDeviceAddressSelection(device_address, self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX])
		return power_brick

	def select_power_brick(self, index, device_address):
		if index != None:
			power_brick_instance = self.get_power_brick_from_index(index)
		elif address != None:
			device_address_int = self.convert_address_string_to_int(address)
			self.verify_device_address(device_address_int)
			power_brick_instance = self.get_power_brick_from_address(device_address_int)
		return power_brick_instance

	def get_command(self, command):
		try:
			new_command = self.convert_address_string_to_int(command)
		except:
			new_command = command
		return new_command

	def get_bytes_to_write(self, value, bytes_read, command_table_entry):
		if value != None
			if command_table_entry.is_linear_data_format():
				bytes_to_write = Q48SC12050.get_linear_write_bytes(command_table_entry, value)
			else:
				pass
				# Error
		elif bytes_read != None:
			bytes_to_write = copy.copy(bytes_read.reverse())
		return bytes_to_write

	def execute_write_command(self, command_arguments):
		write_parser = ArgumentParser()

		write_parser.add_argument("command", help="PMBus Command to write to Power Brick; text or address")

		power_brick_selection_group = write_parser.add_mutually_exclusive_group(required=True)
		power_brick_selection_group.add_argument("-i", "--index", type=int, help="Specifies power brick index to write to")
		power_brick_selection_group.add_argument("-a", "--address", help="Specifies power brick device address to write to")

		data_group = write_parser.add_mutually_exclusive_group()
		data_group.add_argument("-v", "--value", type=float, help="Individual value to send with PMBus Command")
		data_group.add_argument("-b", "--bytes", nargs="+", help="List of Bytes (Hex, Binary, Decimal) to send with PMBus Command with MSByte First")

		consecutive_write_group = write_parser.add_mutually_exclusive_group()
		consecutive_write_group.add_argument("-l", "--loops", type=int, help="Number of consecutive write commands to execute")
		consecutive_write_group.add_argument("-t", "--time", type=int, help="Number of milliseconds to continuously send write command for")

		arguments = write_parser.parse_args(command_arguments)

		command = get_command(arguments.command)

		try:
			power_brick_instance =  self.select_power_brick(arguments.index, arguments.address)
		except Q48SC12050CLInstructionsBaseError as err:
			print(err.error_message)
			return

		try:
			command_table_entry = power_brick_instance.get_command_table_entry(command)
		except Q48SC12050PmbusCommandTableBaseError as err:
			print(err.error_message)
			return

		bytes_to_write = self.get_bytes_to_write(arguments.value, arguments.bytes_read, command_table_entry)
		power_brick_instance.write_data(command_table_entry, bytes_to_write)
			

if __name__ == "__main__":
	#i2c_bus_num = 1;
	#smbus_instance = SMBus(i2c_bus_num)
	#smbus_instance.enable_pec(True)
	smbus_instance = None

	table_input_file = "Q48SC12050_PMBus_Commands.csv"
	command_table = Q48SC12050PmbusCommandTable(table_input_file)
	
	# power_brick1 = Q48SC12050(0x7F, smbus_instance, command_table)
	# power_brick2 = Q48SC12050(0x23, smbus_instance, command_table)

	terminal = Q48SC12050CLInstructions(smbus_instance, command_table)
	#terminal.evoke_device_configuration_prompt()

	#command_list = ["write", "read", "listc", "plot", "help", "trans", "addpb", "deletepb", "listpb", "exit", "pec"]

	#parser = ArgumentParser()
	#parser.add_argument("command", choices=command_list, help="Select Q48SC12050 power supply control command")



	command_list = str(input()).split(" ")
	command = command_list[0]
	argument_list = command_list[1:]
	terminal.execute_instruction(command, argument_list)







