#!/usr/bin/env python3
#

import sys
import struct
from enum import Enum

from Instruction import *
from Type import *
from Module import *


class StringParser:
	def __init__(self, data):
		self.data = data
		self.position = 0
	def pop(self, count = 1):
		data = self.data[self.position:self.position + count]
		self.position += count
		return data
	def peek(self, count = 1):
		return self.data[self.position:self.position + count]
	def revert(self, count = 1):
		self.position -= count

class ParseException(Exception):
	pass


def get_leb128(content):
	value = 0
	
	mask=[0xffffff80,0xffffc000,0xffe00000,0xf0000000,0]
	bitmask=[0x40,0x40,0x40,0x40,0x8]
	value = 0
	for i in range(len(content)):
		tmp = ord(content[i]) & 0x7f
		value = tmp << (i * 7) | value
		if (ord(content[i]) & 0x80) != 0x80:
			if bitmask[i] & tmp:
				value |= mask[i]
			break
	if i == 4 and (tmp & 0xf0) != 0:
		print("parse a error uleb128 number")
		return -1
	buffer = struct.pack("I",value)
	value, =struct.unpack("i",buffer)
	return i+1, value

	
class WasmParser:
	def __init__(self, parser):
		self.parser = parser

		self.instructionHaldlers = {
			0x00:lambda:UnreachableInstruction(), 0x01:lambda:NopInstruction(), 0x02:self.parseBlock, 0x03:self.parseLoop, 0x04:self.parseIf,
			0x0C:lambda:BranchInstruction(self.parseUVal()),
			0x0D:lambda:BranchInstruction(self.parseUVal(), True),
			0x0E:lambda:BranchTableInstruction(self.parseVector(parseUVal), self.parseUVal()),
			0x0F:lambda:ReturnInstruction(),
			0x10:lambda:CallInstruction(target = self.parseFuncId()),
			0x11:self.parseCallInd,
			0x1A:lambda:DropInstruction(),
			0x1B:lambda:SelectInstruction(),
			0x20:lambda:GetLocalInstruction(self.parseUVal()),
			0x21:lambda:SetLocalInstruction(self.parseUVal()),
			0x22:lambda:TeeLocalInstruction(self.parseUVal()),
			0x23:lambda:GetGlobalInstruction(self.parseUVal()),
			0x24:lambda:SetGlobalInstruction(self.parseUVal()),
			0x28:lambda:LoadInstruction(ValType.I32, False, 32, self.parseUVal(), self.parseUVal()), 0x29:lambda:LoadInstruction(ValType.I64, False, 64, self.parseUVal(), self.parseUVal()),
			0x2A:lambda:LoadInstruction(ValType.F32, False, 32, self.parseUVal(), self.parseUVal()), 0x2B:lambda:LoadInstruction(ValType.F64, False, 64, self.parseUVal(), self.parseUVal()),

			0x2C:lambda:LoadInstruction(ValType.I32, True, 8, self.parseUVal(), self.parseUVal()), 0x2D:lambda:LoadInstruction(ValType.I32, False, 8, self.parseUVal(), self.parseUVal()),
			0x2E:lambda:LoadInstruction(ValType.I32, True, 16, self.parseUVal(), self.parseUVal()), 0x2F:lambda:LoadInstruction(ValType.I32, False, 16, self.parseUVal(), self.parseUVal()),
			0x30:lambda:LoadInstruction(ValType.I64, True, 8, self.parseUVal(), self.parseUVal()), 0x31:lambda:LoadInstruction(ValType.I64, False, 8, self.parseUVal(), self.parseUVal()),
			0x32:lambda:LoadInstruction(ValType.I64, True, 16, self.parseUVal(), self.parseUVal()), 0x33:lambda:LoadInstruction(ValType.I64, False, 16, self.parseUVal(), self.parseUVal()),
			0x34:lambda:LoadInstruction(ValType.I64, True, 32, self.parseUVal(), self.parseUVal()), 0x35:lambda:LoadInstruction(ValType.I64, False, 32, self.parseUVal(), self.parseUVal()),

			0x36:lambda:StoreInstruction(ValType.I32, 32, self.parseUVal(), self.parseUVal()), 0x37:lambda:StoreInstruction(ValType.I64, 64, self.parseUVal(), self.parseUVal()),
			0x38:lambda:StoreInstruction(ValType.F32, 32, self.parseUVal(), self.parseUVal()), 0x39:lambda:StoreInstruction(ValType.F64, 64, self.parseUVal(), self.parseUVal()),
			
			0x3A:lambda:StoreInstruction(ValType.I32, 8, self.parseUVal(), self.parseUVal()), 0x3B:lambda:StoreInstruction(ValType.I32, 16, self.parseUVal(), self.parseUVal()),
			0x3C:lambda:StoreInstruction(ValType.I64, 8, self.parseUVal(), self.parseUVal()), 0x3D:lambda:StoreInstruction(ValType.I64, 16, self.parseUVal(), self.parseUVal()), 0x3E:lambda:StoreInstruction(ValType.I64, 32, self.parseUVal(), self.parseUVal()),

			0x3F:lambda:MemSizeInstruction(self.parseUVal()), 0x40:lambda:MemGrowInstruction(self.parseUVal()),

			0x41:lambda:ConstInstruction(ValType.I32, self.parseSVal()), 0x42:lambda:ConstInstruction(ValType.I64, self.parseSVal()),
			0x43:lambda:ConstInstruction(ValType.F32, self.parseSVal()), 0x44:lambda:ConstInstruction(ValType.F64, self.parseSVal()),

			0x45:lambda:OpInstruction(WasmInstr.EQZ, ValType.I32), 0x46:lambda:OpInstruction(WasmInstr.EQ, ValType.I32), 0x47:lambda:OpInstruction(WasmInstr.NE, ValType.I32),
			0x48:lambda:OpInstruction(WasmInstr.LT, ValType.I32, True), 0x49:lambda:OpInstruction(WasmInstr.LT, ValType.I32, False),
			0x4A:lambda:OpInstruction(WasmInstr.GT, ValType.I32, True), 0x4B:lambda:OpInstruction(WasmInstr.GT, ValType.I32, False),
			0x4C:lambda:OpInstruction(WasmInstr.LE, ValType.I32, True), 0x4D:lambda:OpInstruction(WasmInstr.LE, ValType.I32, False),
			0x4E:lambda:OpInstruction(WasmInstr.GE, ValType.I32, True), 0x4F:lambda:OpInstruction(WasmInstr.GE, ValType.I32, False),

			0x50:lambda:OpInstruction(WasmInstr.EQZ, ValType.I64), 0x51:lambda:OpInstruction(WasmInstr.EQ, ValType.I64), 0x52:lambda:OpInstruction(WasmInstr.NE, ValType.I64),
			0x53:lambda:OpInstruction(WasmInstr.LT, ValType.I64, True), 0x54:lambda:OpInstruction(WasmInstr.LT, ValType.I64, False),
			0x55:lambda:OpInstruction(WasmInstr.GT, ValType.I64, True), 0x56:lambda:OpInstruction(WasmInstr.GT, ValType.I64, False),
			0x57:lambda:OpInstruction(WasmInstr.LE, ValType.I64, True), 0x58:lambda:OpInstruction(WasmInstr.LE, ValType.I64, False),
			0x59:lambda:OpInstruction(WasmInstr.GE, ValType.I64, True), 0x5A:lambda:OpInstruction(WasmInstr.GE, ValType.I64, False),

			0x5B:lambda:OpInstruction(WasmInstr.EQ, ValType.F32), 0x5C:lambda:OpInstruction(WasmInstr.NE, ValType.F32), 0x5D:lambda:OpInstruction(WasmInstr.LT, ValType.F32),
			0x5E:lambda:OpInstruction(WasmInstr.GT, ValType.F32), 0x5F:lambda:OpInstruction(WasmInstr.LE, ValType.F32), 0x60:lambda:OpInstruction(WasmInstr.GE, ValType.F32),

			0x61:lambda:OpInstruction(WasmInstr.EQ, ValType.F64), 0x62:lambda:OpInstruction(WasmInstr.NE, ValType.F64), 0x63:lambda:OpInstruction(WasmInstr.LT, ValType.F64),
			0x64:lambda:OpInstruction(WasmInstr.GT, ValType.F64), 0x65:lambda:OpInstruction(WasmInstr.LE, ValType.F64), 0x66:lambda:OpInstruction(WasmInstr.GE, ValType.F64),

			0x67:lambda:OpInstruction(WasmInstr.CLZ, ValType.I32), 0x68:lambda:OpInstruction(WasmInstr.CTZ, ValType.I32), 
			0x69:lambda:OpInstruction(WasmInstr.POPCNT, ValType.I32),
			0x6A:lambda:OpInstruction(WasmInstr.ADD, ValType.I32), 0x6B:lambda:OpInstruction(WasmInstr.SUB, ValType.I32), 
			0x6C:lambda:OpInstruction(WasmInstr.MUL, ValType.I32),
			0x6D:lambda:OpInstruction(WasmInstr.DIV, ValType.I32, True), 0x6E:lambda:OpInstruction(WasmInstr.DIV, ValType.I32, False),
			0x6F:lambda:OpInstruction(WasmInstr.REM, ValType.I32, True), 0x70:lambda:OpInstruction(WasmInstr.REM, ValType.I32, False),
			0x71:lambda:OpInstruction(WasmInstr.AND, ValType.I32), 0x72:lambda:OpInstruction(WasmInstr.OR, ValType.I32),  0x73:lambda:OpInstruction(WasmInstr.XOR, ValType.I32), 
			0x74:lambda:OpInstruction(WasmInstr.SHL, ValType.I32), 0x75:lambda:OpInstruction(WasmInstr.SHR, ValType.I32, False),  0x76:lambda:OpInstruction(WasmInstr.SHR, ValType.I32, False),
			0x77:lambda:OpInstruction(WasmInstr.ROTL, ValType.I32), 0x78:lambda:OpInstruction(WasmInstr.ROR, ValType.I32),

			0x79:lambda:OpInstruction(WasmInstr.CLZ, ValType.I64), 0x7A:lambda:OpInstruction(WasmInstr.CTZ, ValType.I64), 
			0x7B:lambda:OpInstruction(WasmInstr.POPCNT, ValType.I64),
			0x7C:lambda:OpInstruction(WasmInstr.ADD, ValType.I64), 0x7D:lambda:OpInstruction(WasmInstr.SUB, ValType.I64), 
			0x7E:lambda:OpInstruction(WasmInstr.MUL, ValType.I64),
			0x7F:lambda:OpInstruction(WasmInstr.DIV, ValType.I64, True), 0x80:lambda:OpInstruction(WasmInstr.DIV, ValType.I64, False),
			0x81:lambda:OpInstruction(WasmInstr.REM, ValType.I64, True), 0x82:lambda:OpInstruction(WasmInstr.REM, ValType.I64, False),
			0x83:lambda:OpInstruction(WasmInstr.AND, ValType.I64), 0x84:lambda:OpInstruction(WasmInstr.OR, ValType.I64), 0x85:lambda:OpInstruction(WasmInstr.XOR, ValType.I64), 
			0x86:lambda:OpInstruction(WasmInstr.SHL, ValType.I64), 0x87:lambda:OpInstruction(WasmInstr.SHR, ValType.I64, False), 0x88:lambda:OpInstruction(WasmInstr.SHR, ValType.I64, False),
			0x89:lambda:OpInstruction(WasmInstr.ROTL, ValType.I64), 0x8A:lambda:OpInstruction(WasmInstr.ROR, ValType.I64),
			
			0x8B:lambda:OpInstruction(WasmInstr.ABS, ValType.F32), 0x8C:lambda:OpInstruction(WasmInstr.NEG, ValType.F32), 
			0x8D:lambda:OpInstruction(WasmInstr.CEIL, ValType.F32), 0x8E:lambda:OpInstruction(WasmInstr.FLOOR, ValType.F32), 
			0x8F:lambda:OpInstruction(WasmInstr.TRUNC, ValType.F32),  0x90:lambda:OpInstruction(WasmInstr.NEAREST, ValType.F32),
			0x91:lambda:OpInstruction(WasmInstr.SQRT, ValType.F32), 
			0x92:lambda:OpInstruction(WasmInstr.ADD, ValType.F32), 0x93:lambda:OpInstruction(WasmInstr.SUB, ValType.F32),
			0x94:lambda:OpInstruction(WasmInstr.MUL, ValType.F32), 0x95:lambda:OpInstruction(WasmInstr.DIV, ValType.F32),
			0x96:lambda:OpInstruction(WasmInstr.MIN, ValType.F32), 0x97:lambda:OpInstruction(WasmInstr.MAX, ValType.F32), 
			0x98:lambda:OpInstruction(WasmInstr.COPYSIGN, ValType.F32),

			0x99:lambda:OpInstruction(WasmInstr.ABS, ValType.F64),
			0x9A:lambda:OpInstruction(WasmInstr.NEG, ValType.F64),
			0x9B:lambda:OpInstruction(WasmInstr.CEIL, ValType.F64),
			0x9C:lambda:OpInstruction(WasmInstr.FLOOR, ValType.F64),
			0x9D:lambda:OpInstruction(WasmInstr.TRUNC, ValType.F64),
			0x9E:lambda:OpInstruction(WasmInstr.NEAREST, ValType.F64),
			0x9F:lambda:OpInstruction(WasmInstr.SQRT, ValType.F64),
			0xA0:lambda:OpInstruction(WasmInstr.ADD, ValType.F64),
			0xA1:lambda:OpInstruction(WasmInstr.SUB, ValType.F64),
			0xA2:lambda:OpInstruction(WasmInstr.MUL, ValType.F64),
			0xA3:lambda:OpInstruction(WasmInstr.DIV, ValType.F64),
			0xA4:lambda:OpInstruction(WasmInstr.MIN, ValType.F64),
			0xA5:lambda:OpInstruction(WasmInstr.MAX, ValType.F64),
			0xA6:lambda:OpInstruction(WasmInstr.COPYSIGN, ValType.F64),
			
			0xA7:lambda:CastInstruction(ValType.I64, ValType.I32),
			0xA8:lambda:CastInstruction(ValType.F32, ValType.I32, True),
			0xA9:lambda:CastInstruction(ValType.F32, ValType.I32, False),
			0xAA:lambda:CastInstruction(ValType.F64, ValType.I32, True),
			0xAB:lambda:CastInstruction(ValType.F64, ValType.I32, False),
			0xAC:lambda:CastInstruction(ValType.I32, ValType.I64, True),
			0xAD:lambda:CastInstruction(ValType.I32, ValType.I64, False),
			0xAE:lambda:CastInstruction(ValType.F32, ValType.I64, True),
			0xAF:lambda:CastInstruction(ValType.F32, ValType.I64, False),
			0xB0:lambda:CastInstruction(ValType.F64, ValType.I64, True),
			0xB1:lambda:CastInstruction(ValType.F64, ValType.I64, False),
			0xB2:lambda:CastInstruction(ValType.I32, ValType.F32, True),
			0xB3:lambda:CastInstruction(ValType.I32, ValType.F32, False),
			0xB4:lambda:CastInstruction(ValType.I64, ValType.F32, True),
			0xB5:lambda:CastInstruction(ValType.I64, ValType.F32, False),
			0xB6:lambda:CastInstruction(ValType.F64, ValType.F32),
			0xB7:lambda:CastInstruction(ValType.I32, ValType.F64, True),
			0xB8:lambda:CastInstruction(ValType.I32, ValType.F64, False),
			0xB9:lambda:CastInstruction(ValType.I64, ValType.F64, True),
			0xBA:lambda:CastInstruction(ValType.I64, ValType.F64, False),
			0xBB:lambda:CastInstruction(ValType.F32, ValType.F64),
			0xBC:lambda:ReinterpretInstruction(ValType.F32, ValType.I32),
			0xBD:lambda:ReinterpretInstruction(ValType.F64, ValType.I64),
			0xBE:lambda:ReinterpretInstruction(ValType.I32, ValType.F32),
			0xBF:lambda:ReinterpretInstruction(ValType.I64, ValType.F64),
		}	

	def parseCallInd(self):
		type = self.parseTypeId()
		assert self.parseByte() == b"\x00"
		return CallInstruction(type = type)
	def parseMagic(self):
		if self.parser.pop(4) != b"\x00asm":
			raise ParseException()
	def parseVersion(self):
		version = self.parser.pop(4)
		print("Wasm-Version: %d.%d.%d.%d" % (version[0], version[1], version[2], version[3]))
	def parseModule(self):
		if self.parser.pop(4) != "\x00asm":
			self.parser.revert(4)
			raise ParseException()

	def parseInstrs(self):
		instrs = []
		while True:
			instr = self.parseInstr()
			if instr == None:
				break
			instrs.append(instr)
		return instrs

	def parseBlockType(self):
		val = self.parser.pop()
		if val == b'\x40':
			return None
		else:
			return ValType(ord(val))

	def parseExpr(self):
		instrs = self.parseInstrs()
		assert self.parser.pop() == b'\x0b'
		return instrs 
	def parseIf(self):
		blockType = self.parseBlockType()
		instrs = self.parseInstrs()
		obj = {'type': WasmInstr.IFELSE, 'blockType': blockType, 'instrs': instrs}
		if self.parser.peek() == b'\x05':
			self.parser.pop()
			obj['altinstrs'] = self.parseInstrs()
		assert self.parser.pop() == b'\x0b'
		return obj
	def parseBlock(self):
		return BlockInstruction(self.parseBlockType(), self.parseExpr())
	def parseLoop(self):
		return LoopInstruction(self.parseBlockType(), self.parseExpr())
	def parseIf(self):
		blockType = self.parseBlockType()
		exprs = self.parseInstrs()
		if self.parser.peek() == b'\x05':
			self.parser.pop()
			return IfElseInstruction(blockType, exprs, self.parseExpr())
		assert self.parser.pop() == b'\x0b'
		return IfElseInstruction(blockType, exprs)


	def parseSection(self):
		if len(self.parser.peek()) == 0:
			return False
		dispatch = {\
			SectionType.CUSTOM: lambda: self.parser.pop(self.parseUVal()),
			SectionType.TYPE: self.parseTypeSec,
			SectionType.IMPORT: self.parseImportSec,
			SectionType.FUNCTION: self.parseFunctionSec,
			SectionType.TABLE: self.parseTableSec,
			SectionType.MEMORY: self.parseMemorySec,
			SectionType.GLOBAL: self.parseGlobalSec,
			SectionType.EXPORT: self.parseExportSec,
			SectionType.START: self.parseStartSec,
			SectionType.ELEMENT: self.parseElementSec,
			SectionType.CODE: self.parseCodeSec,
			SectionType.DATA: self.parseDataSec,
		}
		sectionType = SectionType(ord(self.parser.pop()))
		print("Parsing Section", sectionType)
		size = self.parseUVal()
		oldpos = self.parser.position
		dispatch[sectionType]()
		assert oldpos + size == self.parser.position
		return True

	def parseTypeSec(self):
		self.module.func_types = self.parseVector(self.parseFuncType)
	def parseImportSec(self):
		self.module.imports = self.parseVector(self.parseImport)
	def parseFunctionSec(self):
		self.module.custom_func_offset = len(self.module.functions)
		self.module.functions.extend(self.parseVectorIndexed(self.parseFuncTypeId))
	def parseTableSec(self):
		self.module.tables.extend(self.parseVector(self.parseTable))
	def parseMemorySec(self):
		self.module.memories.extend(self.parseVector(self.parseMem))
	def parseGlobalSec(self):
		self.module.custom_global_offset = len(self.module.functions)
		self.module.globals.extend(self.parseVectorIndexed(self.parseGlobal))
	def parseExportSec(self):
		self.module.exports.extend(self.parseVector(self.parseExport))
	def parseStartSec(self):
		self.module.start_func = self.parseUVal()
	def parseElementSec(self):
		self.parseVectorIndexed(self.parseElement)
	def parseCodeSec(self):
		self.parseVectorIndexed(self.parseCode)
	def parseDataSec(self):
		self.parseVector(self.parseData)

	def parseGlobalId(self):
		global_id = self.parseUVal()
		assert global_id < len(self.module.globals)
		return self.module.globals[global_id]
	def parseFuncId(self):
		func_id = self.parseUVal()
		assert func_id < len(self.module.functions)
		return self.module.functions[func_id]
	def parseTypeId(self):
		type_id = self.parseUVal()
		assert type_id < len(self.module.func_types)
		return self.module.func_types[type_id]
	def parseMemId(self):
		mem_id = self.parseUVal()
		assert mem_id < len(self.module.memories)
		return self.module.memories[mem_id]
	def parseTableId(self):
		table_id = self.parseUVal()
		assert table_id < len(self.module.tables)
		return self.module.tables[table_id]
		
		
	def parseData(self):
		mem = self.parseMemId()
		init_range = InitRange(InitializableValue(self.parseExpr()), self.parseVector(self.parseByte))
		mem.initialize(init_range)
	def parseCode(self, index):
		size = self.parseUVal()
		oldpos = self.parser.position
		func = self.module.functions[self.module.custom_func_offset + index]
		locals = []
		for locs in self.parseVector(self.parseLocals):
			locals.extend(locs)
		func.locals = locals
		func.expr = self.parseExpr()
		assert oldpos + size == self.parser.position
		return func

	def parseMem(self):
		return Memory(self.parseLimits())
	def parseLocals(self):
		return self.parseUVal() * [self.parseValType()]
	def parseElement(self, index):
		table = self.parseTableId()
		init_range = InitRange(InitializableValue(self.parseExpr()), self.parseVector(self.parseFuncId))
		table.initialize(init_range)
		
		
	def parseExport(self):
		sym = self.parseString()
		exportType = ExportDescrType(ord(self.parser.pop()))
		if exportType == ExportDescrType.FUNC:
			self.parseFuncId().export = True
		elif exportType == ExportDescrType.TABLE:
			self.parseTableId().export = True
		elif exportType == ExportDescrType.MEM:
			self.parseMemId().export = True
		elif exportType == ExportDescrType.GLOBAL:
			self.parseGlobalId().export = True
		else:
			raise ParseException()
		
	def parseInstr(self):
		val = ord(self.parser.pop())
		if val in self.instructionHaldlers:
			instr = self.instructionHaldlers[val]()
			return instr
		self.parser.revert()
		return None
	def parseExpr(self):
		expr = self.parseInstrs()
		assert self.parser.pop() == b'\x0b'
		return expr
	def parseGlobal(self, index):
		return Global(self.parseValType(), "global" + str(self.module.custom_clobal_offset + index), mutable = ord(self.parser.pop()) == 0x01, init_value = InitializableValue(self.parseExpr()))
	def parseByte(self):
		return self.parser.pop()
	def parseFuncTypeId(self, index):
		type = self.parseTypeId()
		return Function(self.module.custom_func_offset + index, type, "func" + str(self.module.custom_func_offset + index))
	def parseImport(self):
		module = self.parseString()
		sym = self.parseString()
		import_module = self.module.get_import_module(module)
		importType = ImportDescrType(ord(self.parser.pop()))
		if importType == ImportDescrType.FUNC:
			func = Function(len(self.module.functions), self.parseTypeId(), sym, _import = True)
			import_module[sym] = func
			self.module.functions.append(func)
		elif importType == ImportDescrType.TABLE:
			self.parseTableType()
			table = Table(self.parseLimits(), name = sym, _import = True)
			import_module[sym] = table
			self.module.tables.append(table)
		elif importType == ImportDescrType.MEM:
			memory = Memory(self.parseLimits(), name = sym, _import = True)
			import_module[sym] = memory
			self.module.memories.append(memory)
		elif importType == ImportDescrType.GLOBAL:
			_global = Global(self.parseValType(), mutable = ord(self.parser.pop()) == 0x01, name = sym, _import = True)
			import_module[sym] = _global
			self.module.globals.append(_global)
		else:
			raise ParseException()
	def parseString(self):
		return self.parser.pop(self.parseUVal()).decode("utf-8") 
	def parseUVal(self):
		result = 0
		shift = 0
		while True:
			byte = ord(self.parser.pop())
			result |= (byte & 0x7f) << shift
			if (byte & 0x80) == 0x00:
				break
			shift += 7
		return result
	def parseSVal(self):
		result = 0
		shift = 0
		lastVal = 0
		while True:
			byte = ord(self.parser.pop())
			lastVal = (byte & 0x7f)
			result |= lastVal << shift
			if (byte & 0x80) == 0x00:
				break
			shift += 7
		if lastVal & 0x40  != 0x00:
			result ^= 1 << (shift + 6)
			result *= -1
		return result

	def parseValType(self):
		type = ValType(ord(self.parser.pop()))
		return type
	def parseTable(self):
		return Table(self.parseTableType())
	def parseTableType(self):
		return TableType(ord(self.parser.pop()))
	def parseLimits(self):
		val = ord(self.parser.pop())
		if val == 0x00:
			return Limit(self.parseUVal())
		elif val == 0x01:
			return Limit(self.parseUVal(), self.parseUVal())
		raise ParseException()
	def parseFuncType(self):
		if self.parser.pop() == b'\x60':
			return FunctionType(self.parseVector(self.parseValType), self.parseVector(self.parseValType))
		raise ParseException()
	def parseVector(self, elementParser):
		length = self.parseUVal()
		arr = []
		for i in range(length):
			arr.append(elementParser())
		return arr
	def parseVectorIndexed(self, elementParser):
		length = self.parseUVal()
		arr = []
		for i in range(length):
			arr.append(elementParser(i))
		return arr

	def parseWasm(self):
		self.module = Module()
		self.parseMagic()
		self.parseVersion()
		while self.parseSection():
			pass
		return self.module
