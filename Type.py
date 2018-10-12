#!/usr/bin/env python3
#
from enum import Enum

class WasmInstr(Enum):
	EQZ = 0x30,
	EQ = 0x31,
	NE = 0x32,
	LT = 0x33,
	GT = 0x34,
	LE = 0x35,
	GE = 0x36,

	CLZ = 0x40,
	CTZ = 0x41,
	POPCNT = 0x42,
	ADD = 0x43,
	SUB = 0x44,
	MUL = 0x45,
	DIV = 0x46,
	REM = 0x47,
	AND = 0x48,
	OR = 0x49,
	XOR = 0x4A,
	SHL = 0x4B,
	SHR = 0x4C,
	ROTL = 0x4D,
	ROTR = 0x4E,

	ABS = 0x50,
	NEG = 0x51,
	CEIL = 0x52,
	FLOOR = 0x53,
	TRUNC= 0x54,
	NEAREST = 0x55,
	SQRT = 0x56,
	MIN = 0x57,
	MAX = 0x58,
	COPYSIGN = 0x59,
	
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name
		
class SectionType(Enum):
	CUSTOM = 0x00
	TYPE = 0x01
	IMPORT = 0x02
	FUNCTION = 0x03
	TABLE = 0x04
	MEMORY = 0x05
	GLOBAL = 0x06
	EXPORT = 0x07
	START = 0x08
	ELEMENT = 0x09
	CODE = 0x0A
	DATA = 0x0B
	
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name

class ValType(Enum):
	F64 = 0x7C
	F32 = 0x7D
	I64 = 0x7E
	I32 = 0x7F
	
	def getValue(self):
		return int(self.name[1:])
	
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name
class TableType(Enum):
	TABLE = 0x70
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name
class ImportDescrType(Enum):
	FUNC = 0x00
	TABLE = 0x01
	MEM = 0x02
	GLOBAL = 0x03
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name
class ExportDescrType(Enum):
	FUNC = 0x00
	TABLE = 0x01
	MEM = 0x02
	GLOBAL = 0x03
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name

import string
import binascii

class Limit():
	def __init__(self, min, max = -1):
		self.min = min
		self.max = max
	def __repr__(self):
		return "(min:" + str(self.min) + ", max:" + str(self.max) + ")"
		
class Global:
	def __init__(self, type, name, mutable = True, _import = False, init_value = None):
		self.name = name
		self.type = type
		self.init_value = init_value
		self._import = _import
		self.mutable = mutable
	def printExpr(self, module):
		string = "Global " + str(self.type) + " " + str(self.name) + " = "
		if self.init_value == None:
			string += "0"
		else:
			string += str(self.init_value.getValue(module))
		return string
	def __repr__(self):
		return "Global " + str(self.type) + " " + str(self.name) + " " + str(self.init_value) + (" extern" if self._import else "") + (" mutable" if self.mutable else "")

class InitRange:
	def __init__(self, offsetExpr, values):	
		self.offsetExpr = offsetExpr
		self.values = values
	def printExpr(self, module):
		if type(self.values[0]) == bytes:
			return "offset " + str(self.offsetExpr.getValue(module)) + " " + str(b''.join(self.values))[1:]
		elif type(self.values[0]) == Function:
			return "offset " + str(self.offsetExpr.getValue(module)) + " (" + ", ".join(map(lambda f: f.name, self.values)) + ")"
		else:
			return "offset " + str(self.offsetExpr.getValue(module)) + " " + ", ".join(map(lambda x: str(x), self.values)) + ")"
			
	def __repr__(self):
		return "Range(" + str(self.offsetExpr) + ": FuncType " + str(self.values)
		
class Table:
	def __init__(self, limit, name = None, _import = False):
		self.name = name
		self.limit = limit
		self.init_list = []
		self._import = _import
		self.export = False
	def initialize(self, initRange):
		self.init_list.append(initRange)
	def printExpr(self, module):
		string = "Table" + str(self.limit) + " " + str(self.name) + " = ("
		string += ", ".join(map(lambda initRange: initRange.printExpr(module), self.init_list))
		string += ")"
		return string
	def __repr__(self):
		return "Table" + str(self.limit) + ": Init " + str(self.init_list)
class Memory:
	def __init__(self, limit, name = None, _import = False):
		self.name = name
		self.limit = limit
		self.export = False
		self.init_list = []
	def initialize(self, initRange):
		self.init_list.append(initRange)
	def printExpr(self, module):
		string = "Memory" + str(self.limit) + " " + str(self.name) + " = ("
		string += ", ".join(map(lambda initRange: initRange.printExpr(module), self.init_list))
		string += ")"
		return string
	def __repr__(self):
		return "Memory " + str(self.name) + ":  " + str(self.limit) + ": Init " + str(self.init_list)
		
class Function:
	def __init__(self, id, type, name, _import = False):
		self.id = id
		self.name = name
		self.type = type
		self._import = _import
		self.export = False
		self.locals = []
		self.expr = None
	def printExpr(self, module):
		string = "Function " + str(self.name) + ": " + str(self.type)
		if self._import:
			string += " import"
		if self.export:
			string += " export"
		if self.expr == None:
			return string
		string += "\n"
		string += str(self.locals) + "\n"
		string += self.expr.printExpr(module, indent = 1)
		return string
	def __repr__(self):
		return "Function " + str(self.name) + ": " + str(self.type)

class FunctionType:
	def __init__(self, parameters, ret_vars):
		self.parameters = parameters
		self.ret_vars = ret_vars

	def __str__(self):
		return "(" + ', '.join(map(str, self.parameters)) + ") -> (" + ', '.join(map(str, self.ret_vars)) + ")"
