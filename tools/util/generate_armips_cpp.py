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
    # validateOverlap only keys on (fileID, virtualAddress), so dynamic segments
    # (same headersize/RAM window, different physical ROM offset, never resident
    # at the same time) trigger false "areas overlap" warnings. Track the physical
    # position alongside the virtual one and only warn when both actually overlap.
    (
        '\tstruct Usage\n'
        '\t{\n'
        '\t\tint64_t space;\n'
        '\t\tint64_t usage;\n'
        '\t\tbool usesFill;\n'
        '\t\tbool shared;\n'
        '\t};\n',
        '\tstruct Usage\n'
        '\t{\n'
        '\t\tint64_t space;\n'
        '\t\tint64_t usage;\n'
        '\t\tbool usesFill;\n'
        '\t\tbool shared;\n'
        '\t\tint64_t physicalPosition;\n'
        '\t};\n',
    ),
    (
        '\tstatic void setArea(int64_t fileID, int64_t position, int64_t space, int64_t usage, bool usesFill, bool shared);\n',
        '\tstatic void setArea(int64_t fileID, int64_t position, int64_t space, int64_t usage, bool usesFill, bool shared, int64_t physicalPosition);\n',
    ),
    (
        'void Allocations::setArea(int64_t fileID, int64_t position, int64_t space, int64_t usage, bool usesFill, bool shared)\n'
        '{\n'
        '\tKey key{ fileID, position };\n'
        '\tallocations[key] = Usage{ space, usage, usesFill, shared };\n'
        '}\n',
        'void Allocations::setArea(int64_t fileID, int64_t position, int64_t space, int64_t usage, bool usesFill, bool shared, int64_t physicalPosition)\n'
        '{\n'
        '\tKey key{ fileID, position };\n'
        '\tallocations[key] = Usage{ space, usage, usesFill, shared, physicalPosition };\n'
        '}\n',
    ),
    (
        'void Allocations::validateOverlap()\n'
        '{\n'
        '\t// An easy mistake to make is a "subarea" where the parent area fills, and erases the subarea.\n'
        '\t// Let\'s detect any sort of area overlap and report a warning.\n'
        '\tKey lastKey{ -1, -1 };\n'
        '\tint64_t lastEndPosition = -1;\n'
        '\tUsage lastUsage{};\n'
        '\n'
        '\tfor (auto it : allocations) {\n'
        '\t\tif (it.first.fileID == lastKey.fileID && it.first.position > lastKey.position && it.first.position < lastEndPosition) {\n'
        '\t\t\t// First, the obvious: does the content overlap?\n'
        '\t\t\tif (it.first.position < lastKey.position + lastUsage.usage)\n'
        '\t\t\t\tLogger::queueError(Logger::Warning, "Content of areas %08llX and %08llx overlap", lastKey.position, it.first.position);\n'
        '\t\t\t// Next question, does the earlier one fill?\n'
        '\t\t\telse if (it.second.usesFill && lastUsage.usesFill)\n'
        '\t\t\t\tLogger::queueError(Logger::Warning, "Areas %08llX and %08llx overlap and both fill", lastKey.position, it.first.position);\n'
        '\n'
        '\t\t\t// If the new area ends before the last, keep it as the last.\n'
        '\t\t\tif (lastEndPosition > it.first.position + it.second.space) {\n'
        '\t\t\t\t// But update the usage to the max position.\n'
        '\t\t\t\tint64_t newUsageEnd = it.first.position + it.second.usage + getSubAreaUsage(it.first);\n'
        '\t\t\t\tlastUsage.usage = newUsageEnd - lastKey.position;\n'
        '\t\t\t\tcontinue;\n'
        '\t\t\t}\n'
        '\t\t}\n'
        '\n'
        '\t\tlastKey = it.first;\n'
        '\t\tlastUsage = it.second;\n'
        '\t\tlastUsage.usage += getSubAreaUsage(lastKey);\n'
        '\t\tlastEndPosition = it.first.position + it.second.space;\n'
        '\t}\n'
        '}\n',
        'void Allocations::validateOverlap()\n'
        '{\n'
        '\t// An easy mistake to make is a "subarea" where the parent area fills, and erases the subarea.\n'
        '\t// Let\'s detect any sort of area overlap and report a warning.\n'
        '\t// Areas can share virtual (RAM) address space on purpose. Dynamic/overlay\n'
        '\t// segments reuse the same headersize/RAM window at different physical ROM\n'
        '\t// offsets and are never resident at the same time. Only warn if the physical\n'
        '\t// byte ranges actually collide.\n'
        '\tKey lastKey{ -1, -1 };\n'
        '\tint64_t lastEndPosition = -1;\n'
        '\tUsage lastUsage{};\n'
        '\n'
        '\tfor (auto it : allocations) {\n'
        '\t\tif (it.first.fileID == lastKey.fileID && it.first.position > lastKey.position && it.first.position < lastEndPosition) {\n'
        '\t\t\tint64_t lastPhysEnd = lastUsage.physicalPosition + lastUsage.usage;\n'
        '\t\t\tint64_t newPhysEnd = it.second.physicalPosition + it.second.usage;\n'
        '\t\t\tbool physicalOverlap = it.second.physicalPosition < lastPhysEnd && lastUsage.physicalPosition < newPhysEnd;\n'
        '\n'
        '\t\t\tif (physicalOverlap) {\n'
        '\t\t\t\t// First, the obvious: does the content overlap?\n'
        '\t\t\t\tif (it.first.position < lastKey.position + lastUsage.usage)\n'
        '\t\t\t\t\tLogger::queueError(Logger::Warning, "Content of areas %08llX and %08llx overlap", lastKey.position, it.first.position);\n'
        '\t\t\t\t// Next question, does the earlier one fill?\n'
        '\t\t\t\telse if (it.second.usesFill && lastUsage.usesFill)\n'
        '\t\t\t\t\tLogger::queueError(Logger::Warning, "Areas %08llX and %08llx overlap and both fill", lastKey.position, it.first.position);\n'
        '\t\t\t}\n'
        '\n'
        '\t\t\t// If the new area ends before the last, keep it as the last.\n'
        '\t\t\tif (lastEndPosition > it.first.position + it.second.space) {\n'
        '\t\t\t\t// But update the usage to the max position.\n'
        '\t\t\t\tint64_t newUsageEnd = it.first.position + it.second.usage + getSubAreaUsage(it.first);\n'
        '\t\t\t\tlastUsage.usage = newUsageEnd - lastKey.position;\n'
        '\t\t\t\tcontinue;\n'
        '\t\t\t}\n'
        '\t\t}\n'
        '\n'
        '\t\tlastKey = it.first;\n'
        '\t\tlastUsage = it.second;\n'
        '\t\tlastUsage.usage += getSubAreaUsage(lastKey);\n'
        '\t\tlastEndPosition = it.first.position + it.second.space;\n'
        '\t}\n'
        '}\n',
    ),
    (
        'private:\n'
        '\tbool shared;\n'
        '\tint64_t position = 0;\n'
        '\tExpression sizeExpression;\n'
        '\tint64_t areaSize = 0;\n'
        '\tint64_t contentSize = 0;\n'
        '\tExpression fillExpression;\n'
        '\tint8_t fillValue = 0;\n'
        '\tint64_t fileID = 0;\n'
        '\tExpression positionExpression;\n'
        '\tstd::unique_ptr<CAssemblerCommand> content;\n'
        '};\n',
        'private:\n'
        '\tbool shared;\n'
        '\tint64_t position = 0;\n'
        '\tint64_t physicalPosition = 0;\n'
        '\tExpression sizeExpression;\n'
        '\tint64_t areaSize = 0;\n'
        '\tint64_t contentSize = 0;\n'
        '\tExpression fillExpression;\n'
        '\tint8_t fillValue = 0;\n'
        '\tint64_t fileID = 0;\n'
        '\tExpression positionExpression;\n'
        '\tstd::unique_ptr<CAssemblerCommand> content;\n'
        '};\n',
    ),
    (
        '\tif (positionExpression.isLoaded())\n'
        '\t{\n'
        '\t\tif (!positionExpression.evaluateInteger(position))\n'
        '\t\t{\n'
        '\t\t\tLogger::queueError(Logger::Error, "Invalid position expression");\n'
        '\t\t\treturn false;\n'
        '\t\t}\n'
        '\t\tArchitecture::current().NextSection();\n'
        '\t\tg_fileManager->seekVirtual(position);\n'
        '\t}\n'
        '\telse\n'
        '\t\tposition = g_fileManager->getVirtualAddress();\n',
        '\tif (positionExpression.isLoaded())\n'
        '\t{\n'
        '\t\tif (!positionExpression.evaluateInteger(position))\n'
        '\t\t{\n'
        '\t\t\tLogger::queueError(Logger::Error, "Invalid position expression");\n'
        '\t\t\treturn false;\n'
        '\t\t}\n'
        '\t\tArchitecture::current().NextSection();\n'
        '\t\tg_fileManager->seekVirtual(position);\n'
        '\t}\n'
        '\telse\n'
        '\t\tposition = g_fileManager->getVirtualAddress();\n'
        '\tphysicalPosition = g_fileManager->getPhysicalAddress();\n',
    ),
    (
        'void Allocations::collectAreaStats(AllocationStats &stats)\n'
        '{\n'
        '\t// Need to work out overlaps.\n'
        '\tKey lastKey{ -1, -1 };\n'
        '\tint64_t lastEndPosition = -1;\n'
        '\tUsage lastUsage{};\n'
        '\n'
        '\tauto applyUsage = [&stats](int64_t position, const Usage &usage)\n'
        '\t{\n'
        '\t\tif (usage.space > stats.largestSize)\n'
        '\t\t{\n'
        '\t\t\tstats.largestPosition = position;\n'
        '\t\t\tstats.largestSize = usage.space;\n'
        '\t\t\tstats.largestUsage = usage.usage;\n'
        '\t\t}\n'
        '\n'
        '\t\tif (usage.space - usage.usage > stats.largestFreeSize - stats.largestFreeUsage)\n'
        '\t\t{\n'
        '\t\t\tstats.largestFreePosition = position;\n'
        '\t\t\tstats.largestFreeSize = usage.space;\n'
        '\t\t\tstats.largestFreeUsage = usage.usage;\n'
        '\t\t}\n'
        '\n'
        '\t\t// We assume overlaps agree on sharing, hopefully...\n'
        '\t\tif (usage.shared && usage.space - usage.usage > stats.sharedFreeSize - stats.sharedFreeUsage)\n'
        '\t\t{\n'
        '\t\t\tstats.sharedFreePosition = position;\n'
        '\t\t\tstats.sharedFreeSize = usage.space;\n'
        '\t\t\tstats.sharedFreeUsage = usage.usage;\n'
        '\t\t}\n'
        '\n'
        '\t\tstats.totalSize += usage.space;\n'
        '\t\tstats.totalUsage += usage.usage;\n'
        '\t\tif (usage.shared)\n'
        '\t\t{\n'
        '\t\t\tstats.sharedSize += usage.space;\n'
        '\t\t\tstats.sharedUsage += usage.usage;\n'
        '\t\t}\n'
        '\t};\n'
        '\n'
        '\tfor (auto it : allocations)\n'
        '\t{\n'
        '\t\tif (it.first.fileID == lastKey.fileID && it.first.position > lastKey.position && it.first.position < lastEndPosition)\n'
        '\t\t{\n'
        '\t\t\t// Overlap, merge.\n'
        '\t\t\tint64_t lastUsageEnd = lastKey.position + lastUsage.usage;\n'
        '\t\t\tint64_t newUsageEnd = it.first.position + it.second.usage + getSubAreaUsage(it.first);\n'
        '\n'
        '\t\t\tif (lastUsageEnd >= it.first.position)\n'
        '\t\t\t\tlastUsage.usage += newUsageEnd - lastUsageEnd;\n'
        '\t\t\telse\n'
        '\t\t\t\tlastUsage.usage += it.second.usage + getSubAreaUsage(it.first);\n'
        '\n'
        '\t\t\tlastEndPosition = it.first.position + it.second.space;\n'
        '\t\t\tlastUsage.space = lastEndPosition - lastKey.position;\n'
        '\n'
        '\t\t\tcontinue;\n'
        '\t\t}\n'
        '\n'
        '\t\tif (lastKey.position != -1)\n'
        '\t\t\tapplyUsage(lastKey.position, lastUsage);\n'
        '\n'
        '\t\tlastKey = it.first;\n'
        '\t\tlastUsage = it.second;\n'
        '\t\tlastUsage.usage += getSubAreaUsage(lastKey);\n'
        '\t\tlastEndPosition = it.first.position + it.second.space;\n'
        '\t}\n'
        '\n'
        '\tif (lastKey.position != -1)\n'
        '\t\tapplyUsage(lastKey.position, lastUsage);\n'
        '}\n',
        'void Allocations::collectAreaStats(AllocationStats &stats)\n'
        '{\n'
        '\t// Need to work out overlaps.\n'
        '\tKey lastKey{ -1, -1 };\n'
        '\tint64_t lastEndPosition = -1;\n'
        '\tUsage lastUsage{};\n'
        '\n'
        '\tauto applyUsage = [&stats](int64_t position, const Usage &usage)\n'
        '\t{\n'
        '\t\tif (usage.space > stats.largestSize)\n'
        '\t\t{\n'
        '\t\t\tstats.largestPosition = position;\n'
        '\t\t\tstats.largestSize = usage.space;\n'
        '\t\t\tstats.largestUsage = usage.usage;\n'
        '\t\t}\n'
        '\n'
        '\t\tif (usage.space - usage.usage > stats.largestFreeSize - stats.largestFreeUsage)\n'
        '\t\t{\n'
        '\t\t\tstats.largestFreePosition = position;\n'
        '\t\t\tstats.largestFreeSize = usage.space;\n'
        '\t\t\tstats.largestFreeUsage = usage.usage;\n'
        '\t\t}\n'
        '\n'
        '\t\t// We assume overlaps agree on sharing, hopefully...\n'
        '\t\tif (usage.shared && usage.space - usage.usage > stats.sharedFreeSize - stats.sharedFreeUsage)\n'
        '\t\t{\n'
        '\t\t\tstats.sharedFreePosition = position;\n'
        '\t\t\tstats.sharedFreeSize = usage.space;\n'
        '\t\t\tstats.sharedFreeUsage = usage.usage;\n'
        '\t\t}\n'
        '\n'
        '\t\tstats.totalSize += usage.space;\n'
        '\t\tstats.totalUsage += usage.usage;\n'
        '\t\tif (usage.shared)\n'
        '\t\t{\n'
        '\t\t\tstats.sharedSize += usage.space;\n'
        '\t\t\tstats.sharedUsage += usage.usage;\n'
        '\t\t}\n'
        '\t};\n'
        '\n'
        '\tfor (auto it : allocations)\n'
        '\t{\n'
        '\t\tbool virtualOverlap = it.first.fileID == lastKey.fileID && it.first.position > lastKey.position && it.first.position < lastEndPosition;\n'
        '\t\tbool physicalOverlap = false;\n'
        '\t\tif (virtualOverlap)\n'
        '\t\t{\n'
        '\t\t\tint64_t lastPhysEnd = lastUsage.physicalPosition + lastUsage.usage;\n'
        '\t\t\tint64_t newPhysEnd = it.second.physicalPosition + it.second.usage;\n'
        '\t\t\tphysicalOverlap = it.second.physicalPosition < lastPhysEnd && lastUsage.physicalPosition < newPhysEnd;\n'
        '\t\t}\n'
        '\n'
        '\t\t// Only merge dynamic/overlay areas that share RAM space if they also share\n'
        '\t\t// physical ROM bytes, otherwise they are independent areas for stats purposes.\n'
        '\t\tif (virtualOverlap && physicalOverlap)\n'
        '\t\t{\n'
        '\t\t\t// Overlap, merge.\n'
        '\t\t\tint64_t lastUsageEnd = lastKey.position + lastUsage.usage;\n'
        '\t\t\tint64_t newUsageEnd = it.first.position + it.second.usage + getSubAreaUsage(it.first);\n'
        '\n'
        '\t\t\tif (lastUsageEnd >= it.first.position)\n'
        '\t\t\t\tlastUsage.usage += newUsageEnd - lastUsageEnd;\n'
        '\t\t\telse\n'
        '\t\t\t\tlastUsage.usage += it.second.usage + getSubAreaUsage(it.first);\n'
        '\n'
        '\t\t\tlastEndPosition = it.first.position + it.second.space;\n'
        '\t\t\tlastUsage.space = lastEndPosition - lastKey.position;\n'
        '\n'
        '\t\t\tcontinue;\n'
        '\t\t}\n'
        '\n'
        '\t\tif (lastKey.position != -1)\n'
        '\t\t\tapplyUsage(lastKey.position, lastUsage);\n'
        '\n'
        '\t\tlastKey = it.first;\n'
        '\t\tlastUsage = it.second;\n'
        '\t\tlastUsage.usage += getSubAreaUsage(lastKey);\n'
        '\t\tlastEndPosition = it.first.position + it.second.space;\n'
        '\t}\n'
        '\n'
        '\tif (lastKey.position != -1)\n'
        '\t\tapplyUsage(lastKey.position, lastUsage);\n'
        '}\n',
    ),
    # * Update the function call for setArea
    (
        '\tif (areaSize != 0)\n'
        '\t\tAllocations::setArea(fileID, position, areaSize, contentSize, fillExpression.isLoaded(), shared);\n',
        '\tif (areaSize != 0)\n'
        '\t\tAllocations::setArea(fileID, position, areaSize, contentSize, fillExpression.isLoaded(), shared, physicalPosition);\n',
    ),

    # Force 4-byte alignment on .importobj injection for N64 ROMs,
    # and update p_align in the segment header to match:
    (
        '\t// align segment to alignment of first section\n'
        '\tint align = std::max<int>(sections[0]->getAlignment(),16);\n'
        '\toutput.alignSize(align);',
        '\t// align segment to 4 bytes for N64 ROM injection\n'
        '\toutput.alignSize(4);\n'
        '\theader.p_align = 4;',
    ),
    # * Also clamp each section's sh_addralign to 4, otherwise sections
    #   with sh_addralign=16 will still pad to 16 when written.
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
    # * One more... make it hardcode alignment of 4 instead
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
