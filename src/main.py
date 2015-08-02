from clang.cindex import *
from ctypes import *
import sys
import getopt
import os

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
    if ctype.kind == TypeKind.CONSTANTARRAY:
        ctype = ctype.get_array_element_type()

    if ctype.kind == TypeKind.POINTER:
        if ctype.get_pointee().get_canonical().kind == TypeKind.VOID:
            # special case for void* type
            return "void *"
        ctype = ctype.get_pointee()

    canonical_name = ctype.get_canonical().spelling

    if canonical_name.startswith("struct "):
        canonical_name = canonical_name[len("struct "):]

    if canonical_name.startswith("const "):
        canonical_name = canonical_name[len("const "):]

    if canonical_name.startswith("enum "):
        return "int"

    return canonical_name 

def get_enum_name_from_decl(enum):
    assert isinstance(enum, Cursor), "argument should be of type Cursor"
    assert enum.kind == CursorKind.ENUM_DECL, "argument should be ENUM_DECL kind"

    if enum.displayname != "":
        return enum.displayname
    else:
        return enum.type.spelling

class CommonDecl(object):
    def __init__(self, cursor):
        assert cursor.kind == CursorKind.ENUM_DECL or cursor.kind == CursorKind.STRUCT_DECL or cursor.kind == CursorKind.FUNCTION_DECL, "type not supported"
        self._cursor = cursor

    def type_name(self):
        if self._cursor.displayname != "":
            return self._cursor.displayname
        else:
            return self._cursor.type.spelling

    def __hash__(self):
        return self.type_name().__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __ne__(self, other):
        return not self.__eq__(other)

class FunctionDecl(CommonDecl):
    def __init__(self, cursor):
        super(FunctionDecl, self).__init__(cursor)

class StructureDecl(CommonDecl):
    def __init__(self, cursor):
        super(StructureDecl, self).__init__(cursor)

    def get_fields(self):
        return self._cursor.get_children()

def print_type(basic_type, structs):
    if basic_type.kind == TypeKind.POINTER:
        return "ctypes.POINTER(%s)" % print_type(basic_type.get_pointee(), structs)

    elif basic_type.kind == TypeKind.CONSTANTARRAY:
        return "%s * %d" % (print_type(basic_type.get_array_element_type(), structs), basic_type.get_array_size())

    else:
        raw_type = get_type_name(basic_type)
        if raw_type in basic_type_map:
            return "ctypes.%s" % basic_type_map[raw_type]
        else:
            for struct in structs:
                if raw_type == struct.type_name():
                    return raw_type

            # not a raw type and not an struct defined before. What to do?
            return None

def generate_struct_declarations(writer, structs):
    for struct in structs:
        writer.write("class %s(ctypes.Structure):" % struct.type_name())
        writer.write("pass\n", 1)

def generate_struct_members(writer, structs):
    for struct in structs:
        writer.write("%s._fields_ = [" % struct.type_name())

        for field in struct.get_fields():
            field_type_name = print_type(field.type, structs) 

            if field_type_name != None and field.type.kind != TypeKind.RECORD:
                writer.write("(\"%s\", %s)," % (field.displayname, field_type_name), 1)
            else:
                writer.write("#(\"%s\", %s)," % (field.displayname, field.type.spelling), 1)
                print("WARN: struct member omited: %s of type: %s, file: %s:%d" % (field.displayname, field.type.spelling, field.location.file, field.location.line))

        writer.write("]\n", 1)

def get_module_name_from_element(entity):
    base = os.path.basename(str(entity.location.file))
    return os.path.splitext(base)[0]

def generate_one_function(writer, function, structs):
    arglist = ["self"]
    argtypes = []
    unnamed_no = 0

    for arg in function.get_arguments():
        arg_type = print_type(arg.type, structs)

        if arg_type == None:
            arg_type = "TransparentType"

        argtypes.append(arg_type)

        if arg.spelling == "":
            arglist.append("unnamed_%d" % unnamed_no)
            unnamed_no = unnamed_no + 1
        else:
            arglist.append(arg.spelling)

    if function.type.kind == TypeKind.FUNCTIONPROTO and function.type.is_function_variadic():
        arglist.append("*args")

    writer.write("def %s(%s):" % (function.spelling, ', '.join(arglist)), 2)
    restype = print_type(function.result_type, structs)

    writer.write("self._handle.%s.argtypes = [%s]" % (function.spelling, ', '.join(argtypes)), 3)

    if restype != "void":
        writer.write("self._handle.%s.restype = %s" % (function.spelling, restype), 3)
        writer.write("return self._handle.%s(%s)\n" % (function.spelling, ', '.join(arglist[1:])), 3)
    else:
        writer.write("self._handle.%s(%s)\n" % (function.spelling, ', '.join(arglist[1:])), 3)

def generate_functions(writer, functions, structs):
    for function in functions:
        generate_one_function(writer, function, structs)

def generate_module(writer, functions, structs):
    # gather names of all header files without extension
    modules = {}
    for function in functions:
        module_name = get_module_name_from_element(function)

        if module_name not in modules:
            modules[module_name] = []

        modules[module_name].append(function)

    writer.write("class %s:" % cfg_name)
    writer.write("def __init__(self, path):", 1)
    writer.write("self._handle = ctypes.CDLL(path)\n", 2)

    for module_name in modules:
        writer.write("self.%s = %s.%s_h(self._handle)" % (module_name, cfg_name, module_name), 2)

    writer.write("")

    for module_name, function_list in modules.iteritems():
        writer.write("class %s_h:" % module_name, 1)
        writer.write("def __init__(self, handle):", 2)
        writer.write("self._handle = handle\n", 3)

        generate_functions(writer, function_list, structs)

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
        #structs.append(node)
        structs.add(StructureDecl(node))

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
    structs = set()
    functions = []
    enums = []
    translation_units = []

    parse_command_line()

    index = Index.create();

    for i in cfg_files:
        translation_units.append(index.parse(i, cfg_includes))

    for tu in translation_units:
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
