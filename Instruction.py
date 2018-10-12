#!/usr/bin/env python3
#

from Decomp import *
from enum import Enum


class Instruction:
	def doDecomp(self, context):
		print(type(self))
		assert False
	def __repr__(self):
		return "undef"
class UnreachableInstruction(Instruction):
	def doDecomp(self, context):
		context.evict(UnreachableAstNode())
	def __repr__(self):
		return "Unreachable"
class NopInstruction(Instruction):
	def doDecomp(self, context):
		pass
	def __repr__(self):
		return "Nop"
class StoreInstruction(Instruction):
	def __init__(self, valtype, length, align, offset):
		self.valtype = valtype
		self.length = length
		self.align = align
		self.offset = offset
	def doDecomp(self, context):
		value = context.pop()
		ptr = context.pop()
		context.evict(StoreAstNode(self.valtype, ptr, self.length, self.align, self.offset, value))
	def __repr__(self):
		return "Store[]"
class LoadInstruction(Instruction):
	def __init__(self, valtype, s_ext, length, align, offset):
		self.valtype = valtype
		self.s_ext = s_ext
		self.length = length
		self.align = align
		self.offset = offset
	def doDecomp(self, context):
		context.push(LoadAstNode(self.valtype, context.pop(), self.s_ext, self.length, self.align, self.offset))
	def __repr__(self):
		return "Load[]"
		
def parseSingleOp(context, op):
	return OpAstNode([context.pop()], op.type, op.valtype, op.signed)
				
def parseDualOp(context, op):
	arg2 = context.pop()
	arg1 = context.pop()
	return OpAstNode([arg1, arg2], op.type, op.valtype, op.signed)
		
wasm_op_dispatcher = {
			WasmInstr.EQZ: parseSingleOp,
			WasmInstr.EQ: parseDualOp,
			WasmInstr.NE: parseDualOp,
			WasmInstr.LT: parseDualOp,
			WasmInstr.GT: parseDualOp,
			WasmInstr.LE: parseDualOp,
			WasmInstr.GE: parseDualOp,
			
			WasmInstr.CLZ: parseSingleOp,
			WasmInstr.CTZ: parseSingleOp,
			WasmInstr.POPCNT: parseSingleOp,
			
			WasmInstr.ADD: parseDualOp,
			WasmInstr.SUB: parseDualOp,
			WasmInstr.MUL: parseDualOp,
			WasmInstr.DIV: parseDualOp,
			WasmInstr.REM: parseDualOp,
			
			WasmInstr.AND: parseDualOp,
			WasmInstr.OR: parseDualOp,
			WasmInstr.XOR: parseDualOp,
			
			WasmInstr.SHL: parseDualOp,
			WasmInstr.SHR: parseDualOp,
			WasmInstr.ROTL: parseDualOp,
			WasmInstr.ROTR: parseDualOp,
			
			WasmInstr.ABS: parseSingleOp,
			WasmInstr.NEG: parseSingleOp,
			WasmInstr.CEIL: parseSingleOp,
			WasmInstr.FLOOR: parseSingleOp,
			WasmInstr.TRUNC: parseSingleOp,
			WasmInstr.NEAREST: parseSingleOp,
			WasmInstr.SQRT: parseSingleOp,
			WasmInstr.MIN: parseDualOp,
			WasmInstr.MAX: parseDualOp,
			WasmInstr.COPYSIGN: parseSingleOp
		}
		
class OpInstruction(Instruction):
	def __init__(self, type, valtype, signed = False):
		self.type = type
		self.valtype = valtype
		self.signed = signed
	def doDecomp(self, context):
		context.push(wasm_op_dispatcher[self.type](context, self))
	def __repr__(self):
		return "Op " + str(self.type)
class ConstInstruction(Instruction):
	def __init__(self, valtype, value):
		self.valtype = valtype
		self.value = value
	def doDecomp(self, context):
		context.push(self.value, valtype = self.valtype)
	def __repr__(self):
		return "Const %d" % self.value
class MemSizeInstruction(Instruction):
	def __init__(self, size):
		self.size = size
	def doDecomp(self, context):
		context.push(MemSizeAstNode(self.size))
	def __repr__(self):
		return "MemSize" % self.value
class MemGrowInstruction(Instruction):
	def __init__(self, size):
		self.size = size
	def doDecomp(self, context):
		context.push(MemGrowAstNode(self.size))
	def __repr__(self):
		return "MemGrow %d" % self.value
class CastInstruction(Instruction):
	def __init__(self, fromtype, totype, signed = False):
		self.fromtype = fromtype
		self.totype = totype
		self.signed = signed
	def doDecomp(self, context):
		context.push(CastAstNode(context.pop(), self.totype))
	def __repr__(self):
		return "Cast"
class ReinterpretInstruction(Instruction):
	def __init__(self, fromtype, totype):
		self.fromtype = fromtype
		self.totype = totype
	def doDecomp(self, context):
		context.push(ReinterpretAstNode(context.pop(), self.totype))
	def __repr__(self):
		return "Reinterpret"
class BranchInstruction(Instruction):
	def __init__(self, label, condition = True):
		self.label = label
		self.condition = condition
	def doDecomp(self, context):
		itcontext = context
		for i in range(self.label):
			itcontext = itcontext.parentcontext
		context.evict(BranchAstNode("label_" + str(itcontext.depth), self.condition))
	def __repr__(self):
		return "Branch" + ("If" if self.condition else "")
class BranchTableInstruction(Instruction):
	def __init__(self, table, label):
		self.label = label
		self.table = table
	def doDecomp(self, context):
		pass
		#assert False
	def __repr__(self):
		return "BranchTable"
class ReturnInstruction(Instruction):
	def doDecomp(self, context):
		context.ret()
	def __repr__(self):
		return "Return"
class CallInstruction(Instruction):
	def __init__(self, target = None, type = None):
		self.target = target
		if target != None:
			self.type = target.type
		elif type != None:
			assert type != None
			self.type = type
		else:
			assert False
	def doDecomp(self, context):
		callnode = CallAstNode(context, self.target, self.type)
		for retvar in callnode.rets[::-1]:
			context.push(retvar)
		context.evict(callnode)
	def __repr__(self):
		return "Call " + str(self.target) + " " + str(self.type)
class DropInstruction(Instruction):
	def doDecomp(self, context):
		context.pop()
	def __repr__(self):
		return "Drop"
class SelectInstruction(Instruction):
	def __repr__(self):
		return "Select"
class GetLocalInstruction(Instruction):
	def __init__(self, index):
		self.index = index
	def doDecomp(self, context):
		context.push(context.getLocal(self.index))
	def __repr__(self):
		return "get_local.%d" % self.index
class SetLocalInstruction(Instruction):
	def __init__(self, index):
		self.index = index
	def doDecomp(self, context):
		context.setLocal(self.index, context.pop())
	def __repr__(self):
		return "set_local.%d" % self.index
class TeeLocalInstruction(SetLocalInstruction):
	def __init__(self, index):
		self.index = index
	def doDecomp(self, context):
		super().doDecomp(context)
		context.push(context.getLocal(self.index))
	def __repr__(self):
		return "tee_local.%d" % self.index
class GetGlobalInstruction(Instruction):
	def __init__(self, index):
		self.index = index
	def doDecomp(self, context):
		context.push(context.getGlobal(self.index))
	def __repr__(self):
		return "get_global.%d" % self.index
class SetGlobalInstruction(Instruction):
	def __init__(self, index):
		self.index = index
	def doDecomp(self, context):
		context.setGlobal(self.index, context.pop())
	def __repr__(self):
		return "set_global.%d" % self.index
		
class BlockInstruction(Instruction):
	def __init__(self, blocktype, expr):
		self.blocktype = blocktype
		self.expr = expr
	def doDecomp(self, context):
		context.evict(context.block(self.expr, self.blocktype))
	def __repr__(self):
		return "block -> " + str(self.blocktype)
class IfElseInstruction(Instruction):
	def __init__(self, blocktype, expr, altexpr = None):
		self.blocktype = blocktype
		self.expr = expr
		self.altexpr = altexpr
	def doDecomp(self, context):
		cond = context.pop()
		context.evict(context.ifelse(cond, self.expr, self.altexpr, self.blocktype))
	def __repr__(self):
		return "if-else"
class LoopInstruction(Instruction):
	def __init__(self, blocktype, expr):
		self.blocktype = blocktype
		self.expr = expr
	def doDecomp(self, context):
		context.evict(context.loop(self.expr, self.blocktype))
	def __repr__(self):
		return "loop"


def calculateConstExpr(exprs, module):
	assert len(exprs) == 1#anything more is not implemented
	if type(exprs[0]) == ConstInstruction:
		return exprs[0].value
	elif type(exprs[0]) == GetGlobalInstruction:
		return module.globals[exprs[0].index].name
	assert False

class InitializableValue:
	def __init__(self, init_exprs):
		self.init_exprs = init_exprs
		self.value = None
	def getValue(self, module):
		if self.value == None:
			self.value = calculateConstExpr(self.init_exprs, module)
		return self.value
	def __repr__(self):
		return "Init " + str(self.init_exprs)











