#!/usr/bin/env python3
#

import sys
import struct
from enum import Enum

from Parser import *
from Decomp import *

class PseudoFile:
	def write(self, string):
		print(string, end='')


if __name__ == '__main__':

	if len(sys.argv) < 2:
		print("No input-file specified")
		exit(1)
	if len(sys.argv) > 2:
		print("Meow")
		exit(1)

	filename = sys.argv[1]


	with open(filename, "rb") as file:
		parser = StringParser(file.read())

		wasmparser = WasmParser(parser)
		module = wasmparser.parseWasm()
		
		print("\n\n\n\n")
		
		decompileWasmModule(module, PseudoFile())
		print()