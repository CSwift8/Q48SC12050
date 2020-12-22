from smbus2 import SMBus
from argparse import ArgumentParser

from pmbus_devices import *
from pmbus_command_table import *
import byte_conversion

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

class PmbusCommunicationsCLI:

	DEVICE_ADDRESS_INDEX = 0
	POWER_BRICK_INSTANCE_INDEX = 1

	def __init__(self):
		self.num_power_bricks_configured = 0
		self.power_bricks_list = [[], []]

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