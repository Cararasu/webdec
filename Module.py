#!/usr/bin/env python3
#

class ImportModule(dict):
	def __init__(self, name):
		self.name = name
	def __repr__(self):
		return self.name + " " + super().__repr__()
	
class Module:
	def __init__(self):
		self.functions = []
		self.func_types = []
		self.tables = []
		self.memories = []
		self.exports = []
		self.globals = []
		self.custom_func_offset = 0
		self.custom_clobal_offset = 0
		self.start_func = -1
		self.import_modules = dict()

	def get_import_module(self, import_module_id):
		if import_module_id in self.import_modules:
			return self.import_modules[import_module_id]
		self.import_modules[import_module_id] = ImportModule(import_module_id)
		return self.import_modules[import_module_id]

	def __str__(self):
		return str(self.functions) + str(self.import_modules)

	def __repr__(self):
		return str(self)

