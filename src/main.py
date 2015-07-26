from clang.cindex import *
from ctypes import *
import sys
import getopt

cfg_name = None
cfg_includes = []
cfg_files = None

infile = None
outfile = None

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

def get_struct_name_from_decl(struct):
    assert isinstance(struct, Cursor), "argument should be of type Cursor"
    assert struct.kind == CursorKind.STRUCT_DECL, "argument sholud be STRUCT_DECL kind"
    return struct.displayname

def get_field_type(field, structs):
    assert isinstance(field, Cursor), "argument should be of type Cursor"
    assert field.kind == CursorKind.FIELD_DECL, "argument should be FIELD_DECL kind"

    is_pointer = False
    is_array = False
    field_type = field.type
    type_name = None

    if field.type.kind == TypeKind.POINTER:
        field_type = field_type.get_pointee()
        is_pointer = True
    elif field.type.kind == TypeKind.CONSTANTARRAY:
        field_type = field_type.get_array_element_type()
        is_array = True

    if field_type.get_canonical().spelling in basic_type_map:
        type_name = "ctypes." + basic_type_map[field_type.get_canonical().spelling]
    else:
        # type is not a basic type, or someone missed this type in translation dict ;)
        # try to find it in declared structures list
        for struct in structs:
            if get_type_name(field_type) == get_struct_name_from_decl(struct):
                type_name = get_struct_name_from_decl(struct)

    if type_name != None:
        if is_pointer:
            return "ctypes.POINTER(%s)" % type_name
        elif is_array:
            return "%s * %d" % (type_name, field.type.get_array_size())
        else:
            return type_name
    else:
        assert False, "type not found"

def generate_struct_declarations(structs):
    for struct in structs:
        print("class %s(ctypes.Structure):" % get_struct_name_from_decl(struct))
        print("\tpass\n")

def generate_struct_members(structs):
    for struct in structs:
        print("%s._fields_ = [" % get_struct_name_from_decl(struct))

        for field in struct.get_children():
                print("\t(\"%s\", %s)," % (field.displayname, get_field_type(field, structs)))

        print("\t]\n")

def generate_functions(functions):
    for function in functions:
        arglist = ["self"]

        for arg in function.get_arguments():
            arglist.append(arg.spelling)

        print("\tdef %s(%s):" % (function.spelling, ', '.join(arglist)))
        print("\t\tself._handle.%s(%s)\n" % (function.spelling, ', '.join(arglist[1:])))

def generate_module(functions):
    print("class %s:" % cfg_name)
    print("\tdef __init__(self, path):")
    print("\t\tself._handle = ctypes.CDLL(path)\n")

    generate_functions(functions)

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

def handle_functions(node, functions):
    functions.append(node)

def handle_structure(node, structs):
    if node.displayname == "":
        # TODO: struct without name, probably typedef-ed. Figure out how to handle it.
        # typedef struct { int a; } some_struct;
        return

    structs.append(node)

def find_definitions(node, types, structs, functions):
    if node.kind == CursorKind.FUNCTION_DECL:
        handle_functions(node, functions)
    elif node.kind == CursorKind.STRUCT_DECL:
        handle_structure(node, structs)
    elif node.kind == CursorKind.TYPEDEF_DECL:
        # TODO: just to do
        pass

def usage():
    # TODO: implement help message
    pass

def parse_command_line():
    global infile
    global outfile
    global cfg_name
    global cfg_includes
    global cfg_files

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:i:", ["help", "output=", "input="])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(1)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif o in("-o", "--output"):
            outfile = a
        elif o in("-i", "--input"):
            infile = a
        else:
            assert False, "Unhandled"

    if infile == None:
        print("input is mandatory")
        sys.exit(2)
    else:
        with open(infile) as config:
            a = {}
            b = {}

            exec(config, a, b)
            if "cfg_name" in b:
                cfg_name = b["cfg_name"]
            else:
                print("cfg_name must be defined in config file")
                sys.exit(1)

            if "cfg_files" in b:
                cfg_files = b["cfg_files"]
            else:
                print("cfg_files must be defined in config gile")
                sys.exit(1)

            if "cfg_includes" in b:
                cfg_includes = b["cfg_includes"]

def main():
    types = []
    structs = []
    functions = []

    parse_command_line()

    index = Index.create();
    tu = index.parse(cfg_files[0], cfg_includes)

    for node in tu.cursor.get_children():
        find_definitions(node, types, structs, functions)

    generate_header()
    generate_struct_declarations(structs)
    generate_struct_members(structs)
    generate_module(functions)

if __name__ == "__main__":
    main()
