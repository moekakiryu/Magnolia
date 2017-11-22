import re

from _abstract import CSSAbstract, CSSParserError
from static import Style

class AtQuery(CSSAbstract):
    """ the stuff between the @ and the { """
    def __init__(self,rule_type, arguments):
        self.rule_type = rule_type
        self.arguments = arguments

    def __repr__(self):
        return "AtQuery('{}','{}')".format(self.rule_type, self.arguments)

    def __str__(self):
        return self.__repr__()

    def get_copy(self):
        return AtQuery(self.rule_type, self.arguments)

    @classmethod
    def parse(cls, inpt):
        print "ATQUERY: "+inpt
        tokenized = re.search(cls.AT_RULE_TOKENIZER,inpt)
        return AtQuery(tokenized.group('name'), tokenized.group('arguments'))

    def match(self, element):
        return False

    def merge(self, other):
        raise ValueError("behavior not supported")

    def render(self, flags=0):
        return "woo AtQuery"

class AtRule(CSSAbstract):
    def __init__(self, style=None,*queries):
        self.style = style
        self.queries = list(queries)
        print "RECIEVED: "+str(list(queries))

    def __repr__(self):
        return "{{{} queries, {}}}".format(len(self.queries),str(self.style))

    def __str__(self):
        return self.__repr__()

    def get_copy(self):
        return AtRule(self.style.get_copy(),*[r.get_copy() for r in self.queries])

    @classmethod
    def parse(cls, inpt):
        print inpt
        tokenized = re.search(cls.AT_RULE_TOKENIZER,inpt)
        return AtQuery(tokenized.group('name'), tokenized.group('arguments'), 
                       tokenized.group('end')=='{')

    def match(self, element):
        return False

    def merge(self, other):
        raise ValueError("behavior not supported")

    def render(self, flags=0):
        return "woo AtQuery"
