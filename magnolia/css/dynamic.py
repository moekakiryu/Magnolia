import re
from bisect import insort as sorted_insert 

from static import Style
from _abstract import (CSSAbstract, StaticAbstract, DynamicAbstract, 
                       ContainerAbstract, CSSParserError)

class AtQuery(DynamicAbstract):
    """ the stuff between the @ and the { """
    def __init__(self,rule_type, arguments):
        self.rule_type = rule_type
        self.arguments = arguments

    def __repr__(self):
        return "AtQuery('{}','{}')".format(self.rule_type, self.arguments)

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return (isinstance(other, AtQuery)
                and self.rule_type==other.rule_type
                and self.arguments==other.arguments)

    def __ne__(self, other):
        return not self==other

    def get_copy(self):
        return AtQuery(self.rule_type, self.arguments)

    @classmethod
    def parse(cls, inpt):
        tokenized = re.search(cls.AT_RULE_TOKENIZER,inpt)
        return AtQuery(tokenized.group('name'), tokenized.group('arguments') or '')

    def render(self, flags=0):
        return "@{} {}".format(self.rule_type, self.arguments)

    def evaluate(self, environment=None):
        if environment:
            pass
        return True

class AtRule(CSSAbstract, StaticAbstract, DynamicAbstract, ContainerAbstract):
    def __init__(self, query, is_block=False):
        super(AtRule,self).__init__()
        self.query = query
        self.children = []
        self.is_block = is_block
        self.environment = None # this will be able to be set later

    def __repr__(self):
        return "{{{}, {} children}}".format(self.query, len(self.children))

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return (isinstance(other, AtRule)
                and self.query==other.query)

    def __ne__(self, other):
        return not self==other

    def has(self, child):
        return child in self.children

    def add(self, child):
        sorted_insert(self.children, child)

    def remove(self, child):
        self.children.remove(child)

    def get_copy(self, without_children=False):
        new_rule = AtRule(self.query.get_copy())
        new_rule._instance_no = self._instance_no
        new_rule.is_block = self.is_block
        if not without_children:
            new_rule.children = [c.get_copy() for c in self.children]
        return new_rule

    def flatten(self):
        styles = []
        if self.evaluate():
            for child in self.children:
                if isinstance(child, AtRule):
                    styles.extend(child.flatten())
                elif isinstance(child, Style):
                    styles.append(child)
        return styles

    @classmethod
    def _parse(cls, inpt, head=None):        
        for token in cls._parse_css(inpt):
            if token.head.startswith("@"): # if its a nested at rule
                new_head = AtRule(AtQuery.parse(token.head), token.is_block)
                if new_head.is_block:
                    new_head._parse(token.tail, new_head)
                if head:
                    head.add(new_head)
                else:
                    head = new_head
            else: # if its a style, presumably (hopefully)
                if not head: # as this is parsing at-rules, there is a problem
                             # if there are orphan styles
                    raise CSSParserError("found style, expected at-rule")
                selectors = [s.strip() for s in token.head.split(",")]
                for selector in selectors:
                    head.add(Style.parse("{}{{{}}}".format(selector, token.tail)))
        return head

    @classmethod
    def parse(cls, inpt):
        return cls._parse(inpt)

    def _match(self, element, head=None):
        if self.evaluate():
            new_rule = self.get_copy(True)
            has_match = False
            for child in self.children:
                if isinstance(child, AtRule):
                    new_child = child._match(element, new_rule)
                    if new_child and len(new_child.children)>0:
                        has_match = True
                        new_rule.add(new_child)
                elif isinstance(child, Style):
                    if child.match(element):
                        has_match = True
                        new_rule.add(child)
            if has_match:
                return new_rule
            else:
                return None
        return None

    def match(self, element):
        return self._match(element)

    def merge(self, other):
        if self==other:
            for child in other.children:
                if child in self.children:
                    self.children[self.children.index(child)].merge(child)
                else:
                    self.add(child)

    @staticmethod
    def _indent(s):
        indented = "\n\t".join(s.splitlines())
        return indented

    def render(self, flags=0):
        rendered_string = self.query.render(flags)
        if self.is_block:
            rendered_string+="{ "
            for child in self.children:
                rendered_string += self._indent("\n"+child.render(flags))
            rendered_string+="\n}\n"
        else:
            rendered_string+="; "
        return rendered_string


    def evaluate(self, environment=None):
        if environment:
            return self.query.evaluate(environment)
        return self.query.evaluate(self.environment)