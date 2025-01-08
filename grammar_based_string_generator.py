#
# Copyright (c) 2024 Mackenzie High. All rights reserved.
#

import abc
import argparse
import sys
import random
import json

from abc import abstractmethod

from pyparsing import alphanums
from pyparsing import alphas
from pyparsing import Char
from pyparsing import Combine
from pyparsing import Forward
from pyparsing import Group
from pyparsing import Literal
from pyparsing import OneOrMore
from pyparsing import Optional
from pyparsing import QuotedString
from pyparsing import Regex
from pyparsing import StringEnd
from pyparsing import StringStart
from pyparsing import Suppress
from pyparsing import Word
from pyparsing import ZeroOrMore
from pyparsing import ParseException

class State:

    def __init__ (self):
        self.rules = {}
        self.sentence = []
        self.depth = 0
        self.length = 0
        self.maximum_depth = 256
        self.maximum_length = 4096

    def __enter__ (self):
        self.depth += 1
        if self.depth > self.maximum_depth:
            raise RuntimeError("stack is too deep")
        if self.length > self.maximum_length:
            raise RuntimeError("sentence is too long")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.depth -= 1

    def append (self, word):
        self.sentence.append(word)
        self.length += len(word)

class GeneratorRule (abc.ABC):

    def __init__ (self):
        pass

    def __repr__ (self):
        return self.__str__()

    @abstractmethod
    def random_walk (self, state):
        pass

class StringGeneratorRule (GeneratorRule):

    def __init__ (self, text):
        super().__init__()
        self.text = text

    def __str__ (self):
        return f'\"{self.text}\"'

    def random_walk (self, state):
        with state:
            state.append(self.text)

class SequenceGeneratorRule (GeneratorRule):

    def __init__ (self, members):
        super().__init__()
        self.members = members

    def __str__ (self):
        members = [str(x) for x in self.members]
        members = " , ".join(members)
        return f'({members})'

    def random_walk (self, state):
        with state:
            for item in self.members:
                item.random_walk(state)

class ChoiceGeneratorRule (GeneratorRule):

    def __init__ (self, members):
        super().__init__()
        self.members = members

    def __str__ (self):
        members = [str(x) for x in self.members]
        members = " | ".join(members)
        return f'({members})'

    def random_walk (self, state):
        with state:
            option = random.choice(self.members)
            option.random_walk(state)

class RefGeneratorRule (GeneratorRule):

    def __init__ (self, name):
        super().__init__()
        self.name = name

    def __str__ (self):
        return self.name

    def random_walk (self, state):
        with state:
            target = state.rules.get(self.name, None)
            if target is None:
                raise RuntimeError(f"no such rule: {self.name}")
            else:
                target.random_walk(state)

class RepeatGeneratorRule (GeneratorRule):

    def __init__ (self, operand, minimum, maximum):
        super().__init__()
        self.operand = operand
        self.minimum = minimum
        self.maximum = maximum

    def __str__ (self):
        return f'{str(self.operand)} {{ {self.minimum} , {self.maximum} }}'

    def random_walk (self, state):
        with state:
            count = random.randint(self.minimum, self.maximum)
            for i in range(0, count):
                self.operand.random_walk(state)

class NamedGeneratorRule (GeneratorRule):

    def __init__ (self, name, rule):
        super().__init__()
        self.name = name
        self.rule = rule

    def __str__ (self):
        return f'{self.name} = {str(self.rule)}'

    def random_walk (self, state):
        with state:
            self.rule.random_walk(state)

class RootGeneratorRule (GeneratorRule):

    def __init__ (self, rules):
        super().__init__()
        self.rules = rules

    def __str__ (self):
        lines = [str(x) for x in self.rules]
        lines = "\n".join(lines)
        return lines

    def random_walk (self, state):
        if self.rules:
            for rule in self.rules:
                assert isinstance(rule, NamedGeneratorRule)
                state.rules[rule.name] = rule
            with state:
                root = self.rules[-1]
                root = state.rules.get("ROOT", root)
                root = state.rules.get("Root", root)
                root = state.rules.get("root", root)
                root.random_walk(state)

def action_make_opt (source, location, tokens):
    operand = tokens[0]
    return RepeatGeneratorRule(operand, 0, 1)

def action_make_zom (source, location, tokens):
    operand = tokens[0]
    maximum = int(str(tokens[1]))
    return RepeatGeneratorRule(operand, 0, maximum)

def action_make_oom (source, location, tokens):
    operand = tokens[0]
    maximum = int(str(tokens[1]))
    return RepeatGeneratorRule(operand, 1, maximum)

def action_make_repeat (source, location, tokens):
    operand = tokens[0]
    minimum = int(str(tokens[1]))
    maximum = int(str(tokens[2]))
    return RepeatGeneratorRule(operand, minimum, maximum)

def action_make_ref (source, location, tokens):
    name = str(tokens[0])
    return RefGeneratorRule(name)

def action_make_string (source, location, tokens):
    string = str(tokens[0])
    return StringGeneratorRule(string)

def action_make_sequence (source, location, tokens):
    items = [x for x in tokens if isinstance(x, GeneratorRule)]
    return SequenceGeneratorRule(items)

def action_make_choice (source, location, tokens):
    items = [x for x in tokens if isinstance(x, GeneratorRule)]
    return ChoiceGeneratorRule(items)

def action_make_named_rule (source, location, tokens):
    name = tokens[0]
    rule = tokens[1]
    return NamedGeneratorRule(name, rule)

def action_make_root (source, location, tokens):
    items = [x for x in tokens if isinstance(x, GeneratorRule)]
    return RootGeneratorRule(items)

def grammar ():
    WORD = Regex("[A-Za-z_0-9]+")
    L_BRACE = Suppress(Literal("{"))
    R_BRACE = Suppress(Literal("}"))
    L_PAREN = Suppress(Literal("("))
    R_PAREN = Suppress(Literal(")"))
    INTEGER = Regex("[0-9]+")
    COMMA = Suppress(Char(","))
    SLASH = Suppress(Word("/|"))
    SEMICOLON = Suppress(Char(";"))
    ASSIGN = Suppress(Char("="))
    STRING = QuotedString('"')

    WS_PART = Forward()
    COMMENT = Regex("#[^\n]*")
    SPACE = Word(" \t")
    NEWLINE = Word("\r\n")
    WS_PART << (COMMENT | SPACE | NEWLINE)
    WS = Suppress(ZeroOrMore(WS_PART))

    name = WORD + WS

    operand = Forward()
    prefix_operand = Forward()

    string_rule = Combine(STRING) + WS
    ref_rule =  WORD + WS
    opt_rule = prefix_operand + WS + Suppress(Char("?")) + WS
    zom_rule = prefix_operand + WS + Suppress(Char("*")) + WS + INTEGER + WS
    oom_rule = prefix_operand + WS + Suppress(Char("+")) + WS + INTEGER + WS
    repeat_rule = prefix_operand + WS + L_BRACE + INTEGER + WS + COMMA + WS + INTEGER + WS + R_BRACE + WS
    sequence_rule = operand + OneOrMore(WS + COMMA + WS + operand)
    choice_rule = operand + OneOrMore(WS + SLASH + WS + operand)

    nested_anon_rule = Forward()
    nested_rule = L_PAREN + WS + nested_anon_rule + WS + R_PAREN + WS
    anon_rule =  sequence_rule | choice_rule | operand
    named_rule = name + WS + ASSIGN + WS + anon_rule + WS + SEMICOLON + WS
    nested_anon_rule << anon_rule

    root = StringStart() + WS + ZeroOrMore(named_rule) + WS + StringEnd()

    prefix_operand << (nested_rule | ref_rule | string_rule)
    postfix_operand = opt_rule | zom_rule | oom_rule | repeat_rule | prefix_operand
    operand << postfix_operand

    opt_rule.set_parse_action(action_make_opt)
    zom_rule.set_parse_action(action_make_zom)
    oom_rule.set_parse_action(action_make_oom)
    repeat_rule.set_parse_action(action_make_repeat)
    string_rule.set_parse_action(action_make_string)
    ref_rule.set_parse_action(action_make_ref)
    sequence_rule.set_parse_action(action_make_sequence)
    choice_rule.set_parse_action(action_make_choice)
    named_rule.set_parse_action(action_make_named_rule)
    root.set_parse_action(action_make_root)
    return root

def main ():
    kwargs = { }
    kwargs["prog"]        = "grammar_based_string_generator.py"
    kwargs["usage"]       = None
    kwargs["description"] = "Generate random strings from PEG like grammars."
    kwargs["epilog"]      = None
    parser = argparse.ArgumentParser(**kwargs)

    name_or_flags      = ["--packrat"]
    kwargs = { }
    kwargs["action"]   = "store"
    kwargs["nargs"]    = 1
    kwargs["default"]  = None
    kwargs["type"]     = int
    kwargs["required"] = False
    kwargs["help"]     = "Enable packrat parsing and set memoization cache size."
    kwargs["metavar"]  = "<integer>"
    parser.add_argument(*name_or_flags, **kwargs)

    name_or_flags      = ["--max-depth"]
    kwargs = { }
    kwargs["action"]   = "store"
    kwargs["nargs"]    = 1
    kwargs["default"]  = [256]
    kwargs["type"]     = int
    kwargs["required"] = False
    kwargs["help"]     = "Limit the recursion depth."
    kwargs["metavar"]  = "<integer>"
    parser.add_argument(*name_or_flags, **kwargs)

    name_or_flags      = ["--max-length"]
    kwargs = { }
    kwargs["action"]   = "store"
    kwargs["nargs"]    = 1
    kwargs["default"]  = [4096]
    kwargs["type"]     = int
    kwargs["required"] = False
    kwargs["help"]     = "Limit the length of the generated string."
    kwargs["metavar"]  = "<integer>"
    parser.add_argument(*name_or_flags, **kwargs)

    name_or_flags      = ["--grammar-file", "--file", "-f"]
    kwargs = { }
    kwargs["action"]   = "store"
    kwargs["nargs"]    = 1
    kwargs["default"]  = None
    kwargs["type"]     = str
    kwargs["required"] = False
    kwargs["help"]     = "Read the grammar from a file."
    kwargs["metavar"]  = "<path>"
    parser.add_argument(*name_or_flags, **kwargs)

    name_or_flags      = ["--grammar", "-g"]
    kwargs = { }
    kwargs["action"]   = "store"
    kwargs["nargs"]    = 1
    kwargs["default"]  = None
    kwargs["type"]     = str
    kwargs["required"] = False
    kwargs["help"]     = "Read the grammar from the command-line."
    kwargs["metavar"]  = "<grammar>"
    parser.add_argument(*name_or_flags, **kwargs)

    name_or_flags      = ["--sentence", "-s"]
    kwargs = { }
    kwargs["action"]   = "store_true"
    kwargs["default"]  = False
    kwargs["required"] = False
    kwargs["help"]     = "Output the generated string in sentence format."
    parser.add_argument(*name_or_flags, **kwargs)

    name_or_flags      = ["--delimiter", "-d"]
    kwargs = { }
    kwargs["action"]   = "store"
    kwargs["nargs"]    = 1
    kwargs["default"]  = [" "]
    kwargs["type"]     = str
    kwargs["required"] = False
    kwargs["help"]     = "Set the delimiter for use in the sentence format."
    kwargs["metavar"]  = "<text>"
    parser.add_argument(*name_or_flags, **kwargs)

    args = sys.argv[1:]
    args = parser.parse_args(args)
    #print(args)

    state = State()
    state.maximum_depth = args.max_depth[0]
    state.maximum_length = args.max_length[0]

    if args.grammar_file:
        with open(args.grammar_file[0]) as fd:
            language = fd.read()
    elif args.grammar:
        language = args.grammar[0]
    else:
        print("Error: no grammar")
        sys.exit(1)

    groot = grammar()

    if args.packrat:
        groot.enable_packrat(args.packrat[0])

    try:
        result = groot.parseString(language)
    except ParseException as ex:
        print(f"Syntax Error:")
        print(f"    Line: {ex.line}")
        print(f"    Lineno: {ex.lineno}")
        print(f"    Column: {ex.col}")
        print(f"    Message: {str(ex)}")
        sys.exit(1)

    assert result is not None

    generator = result[0]
    generator.random_walk(state)

    if args.sentence:
        delimiter = args.delimiter[0]
        output = delimiter.join(state.sentence)
        print(output)
    else:
        output = json.dumps(state.sentence)
        print(output)

if __name__ == "__main__":
    main()

#
# Copyright (c) 2024 Mackenzie High. All rights reserved.
#
