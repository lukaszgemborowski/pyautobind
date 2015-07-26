from clang.cindex import *
from ctypes import *
import sys
import getopt

cfg_name = None
cfg_includes = []
cfg_files = None

infile = None
outfilename = None
outstream = None

basic_type_map = {"int" : "c_int", 
    "char" : "c_char", 
    "unsigned short" : "c_ushort", 
    "unsigned char" : "c_ubyte",
    "long" : "c_long",
    "signed char" : "c_char",
    "void *" : "c_void_p",
    "unsigned long" : "c_ulong"}

class Writer:
    def __init__(self, filename):
        if filename == None:
            self._stream = sys.stdout
            self._isfile = False
        else:
            self._stream = open(filename, "w")
            self._isfile = True

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._isfile:
            self._stream.close()

    def write(self, line, tabs = 0):
        while tabs > 0:
            self._stream.write("\t")
            tabs = tabs - 1

        self._stream.write("%s\n" % line)

def get_type_name(ctype):
    """
    Translate libclang Type into ctypes type (without struct, const prefix)
    """
    if ctype.kind == TypeKind.POINTER:
        ctype = ctype.get_pointee()

    if ctype.kind == TypeKind.CONSTANTARRAY:
        ctype = ctype.get_array_element_type()

    canonical_name = ctype.get_canonical().spelling

    if canonical_name.startswith("struct "):
        canonical_name = canonical_name[len("struct "):]

    if canonical_name.startswith("const "):
        canonical_name = canonical_name[len("const "):]

    if canonical_name.startswith("enum "):
        return "int"

    return canonical_name 

def get_struct_name_from_decl(struct):
    assert isinstance(struct, Cursor), "argument should be of type Cursor"
    assert struct.kind == CursorKind.STRUCT_DECL, "argument sholud be STRUCT_DECL kind"
    return struct.displayname

def type_to_ctype(typedef, structs):
    assert isinstance(typedef, Type), "argument should be of type Type"
    is_pointer = False
    is_array = False
    raw_type = get_type_name(typedef)

    if typedef.kind == TypeKind.POINTER:
        # void* is special case, we don't handle it as pointer type
        if typedef.get_pointee().get_canonical().kind != TypeKind.VOID:
            is_pointer = True
    elif typedef.kind == TypeKind.CONSTANTARRAY:
        is_array = True

    if raw_type in basic_type_map:
        raw_type = "ctypes." + basic_type_map[raw_type]
    else:
        # type is not a basic type, or someone missed this type in translation dict ;)
        # try to find it in declared structures list
        for struct in structs:
            if get_type_name(typedef) == get_struct_name_from_decl(struct):
                raw_type = get_struct_name_from_decl(struct)

    if raw_type != None:
        if is_pointer:
            return "ctypes.POINTER(%s)" % raw_type 
        elif is_array:
            return "%s * %d" % (raw_type, typedef.get_array_size())
        else:
            return raw_type
    else:
        return None 

def generate_struct_declarations(writer, structs):
    for struct in structs:
        writer.write("class %s(ctypes.Structure):" % get_struct_name_from_decl(struct))
        writer.write("pass\n", 1)

def generate_struct_members(writer, structs):
    for struct in structs:
        writer.write("%s._fields_ = [" % get_struct_name_from_decl(struct))

        for field in struct.get_children():
                writer.write("(\"%s\", %s)," % (field.displayname, type_to_ctype(field.type, structs)), 1)

        writer.write("]\n", 1)

def generate_functions(writer, functions, structs):
    for function in functions:
        arglist = ["self"]
        argtypes = []
        unnamed_no = 0

        for arg in function.get_arguments():
            argtypes.append(type_to_ctype(arg.type, structs))

            if arg.spelling == "":
                arglist.append("unnamed_%d" % unnamed_no)
                unnamed_no = unnamed_no + 1
            else:
                arglist.append(arg.spelling)

        writer.write("def %s(%s):" % (function.spelling, ', '.join(arglist)), 1)
        restype = type_to_ctype(function.result_type, structs)

        writer.write("self._handle.%s.argtypes = [%s]" % (function.spelling, ', '.join(argtypes)), 2)

        if restype != "void":
            writer.write("self._handle.%s.restype = %s" % (function.spelling, restype), 2)
            writer.write("return self._handle.%s(%s)\n" % (function.spelling, ', '.join(arglist[1:])), 2)
        else:
            writer.write("self._handle.%s(%s)\n" % (function.spelling, ', '.join(arglist[1:])), 2)

def generate_module(writer, functions, structs):
    writer.write("class %s:" % cfg_name)
    writer.write("def __init__(self, path):", 1)
    writer.write("self._handle = ctypes.CDLL(path)\n", 2)

    generate_functions(writer, functions, structs)

def generate_enums(writer, enums):
    for enum in enums:
        writer.write("class %s:" % enum.spelling)
        writer.write("pass\n", 1)

def generate_enum_values(writer, enums):
    for enum in enums:
        for value in enum.get_children():
            writer.write("%s.%s = %d" % (enum.spelling, value.spelling, value.enum_value))

        writer.write("")

def generate_header(writer):
    writer.write("import ctypes\n")

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

    if node.is_definition():
        # do not include forward declarations in list
        structs.append(node)

def handle_enum(node, enums):
    enums.append(node)

def find_definitions(node, types, structs, functions, enums):
    if node.kind == CursorKind.FUNCTION_DECL:
        handle_functions(node, functions)
    elif node.kind == CursorKind.STRUCT_DECL:
        handle_structure(node, structs)
    elif node.kind == CursorKind.TYPEDEF_DECL:
        # TODO: just to do
        pass
    elif node.kind == CursorKind.ENUM_DECL:
        handle_enum(node, enums)

def usage():
    # TODO: implement help message
    pass

def parse_command_line():
    global infile
    global outfilename
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
            outfilename = a
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
    global outfilename

    types = []
    structs = []
    functions = []
    enums = []

    parse_command_line()

    index = Index.create();
    tu = index.parse(cfg_files[0], cfg_includes)

    for node in tu.cursor.get_children():
        find_definitions(node, types, structs, functions, enums)

    with Writer(outfilename) as writer:
        generate_header(writer)
        generate_enums(writer, enums)
        generate_enum_values(writer, enums)
        generate_struct_declarations(writer, structs)
        generate_struct_members(writer, structs)
        generate_module(writer, functions, structs)

if __name__ == "__main__":
    main()
