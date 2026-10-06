import json, sys

BLOCK = [
 '    "key_mappings_table": {',
 '      "log_level": "warning",',
 '      "on_fail": "continue",',
 '      "steps": [',
 '        { "name": "find_assertion_use", "op": "find_use_of_string", "literal": "count == arrsize(s_remapTable)", "out": "string_use" },',
 '        { "name": "table_immediate", "op": "add", "in": "string_use", "value": "0xD", "out": "table_immediate" },',
 '        { "name": "table_pointer", "op": "read_u32", "in": "table_immediate", "out": "candidate" },',
 '        { "name": "validate_data", "op": "validate_section", "in": "candidate", "section": "data", "out": "final" }',
 '      ]',
 '    },',
]
ANCHOR = '"load_settings_func": {'

for path in sys.argv[1:]:
    raw = open(path, 'rb').read().decode('utf-8')
    nl = '\r\n' if '\r\n' in raw else '\n'
    if '"key_mappings_table"' in raw:
        print('%-22s already present' % path.split('\\')[-1]); continue
    lines = raw.split(nl)
    idx = next(i for i, l in enumerate(lines) if ANCHOR in l)
    lines[idx:idx] = [b.replace('\n', '') for b in BLOCK]
    out = nl.join(lines)
    json.loads(out)  # refuse to write invalid JSON
    open(path, 'wb').write(out.encode('utf-8'))
    n = len(json.loads(out)['resolvers'])
    print('%-22s inserted before line %d -> resolvers=%d' % (path.split('\\')[-1], idx + 1, n))
