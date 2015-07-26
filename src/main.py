from clang.cindex import *
from ctypes import *
import sys

# this should be handled as program arguments:
library_name = "libsample"
include_path = ["-I/home/icek/Projects/binding/libsample/include"]
interface_files = ["/home/icek/Projects/binding/libsample/include/interface.h"]

basic_type_map = {"int" : "c_int", 
    "char" : "c_char", 
    "unsigned short" : "c_ushort", 
    "unsigned char" : "c_ubyte"}

def generate_header():
    print("import ctypes\n")

def get_type_name(ctype):
    canonical_name = ctype.get_canonical().spelling

    if canonical_name.startswith("struct "):
        canonical_name = canonical_name[len("struct "):]

    return canonical_name 

def get_struct_name(struct):
    assert isinstance(struct, Cursor), "argument should be of type Cursor"
    assert struct.kind == CursorKind.STRUCT_DECL, "argument sholud be STRUCT_DECL kind"
    return struct.displayname

def get_field_type(field, structs):
    assert isinstance(field, Cursor), "argument should be of type Cursor"
    assert field.kind == CursorKind.FIELD_DECL, "argument should be FIELD_DECL kind"

    is_pointer = False
    field_type = field.type
    type_name = None

    if field.type.kind == TypeKind.POINTER:
        field_type = field_type.get_pointee()
        is_pointer = True

    if field_type.get_canonical().spelling in basic_type_map:
        type_name = "ctypes." + basic_type_map[field_type.get_canonical().spelling]
    else:
        # type is not a basic type, or someone missed this type in translation dict ;)
        # try to find it in declared structures list
        for struct in structs:
            if get_type_name(field_type) == get_struct_name(struct):
                type_name = get_struct_name(struct)

    if type_name != None:
        if is_pointer:
            return "ctypes.POINTER(%s)" % type_name
        else:
            return type_name
    else:
        assert False, "type not found"

def generate_struct_declarations(structs):
    for struct in structs:
        print("class %s(ctypes.Structure):" % get_struct_name(struct))
        print("\tpass\n")

def generate_struct_members(structs):
    for struct in structs:
        print("%s._fields_ = [" % get_struct_name(struct))

        for field in struct.get_children():
                print("\t(\"%s\", %s)," % (field.displayname, get_field_type(field, structs)))

        print("\t]\n")

def debug_print_ast(node, level):
    next_level = level + 1
    while level > 0:
        sys.stdout.write("\t")
        level = level - 1

    print(node.displayname, node.kind)

    for c in node.get_children():
        debug_print_ast(c, next_level)

def ctype_to_python(ctypename):
    return "ctypes." + basic_type_map[ctypename.get_canonical().spelling]

def handle_structure(node, structs):
    if node.displayname == "":
        # TODO: struct without name, probably typedef-ed. Figure out how to handle it.
        return

    # append struct node
    structs.append(node)

    #print("class %s(ctypes.Structure):" % node.displayname)
    #print("\t_fields_ = [ \\")

    #for field in node.get_children():
    #    print("\t\t(\"%s\", %s), \\" % (field.displayname, ctype_to_python(field.type)))
    
    #print("\t\t]")

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

    for node in tu.cursor.get_children():
        find_definitions(node, types, structs, functions)

    generate_header()
    generate_struct_declarations(structs)
    generate_struct_members(structs)

if __name__ == "__main__":
    main()
