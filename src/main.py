from clang.cindex import *
from ctypes import *
import sys

library_so = ""
include_path = ["-I/home/icek/Projects/binding/libsample/include"]
interface_files = ["/home/icek/Projects/binding/libsample/include/interface.h"]

basic_type_map = {"int" : "c_int", "char" : "c_char", "unsigned short" : "c_ushort", "unsigned char" : "c_ubyte"}

def generate_header():
    print("import ctypes")

def debug_print_ast(node, level):
    next_level = level + 1
    while level > 0:
        sys.stdout.write("\t")
        level = level - 1

    print(node.displayname, node.kind)

    for c in node.get_children():
        debug_print_ast(c, next_level)

def ctype_to_python(ctypename):
    print("type is %s" % ctypename.kind)
    return "ctypes." + basic_type_map[ctypename.get_canonical().spelling]

def handle_structure(node, structs):
    if node.displayname == "":
        # TODO: struct without name, probably typedef-ed
        return

    print("class %s(ctypes.Structure):" % node.displayname)
    print("\t_fields_ = [ \\")

    for field in node.get_children():
        print("\t\t(\"%s\", %s), \\" % (field.displayname, ctype_to_python(field.type)))
    
    print("\t\t]")

def find_definitions(node, types, structs, functions):
    if node.kind == CursorKind.FUNCTION_DECL:
        pass
#        print("function declaration", node.displayname)
#        functions.append(node)
    elif node.kind == CursorKind.STRUCT_DECL:
        handle_structure(node, structs)
    elif node.kind == CursorKind.TYPEDEF_DECL:
        pass
#        print("typedef declaration", node.displayname, node.type.get_canonical().spelling)
#        types.append(node)

def main():
    types = []
    structs = []
    functions = []

    index = Index.create();
    tu = index.parse(interface_files[0], include_path)

    generate_header()

    for node in tu.cursor.get_children():
        find_definitions(node, types, structs, functions)


if __name__ == "__main__":
    main()
