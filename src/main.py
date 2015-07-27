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
        if ctype.get_pointee().get_canonical().kind == TypeKind.VOID:
            # special case for void* type
            return "void *"
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

    if struct.displayname != "":
        return struct.displayname
    else:
        return struct.type.spelling

def get_enum_name_from_decl(enum):
    assert isinstance(enum, Cursor), "argument should be of type Cursor"
    assert enum.kind == CursorKind.ENUM_DECL, "argument should be ENUM_DECL kind"

    if enum.displayname != "":
        return enum.displayname
    else:
        return enum.type.spelling

def print_pointer(basic_type, level):
    """ 
    recursively print nested pointers
    """
    if level == 0:
        return basic_type
    else:
        return "ctypes.POINTER(%s)" % print_pointer(basic_type, level - 1)

def type_to_ctype(typedef, structs):
    assert isinstance(typedef, Type), "argument should be of type Type"
    pointer_level = 0
    is_array = False
    raw_type = get_type_name(typedef)
    
    if typedef.kind == TypeKind.POINTER:
        # void* is special case, we don't handle it as pointer type
        if typedef.get_pointee().get_canonical().kind != TypeKind.VOID:
            next_level = typedef
            while next_level.kind == TypeKind.POINTER:
                next_level = next_level.get_pointee()
                pointer_level = pointer_level + 1

            raw_type = get_type_name(next_level)

    elif typedef.kind == TypeKind.CONSTANTARRAY:
        is_array = True

    if raw_type in basic_type_map:
        raw_type = "ctypes." + basic_type_map[raw_type]
    else:
        # type is not a basic type, or someone missed this type in translation dict ;)
        # try to find it in declared structures list
        raw_type = None

        for struct in structs:
            if get_type_name(typedef) == get_struct_name_from_decl(struct):
                raw_type = get_struct_name_from_decl(struct)

    if raw_type != None:
        if pointer_level > 0:
            return print_pointer(raw_type, pointer_level)
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
            if field.type.kind != TypeKind.RECORD and field.type.kind != TypeKind.UNEXPOSED:
                writer.write("(\"%s\", %s)," % (field.displayname, type_to_ctype(field.type, structs)), 1)
            else:
                print("WARN: struct member ommited: %s of type: %s" % (field.displayname, field.type.spelling))

        writer.write("]\n", 1)

def generate_functions(writer, functions, structs):
    for function in functions:
        arglist = ["self"]
        argtypes = []
        unnamed_no = 0

        for arg in function.get_arguments():
            arg_type = type_to_ctype(arg.type, structs)

            if arg_type == None:
                arg_type = "TransparentType"

            argtypes.append(arg_type)

            if arg.spelling == "":
                arglist.append("unnamed_%d" % unnamed_no)
                unnamed_no = unnamed_no + 1
            else:
                arglist.append(arg.spelling)

        if function.type.is_function_variadic():
            arglist.append("*args")

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
        writer.write("class %s:" % get_enum_name_from_decl(enum))
        writer.write("pass\n", 1)

def generate_enum_values(writer, enums):
    for enum in enums:
        for value in enum.get_children():
            writer.write("%s.%s = %d" % (get_enum_name_from_decl(enum), value.spelling, value.enum_value))

        writer.write("")

def generate_header(writer):
    import helpers
    writer.write(helpers.helpers_string)

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
