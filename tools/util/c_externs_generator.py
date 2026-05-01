#!/usr/bin/env python3
"""
c_externs_generator.py
----------------------
Scans C source files for:
  - static functions
  - static variables
  - struct definitions   (from .c files only, unless --include-h-types)
  - enum definitions     (from .c files only, unless --include-h-types)
  - union definitions    (from .c files only, unless --include-h-types)
  - typedef declarations (from .c files only, unless --include-h-types)

...and generates a header with extern declarations and type forwarding.
Every declaration is annotated with the FULL path of the file it came from.

Usage:
    python c_externs_generator.py [options] <path> [<path> ...]

Examples:
    python c_externs_generator.py src/main.c
    python c_externs_generator.py --recursive ./src
    python c_externs_generator.py -r ./src -o generated_externs.h
    python c_externs_generator.py -r ./src --dry-run
    python c_externs_generator.py -r ./src -v
    python c_externs_generator.py -r ./src --extensions .c --exclude "*_test.c"
"""

import argparse
import fnmatch
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CSymbol:
    kind: str               # 'function' | 'variable' | 'struct' | 'enum'
                            # | 'union' | 'typedef'
    name: str               # symbol / tag name
    return_type: str        # type string (functions/variables); type for types
    params: str             # parameter list string (functions only)
    source_file: str        # FULL absolute path of the originating file
    source_line: int        # 1-based line number
    comment: Optional[str]  # comment sitting directly above the declaration
    is_static: bool = False
    is_inline: bool = False
    is_const: bool = False
    is_pointer: bool = False
    body: str = ''          # raw body text for structs / enums / unions
    already_in_header: bool = False   # True if a matching decl was found in the .h


# ---------------------------------------------------------------------------
# Comment helpers
# ---------------------------------------------------------------------------

BLOCK_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


def _strip_comments_copy(source: str) -> str:
    """Replace comment text with spaces, preserving positions/line numbers."""
    result = list(source)
    i = 0
    while i < len(source):
        if source[i:i+2] == '/*':
            j = source.find('*/', i + 2)
            if j == -1:
                j = len(source) - 2
            for k in range(i, j + 2):
                if source[k] != '\n':
                    result[k] = ' '
            i = j + 2
        elif source[i:i+2] == '//':
            j = source.find('\n', i + 2)
            if j == -1:
                j = len(source)
            for k in range(i, j):
                result[k] = ' '
            i = j
        elif source[i] == '"':
            i += 1
            while i < len(source) and source[i] != '"':
                if source[i] == '\\':
                    i += 1
                i += 1
            i += 1
        else:
            i += 1
    return ''.join(result)


def _extract_comment_before(source: str, pos: int) -> Optional[str]:
    """Return the block or line comment immediately preceding position pos."""
    preceding = source[:pos]

    block_matches = list(BLOCK_COMMENT_RE.finditer(preceding))
    if block_matches:
        last = block_matches[-1]
        if not preceding[last.end():].strip():
            return last.group(0).strip()

    comment_lines = []
    for line in reversed(preceding.splitlines()):
        s = line.strip()
        if s.startswith('//'):
            comment_lines.insert(0, s)
        elif s == '':
            continue
        else:
            break
    if comment_lines:
        return '\n'.join(comment_lines)

    return None


def _line_number(source: str, pos: int) -> int:
    return source[:pos].count('\n') + 1

def _is_global_position(source: str, pos: int) -> bool:
    before = source[:pos]
    return before.count('{') == before.count('}')


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------

_PRIMITIVES = (
    r'(?:unsigned\s+|signed\s+|long\s+|short\s+)*'
    r'(?:int|char|float|double|long|short|void|bool|'
    r'uint8_t|uint16_t|uint32_t|uint64_t|'
    r'int8_t|int16_t|int32_t|int64_t|'
    r'size_t|ssize_t|ptrdiff_t|uintptr_t|intptr_t|'
    r'[A-Za-z_][A-Za-z0-9_]*)'
)


def _normalize_type(type_str: str,
                    ptr: Optional[str],
                    const: Optional[str]) -> tuple:
    parts = []
    if const:
        parts.append('const')
    parts.append(type_str.strip())
    is_ptr = bool(ptr and ptr.strip())
    full = (' '.join(parts) + ptr.rstrip()) if is_ptr else ' '.join(parts)
    return full.strip(), is_ptr


def _clean_params(raw: str) -> str:
    return re.sub(r'\s+', ' ', raw.strip())


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

STATIC_FUNC_RE = re.compile(
    r'^[ \t]*static\s+'
    r'(?P<inline>inline\s+)?'
    r'(?P<const>const\s+)?'
    r'(?P<ret>' + _PRIMITIVES + r')'
    r'(?P<ptr>\s*\*+)?'
    r'\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'\s*\((?P<params>[^)]*)\)'
    r'\s*(?:\{|;)',
    re.MULTILINE,
)

STATIC_VAR_RE = re.compile(
    r'^[ \t]*static\s+'
    r'(?P<const>const\s+)?'
    r'(?P<type>' + _PRIMITIVES + r')'
    r'(?P<ptr>\s*\*+)?'
    r'\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'(?P<array>(\s*\[[^\]]*\])*)'
    r'\s*(?:=[^;]*)?\s*;',
    re.MULTILINE,
)

NONSTATIC_FUNC_RE = re.compile(
    r'^[ \t]*'
    r'(?!(?:static)\b)'
    r'(?P<inline>inline\s+)?'
    r'(?P<const>const\s+)?'
    r'(?P<ret>' + _PRIMITIVES + r')'
    r'(?P<ptr>\s*\*+)?'
    r'\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'\s*\((?P<params>[^)]*)\)'
    r'\s*\{',
    re.MULTILINE,
)

NONSTATIC_VAR_RE = re.compile(
    r'^[ \t]*'
    r'(?!(?:static)\b)'
    r'(?P<const>const\s+)?'
    r'(?P<type>' + _PRIMITIVES + r')'
    r'(?P<ptr>\s*\*+)?'
    r'\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'(?P<array>(\s*\[[^\]]*\])*)'
    r'\s*(?:=[^;]*)?\s*;',
    re.MULTILINE,
)

STRUCT_RE = re.compile(
    r'^(?:typedef\s+)?(?P<kw>struct|union)'
    r'(?:\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*))?'
    r'\s*\{',
    re.MULTILINE,
)

ENUM_RE = re.compile(
    r'^(?:typedef\s+)?enum\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'\s*\{',
    re.MULTILINE,
)

TYPEDEF_RE = re.compile(
    r'^typedef\s+'
    r'(?!struct\b)(?!enum\b)(?!union\b)'
    r'(?P<type>' + _PRIMITIVES + r')'
    r'(?P<ptr>\s*\*+)?'
    r'\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;',
    re.MULTILINE,
)

TYPEDEF_FUNC_PTR_RE = re.compile(
    r'^typedef\s+'
    r'(?P<ret>' + _PRIMITIVES + r')'
    r'\s*\(\s*\*\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\)'
    r'\s*\((?P<params>[^)]*)\)\s*;',
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Brace body extractor
# ---------------------------------------------------------------------------

def _extract_brace_body(source: str, open_brace_pos: int) -> str:
    depth = 0
    i = open_brace_pos
    while i < len(source):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[open_brace_pos: i + 1]
        i += 1
    return source[open_brace_pos:]



# ---------------------------------------------------------------------------
# Header cross-checker (FIXED)
# ---------------------------------------------------------------------------

def _split_statements(text: str):
    """
    Split header into ';'-terminated statements.
    This avoids multi-line prototype issues.
    """
    buf = []
    cur = []

    for line in text.splitlines():
        # strip preprocessor lines completely
        if line.strip().startswith('#'):
            continue

        cur.append(line)
        if ';' in line:
            stmt = ' '.join(cur)
            buf.append(stmt)
            cur = []

    return buf


def _extract_func_name(stmt: str) -> Optional[str]:
    """
    Extract function name from a statement like:
        int foo(int a);
    Rejects macros, function pointers, etc.
    """
    stmt = stmt.strip()

    if '(' not in stmt or ')' not in stmt:
        return None

    if '{' in stmt:
        return None  # definition, not prototype

    if stmt.startswith('typedef'):
        return None

    if '(*' in stmt:
        return None  # function pointer typedef

    if stmt.startswith('static'):
        return None  # ignore static/internal

    # get token before '('
    left = stmt.split('(')[0].strip()
    tokens = left.split()

    if not tokens:
        return None

    name = tokens[-1]

    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
        return None

    return name


def _parse_header_names(h_path: str) -> dict:
    """
    MUCH more reliable header parsing.
    """
    try:
        with open(h_path, encoding='utf-8', errors='replace') as fh:
            raw = fh.read()
    except OSError:
        return {}

    stripped = _strip_comments_copy(raw)

    statements = _split_statements(stripped)

    functions = set()
    variables = set()
    typedefs = set()
    structs = set()
    enums = set()

    for stmt in statements:
        s = stmt.strip()

        # --- FUNCTION ---
        name = _extract_func_name(s)
        if name:
            functions.add(name)
            continue

        # --- TYPEDEF ---
        if s.startswith('typedef'):
            m = re.search(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*;', s)
            if m:
                typedefs.add(m.group(1))
            continue

        # --- STRUCT / UNION ---
        m = re.search(r'\b(struct|union)\s+([A-Za-z_][A-Za-z0-9_]*)', s)
        if m:
            structs.add(m.group(2))

        # --- ENUM ---
        m = re.search(r'\benum\s+([A-Za-z_][A-Za-z0-9_]*)', s)
        if m:
            enums.add(m.group(1))

        # --- VARIABLE (extern only) ---
        if s.startswith('extern'):
            m = re.search(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*(\[.*\])?\s*;', s)
            if m:
                variables.add(m.group(1))

    return {
        'functions': functions,
        'variables': variables,
        'structs': structs,
        'enums': enums,
        'typedefs': typedefs,
    }


def _mark_already_in_header(symbols: list, h_names: dict) -> None:
    """
    Strict, name-based but CLEAN matching.
    """
    kind_map = {
        'function': 'functions',
        'variable': 'variables',
        'struct':   'structs',
        'union':    'structs',
        'enum':     'enums',
        'typedef':  'typedefs',
    }

    for sym in symbols:
        bucket = kind_map.get(sym.kind)
        if not bucket:
            continue

        if sym.name in h_names.get(bucket, set()):
            sym.already_in_header = True

def _find_header_for(c_path: str) -> Optional[str]:
    """
    Given /abs/path/to/foo.c, return /abs/path/to/foo.h if it exists,
    else None.
    """
    base = os.path.splitext(c_path)[0]
    h = base + '.h'
    return h if os.path.isfile(h) else None

# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def scan_file(filepath: str, include_h_types: bool = False) -> list:
    abs_path = os.path.abspath(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    is_c_file = (ext == '.c')
    scan_types = is_c_file or include_h_types

    try:
        with open(abs_path, encoding='utf-8', errors='replace') as fh:
            source = fh.read()
    except OSError as exc:
        raise RuntimeError(f"Cannot read {abs_path}: {exc}") from exc

    stripped = _strip_comments_copy(source)
    symbols = []
    seen = set()

    def _add(sym):
        key = (sym.kind, sym.name)
        if key not in seen:
            seen.add(key)
            symbols.append(sym)

    # 1. Static functions
    for m in STATIC_FUNC_RE.finditer(stripped):
        name = m.group('name')
        ret_type, is_ptr = _normalize_type(
            m.group('ret'), m.group('ptr'), m.group('const'))
        _add(CSymbol(
            kind='function',
            name=name,
            return_type=ret_type,
            params=_clean_params(m.group('params')),
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            is_static=True,
            is_inline=bool(m.group('inline')),
            is_pointer=is_ptr,
        ))

    # --- NON-STATIC FUNCTIONS ---
    for m in NONSTATIC_FUNC_RE.finditer(stripped):
        if not _is_global_position(source, m.start()):
            continue

        name = m.group('name')

        if any(s.name == name and s.kind == 'function' for s in symbols):
            continue

        ret_type, is_ptr = _normalize_type(
            m.group('ret'), m.group('ptr'), m.group('const'))

        _add(CSymbol(
            kind='function',
            name=name,
            return_type=ret_type,
            params=_clean_params(m.group('params')),
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            is_static=False,
            is_inline=bool(m.group('inline')),
            is_pointer=is_ptr,
        ))

    # 2. Static variables
    for m in STATIC_VAR_RE.finditer(stripped):
        name = m.group('name')
        if any(s.name == name and s.kind == 'function' for s in symbols):
            continue
        var_type, is_ptr = _normalize_type(
            m.group('type'), m.group('ptr'), m.group('const'))
        array_suffix = m.group('array') or ''
        var_type = var_type + array_suffix
        _add(CSymbol(
            kind='variable',
            name=name,
            return_type=var_type,
            params='',
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            is_static=True,
            is_const='const' in var_type,
            is_pointer=is_ptr,
        ))

    # --- NON-STATIC VARIABLES ---
    for m in NONSTATIC_VAR_RE.finditer(stripped):
        if not _is_global_position(source, m.start()):
            continue

        name = m.group('name')

        if any(s.name == name and s.kind == 'function' for s in symbols):
            continue

        if any(s.name == name and s.kind == 'variable' for s in symbols):
            continue

        var_type, is_ptr = _normalize_type(
            m.group('type'), m.group('ptr'), m.group('const'))

        array_suffix = m.group('array') or ''
        var_type = var_type + array_suffix

        _add(CSymbol(
            kind='variable',
            name=name,
            return_type=var_type,
            params='',
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            is_static=False,
            is_const='const' in var_type,
            is_pointer=is_ptr,
        ))

    if not scan_types:
        symbols.sort(key=lambda s: s.source_line)
        return symbols

    # 3. Structs and unions
    for m in STRUCT_RE.finditer(stripped):
        kw   = m.group('kw')
        name = m.group('name')
        if not name:
            # find name after closing brace
            brace_pos = source.find('{', m.start())
            body = _extract_brace_body(source, brace_pos)
            end_pos = brace_pos + len(body)
            rest = source[end_pos:]

            name_match = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)', rest)
            if name_match:
                name = name_match.group(1)
            else:
                continue
        brace_pos = source.find('{', m.start())
        body = _extract_brace_body(source, brace_pos) if brace_pos != -1 else '{}'
        _add(CSymbol(
            kind=kw,
            name=name,
            return_type=f'{kw} {name}' if m.group('name') else kw,
            params='',
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            body=body,
        ))

    # 4. Enums
    for m in ENUM_RE.finditer(stripped):
        name = m.group('name')
        brace_pos = source.find('{', m.start())
        body = _extract_brace_body(source, brace_pos) if brace_pos != -1 else '{}'
        _add(CSymbol(
            kind='enum',
            name=name,
            return_type=f'enum {name}',
            params='',
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            body=body,
        ))

    # 5. Typedefs (scalar / pointer aliases only)
    for m in TYPEDEF_RE.finditer(stripped):
        name = m.group('name')
        base_type, is_ptr = _normalize_type(m.group('type'), m.group('ptr'), None)
        _add(CSymbol(
            kind='typedef',
            name=name,
            return_type=base_type,
            params='',
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            is_pointer=is_ptr,
        ))

    # 6. Typedef function pointers
    for m in TYPEDEF_FUNC_PTR_RE.finditer(stripped):
        ret_type = m.group('ret')
        name = m.group('name')
        params = _clean_params(m.group('params'))

        _add(CSymbol(
            kind='typedef',
            name=name,
            return_type=ret_type,
            params=params,
            source_file=abs_path,
            source_line=_line_number(source, m.start()),
            comment=_extract_comment_before(source, m.start()),
            is_pointer=True,
        ))

    symbols.sort(key=lambda s: s.source_line)

    # Cross-check against the corresponding .h file (only for .c files)
    if is_c_file:
        h_path = _find_header_for(abs_path)
        if h_path:
            h_names = _parse_header_names(h_path)
            _mark_already_in_header(symbols, h_names)

    return symbols


# ---------------------------------------------------------------------------
# ScanResult + directory scanner
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    symbols: list = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    errors: list = field(default_factory=list)


def scan_paths(
    paths: list,
    recursive: bool = False,
    include_patterns: list = None,
    exclude_patterns: list = None,
    extensions: list = None,
    include_h_types: bool = False,
    verbose: bool = False,
) -> ScanResult:
    if extensions is None:
        extensions = ['.c', '.h']
    if include_patterns is None:
        include_patterns = []
    if exclude_patterns is None:
        exclude_patterns = []

    result = ScanResult()

    def _should_include(fp: str) -> bool:
        filename = os.path.basename(fp)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in extensions:
            return False
        if include_patterns and not any(
                fnmatch.fnmatch(filename, p) for p in include_patterns):
            return False
        if any(fnmatch.fnmatch(filename, p) for p in exclude_patterns):
            return False
        return True

    def _process(fp: str):
        if not _should_include(fp):
            result.files_skipped += 1
            return
        if verbose:
            print(f"  [scan] {fp}", file=sys.stderr)
        try:
            syms = scan_file(fp, include_h_types=include_h_types)
            result.symbols.extend(syms)
            result.files_scanned += 1
            if verbose:
                for s in syms:
                    print(f"         [{s.kind:<8}] {s.name}  "
                          f"(line {s.source_line})", file=sys.stderr)
        except RuntimeError as exc:
            result.errors.append(str(exc))
            result.files_skipped += 1

    for raw in paths:
        path = os.path.abspath(raw)
        if os.path.isfile(path):
            _process(path)
        elif os.path.isdir(path):
            if recursive:
                for dirpath, dirnames, filenames in os.walk(path):
                    dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                    for fn in sorted(filenames):
                        _process(os.path.join(dirpath, fn))
            else:
                for fn in sorted(os.listdir(path)):
                    fp = os.path.join(path, fn)
                    if os.path.isfile(fp):
                        _process(fp)
        else:
            result.errors.append(f"Path not found: {raw}")

    return result


# ---------------------------------------------------------------------------
# Extern / header generator
# ---------------------------------------------------------------------------

def _emit_type_block(sym, include_body: bool,
                     include_original_comments: bool) -> list:
    lines = []
    if include_original_comments and sym.comment:
        for cl in sym.comment.splitlines():
            lines.append(cl)

    lines.append(f'/* Generated from: {sym.source_file}:{sym.source_line} */')

    if sym.kind in ('struct', 'union'):
        if include_body and sym.body:
            # Anonymous struct/union: return_type is just the keyword (e.g. 'struct')
            # Named struct/union: return_type is 'struct Foo' — emit typedef with same name
            lines.append(f'typedef {sym.kind} {sym.name} {sym.body} {sym.name};')
        else:
            lines.append(f'{sym.kind} {sym.name};')

    elif sym.kind == 'enum':
        if include_body and sym.body:
            lines.append(f'typedef enum {sym.name} {sym.body} {sym.name};')
        else:
            lines.append(f'enum {sym.name};')

    elif sym.kind == 'typedef':
        if sym.is_pointer and sym.params:
            lines.append(
                f'typedef {sym.return_type} (*{sym.name})({sym.params});')
        else:
            ptr = '*' if sym.is_pointer else ''
            lines.append(f'typedef {sym.return_type} {ptr}{sym.name};')

    return lines


def generate_externs(
    result: ScanResult,
    guard_name: str = 'GENERATED_EXTERNS_H',
    group_by_file: bool = False,
    include_source_comments: bool = True,
    include_original_comments: bool = True,
    include_type_bodies: bool = True,
) -> str:
    lines = []

    lines += [
        f'#ifndef {guard_name}',
        f'#define {guard_name}',
        '',
        '/*',
        ' * Auto-generated extern declarations.',
        ' * Generated by c_externs_generator.py',
        f' * Files scanned : {result.files_scanned}',
        f' * Symbols found : {len(result.symbols)}',
        ' *',
        ' * DO NOT EDIT — regenerate with c_externs_generator.py',
        ' */',
        '',
    ]

    type_kinds   = {'struct', 'union', 'enum', 'typedef'}
    extern_kinds = {'function', 'variable'}

    type_syms   = [s for s in result.symbols if s.kind in type_kinds]
    extern_syms = [s for s in result.symbols if s.kind in extern_kinds]

    # ---- Section 1: Type definitions ----------------------------------------
    if type_syms:
        lines += [
            '/* ================================================================',
            ' * Type definitions (extracted from .c files)',
            ' * ================================================================',
            ' */',
            '',
        ]

        if group_by_file:
            by_file = defaultdict(list)
            for sym in type_syms:
                by_file[sym.source_file].append(sym)
            grouped = sorted(by_file.items())
        else:
            grouped = [('', type_syms)]

        for file_label, syms in grouped:
            if group_by_file and file_label:
                lines += [f'/* --- {file_label} --- */', '']
            for sym in syms:
                lines += _emit_type_block(sym, include_type_bodies,
                                          include_original_comments)
                lines.append('')

    # ---- Section 2: Extern declarations -------------------------------------
    if extern_syms:
        lines += [
            '/* ================================================================',
            ' * Extern declarations',
            ' * ================================================================',
            ' */',
            '',
        ]

        if group_by_file:
            by_file2 = defaultdict(list)
            for sym in extern_syms:
                by_file2[sym.source_file].append(sym)
            grouped2 = sorted(by_file2.items())
        else:
            grouped2 = [('', extern_syms)]

        for file_label, syms in grouped2:
            if group_by_file and file_label:
                lines += [f'/* --- {file_label} --- */', '']
            for sym in syms:
                if include_original_comments and sym.comment:
                    for cl in sym.comment.splitlines():
                        lines.append(cl)
                if include_source_comments:
                    lines.append(
                        f'/* Generated from: {sym.source_file}:{sym.source_line} */')
                ptr_gap = '' if sym.return_type.endswith('*') else ' '
                if sym.kind == 'function':
                    params = sym.params if sym.params.strip() else 'void'
                    if '[' in sym.return_type:
                        # Array return types are illegal in C; treat as pointer instead
                        base_type = sym.return_type.split('[')[0].strip()
                        lines.append(
                            f'extern {base_type} *{sym.name}({params});')
                    else:
                        lines.append(
                            f'extern {sym.return_type}{ptr_gap}{sym.name}({params});')
                else:
                    if '[' in sym.return_type:
                        base_type = sym.return_type.split('[')[0].strip()
                        array_part = sym.return_type[len(base_type):]
                        lines.append(
                            f'extern {base_type}{ptr_gap}{sym.name}{array_part};')
                    else:
                        lines.append(
                            f'extern {sym.return_type}{ptr_gap}{sym.name};')
                lines.append('')

    lines += [f'#endif /* {guard_name} */', '']
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Alternative output formats
# ---------------------------------------------------------------------------

def _output_json(result: ScanResult) -> str:
    import json
    rows = [{
        'kind': s.kind, 'name': s.name, 'return_type': s.return_type,
        'params': s.params, 'source_file': s.source_file,
        'source_line': s.source_line, 'is_static': s.is_static,
        'is_inline': s.is_inline, 'is_const': s.is_const,
        'is_pointer': s.is_pointer, 'comment': s.comment, 'body': s.body,
    } for s in result.symbols]
    return json.dumps(rows, indent=2)


def _output_csv(result: ScanResult) -> str:
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['kind', 'name', 'return_type', 'params', 'source_file',
                'source_line', 'is_static', 'is_inline', 'is_const', 'is_pointer'])
    for s in result.symbols:
        w.writerow([s.kind, s.name, s.return_type, s.params, s.source_file,
                    s.source_line, s.is_static, s.is_inline, s.is_const, s.is_pointer])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(result: ScanResult, verbose: bool = False):
    kind_order = ['function', 'variable', 'struct', 'union', 'enum', 'typedef']
    counts = defaultdict(int)
    for sym in result.symbols:
        counts[sym.kind] += 1

    print(f"\n{'═' * 58}", file=sys.stderr)
    print(f"  SCAN SUMMARY", file=sys.stderr)
    print(f"{'═' * 58}", file=sys.stderr)
    print(f"  Files scanned  : {result.files_scanned}", file=sys.stderr)
    print(f"  Files skipped  : {result.files_skipped}", file=sys.stderr)
    already = sum(1 for s in result.symbols if s.already_in_header)
    missing = len(result.symbols) - already
    print(f"  Symbols total  : {len(result.symbols)}", file=sys.stderr)
    print(f"  Already in .h  : {already}", file=sys.stderr)
    print(f"  Missing in .h  : {missing}", file=sys.stderr)
    for k in kind_order:
        if counts[k]:
            print(f"    {k:<12} : {counts[k]}", file=sys.stderr)
    if result.errors:
        print(f"\n  ERRORS ({len(result.errors)}):", file=sys.stderr)
        for e in result.errors:
            print(f"    ✗ {e}", file=sys.stderr)
    if verbose and result.symbols:
        print(f"\n  SYMBOLS:", file=sys.stderr)
        for s in result.symbols:
            print(f"    [{s.kind:<8}] {s.name}\n"
                  f"             {s.source_file}:{s.source_line}", file=sys.stderr)
    print(f"{'═' * 58}\n", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='c_externs_generator',
        description=(
            'Scan C files for static functions, variables, structs, enums, '
            'unions, and typedefs — then emit a header with externs and type '
            'forwarding. Every item is annotated with its full source path.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument('paths', nargs='+', metavar='PATH',
                   help='Files or directories to scan.')

    scan = p.add_argument_group('Scanning')
    scan.add_argument('-r', '--recursive', action='store_true',
                      help='Recurse into subdirectories.')
    scan.add_argument('-e', '--extensions', nargs='+', metavar='EXT',
                      help='Extensions to scan (default: .c .h).')
    scan.add_argument('--include', nargs='+', metavar='GLOB', default=[],
                      help='Filename glob whitelist, e.g. "*.c".')
    scan.add_argument('--exclude', nargs='+', metavar='GLOB', default=[],
                      help='Filename glob blacklist, e.g. "*_test.c".')
    scan.add_argument('--include-h-types', action='store_true',
                      help='Also extract structs/enums/unions/typedefs from .h files.')
    scan.add_argument('--functions-only', action='store_true',
                      help='Only emit externs for static functions.')
    scan.add_argument('--variables-only', action='store_true',
                      help='Only emit externs for static variables.')
    scan.add_argument('--include-already-declared', action='store_true',
                      help='Also emit symbols that are already declared/prototyped in the corresponding .h file (default: skip them).')
    scan.add_argument('--no-types', action='store_true',
                      help='Skip all struct/enum/union/typedef output.')

    out = p.add_argument_group('Output')
    out.add_argument('-o', '--output', metavar='FILE',
                     help='Output file (default: <basename>.externs.h).')
    out.add_argument('--dry-run', action='store_true',
                     help='Print to stdout, do not write a file.')
    out.add_argument('--guard', metavar='NAME', default='',
                     help='Header guard macro (default: derived from filename).')
    out.add_argument('--group-by-file', action='store_true',
                     help='Add section headers showing the originating file.')
    out.add_argument('--no-source-comments', action='store_true',
                     help='Omit /* Generated from: … */ comments.')
    out.add_argument('--no-original-comments', action='store_true',
                     help='Omit original comments copied from source.')
    out.add_argument('--no-type-bodies', action='store_true',
                     help='Emit forward declarations only, not full type bodies.')
    out.add_argument('--format', choices=['header', 'json', 'csv'],
                     default='header', help='Output format (default: header).')

    p.add_argument('-v', '--verbose', action='store_true',
                   help='Print every scanned file and symbol to stderr.')
    p.add_argument('--stats-only', action='store_true',
                   help='Print summary only, no output file.')

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    extensions = None
    if args.extensions:
        extensions = [e if e.startswith('.') else f'.{e}' for e in args.extensions]

    result = scan_paths(
        paths=args.paths,
        recursive=args.recursive,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        extensions=extensions,
        include_h_types=args.include_h_types,
        verbose=args.verbose,
    )

    type_kinds = {'struct', 'union', 'enum', 'typedef'}
    # Always filter: only emit symbols not already covered by the corresponding .h
    if not args.include_already_declared:
        result.symbols = [s for s in result.symbols if not s.already_in_header]
    if args.no_types:
        result.symbols = [s for s in result.symbols if s.kind not in type_kinds]
    if args.functions_only:
        result.symbols = [s for s in result.symbols if s.kind == 'function']
    elif args.variables_only:
        result.symbols = [s for s in result.symbols if s.kind == 'variable']

    if args.stats_only:
        print_summary(result, verbose=args.verbose)
        sys.exit(0 if not result.errors else 1)

    if args.output:
        out_path = args.output
    else:
        first = os.path.basename(os.path.abspath(args.paths[0]))
        base = os.path.splitext(first)[0] if os.path.isfile(args.paths[0]) else first
        ext_map = {'header': '.externs.h', 'json': '.externs.json', 'csv': '.externs.csv'}
        out_path = f"{base}{ext_map[args.format]}"

    guard = args.guard or re.sub(
        r'[^A-Z0-9]', '_', os.path.basename(out_path).upper())

    if args.format == 'json':
        content = _output_json(result)
    elif args.format == 'csv':
        content = _output_csv(result)
    else:
        content = generate_externs(
            result,
            guard_name=guard,
            group_by_file=args.group_by_file,
            include_source_comments=not args.no_source_comments,
            include_original_comments=not args.no_original_comments,
            include_type_bodies=not args.no_type_bodies,
        )

    if args.dry_run:
        print(content)
    else:
        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f"✓ Written → {out_path}", file=sys.stderr)

    print_summary(result, verbose=args.verbose)
    sys.exit(0 if not result.errors else 1)


if __name__ == '__main__':
    main()

