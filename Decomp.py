#!/usr/bin/env python3
#

from functools import reduce
from Type import ValType, Function, WasmInstr

class AstNode:
	def __init__(self, type):
		self.type = type
	def readsGlobal(self, index):
		return False
	def readsLocal(self, index):
		return False
	def readsMemory(self, index):
		return False
class ValueAstNode(AstNode):
	def __init__(self, type, value):
		super().__init__(type)
		self.value = value
	def __repr__(self):
		#return str(self.type) + " " + str(self.value)
		return str(self.value)
class CallAstNode(AstNode):
	def __init__(self, context, target, type):
		super().__init__(type)
		self.params = []
		if target == None:
			self.target = context.pop()
		else:
			self.target = target
		for param in type.parameters:
			self.params.append(context.pop())
		self.type = type
		self.rets = []
		for i in range(len(type.ret_vars)):
			self.rets.append(VarAstNode(type.ret_vars[i], context = context))
	def __repr__(self):
		print()
		return (("(" + ', '.join(map(str,self.rets)) + ") <- ") if len(self.rets) != 0 else "") + "Calling " + (self.target.name if type(self.target) == Function else str(self.target)) + "(" + ', '.join(map(str,self.params)) + ")"
class VarAstNode(AstNode):
	def __init__(self, type, name = None, context = None, globalindex = None, localindex = None):
		super().__init__(type)
		self.globalindex = globalindex
		self.localindex = localindex
		if name == None and context != None:
			self.name = context.newVar()
		elif name != None:
			self.name = name
		else:
			assert False
	def readsGlobal(self, index):
		return self.globalindex == index
	def readsLocal(self, index):
		return self.localindex == index
	def __repr__(self):
		return str(self.name)
class ReturnAstNode(VarAstNode):
	def __init__(self, args = []):
		self.args = args
	def __repr__(self):
		return "Return " + str(self.args)
class BlockReturnAstNode(VarAstNode):
	def __init__(self, args = [], index = 0):
		self.args = args
	def __repr__(self):
		return "BlockReturn " + str(self.args)
class BranchBlockReturnAstNode(BlockReturnAstNode):
	def __init__(self, cond, args = [], index = 0):
		super().__init__(args, index)
		self.cond = cond
	def __repr__(self):
		return "if(" + str(self.cond) + ")" + str(super())
class OpAstNode(AstNode):
	def __init__(self, args, type, valtype, signed):
		self.args = args
		self.type = type
		self.valtype = valtype
		self.signed = signed
	def readsGlobal(self, index):
		return reduce(lambda x,y: x | y, map(lambda arg: arg.readsGlobal(index), self.args))
	def readsLocal(self, index):
		return reduce(lambda x,y: x | y, map(lambda arg: arg.readsLocal(index), self.args))
	def readsMemory(self, index):
		return reduce(lambda x,y: x | y, map(lambda arg: arg.readsMemory(index), self.args))
	def __repr__(self):
		if self.type == WasmInstr.EQZ:
			return "(" + str(self.args[0]) + " == 0)"
		elif self.type == WasmInstr.EQ:
			return "(" + ' == '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.NE:
			return "(" + ' != '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.LT:
			return "(" + ' < '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.GT:
			return "(" + ' > '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.LE:
			return "(" + ' <= '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.GE:
			return "(" + ' >= '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.ADD:
			return "(" + ' + '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.SUB:
			return "(" + ' - '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.MUL:
			return "(" + ' * '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.DIV:
			return "(" + ' / '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.REM:
			return "(" + ' % '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.AND:
			return "(" + ' & '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.OR:
			return "(" + ' | '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.XOR:
			return "(" + ' ^ '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.SHL:
			return "(" + ' << '.join(map(str, self.args)) + ")"
		elif self.type == WasmInstr.SHR:
			return "(" + ' >> '.join(map(str, self.args)) + ")"
		return str(self.type) + "(" + ', '.join(map(str, self.args)) + ")"
class LoadAstNode(AstNode):
	def __init__(self, valtype, base, s_ext, length, align, offset):
		self.offset = offset
		self.base = base
		self.align = align
		self.length = length
		self.valtype = valtype
		self.s_ext = s_ext
	def readsMemory(self, index):
		return True
	def __repr__(self):
		if self.length == 32 and (self.valtype == ValType.I32 or self.valtype == ValType.F32):
			return "load_%d(%s + %d align %d)" % (self.length, str(self.base), self.offset, 2**self.align)
		elif self.length == 64 and (self.valtype == ValType.I64 or self.valtype == ValType.F64):
			return "load_%d(%s + %d align %d)" % (self.length, str(self.base), self.offset, 2**self.align)
		return "(%s) load_%d(%s + %d align %d %s)" % (str(self.valtype), self.length, str(self.base), self.offset, 2**self.align, "as_signed " if self.s_ext else "")
class StoreAstNode(AstNode):
	def __init__(self, valtype, base, length, align, offset, value):
		self.offset = offset
		self.base = base
		self.align = align
		self.length = length
		self.valtype = valtype
		self.value = value
	def __repr__(self):
		return "store_%d(%s + %d align %d, %s)" % (self.length, str(self.base), self.offset, 2**self.align, str(self.value))
class CastAstNode(AstNode):
	def __init__(self, val, type):
		self.val = val
		self.type = type
	def __repr__(self):
		return str(type) + " " + str(self.val)
class ReinterpretAstNode(AstNode):
	def __init__(self, val, type):
		self.val = val
		self.type = type
	def __repr__(self):
		return "Reinterpret " + str(type) + " " + str(self.val)
class MemSizeAstNode(AstNode):
	def __init__(self, size):
		self.size = size
	def __repr__(self):
		return "MemSize(" + str(size) + ")"
class MemGrowAstNode(AstNode):
	def __init__(self, size):
		self.size = size
	def __repr__(self):
		return "MemGrow(" + str(size) + ")"
class UnreachableAstNode(AstNode):
	def __init__(self):
		pass
	def __repr__(self):
		return "Unreachable"
class BranchAstNode(AstNode):
	def __init__(self, label, cond):
		self.label = label
		self.cond = cond
	def __repr__(self):
		if self.cond:
			return "break " + str(self.label) + " block(s)"
		return "if(" + str(self.cond) + ") break " + str(self.label) + " block(s)"
		
		
class BlockAstNode(AstNode):
	def __init__(self, exprs, returns):
		self.exprs = exprs
		self.returns = returns
	def __repr__(self):
		if len(self.returns) == 0:
			return "block {" + '; '.join(map(str, self.exprs)) + "}"
		return ", ".join(map(str, self.returns)) + " <- {" + '; '.join(map(str, self.exprs)) + "}"
class IfElseAstNode(AstNode):
	def __init__(self, cond, trueexprs, falseexprs, returns):
		self.cond = cond
		self.trueexprs = trueexprs
		self.falseexprs = falseexprs
		self.returns = returns
	def __repr__(self):
		string = ""
		if len(self.returns) != 0:
			string += ", ".join(map(str, self.returns)) + " <- "
		string += "if(" + str(self.cond) + ")\n"
		string += str(self.trueexprs)
		if self.falseexprs != None:
			string += "else\n"
			string += str(self.falseexprs)
		return string
class LoopAstNode(AstNode):
	def __init__(self, exprs, returns):
		self.exprs = exprs
		self.returns = returns
	def __repr__(self):
		if len(self.returns) == 0:
			return "loop {" + '; '.join(map(str, self.exprs)) + "}"
		return ", ".join(map(str, self.returns)) + " <- {" + '; '.join(map(str, self.exprs)) + "}"
class SetAstNode(AstNode):
	def __init__(self, toExpr, fromExpr):
		self.toExpr = toExpr
		self.fromExpr = fromExpr
	def __repr__(self):
		return "%s %s = %s" % (str(self.toExpr.type), str(self.toExpr), str(self.fromExpr))
class AstExpr:
	def __init__(self, astnode, indent = 0):
		self.astnode = astnode
		self.indent = indent
	def __repr__(self):
		return (" "*(4*self.indent)) + str(self.astnode)

		
class DecompilationContext:
	def __init__(self, module, func, parentcontext = None):
		self.module = module
		self.func = func
		self.stack = []
		self.exprs = []
		self.parentcontext = parentcontext
		if parentcontext == None:
			self.indent = 0
		else:
			self.indent = parentcontext.indent + 1
		self.variablecount = 0
	def newVar(self):
		if self.parentcontext == None:
			name = "var" + str(self.variablecount)
			self.variablecount += 1
			return name
		else:
			return self.parentcontext.newVar()
	def setLocal(self, index, value):
		for i in range(len(self.stack)):
			stackentry = self.stack[i]
			if stackentry.readsLocal(index):
				var = VarAstNode(self.func.locals[index], context = self)
				self.evict(SetAstNode(var, stackentry))
				self.stack[i] = var
		self.evict(SetAstNode(self.getLocal(index), value))
		return value
	def getLocal(self, index):
		if index < len(self.func.type.parameters):
			return VarAstNode(self.func.type.parameters[index], name = "arg" + str(index))
		index = index - len(self.func.type.parameters)
		return VarAstNode(self.func.locals[index], name = "local" + str(index))
	def setGlobal(self, index, value):
		for i in range(len(self.stack)):
			stackentry = self.stack[i]
			if stackentry.readsLocal(index):
				var = VarAstNode(self.func.locals[index], context = self)
				self.evict(SetAstNode(var, stackentry))
				self.stack[i] = var
		self.evict(SetAstNode(self.getGlobal(index), value))
	def getGlobal(self, index):
		globalObj = self.module.globals[index]
		return VarAstNode(globalObj.type, name = globalObj.name)
	def pop(self):
		return self.stack.pop()
	def ret(self):
		if len(self.func.type.ret_vars) == 0:
			return
		ret_vals = []
		for ret in self.func.type.ret_vars[::-1]:
			ret_vals.append(self.pop())
		self.evict(ReturnAstNode(ret_vals))
	def push(self, value, valtype = None):
		if valtype != None:
			self.stack.append(ValueAstNode(valtype, value))
		else:
			self.stack.append(value)
	def evict(self, astnode):
		self.exprs.append(astnode)
	def ifelse(self, cond, exprtrue, exprfalse, type):
		truecontext = DecompilationContext(self.module, self.func, self)
		decompileExpr(truecontext, exprtrue)
		
		falsecontext = None
		if exprfalse != None:
			falsecontext = DecompilationContext(self.module, self.func, self)
			decompileExpr(falsecontext, exprfalse)
			
		blockreturns = []
		if type != None:
			truecontext.evict(BlockReturnAstNode([truecontext.pop()]))
			if falsecontext == None:
				falsecontext.evict(BlockReturnAstNode([falsecontext.pop()]))
				
			blockreturns.append(VarAstNode(type, context = self))
			self.push(blockreturns[-1])
		
		return IfElseAstNode(cond, truecontext.exprs, None if falsecontext == None else falsecontext.exprs, blockreturns)
	def block(self, exprs, type):
		context = DecompilationContext(self.module, self.func, self)
		decompileExpr(context, exprs)
		
		blockreturns = []
		if type != None:
			blockreturns.append(VarAstNode(type, context = self))
			self.push(blockreturns[-1])
			context.evict(BlockReturnAstNode([context.pop()]))
			
		return BlockAstNode(context.exprs, blockreturns)
		
	def loop(self, loopexpr, type):
		context = DecompilationContext(self.module, self.func, self)
		decompileExpr(context, loopexpr)
		
		blockreturns = []
		if type != None:
			blockreturns.append(VarAstNode(type, context = self))
			self.push(blockreturns[-1])
			context.evict(BlockReturnAstNode([context.pop()]))
			
		return LoopAstNode(context.exprs, blockreturns)
	def branch(self, label, condition):
		return BranchBlockReturnAstNode()
	def __repr__(self):
		return "Stack: " + str(self.stack) + "\nExprs:\n\t" + '\n\t'.join(map(str,self.exprs))
	
def decompileExpr(context, exprs):
	for instr in exprs:
		instr.doDecomp(context)

def returnsToString(returnvalues):
	if len(returnvalues) == 0:
		return ""
	return "["+ ", ".join(map(str, returnvalues)) + "] <- "

def printExprs(exprs, indent = 0):
	for expr in exprs:
		if type(expr) == BlockAstNode:
			print("    "*indent + returnsToString(expr.returns) + "{")
			printExprs(expr.exprs, indent + 1)
			print("    "*indent + "}")
		elif type(expr) == IfElseAstNode:
			print("    "*indent + returnsToString(expr.returns) + "if(" + str(expr.cond) + "){")
			printExprs(expr.trueexprs, indent + 1)
			print("    "*indent + "}")
			if expr.falseexprs != None:
				print("    "*indent + "else{")
				printExprs(expr.falseexprs, indent + 1)
				print("    "*indent + "}")
		elif type(expr) == LoopAstNode:
			print("    "*indent + returnsToString(expr.returns) + "loop{")
			printExprs(expr.exprs, indent + 1)
			print("    "*indent + "}")
		else:
			print("    "*indent + str(expr))

def decompileWasmFunction(module, function, file):
	print("\n\n\n\n\n\n")
	print("Decompiling function")
	print(function)
	print(function.expr)
	context = DecompilationContext(module, function)
	decompileExpr(context, function.expr)
	context.ret()
	print("------------------------")
	print("Final Result:")
	printExprs(context.exprs, 1)
	#file.write(function.printExpr(module))

def decompileWasmModule(module, file):
	for glob in module.globals:
		file.write(glob.printExpr(module))
		file.write("\n")
	file.write("\n")
	for mem in module.memories:
		file.write(mem.printExpr(module))
		file.write("\n")
	file.write("\n")
	for table in module.tables:
		file.write(table.printExpr(module))
		file.write("\n")
	file.write("\n")
	for func in module.functions:
		if not func._import:
			decompileWasmFunction(module, func, file)
	
