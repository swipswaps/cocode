import types
import watch

from cocode.instruction_base import BaseInstruction
from cocode.argy.branching import Label


class ContextProxy:

    def _push_value_in_context(self, value, context_field):
        if value in context_field:
            index = context_field.index(value)
        else:
            context_field.append(value)
            index = self._push_value_in_context(value, context_field)
        return index

    def register_name(self, name):
        return self._push_value_in_context(name, self.names)

    def register_varname(self, name):
        return self._push_value_in_context(name, self.varnames)

    def register_constant(self, name):
        return self._push_value_in_context(name, self.constants)

    @property
    def nlocals(self):
        return len(self.names)

    def __init__(self, interface):
        self.names = list()
        self.varnames = (
            interface and list(interface.__code__.co_varnames) or list()
        )
        self.constants = list()


class BytecodeProxy(watch.WatchMe):
    bytes = watch.ArrayOf(watch.builtins.InstanceOf(int))

    def add(self, value):
        self.bytes.append(value)

    @property
    def stacksize(self):
        return 3

    def __init__(self):
        self.bytes = list()


class CodeObjectProxy(watch.WatchMe):

    bytecode = BytecodeProxy
    context = ContextProxy
    instructions = watch.ArrayOf(watch.builtins.InstanceOf(BaseInstruction))
    label_map = watch.MappingOf(
        values_type=watch.builtins.InstanceOf(int),
        keys_type=watch.builtins.InstanceOf(str)
    )
    argcount = watch.builtins.InstanceOf(int)
    kw_argcount = watch.builtins.InstanceOf(int)
    flags = watch.builtins.InstanceOf(int)
    interface = watch.SomeOf(
        watch.builtins.InstanceOf(types.FunctionType),
        watch.builtins.EqualsTo(None)
    )

    def __init__(self, *instr, args=0, kwargs=0, flags=64, interface=None):
        self.instructions = instr
        self.argcount = args
        self.kw_argcount = kwargs
        self.flags = flags
        self.interface = interface

    def assemble(self):
        # create new proxy instances on every assembly request
        self.context = type(self).context(self.interface)
        self.bytecode = type(self).bytecode()
        self.label_map = dict()

        # calculation of byte shift for every instruction
        current_position = 0
        for instruction in self.instructions:
            instruction.set_position(current_position)
            current_position += len(instruction)

        # finally setting label map
        self.label_map = {
            label.label_name: label.get_position() for
            label in self.instructions if isinstance(label, Label)
        }

        # now everything is ready to render instructions
        for instruction in self.instructions:
            instruction.render(self)

        return types.CodeType(
            self.argcount,                  # argcount
            self.kw_argcount,               # kwonlyargcount
            self.context.nlocals,           # nlocals
            self.bytecode.stacksize,        # stacksize
            self.flags,                     # flags
            bytes(self.bytecode.bytes),     # codestring
            tuple(self.context.constants),  # constants
            tuple(self.context.names),      # names
            tuple(self.context.varnames),   # varnames
            '<string>',                     # filename
            '<noname code object>',         # name
            0,                              # firstlineno
            bytes()                         # lnotab
        )
