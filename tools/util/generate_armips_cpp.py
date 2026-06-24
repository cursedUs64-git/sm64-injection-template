#!/usr/bin/env python

import os
import re
import sys

file_list = [
    'ext/tinyformat/tinyformat.h',
    'Core/Types.h',
    'Util/Util.h',
    'Util/FileClasses.h',
    'Util/ByteArray.h',
    'Util/EncodingTable.h',
    'Util/CRC.h',
    'Core/Expression.h',
    'Core/ExpressionFunctionHandler.h',
    'Core/ExpressionFunctions.h',
    'Core/SymbolData.h',
    'Core/FileManager.h',
    'Core/ELF/ElfTypes.h',
    'Core/ELF/ElfFile.h',
    'Core/ELF/ElfRelocator.h',
    'Core/Allocations.h',
    'Core/Misc.h',
    'Core/Assembler.h',
    'Core/SymbolTable.h',
    'Core/Common.h',
    'Commands/CAssemblerCommand.h',
    'Commands/CAssemblerLabel.h',
    'Commands/CDirectiveArea.h',
    'Commands/CDirectiveConditional.h',
    'Commands/CDirectiveData.h',
    'Commands/CDirectiveFile.h',
    'Commands/CDirectiveMessage.h',
    'Commands/CommandSequence.h',
    'Parser/DirectivesParser.h',
    'Parser/ExpressionParser.h',
    'Parser/Tokenizer.h',
    'Parser/Parser.h',
    'Archs/Architecture.h',
    'Archs/ARM/ArmOpcodes.h',
    'Archs/ARM/ThumbOpcodes.h',
    'Archs/ARM/Pool.h',
    'Archs/ARM/Arm.h',
    'Archs/ARM/CArmInstruction.h',
    'Archs/ARM/CThumbInstruction.h',
    'Archs/ARM/ArmElfRelocator.h',
    'Archs/ARM/ArmExpressionFunctions.h',
    'Archs/ARM/ArmParser.h',
    'Archs/ARM/Arm.cpp',
    'Archs/ARM/ArmOpcodes.cpp',
    'Archs/ARM/CArmInstruction.cpp',
    'Archs/ARM/CThumbInstruction.cpp',
    'Archs/ARM/ArmElfRelocator.cpp',
    'Archs/ARM/ArmExpressionFunctions.cpp',
    'Archs/ARM/Pool.cpp',
    'Archs/ARM/ThumbOpcodes.cpp',
    'Archs/ARM/ArmParser.cpp',
    'Commands/CAssemblerLabel.cpp',
    'Archs/MIPS/Mips.h',
    'Archs/SuperH/ShOpcodes.h',
    'Archs/SuperH/SuperH.h',
    'Archs/SuperH/CShInstruction.h',
    'Archs/SuperH/ShParser.h',
    'Archs/SuperH/ShElfRelocator.h',
    'Archs/SuperH/ShExpressionFunctions.h',
    'Archs/MIPS/MipsOpcodes.h',
    'Archs/MIPS/CMipsInstruction.h',
    'Archs/MIPS/MipsExpressionFunctions.h',
    'Archs/MIPS/MipsElfRelocator.h',
    'Archs/MIPS/MipsElfFile.h',
    'Archs/MIPS/MipsMacros.h',
    'Archs/MIPS/MipsParser.h',
    'Archs/MIPS/PsxRelocator.h',
    'Archs/MIPS/CMipsInstruction.cpp',
    'Archs/MIPS/Mips.cpp',
    'Archs/MIPS/MipsElfFile.cpp',
    'Archs/MIPS/MipsElfRelocator.cpp',
    'Archs/MIPS/MipsExpressionFunctions.cpp',
    'Archs/MIPS/MipsMacros.cpp',
    'Archs/MIPS/MipsOpcodes.cpp',
    'Archs/MIPS/MipsParser.cpp',
    'Archs/MIPS/PsxRelocator.cpp',
    'Archs/SuperH/SuperH.cpp',
    'Archs/SuperH/CShInstruction.cpp',
    'Archs/SuperH/ShParser.cpp',
    'Archs/SuperH/ShOpcodes.cpp',
    'Archs/SuperH/ShElfRelocator.cpp',
    'Archs/SuperH/ShExpressionFunctions.cpp',
    'Archs/Architecture.cpp',
    'Commands/CAssemblerCommand.cpp',
    'Commands/CDirectiveArea.cpp',
    'Commands/CDirectiveConditional.cpp',
    'Commands/CDirectiveData.cpp',
    'Commands/CDirectiveFile.cpp',
    'Commands/CDirectiveMessage.cpp',
    'Commands/CommandSequence.cpp',
    'Parser/DirectivesParser.cpp',
    'Parser/ExpressionParser.cpp',
    'Parser/Parser.cpp',
    'Parser/Tokenizer.cpp',
    'Util/ByteArray.cpp',
    'Util/CRC.cpp',
    'Util/EncodingTable.cpp',
    'Util/FileClasses.cpp',
    'Util/Util.cpp',
    'Main/CommandLineInterface.h',
    'Main/CommandLineInterface.cpp',
    'Core/ELF/ElfFile.cpp',
    'Core/ELF/ElfRelocator.cpp',
    'Core/Allocations.cpp',
    'Core/Assembler.cpp',
    'Core/Common.cpp',
    'Core/Expression.cpp',
    'Core/ExpressionFunctionHandler.cpp',
    'Core/ExpressionFunctions.cpp',
    'Core/FileManager.cpp',
    'Core/Misc.cpp',
    'Core/SymbolData.cpp',
    'Core/SymbolTable.cpp',
    'Core/Types.cpp',
    'Main/main.cpp',
]

file_header =  \
"""// armips assembler v0.11
// https://github.com/Kingcom/armips/
// To simplify compilation, all files have been concatenated into one.
// MIPS only, ARM is not included.
// Requires C++17 or later.

// WARNING FOR N64:
// Unless you 8-byte align (instead of the usual 4-byte) the address of a double float (f64) or bare float literals (0.0 instead of 0.0f),
// GCC, IDO CC will emit LDC1/SDC1 for doubles which requre 8-byte alignment.
// If this code is injected at a 4-byte aligned address, it WILL crash.

#define ARMIPS_USE_STD_FILESYSTEM
#include <filesystem>
#include <fstream>
#include <vector>
namespace fs {
    using namespace std::filesystem;
    using fstream  = std::fstream;
    using ifstream = std::ifstream;
    using ofstream = std::ofstream;
}\n\n"""

# angle-bracket includes for headers we fully inline into the output
INLINED_HEADERS = {'tinyformat.h', 'ghc/filesystem.hpp', 'ghc/fs_fwd.hpp', 'ghc/fs_impl.hpp'}

def banned(line):
    if '#pragma once' in line:
        return True
    if '#include "' in line:
        return True
    # strip angle-bracket includes for headers we inline into the output
    m = re.search(r'#include\s*<([^>]+)>', line)
    if m and m.group(1) in INLINED_HEADERS:
        return True
    return False

def cat_file(fout, fin_name):
    with open(fin_name) as fin:
        lines = fin.readlines()
        lines = [l.rstrip() for l in lines if not banned(l)]
        for l in lines:
            fout.write(l + '\n')
        fout.write('\n')

PATCHES = [
    # Force 4-byte alignment on .importobj injection for N64 ROMs,
    # and update p_align in the segment header to match.
    (
        '\t// align segment to alignment of first section\n'
        '\tint align = std::max<int>(sections[0]->getAlignment(),16);\n'
        '\toutput.alignSize(align);',
        '\t// align segment to 4 bytes for N64 ROM injection\n'
        '\toutput.alignSize(4);\n'
        '\theader.p_align = 4;',
    ),
    # Also clamp each section's sh_addralign to 4, otherwise sections
    # with sh_addralign=16 will still pad to 16 when written.
    (
        '\tif (header.sh_addralign != (unsigned) -1)\n'
        '\t\toutput.alignSize(header.sh_addralign);',
        '\tif (header.sh_addralign != (unsigned) -1)\n'
        '\t{\n'
        '\t\tElf32_Word secAlign = std::min(header.sh_addralign, (Elf32_Word)4);\n'
        '\t\tif (secAlign < 1) secAlign = 1;\n'
        '\t\toutput.alignSize(secAlign);\n'
        '\t\theader.sh_addralign = secAlign;\n'
        '\t}',
    ),
    # One more... make it hardcode alignment of 4 instead
    (
        '\twhile (relocationAddress % section->getAlignment())\n',
        '\twhile (relocationAddress % 4)\n'
    ),
]

def apply_patches(text):
    for old, new in PATCHES:
        if old not in text:
            print(f'WARNING: patch target not found: {old!r}', file=sys.stderr)
            continue
        text = text.replace(old, new, 1)
    return text

def combine_armips(fout_name, armips_path):
    import io
    buf = io.StringIO()
    buf.write(file_header)
    buf.write("/*\n")
    cat_file(buf, os.path.join(armips_path, 'LICENSE.txt'))
    buf.write("*/\n\n")
    for f in file_list:
        buf.write(f"// file: {f}\n")
        cat_file(buf, os.path.join(armips_path, f))
    text = apply_patches(buf.getvalue())
    with open(fout_name, 'w') as fout:
        fout.write(text)

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print('Usage: generate_armips_cpp.py [output_filename] [armips_src_dir]')
        print('Defaults: [output_filename = "armips.cpp"] [armips_src_dir = "./armips"]')
        return
    fout_name = sys.argv[1] if len(sys.argv) > 1 else 'armips.cpp'
    armips_path = sys.argv[2] if len(sys.argv) > 2 else './armips'
    combine_armips(fout_name, os.path.expanduser(armips_path))

main()

