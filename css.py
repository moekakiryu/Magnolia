import re
import abc

PSEUDO_CLASSES = ["active","any","checked","default","dir","disabled","empty",
                  "enabled","first","first-child","first-of-type","fullscreen",
                  "focus","hover","indeterminate","in-range","invalid","lang",
                  "last-child","last-of-type","left","link","not","nth-child",
                  "nth-last-child","nth-last-of-type","nth-of-type",
                  "only-child","only-of-type","optional","out-of-range",
                  "read-only","read-write","required","right","root","scope",
                  "target","valid","visited"]

PSEUDO_ELEMENTS = ["after","before","cue","first-letter","first-line",
                   "selection","backdrop","placeholder","marker",
                   "spelling-error","grammar-error"]

PSEUDO_CLASSES.sort(key=lambda i:len(i),reverse=True)
PSEUDO_ELEMENTS.sort(key=lambda i:len(i),reverse=True)

class CSSAbstract():
    __metaclass__ = abc.ABCMeta
    CSS_TOKENIZER = re.compile(r"(?P<style>(?P<selector>[^{}]*){(?P<attributes>(?:.|\n)*?)})",
                                re.MULTILINE|re.DOTALL)

    SELECTOR_TOKENIZER = re.compile(r"(?P<type>[#.]?)(?P<name>(?:-?[_a-zA-Z]+[_a-zA-Z0-9\-]*|\*)?)"
                                    r"(?P<attribute>(?:\[.*?\])?)"
                                    r"(?P<pseudo_class>(?:::?(?:{pseudo_classes})(?:\(.*?\))?)?)"
                                    r"(?P<pseudo_element>(?:::?(?:{pseudo_elems})(?:\(.*?\))?)?)"
                                    r"(?:\s*(?P<conn_type>[> +~])\s*)?".format(
                                        pseudo_classes="|".join(PSEUDO_CLASSES),
                                        pseudo_elems="|".join(PSEUDO_ELEMENTS)),
                                    re.DOTALL)

    FILTER_TOKENIZER = re.compile(r"\[(?P<name>-?[_a-zA-Z]+[_a-zA-Z0-9-]*)"
            r"(?:(?P<type>[*~|$^]?)=)['\"](?P<value>-?[_a-zA-Z]+[_a-zA-Z0-9-]*)['\"]\]",re.DOTALL)

    PSEUDO_TOKENIZER = re.compile(r":(?P<second_colon>:?)(?P<name>{pseudo_names})"
                                  r"(?:\((?P<argument>.*?)\))?".format(
                                   pseudo_names="|".join(PSEUDO_CLASSES+PSEUDO_ELEMENTS)),re.DOTALL)

    @classmethod
    def tokenize_selector(cls, inpt):
            results = re.finditer(cls.SELECTOR_TOKENIZER, inpt)
            found = []
            for result in results:
                if any(result.groups()):
                    found.append(result)
            return iter(found)

    @abc.abstractmethod
    def parse(self, inpt):
        return

    @abc.abstractmethod
    def match(self, element):
        return

    @abc.abstractmethod
    def merge(self, other):
        return

    @abc.abstractmethod
    def render(self, inline=False):
        return


class Attribute:
    def __init__(self, parent, attribute, value, important=False):
        self.parent = parent
        self.attribute = attribute
        self.value = value
        self.important = important

    def __repr__(self):
        return "('{}','{}',{})".format(self.attribute, self.value, self.important)

    def __eq__(self, other):
        """ NOTE: this does NOT compare attrribute values """
        return isinstance(other, Attribute) and self.attribute==other.attribute

    def __ne__(self, other):
        return not self == other

    @classmethod
    def parse(cls, inpt,parent=None):
        inpt = inpt.strip()
        if inpt.endswith(';'):
            inpt = inpt[:-1]
        if inpt.lower().endswith("!important"):
            important = True
            inpt = inpt[:-len("!important")]
        else:
            important = False
        name,val = inpt.split(':',1)
        name = name.strip()
        val = val.strip()
        return Attribute(parent,name, val, important)

    def merge(self, other):
        if self.attribute==other.attribute:
            if not self.important or other.important:
                if self.parent != None and other.parent != None and \
                   self.parent.compare_priority(other.parent)<=0:
                    self.value = other.value

    def get_copy(self):
        return Attribute(self.parent, self.attribute, self.value, self.important)

    def render(self, inline=False):
        rendered_string = "{}:{}".format(self.attribute,self.value)
        if self.important:
            rendered_string += "!important"
        rendered_string+=";"
        if inline:
            return rendered_string
        else:
            return "\t"+rendered_string


class Element(CSSAbstract):
    CLASS = 0
    ELEMENT = 1
    ID = 2

    def __init__(self, element_tag, element_type, attribute_filter=None, 
                       pseudo_class=None,pseudo_element=None):
        self.element_tag = element_tag
        self.element_type = element_type
        self.attribute_filter = attribute_filter
        self.pseudo_class = pseudo_class
        self.pseudo_element = pseudo_element

    def __repr__(self):
        return self.render(False)

    def __str__(self):
        return self.__repr__()

    def __eq__(self,other):
        return isinstance(other,Element) and ((self.element_tag==other.element_tag and \
                self.element_type==other.element_type) or \
                (self.element_tag=="*" or other.element_tag=="*")) and \
                self.attribute_filter==other.attribute_filter and \
                self.pseudo_class == other.pseudo_class and \
                self.pseudo_element == other.pseudo_element


    def __ne__(self, other):
        return not self == other

    def get_copy(self):
        return Element(self.element_tag, self.element_type, self.attribute_filter.get_copy())

    def get_priority(self):
        # [Inline styles,
        #  IDs,
        #  Classes, attributes and pseudo-classes,
        #  Elements and pseudo-elements]
        priority = [0,0,0,0]
        if self.element_type == Element.ID:
            priority[1]+=1
        elif self.element_type == Element.CLASS:
            priority[2]+=1
        else:
            priority[3]+=1
        if self.pseudo_class:
            priority[3]+=1
        if self.pseudo_element:
            priority[3]+=1
        if self.attribute_filter!=None:
            priority[2]+=1
        return priority

    @classmethod
    def parse(cls, inpt):
        inpt = inpt.strip()
        # again, there should only be one element passed anyway
        # P.S RE:'again', I wrote the parse methods starting at the bottom
        #                 of this file
        tokenized = cls.tokenize_selector(inpt).next()
        element_tag = tokenized.group('name')
        if not element_tag:
            element_tag = "*"
        if tokenized.group('type') == '.':
            element_type = cls.CLASS
        elif tokenized.groups('type') == '#':
            element_type = cls.ID
        else:
            element_type = cls.ELEMENT

        if tokenized.group('attribute'):
            attribute_filter = ElementFilter.parse(tokenized.group('attribute'))
        else:
            attribute_filter = None

        if tokenized.group("pseudo_class"):
            pseudo_class = Pseudo.parse(tokenized.group("pseudo_class"))
        else:
            pseudo_class = None
        if tokenized.group("pseudo_element"):
            pseudo_element = Pseudo.parse(tokenized.group("pseudo_element"))
        else:
            pseudo_element = None
        return Element(element_tag, element_type, attribute_filter,
                       pseudo_class, pseudo_element)

    def match(self, element):
        if not element:
            return False
        element_matches = False
        if self.element_type == Element.ID:
            element_matches = element.has_attribute("id") and \
                   element.get_attribute("id") == self.element_tag
        elif self.element_type == Element.ELEMENT:
            element_matches =  (element.tag == self.element_tag) or (self.element_tag=="*")
        elif self.element_type == Element.CLASS:
            element_matches =  element.has_attribute("class") and \
                   re.search(r"(?:^| ){}(?:$| )".format(self.element_tag),
                                element.get_attribute("class"))
        pseudo_element_matches = True
        if self.pseudo_element:
            pseudo_element_matches = self.pseudo_element.match(element)
        pseudo_class_matches = True
        if self.pseudo_class:
            pseudo_class_matches = self.pseudo_class.match(element)
        attribute_matches = True
        if self.attribute_filter:
            attribute_matches = self.attribute_filter.match(element)
        return pseudo_element_matches and pseudo_class_matches and \
                attribute_matches and element_matches

    def merge(self, other):
        if self != other:
            raise ValueError("behavior for merging non-equivalent elements is undefined")
        return self

    def render(self,inline=False):
        rendered_string = ""
        # Note that elements do not have a prefix
        if self.element_type == Element.ID:
            rendered_string+="#"
        elif self.element_type == Element.CLASS:
            rendered_string+="."
        rendered_string += self.element_tag
        if self.attribute_filter != None:
            rendered_string+="[{}]".format(self.attribute_filter.render(inline))
        if self.pseudo_class != None:
            rendered_string+=self.pseudo_class.render(inline)
        if self.pseudo_element != None:
            rendered_string+=self.pseudo_element.render(inline)
        return rendered_string


class ElementFilter(CSSAbstract):
    HAS = 0
    EQUALS = 1
    STARTS_WITH = 2
    STARTS_WITH_WORD = 4
    ENDS_WITH = 8
    CONTAINS = 16
    CONTAINS_WORD = 32

    def __init__(self, attribute, filter_type=None, value=None):
        self.attribute = attribute
        self.value = value
        self.filter_type = filter_type

    def __eq__(self, other):
        return isinstance(other, ElementFilter) and self.attribute==other.attribute and \
                self.filter_type==other.filter_type and self.value==other.value

    def __ne__(self, other):
        return not self == other

    def get_copy(self):
        return ElementFilter(self.attribute, self.filter_type, self.value)

    @classmethod
    def parse(cls, inpt):
        inpt = inpt.strip()
        tokenized = re.finditer(cls.FILTER_TOKENIZER,inpt).next()
        name = tokenized.group("name")
        if tokenized.group("value"):
            value = tokenized.group("value")
            if tokenized.group("type") == "^":
                filter_type = cls.STARTS_WITH
            elif tokenized.group("type") == "|":
                filter_type = cls.STARTS_WITH_WORD
            elif tokenized.group("type") == "$":
                filter_type = cls.ENDS_WITH
            elif tokenized.group("type") == "*":
                filter_type = cls.CONTAINS
            elif tokenized.group("type") == "~":
                filter_type = cls.CONTAINS_WORD
            else:
                filter_type = cls.EQUALS
        else:
            filter_type = None
            value = None
        return ElementFilter(name, filter_type, value)

    def match(self, element):
        if element.has_attribute(self.attribute):
            if self.filter_type == None:
                return True
            else:
                attribute_value = element.get_attribute(self.attribute)
                if self.filter_type == ElementFilter.EQUALS:
                    return attribute_value == self.value

                elif self.filter_type == ElementFilter.STARTS_WITH:
                    return attribute_value.startswith(self.value)

                elif self.filter_type == ElementFilter.STARTS_WITH_WORD:
                    return (attribute_value == self.value) or \
                           (attribute_value.startswith(self.value+'-'))

                elif self.filter_type == ElementFilter.ENDS_WITH:
                    return attribute_value.endswith(self.value)

                elif self.filter_type == ElementFilter.CONTAINS:
                    return self.value in attribute_value

                elif self.filter_type == ElementFilter.CONTAINS_WORD:
                    return re.search(r"\b{}\b".format(self.value),attribute_value)

    def merge(self, other):
        if self != other:
            raise ValueError("behavior for merging non-equivalent elements is undefined")
        return self

    def render(self,inline=False):
        if self.filter_type==None:
            return self.attribute
        else:
            output_template = '{}{}="{}"'
            if self.filter_type == ElementFilter.EQUALS:
                return output_template.format(self.attribute,'',self.value)
            elif self.filter_type == ElementFilter.STARTS_WITH:
                return output_template.format(self.attribute,'^',self.value)
            elif self.filter_type == ElementFilter.STARTS_WITH_WORD:
                return output_template.format(self.attribute,'|',self.value)
            elif self.filter_type == ElementFilter.ENDS_WITH:
                return output_template.format(self.attribute,'$',self.value)
            elif self.filter_type == ElementFilter.CONTAINS:
                return output_template.format(self.attribute,'*',self.value)
            elif self.filter_type == ElementFilter.CONTAINS_WORD:
                return output_template.format(self.attribute,'~',self.value)

class Pseudo(CSSAbstract):
    def __init__(self, name, argument=None, has_two_colons=False):
        self.name = name
        self.argument = argument
        self.has_two_colons = False # lol

    def __eq__(self,other):
        return isinstance(other, Pseudo) and \
                (self.name==other.name and self.argument==other.argument)

    def __ne__(self, other):
        return not self == other

    def get_copy(self):
        return Pseudo(self.name, self.argument, self.has_two_colons)

    @classmethod
    def parse(cls, inpt):
        tokenized = re.finditer(cls.PSEUDO_TOKENIZER, inpt).next()
        name = tokenized.group("name")
        if tokenized.group("argument") != None:
            argument = tokenized.group("argument").strip()
        else:
            argument = None
        has_two_colons = bool(tokenized.group("second_colon"))
        return Pseudo(name, argument, has_two_colons)

    @staticmethod
    def _parse_equation(s):
        s=s.lower()
        if s=="even":
            s="2n"
        elif s=="odd":
            s="2n+1"
        a = 1
        b = 0
        if not "n" in s:
            try:
                b = int(s)
                return lambda k:k==b
            except ValueError:
                return lambda k:False
        pre_n,post_n = s.split("n")
        pre_n.replace("*","")
        if pre_n=="-" or pre_n=="+":
            pre_n+="1"
        try:
            a = int(pre_n)
        except ValueError:
            pass
        try:
            b = int(post_n)
        except ValueError:
            pass
        return lambda k: ((k-b)/float(a)).is_integer() and ((k-b)/float(a))>=0

    def match(self, element):
        # unfortunately, as each pseudo-class has unique behaviour, each one
        # has to be programmed for individually
        #
        # also, pseudo-classes whose behaviour can not be determined from the
        # DOM (such as ':hover') are ignored and assumed False (to avoid 
        # accidentally applying hover styles to a normal element, to contiue
        # from the example before). Due to their complexity, pseudo-classes
        # relating to input elements are not currently supported either
        #
        # honestly, it is a shame python does not have switch statements, as 
        # this is the perfect case for one
        #
        if self.name == "empty":
            return element.get_empty()
        elif self.name == "first-child":
            if element.has_parent():
                return element.get_parent().get_tags().index(element)==0
            else:
                return True
        elif self.name == "first-of-type":
            if element.has_parent():
                return element.get_parent().get_tags(element.tag).index(element)==0
            else:
                return True
        elif self.name == "last-child":
            if element.has_parent():
                children = element.get_parent().get_tags()
                return children.index(element)==len(children)-1
            else:
                return True
        elif self.name == "last-of-type":
            if element.has_parent():
                children = element.get_parent().get_tags(element.tag)
                return children.index(element)==len(children)-1
            else:
                return True
        elif self.name == "nth-child":
            if element.has_parent():
                children = element.get_parent().get_tags()
                return self._parse_equation(self.argument)(children.index(element)+1)
            else:
                return True
        elif self.name == "nth-of-type":
            if element.has_parent():
                children = element.get_parent().get_tags(element.tag)
                return self._parse_equation(self.argument)(children.index(element)+1)
            else:
                return True
        elif self.name == "only-child":
            if element.has_parent():
                children = element.get_parent().get_tags()
                return len(children)==1 and element in children
            else:
                return True
        elif self.name == "only-of-type":
            if element.has_parent():
                children = element.get_parent().get_tags(element.tag)
                return len(children)==1 and element in children
            else:
                return True

    def merge(self, other):
        if self != other:
            raise ValueError("behavior for merging non-equivalent pseudo-elements is undefined")
        return self

    def render(self, inline=False):
        output_string = ":"
        if self.has_two_colons:
            output_string+=":"
        output_string += self.name
        if self.argument:
            output_string+="({})".format(self.argument)
        return output_string


class Selector(CSSAbstract):
    HAS_ALSO = 0
    HAS_CHILD = 1
    HAS_DIRECT_CHILD = 2
    HAS_NEXT_SIBLING = 4
    HAS_FOLLOWING_SIBLINGS = 8

    def __init__(self, tail, conn_type=None, head=None):
        # head and tail are both CSSElements or CSSSelectors
        self.head = head
        self.tail = tail
        self.conn_type = conn_type

    def __repr__(self):
        return self.render(False)

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if isinstance(other, Selector):
            if self.head and other.head and self.conn_type and other.conn_type:
                return self.head==other.head and self.tail==other.tail and \
                    self.conn_type==other.conn_type
            else:
                return self.tail == other.tail
        else:
            return False
    def __ne__(self, other):
        return not self == other

    def get_copy(self):
        if self.head:
            return Selector(self.tail.get_copy(), self.conn_type, self.head.get_copy())
        else:
            return Selector(self.tail.get_copy())

    def get_priority(self):
        if self.head:
            return map(sum,zip(*(self.head.get_priority(),self.tail.get_priority())))
        else:
            return self.tail.get_priority()

    def compare_priority(self, other):
        """ compares priority of another CSS Selector

        returns False if 'other' has higher priority """
        self_priority = self.get_priority()
        other_priority = other.get_priority()
        if len(self_priority)!=len(other_priority):
            raise ValueError("both iterables must have the same length")
        for i in range(len(self_priority)):
            if cmp(self_priority[i],other_priority[i])>0:
                return 1
            elif cmp(self_priority[i],other_priority[i])<0:
                return -1
        return 0

    def get_fragment(self, n_frags=0):
        if n_frags<1:
            return self
        else:
            node_list = [self]
            while isinstance(node_list[-1], Selector):
                node_list.append(node_list[-1].head)
            if n_frags<=len(node_list):
                return node_list[-1*n_frags]
            else:
                return None

    @classmethod
    def parse(cls, inpt):
        inpt = inpt.strip()
        tokens = list(cls.tokenize_selector(inpt))
        element = tokens[-1]
        tail = Element.parse(''.join(element.groups()[:-1]))

        if len(tokens)>1:
            parent = tokens[-2]
            if parent.group("conn_type"):
                if parent.group("conn_type")==" ":
                    conn_type = Selector.HAS_CHILD
                elif parent.group("conn_type")==">":
                    conn_type = Selector.HAS_DIRECT_CHILD
                elif parent.group("conn_type")=="+":
                    conn_type = Selector.HAS_NEXT_SIBLING
                elif parent.group("conn_type")=="~":
                    conn_type = Selector.HAS_FOLLOWING_SIBLINGS
            elif len(tokens)>1:
                conn_type = Selector.HAS_ALSO
            selector_string = ''.join([''.join([s or '' for s in t.groups()]) for t in tokens[:-1]])
            if len(tokens)<=2:
                head = Element.parse(selector_string)
            else:
                head = Selector.parse(selector_string)
        else:
            head = None
            conn_type = None
        return Selector(tail,conn_type,head)


    def match(self, element):
        if self.conn_type==None or self.head==None:
            return self.tail.match(element)
        else:
            head_match_value = False
            if self.conn_type == Selector.HAS_ALSO:
                head_match_value = self.head.match(element)

            elif self.conn_type == Selector.HAS_CHILD:
                for e in element.get_parents():
                    if self.head.match(e):
                        head_match_value = True
                        break

            elif self.conn_type == Selector.HAS_DIRECT_CHILD:
                head_match_value = self.head.match(element.get_parent())

            elif self.conn_type == Selector.HAS_NEXT_SIBLING:
                head_match_value = self.head.match(element.get_pre_siblings()[-1])

            elif self.conn_type == Selector.HAS_FOLLOWING_SIBLINGS:
                for e in element.get_pre_siblings():
                    if self.head.match(e):
                        head_match_value = True
                        break

            return self.tail.match(element) and head_match_value

    def merge(self, other):
        if self != other:
            raise ValueError("behavior for merging non-equivalent selectors is undefined")
        return self

    def render(self, inline=False):
        if inline:
            return ""

        if self.conn_type==None or self.head==None:
            return self.tail.render(inline)
        else:
            if self.conn_type == Selector.HAS_ALSO:
                return self.head.render(inline)+self.tail.render(inline) 
            elif self.conn_type == Selector.HAS_CHILD:
                return self.head.render(inline)+" "+self.tail.render(inline)
            elif self.conn_type == Selector.HAS_DIRECT_CHILD:
                return self.head.render(inline)+">"+self.tail.render(inline)
            elif self.conn_type == Selector.HAS_NEXT_SIBLING:
                return self.head.render(inline)+"+"+self.tail.render(inline)
            elif self.conn_type == Selector.HAS_FOLLOWING_SIBLINGS:
                return self.head.render(inline)+"~"+self.tail.render(inline)


class Style(CSSAbstract):
    def __init__(self,selector,*attributes):
        self.selector = selector
        self.attributes = list(attributes)

    def __repr__(self):
        return "('{}',{})".format(str(self.selector),len(self.attributes))

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, Style) and self.selector==other.selector

    def __ne__(self, other):
        return not self == other

    def add_attribute(self,attribute):
        self.attributes.append(attribute)

    def get_copy(self):
        return Style(self.selector.get_copy(), 
            *[attribute.get_copy() for attribute in self.attributes])

    @classmethod
    def parse(cls, inpt):
        #there should only be 1 style, so that will be the only one we care about
        match_obj = re.finditer(cls.CSS_TOKENIZER, inpt).next()
        selector = Selector.parse(match_obj.group("selector"))
        new_style = Style(selector)
        for attribute in match_obj.group("attributes").split(";"):
            if attribute.strip():
                new_style.add_attribute(Attribute.parse(attribute,selector))
        return new_style

    def match(self, element):
        return self.selector.match(element)

    def merge(self, other):
        if self != other:
            return None
        if self.selector.compare_priority(other.selector)<=0:
            for attribute in other.attributes:
                if attribute in self.attributes:
                    attribute_index = self.attributes.index(attribute)
                    self.attributes[attribute_index].merge(attribute)
                else:
                    self.attributes.append(attribute.get_copy())
        return self

    def render(self, inline=False):
        rendered_string = ""
        if not inline:
            rendered_string += self.selector.render(inline)+" {"
            for attribute in self.attributes:
                rendered_string+="\n"+attribute.render(inline)
            rendered_string+="\n}\n"
        else:
            for attribute in self.attributes:
                rendered_string+=attribute.render(inline)
        return rendered_string


class StyleSheet(CSSAbstract):
    def __init__(self):
        self.styles = []

    def __repr__(self):
        return "CSS Stylesheet ({} styles)".format(len(self.styles))

    def __str__(self):
        return self.__repr__()

    def add_style(self, style):
        self.styles.append(style)

    def remove_style(self, style):
        self.styles.remove(style)

    @classmethod
    def parse(cls, inpt):
        new_stylesheet = StyleSheet()
        for style in re.finditer(cls.CSS_TOKENIZER, inpt):
            selectors =  style.group("selector").split(",")
            for selector in selectors:
                selector = selector.strip()
                new_style = Style.parse("{}{{{}}}".format(selector, style.group("attributes"))) 
                new_stylesheet.add_style(new_style)
       
        return new_stylesheet

    def match(self, element,collapse=True):
        matching = []
        for style in self.styles:
            if style.match(element):
                matching.append(style)
        if collapse:
            new_style = Style("*{}")
            for style in matching:
                new_style.merge(style)
            return new_style
        else:
            return matching
    
    def merge(self, other):
        for style in other.styles:
            if style in self.styles:
                self.styles[self.styles.index(style)].merge(style)
            else:
                self.styles.append(style)

    def safe_merge(self, other):
        new_stylesheet = self.get_copy()
        for style in other.styles:
            if style in new_stylesheet.styles:
                new_stylesheet.styles[new_stylesheet.index(style)].merge(style)
            else:
                new_stylesheet.styles.append(style)
        return new_stylesheet

    def render(self,inline=False):
        rendered_string = ""
        if inline:
            inline_style = Style.parse("* {}")
            for style in self.styles:
                inline_style.merge(style)
            rendered_string+=inline_style.render(inline)
        else:
            for style in self.styles:
                rendered_string+=style.render(inline)
        return rendered_string
