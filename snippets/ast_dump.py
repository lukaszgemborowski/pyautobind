import sys
from clang.cindex import *

def debug_print_ast(node, level):
    next_level = level + 1
    while level > 0:
        sys.stdout.write("\t")
        level = level - 1

    print(node.displayname, node.kind)

    if node.type.kind == TypeKind.FUNCTIONPROTO:
        if node.type.is_function_variadic():
            print("function is variadic")
        else:
            print("function is NOT variadic")

    for c in node.get_children():
        debug_print_ast(c, next_level)


def main():
    if len(sys.argv) != 2:
        print("you must provide source code file as sole argument")
        sys.exit(1)

    index = Index.create();
    tu = index.parse(sys.argv[1])

    for node in tu.cursor.get_children():
        debug_print_ast(node, 0)

if __name__ == "__main__":
    main()
