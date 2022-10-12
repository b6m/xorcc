import os
import sys
import ast
import base64
import random
import string
import secrets
import binascii
import argparse
import textwrap
import subprocess
from typing import Any

func_lookup = {'print': 'printf'}
vars = {}

def rw(length):
   letters = string.ascii_lowercase
   return ''.join(random.choice(letters) for i in range(length))

class CodeGenerator:
    def __init__(self):
        self.ind = 0
        self.code = []
        self.create_header()

    def indent(self):
        self.ind += 1

    def dedent(self):
        self.ind -= 1
        self.ind = max(0, self.ind)

    def add_code(self, code: str):
        self.add_byte_code(code.encode("utf-8"))

    def create_header(self):
        self.add_code('#include <stdio.h>\n')
        self.add_code('#define _(___,____,_____,______) m##a##i##n')
        self.add_code('#define __ _(___,____,_____,______)\n')
        self.add_code('int real(int fake) {return fake;}\n')
        self.add_code('int __() {')
        self.add_code('\tif (real(0) == 1) {\n\t\tasm("jmp 0xFF");\n\t}\n')
        self.indent()

    def end_header(self):
        self.add_code('return 0;')
        self.dedent()
        self.add_code('}')

    def add_int(self, name: str, value):
        vars[name] = 'int'
        key = random.getrandbits(32)
        value = ~(value ^ key)
        self.add_code(f'int {name} = ~({value} ^ {key});')

    def add_char(self, name: str, value: str):
        vars[name] = 'char'
        length = len(value)
        vl = [value[idx:idx + 1] for idx in range(0, length, 1)]
        self.add_code(f'char {name}[{len(value)}];')
        pos_list = []
        c = 0
        for i in vl: key = random.getrandbits(32); SHIFT = random.getrandbits(48); xkey = random.getrandbits(56); skey = random.getrandbits(48); cm = ~(~(ord(i) ^ key) ^ ~(SHIFT +~xkey)) ^ skey; pos_list.append(f'{name}[{c}] = ~(~({cm} ^ {key}) ^ ~({SHIFT} +~{xkey})) ^ {skey};'); c = c +1

        random.shuffle(pos_list)

        for x in pos_list: self.add_code(x)

        # key = random.getrandbits(32)
        # pos = random.sample(range(0, length), 1)[0]

        # cm = ord(vl[c]) ^ key
        # self.add_code(f'{name}[{pos}] = {cm} ^ {key};')

        # self.add_code(f'char {name}[] = {value};')

        
    def call_func(self, name: str, params, format: int):
        name = func_lookup[f"{name}"] if name in func_lookup else ";"
        if format != 0:
            formats = {
                'int':'%d',
                'char':'%s',
                'lit':'%s'
            }

            if params in vars:
                params = f'"{formats.get(vars[params])}\\n", {params}'
        self.add_code(f'{name}({params});')

    def add_BinOp(self, name: str, left: str, op, right: str):
        ops = {
            ast.BitXor: '^',
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/'
        }

        # Use better checking
        if isinstance(op, ast.BitXor):
            op = '^'
        elif isinstance(op, ast.Add):
            op = '+'
        elif isinstance(op, ast.Sub):
            op = '-'
        elif isinstance(op, ast.Mult):
            op = '*'
        elif isinstance(op, ast.Div):
            op = '/'
        else:
            print(f"Unknown Binary operation! {op}")
            sys.exit(-1)
        vars[name] = 'int'
        self.add_code(f'int {name} = {left} {op} {right};')

    def add_byte_code(self, code: bytes):
        self.code.append(b"    " * self.ind + code)

    def construct(self):
        self.end_header()
        return b"\n".join(self.code)

generator = CodeGenerator()

class Analyzer(ast.NodeTransformer):
    def visit_Call(self, node: ast.Name) -> Any:
        name = node.func.id
        if isinstance(node.args[0], ast.Name):
            args = node.args[0].id
            format = 1
        else:
            args = f'\"{node.args[0].value}\\n\"' if node.args else None
            format = 0
        print(f'found call for {name} with args {args}')
        generator.call_func(name, args, format)
        return super().generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> Any:
        if isinstance(node.value, int) or isinstance(node.value, ast.Constant):
            name = node.targets[0].id
            value = f'{node.value.value}' if isinstance(node.value.value, str) else node.value.value
            print(f"Found variable {name} with value {value}")
            if isinstance(value, int):
                generator.add_int(name, value)
            else:
                generator.add_char(name, value)
        elif isinstance(node.value, ast.BinOp):
            name = node.targets[0].id
            value = node
            generator.add_BinOp(name, node.value.right.id, node.value.op, node.value.left.id)
            print(f"Found a BinOp variable {name} with value {value}")
        return super().generic_visit(node)

    def generic_visit(self, node):
            return super().generic_visit(node)

def init():
    parser = argparse.ArgumentParser(
        prog="xorcc",
        description="Convert a python script to C code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
        Examples:
            xorcc --infile test.py --output test.bin
        Copyright (c) xor7, 2022.
        """
        ),
    )
    parser.add_argument("--infile", help="The input file", required=True)
    parser.add_argument("--outfile", help="The output file", required=True)
    args = parser.parse_args()
    infile = args.infile
    outfile = args.outfile
    
    with open(infile, "r") as f:
        tree = ast.parse(f.read())
        # for node in ast.walk(tree):
        #     print('Found', ast.dump(node))
        mt = Analyzer().visit(tree)
        mt = ast.fix_missing_locations(mt)

    with open("/tmp/xorcc.c", 'wb') as f:
        f.write(generator.construct())

    subprocess.run(["clang", "-o", outfile, "-s", "/tmp/xorcc.c"])
    print('Done!')

init()
