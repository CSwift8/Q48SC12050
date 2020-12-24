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
	pass

class Q48SC12050CLInstructionsInvalidPowerBrickIndexSelection(Q48SC12050CLInstructionsInvalidPowerBrickSelection):
	def __init__(self, index, num_power_bricks_configured):
		super().__init__(f"{index} is not a valid power brick index; valid indices are [0, {num_power_bricks_configured - 1}]")

class Q48SC12050CLInstructionsInvalidPowerBrickDeviceAddressSelection(Q48SC12050CLInstructionsInvalidPowerBrickSelection):
	def __init__(self, device_address, device_address_list):
		super().__init__(f"{device_address} is not a configured device address; choose from {device_address_list} or configure new device")

class Q48SC12050CLInstructionsInvalidDeviceType(Q48SC12050CLInstructionsInvalidPowerBrickSelection):
	def __init__(self, user_selected_device_type):
		super().__init__(f"{user_selected_device_type} is not a valid device type")

class PmbusCommunicationsCLI:

	DEVICE_ADDRESS_INDEX = 0
	POWER_BRICK_INSTANCE_INDEX = 1
	GENERAL_PMBUS_DEVICE_NAME = "other"

	def __init__(self):
		self.num_power_bricks_configured = 0
		self.power_bricks_list = [[], []]

	def evoke_device_configuration_prompt(self):
		self.configure_initial_num_pmbus_devices()
		self.configure_initial_pmbus_devices()

	def configure_initial_num_pmbus_devices(self):
		is_valid_input = False
		while not is_valid_input:
			print("Number of Q48SSC12050 Power Bricks:", end=" ")
			try:
				self.num_power_bricks_configured = int(input())
			except:
				print("Invalid input; try again")
			else:
				is_valid_input = True

	def configure_initial_pmbus_devices(self):
		self.configure_pmbus_devices()
		for i in range(self.num_power_bricks_configured):
			device_class = prompt_and_get_pmbus_device_type(i)
			if device_class == PmbusDevice:
				command_table = prompt_and_get_command_table(i)
			else:
				command_table = None
			device_address = prompt_and_get_device_address(i)
			smbus_instance = prompt_and_get_smbus_instance(i)
			self.add_pmbus_device(device_class, device_address, smbus_instance, command_table)

	def prompt_and_get_device_address(self, device_index):
		prompt = f"PMBus Device #{device_index} Address:"
		def try_statement_function():
			device_address_string = str(input())
			device_address_int = byte_conversion.convert_byte_string_to_int(device_address_string)
			self.verify_device_address(device_address_int)
			self.check_unique_device_address(device_address_int)
			return device_address_int
		device_address_int = self.prompt_and_get(prompt, try_statement_function)
		return device_address_int

	def prompt_and_get_pmbus_device_type(self, device_index):
		prompt = f"Select PMBus Device #{device_index} Type:\n"
		for device_class in list(self.pmbus_devices_dict):
			prompt += (device_class + "\n")
		prompt += PmbusCommunicationsCLI.GENERAL_PMBUS_DEVICE_NAME + "\n"
		def try_statement_function():
			user_selected_device_type = str(input())
			device_class = self.get_pmbus_device_class(user_selected_device_type)
			return device_class
		device_class = self.prompt_and_get(prompt, try_statement_function)
		return device_class

	def prompt_and_get_command_table(self, device_index):
		prompt = f"PMBus Device #{device_index} Command Table File Path: "
		def try_statement_function():
			user_selected_command_table = str(input())
			command_table = PmbusCommandTable(user_selected_command_table)
			return command_table
		command_table = self.prompt_and_get(prompt, try_statement_function)
		return command_table

	def prompt_and_get_smbus_instance(self, device_index):
		prompt = f"PMBus Device #{device_index} SMBus Number: "
		def try_statement_function():
			smbus_number = int(input())
			self.verify_smbus_number(smbus_number)
			smbus_instance = SMBus(smbus_number)
			return smbus_instance
		smbus_instance = self.prompt_and_get(prompt, try_statement_function)
		return smbus_instance

	def prompt_and_get(self, prompt, try_statement_function):
		is_valid = False
		while not is_valid:
			print(prompt, end="")
			try:
				value = try_statement_function()
			except Exception as err:
				print(err)
				is_valid = False
			else:
				is_valid = True
		return value

	def configure_pmbus_devices(self):
		self.pmbus_devices_dict = dict()
		for pmbus_device_class in PmbusDevice.__subclasses__():
			class_name = pmbus_device_class.__name__
			pmbus_devices_dict.update({class_name : pmbus_device_class})

	def get_pmbus_device_class(self, class_name):
		if class_name == PmbusCommunicationsCLI.GENERAL_PMBUS_DEVICE_NAME:
			device_class = PmbusDevice
		else:
			try:
				device_class = self.pmbus_devices_dict[class_name]
			except:
				raise Q48SC12050CLInstructionsInvalidDeviceType(class_name)
		return device_class

	def add_pmbus_device(self, device_class, device_address, smbus_instance, command_table):
		if command_table == None:
			pmbus_device = device_class(device_address, smbus_instance)
		else:
			pmbus_device = device_class(device_address, smbus_instance, command_table)

		self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX].append(device_address)
		self.power_bricks_list[Q48SC12050CLInstructions.POWER_BRICK_INSTANCE_INDEX].append(pmbus_device)

	def delete_power_brick(self, device_address):
		if device_address in self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX]:
			index = self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX].index(device_address)
			self.power_bricks_list[Q48SC12050CLInstructions.DEVICE_ADDRESS_INDEX].pop(index)
			self.power_bricks_list[Q48SC12050CLInstructions.POWER_BRICK_INSTANCE_INDEX].pop(index)

	def verify_smbus_number(self, smbus_number):
		if (smbus_number != 0) and (smbus_number != 1)
			# Raise Error

	def verify_device_address(self, device_address):
		# SMBus Device Addresses are 7-bits
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