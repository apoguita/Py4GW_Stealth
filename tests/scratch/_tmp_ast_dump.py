import ast, sys
p = r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\enums_src\Model_enums.py"
src = open(p, encoding="utf-8").read()
tree = ast.parse(src)
for node in tree.body:
    kind = type(node).__name__
    if kind in ("ClassDef", "FunctionDef", "AsyncFunctionDef"):
        print(f"{node.lineno:5d} {kind} {node.name}")
    elif kind == "Import":
        print(f"{node.lineno:5d} Import {[a.name for a in node.names]}")
    elif kind == "ImportFrom":
        print(f"{node.lineno:5d} ImportFrom {node.module} {[a.name for a in node.names]}")
    elif kind == "Assign":
        print(f"{node.lineno:5d} Assign {[t.id for t in node.targets if isinstance(t, ast.Name)]}")
    elif kind == "AnnAssign":
        print(f"{node.lineno:5d} AnnAssign")
    else:
        print(f"{node.lineno:5d} OTHER {kind} :: {ast.dump(node)[:120]}")
print("total top-level nodes:", len(tree.body))
