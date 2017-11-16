import re
import abc

AT_RULES = ["charset","import","namespace","media","supports","document",
            "page","font-face","keyframes","viewport","counter-style",
            "font-feature-values","swash","ornaments","annotation",
            "stylistic","styleset","character-variant"]

INHERITED_ATTRIBUTES = ["caption-side","caret-color","color","cursor",
                        "direction","empty-cells","font","font-family",
                        "font-feature-settings","font-kerning",
                        "font-language-override","font-size","font-size-adjust",
                        "font-stretch","font-style","font-synthesis",
                        "font-variant","font-variant-alternates",
                        "font-variant-caps","font-variant-east-asian",
                        "font-variant-ligatures","font-variant-numeric",
                        "font-variant-position","font-weight",
                        "hanging-punctuation","hyphens","image-orientation",
                        "image-rendering","letter-spacing","line-height",
                        "list-style","list-style-image","list-style-position",
                        "list-style-type","object-position","orphans",
                        "overflow-wrap","pointer-events","quotes","ruby-align",
                        "ruby-position","tab-size","text-align",
                        "text-align-last","text-combine-upright","text-indent",
                        "text-justify","text-orientation","text-rendering",
                        "text-shadow","text-transform",
                        "text-underline-position","visibility","white-space",
                        "widows","word-break","word-spacing","word-wrap",
                        "writing-mode"]

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

# sorting longest to shortest will ensure short-circuit matches do not occur
# for example, 'first' matching 'first-child'
PSEUDO_CLASSES.sort(key=lambda i:len(i),reverse=True)
PSEUDO_ELEMENTS.sort(key=lambda i:len(i),reverse=True)

class CSSParserError(Exception):
    pass

class CSSAbstract():
    __metaclass__ = abc.ABCMeta
    AT_RULE_SELECTOR = re.compile(r"@(?P<rule_type>[_a-zA-Z\-]+)\s+(?P<args>.*?)" 
                                  r"(?:;\s*$|(?P<nested>\{))",re.DOTALL|re.MULTILINE)

    AT_RULE_TOKENIZER = re.compile(r"@\s*(?P<name>{rules})\s+(?P<args>.*?)"
                                   r"(?P<end>;\s*$|\{{)".format(rules="|".join(AT_RULES)),
                                re.DOTALL|re.MULTILINE)

    CSS_TOKENIZER = re.compile(r"(?P<style>(?P<selector>[^{}]*){(?P<rules>(?:.|\n)*?)})",
                                re.MULTILINE|re.DOTALL)

    # https://www.w3.org/TR/CSS21/grammar.html
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

    PSEUDO_TOKENIZER = re.compile(r"::?(?P<name>{pseudo_names})"
                                  r"(?:\((?P<argument>.*?)\))?".format(
                                   pseudo_names="|".join(PSEUDO_CLASSES+PSEUDO_ELEMENTS)),re.DOTALL)

    INLINE = 1
    AT_RULES = 2
    STYLES = 4

    @classmethod
    def tokenize_selector(cls, inpt):
            results = re.finditer(cls.SELECTOR_TOKENIZER, inpt)
            found = []
            for result in results:
                if any(result.groups()):
                    found.append(result)
            return iter(found)

    @classmethod
    def parse_at_rules(cls, inpt):
        for at_rule in re.finditer(cls.AT_RULE_SELECTOR,inpt):
            rule_dict = {'rule_type':at_rule.group("rule_type"),
                         'args':at_rule.group("args"),
                         'nested':at_rule.group("nested"),
                         'span':(0,0),
                         'content':None}
            if at_rule.group("nested"):
                nest_layer = 1
                i = at_rule.end()
                while nest_layer>0:
                    i+=1
                    if inpt[i]=="{":
                        nest_layer+=1
                    elif inpt[i]=="}":
                        nest_layer-=1
                rule_dict['content'] = inpt[at_rule.end():i]
                rule_dict['span'] = (at_rule.start(),i)
            else:
                rule_dict['span'] = at_rule.span()
            yield rule_dict # this is supposed to mimic the behavior of finditer

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
    def render(self, flags=0):
        return

class StyleContainer():
    __metaclass__ = abc.ABCMeta
    def __init__(self):
        self.styles = []

    @classmethod
    def _parse_styles(cls, new_container, inpt):
        for style in re.finditer(cls.CSS_TOKENIZER, inpt):
            selectors =  style.group("selector").split(",")
            for selector in selectors:
                selector = selector.strip()
                new_style = Style.parse("{}{{{}}}".format(selector, style.group("rules"))) 
                new_container.add_style(new_style)

    def add_style(self, style):
        self.styles.append(style)

    def remove_style(self, style):
        self.styles.remove(style)


class Property:
    def __init__(self, style, name, value, important=False):
        self.style = style
        self.name = name
        self.value = value
        self.important = important
        self.inline = False
        self.inherited = False

    def __repr__(self):
        return "('{}','{}',{})".format(self.name, self.value, self.important)

    def __eq__(self, other):
        """ NOTE: this does NOT compare attrribute values """
        return isinstance(other, Property) and self.name==other.name

    def __ne__(self, other):
        return not self == other

    @classmethod
    def parse(cls, inpt,style=None):
        inpt = inpt.strip()
        if inpt.endswith(';'):
            inpt = inpt[:-1]
        if inpt.lower().endswith("!important"):
            important = True
            inpt = inpt[:-len("!important")]
        else:
            important = False
        if not inpt:
            raise CSSParserError("Invalid rule provided.")
        name,val = inpt.split(':',1)
        name = name.strip()
        val = val.strip()
        return Property(style,name, val, important)

    def get_priority(self, other):
        priority = [0,0,0]
        priority[0] = not self.inherited
        priority[1] = self.inline
        priority[2] = self.style.selector.compare_priority(other.style.selector)
        return priority

    def compare_priority(self, other):
        self_priority = self.get_priority(other)
        other_priority = other.get_priority(other)

        if len(self_priority)!=len(other_priority):
            raise ValueError("both iterables must have the same length")
        for i in range(len(self_priority)):
            if cmp(self_priority[i],other_priority[i])>0:
                return 1
            elif cmp(self_priority[i],other_priority[i])<0:
                return -1
        return 0

    def merge(self, other):
        if self.name==other.name:
            if not self.important or other.important:
                if self.style != None and other.style != None and \
                   self.compare_priority(other)<=0:
                    self.value = other.value

    def get_copy(self, parent=None):
        if parent:
            new_property = Property(parent, self.name, self.value, self.important)
        else:
            new_property = Property(self.style, self.name, self.value, self.important)
        new_property.inherited = self.inherited
        new_property.inline = self.inline
        return new_property

    def render(self, flags=0):
        rendered_string  = ""
        rendered_string += "{}:{}".format(self.name,self.value)
        if not flags&CSSAbstract.INLINE:
            rendered_string = "\t"+rendered_string
            if self.important:
                rendered_string += "!important"
        return rendered_string+";"


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
        new_attribute_filter = None
        if self.attribute_filter:
            new_attribute_filter = self.attribute_filter.get_copy()
        new_pseudo_class = None
        if self.pseudo_class:
            new_pseudo_class = self.pseudo_class.get_copy()
        new_pseudo_element = None
        if self.pseudo_element:
            new_pseudo_element = self.pseudo_element.get_copy()
        return Element(self.element_tag, self.element_type, new_attribute_filter,
                       new_pseudo_class, new_pseudo_element)

    def get_priority(self):
        # [Inline styles,
        #  IDs,
        #  Classes, attributes and pseudo-classes,
        #  Elements and pseudo-elements]
        priority = [0,0,0,0]
        if self.element_type == Element.ID:
            priority[-3]+=1
        elif self.element_type == Element.CLASS:
            priority[-2]+=1
        else:
            priority[-1]+=1
        if self.pseudo_class:
            priority[-1]+=1
        if self.pseudo_element:
            priority[-1]+=1
        if self.attribute_filter!=None:
            priority[-2]+=1
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
        elif tokenized.group('type') == '#':
            element_type = cls.ID
        else:
            element_type = cls.ELEMENT
            element_tag = element_tag

        if tokenized.group('attribute'):
            attribute_filter = AttributeFilter.parse(tokenized.group('attribute'))
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

    # https://www.w3.org/TR/CSS2/syndata.html#characters (for case sensitivity)
    def match(self, element):
        if not element:
            return False
        element_matches = False
        if self.element_type == Element.ID:
            element_matches = element.has_attribute("id") and \
                   element.get_attribute("id") == self.element_tag
        elif self.element_type == Element.ELEMENT:
            element_matches = (element.name.lower() == self.element_tag.lower()) \
                                or (self.element_tag=="*")
        elif self.element_type == Element.CLASS:
            element_matches =  element.has_attribute("class") and \
                   self.element_tag in element.get_attribute("class").split(" ")
            
        attribute_matches = True
        if self.attribute_filter:
            attribute_matches = self.attribute_filter.match(element)
        pseudo_element_matches = True
        if self.pseudo_element:
            pseudo_element_matches = self.pseudo_element.match(element)
        pseudo_class_matches = True
        if self.pseudo_class:
            pseudo_class_matches = self.pseudo_class.match(element)
        return pseudo_element_matches and pseudo_class_matches and \
                attribute_matches and element_matches

    def merge(self, other):
        if self != other:
            raise ValueError("behavior for merging non-equivalent elements is undefined")
        return self

    def render(self,flags=0):
        rendered_string = ""
        if flags&CSSAbstract.INLINE:
            return rendered_string
        # Note that elements do not have a prefix
        if self.element_type == Element.ID:
            rendered_string+="#"
        elif self.element_type == Element.CLASS:
            rendered_string+="."
        rendered_string += self.element_tag
        if self.attribute_filter != None:
            rendered_string+="[{}]".format(self.attribute_filter.render(flags))
        if self.pseudo_class != None:
            rendered_string+=self.pseudo_class.render(flags)
        if self.pseudo_element != None:
            rendered_string+=self.pseudo_element.render(flags)
        return rendered_string


class AttributeFilter(CSSAbstract):
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
        return isinstance(other, AttributeFilter) and self.attribute==other.attribute and \
                self.filter_type==other.filter_type and self.value==other.value

    def __ne__(self, other):
        return not self == other

    def get_copy(self):
        return AttributeFilter(self.attribute, self.filter_type, self.value)

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
        return AttributeFilter(name, filter_type, value)

    def match(self, element):
        if element.has_attribute(self.attribute):
            if self.filter_type == None:
                return True
            else:
                attribute_value = element.get_attribute(self.attribute)
                if self.filter_type == AttributeFilter.EQUALS:
                    return attribute_value == self.value

                elif self.filter_type == AttributeFilter.STARTS_WITH:
                    return attribute_value.startswith(self.value)

                elif self.filter_type == AttributeFilter.STARTS_WITH_WORD:
                    return (attribute_value == self.value) or \
                           (attribute_value.startswith(self.value+'-'))

                elif self.filter_type == AttributeFilter.ENDS_WITH:
                    return attribute_value.endswith(self.value)

                elif self.filter_type == AttributeFilter.CONTAINS:
                    return self.value in attribute_value

                elif self.filter_type == AttributeFilter.CONTAINS_WORD:
                    return re.search(r"\b{}\b".format(self.value),attribute_value)

    def merge(self, other):
        if self != other:
            raise ValueError("behavior for merging non-equivalent elements is undefined")
        return self

    def render(self,flags=0):
        if flags&CSSAbstract.INLINE:
            return ""
        if self.filter_type==None:
            return self.attribute
        else:
            output_template = '{}{}="{}"'
            if self.filter_type == AttributeFilter.EQUALS:
                return output_template.format(self.attribute,'',self.value)
            elif self.filter_type == AttributeFilter.STARTS_WITH:
                return output_template.format(self.attribute,'^',self.value)
            elif self.filter_type == AttributeFilter.STARTS_WITH_WORD:
                return output_template.format(self.attribute,'|',self.value)
            elif self.filter_type == AttributeFilter.ENDS_WITH:
                return output_template.format(self.attribute,'$',self.value)
            elif self.filter_type == AttributeFilter.CONTAINS:
                return output_template.format(self.attribute,'*',self.value)
            elif self.filter_type == AttributeFilter.CONTAINS_WORD:
                return output_template.format(self.attribute,'~',self.value)

class Pseudo(CSSAbstract):
    def __init__(self, name, argument=None):
        self.name = name
        self.argument = argument

    def __eq__(self,other):
        return isinstance(other, Pseudo) and \
                (self.name==other.name and self.argument==other.argument)

    def __ne__(self, other):
        return not self == other

    def get_copy(self):
        return Pseudo(self.name, self.argument)

    @classmethod
    def parse(cls, inpt):
        tokenized = re.finditer(cls.PSEUDO_TOKENIZER, inpt).next()
        name = tokenized.group("name")
        if tokenized.group("argument") != None:
            argument = tokenized.group("argument").strip()
        else:
            argument = None
        return Pseudo(name, argument)

    @staticmethod
    def _parse_equation(inpt):
        inpt=inpt.lower()
        if inpt=="even":
            inpt="2n"
        elif inpt=="odd":
            inpt="2n+1"
        a = 1
        b = 0
        if not "n" in inpt:
            try:
                b = int(inpt)
                return lambda k:k==b
            except ValueError:
                return lambda k:False
        pre_n,post_n = inpt.split("n")
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
                return element.get_parent().get_tags(element.name).index(element)==0
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
                children = element.get_parent().get_tags(element.name)
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
                children = element.get_parent().get_tags(element.name)
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
                children = element.get_parent().get_tags(element.name)
                return len(children)==1 and element in children
            else:
                return True

    def merge(self, other):
        if self != other:
            raise ValueError("behavior for merging non-equivalent pseudo-elements is undefined")
        return self

    def render(self, flags=0):
        if flags&CSSAbstract.INLINE:
            return ""
        output_string = ":"
        if self.name in PSEUDO_ELEMENTS:
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
            elif (not self.head and other.head) or (self.head and not other.head) \
                  or (not self.conn_type and other.conn_type) \
                  or (self.conn_type and not other.conn_type):
                return False
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
            # this made sense when I wrote it, have fun working through what
            # it does now :P
            #
            # in all truth, the zip(*(foo,bar)) makes 2 lists into on list
            # of tuple value pairs, then map(sum,baz) takes the sum of those
            # pairs.... effectively the whole thing returns a sum of the
            # corresponding elements in both lists in a new list 
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
                if not element.has_parent():
                    return False
                head_match_value = self.head.match(element.get_parent())

            elif self.conn_type == Selector.HAS_NEXT_SIBLING:
                if not element.get_pre_siblings():
                    return False
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

    def render(self, flags=0):
        if flags&CSSAbstract.INLINE:
            return ""

        if self.conn_type==None or self.head==None:
            return self.tail.render(flags)
        else:
            if self.conn_type == Selector.HAS_ALSO:
                return self.head.render(flags)+self.tail.render(flags) 
            elif self.conn_type == Selector.HAS_CHILD:
                return self.head.render(flags)+" "+self.tail.render(flags)
            elif self.conn_type == Selector.HAS_DIRECT_CHILD:
                return self.head.render(flags)+">"+self.tail.render(flags)
            elif self.conn_type == Selector.HAS_NEXT_SIBLING:
                return self.head.render(flags)+"+"+self.tail.render(flags)
            elif self.conn_type == Selector.HAS_FOLLOWING_SIBLINGS:
                return self.head.render(flags)+"~"+self.tail.render(flags)


class Style(CSSAbstract):
    UNIVERSAL_EMPTY_STYLE = "* {}"
    def __init__(self,selector,*properties):
        self.selector = selector
        self.properties = list(properties)
        self.inline = False
        self.inherited = False

    def __repr__(self):
        return "('{}',{})".format(str(self.selector),len(self.properties))

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, Style) and self.selector==other.selector

    def __ne__(self, other):
        return not self == other

    def __bool__(self):
        return bool(len(self.properties))

    def __nonzero__(self):
        return self.__bool__()

    @property 
    def inline(self):
        return self._inline

    @inline.setter
    def inline(self, val):
        for p in self.properties:
            p.inline = val
        self._inline = val

    @property 
    def inherited(self):
        return self._inherited

    @inherited.setter
    def inherited(self, val):
        # print "Setting inherited to {}".format(val)
        for p in self.properties:
            p.inherited = val
        self._inherited = val

    def add_property(self,p):
        self.properties.append(p)       

    def has_property(self, name):
        for p in self.properties:
            if p.name==name:
                return True 

    def get_property(self, name):
        for p in self.properties:
            if p.name==name:
                return p

    def set_property(self, name, val):
        for p in self.properties:
            if p.name==name:
                p.value = val
                break

    def get_copy(self, inherited=False):
        if inherited:
            new_style = Style(self.selector.get_copy())
            for p in self.properties:
                if p.name in INHERITED_ATTRIBUTES:
                    new_style.add_property(p.get_copy(new_style))
        else:
            new_style = Style(self.selector.get_copy(), 
                *[p.get_copy() for p in self.properties])
        new_style.inline = self.inline
        new_style.inherited = inherited or self.inherited
        return new_style

    @classmethod
    def from_properties(self,inpt,selector=None):
        if not selector:
            selector = Style.UNIVERSAL_EMPTY_STYLE
        selector = Selector.parse(selector) # man I love not having types in python
        new_style = Style(selector)
        for p in inpt.split(";"):
            if p:
                new_style.add_property(Property.parse(p, new_style))
        return new_style

    @classmethod
    def parse(cls, inpt):
        #there should only be 1 style, so that will be the only one we care about
        match_obj = re.finditer(cls.CSS_TOKENIZER, inpt)
        if match_obj:
            match_obj = match_obj.next()
        else:
            return None
        selector = Selector.parse(match_obj.group("selector"))
        new_style = Style(selector)
        for attribute in match_obj.group("rules").split(";"):
            if attribute.strip():
                new_style.add_property(Property.parse(attribute,new_style))
        return new_style

    def match(self, element):
        return self.selector.match(element)

    def merge(self, other, check_equality=True):
        if (self != other) and check_equality:
            return None
        # if this has a lower priority than the other or this is inherited
        # merge the styles together
        for attribute in other.properties:
            if attribute in self.properties:
                attribute_index = self.properties.index(attribute)
                self.properties[attribute_index].merge(attribute)
            else:
                self.properties.append(attribute.get_copy())
        return self

    def render(self, flags=0):
        rendered_string = ""
        if flags&CSSAbstract.INLINE:
            for attribute in self.properties:
                rendered_string+=attribute.render(flags)
        else:
            rendered_string += self.selector.render(flags)+" {"
            for attribute in self.properties:
                rendered_string+="\n"+attribute.render(flags)
            rendered_string+="\n}\n"
        return rendered_string


class AtRule(CSSAbstract, StyleContainer):
    # this should eventually be moved to a separate file
    def __init__(self, rule_type, arguments, nested):
        self.rule_type = rule_type
        self.arguments = arguments
        self.nested = nested
        self.styles = []

    def __eq__(self, other):
        return isinstance(other, AtRule) and self.rule_type==other.rule_type \
            and self.arguments==other.arguments and self.nested==other.nested

    def __ne__(self, other):
        return not self==other

    def get_copy(self):
        new_at_rule = AtRule(self.rule_type, self.arguments, self.nested)
        for style in self.styles:
            new_at_rule.add_style(style.get_copy())
        return new_at_rule

    @classmethod
    def parse(cls, inpt):
        tokenized = cls.parse_at_rules(inpt).next() #there should only be one
        new_at_rule = AtRule(tokenized['rule_type'], tokenized['args'], 
                      bool(tokenized['nested']))
        if tokenized['content'] and tokenized['nested']:
            cls._parse_styles(new_at_rule, tokenized['content'])
        return new_at_rule
    
    def match(self, e):
        # for the time being, at rules are completely ignored in computations
        return False 

    def merge(self, other):
        if self==other and self.nested:
            for style in other.styes:
                if style in self.styles:
                    style_index = self.styles.index(style)
                    self.styles[style_index].merge(style)
                else:
                    self.styles.append(style.get_copy())

    def render(self, flags=0):
        rendered_string = ""
        if flags&CSSAbstract.INLINE:
            raise CSSParserError("At rules can not be rendered inline.")
        elif flags&CSSAbstract.AT_RULES:
            rendered_string += "@"+" ".join((self.rule_type, self.arguments))
            if self.nested:
                rendered_styles = "\n".join(map(lambda s:s.render(flags),
                                                                     self.styles))
                # below is a really hacked way to indent all lines except the last newline
                rendered_string += "{{\n{}}}\n".format("\t"+rendered_styles.replace("\n","\n\t",
                    rendered_styles.count("\n")-1)) 
            else:
                rendered_string += ";\n"
        return rendered_string



class StyleSheet(CSSAbstract, StyleContainer):
    def __init__(self):
        self.styles = []
        self.at_rules = []

    def __repr__(self):
        return "CSS Stylesheet ({} styles)".format(len(self.styles))

    def __str__(self):
        return self.__repr__()

    def __bool__(self):
        return bool(self.styles)

    def __nonzero__(self):
        return self.__bool__()

    def add_at_rule(self, at_rule):
        self.at_rules.append(at_rule)

    def remove_at_rule(self, at_rule):
        self.at_rules.remove(at_rule)

    def get_copy(self, inherited=False):
        new_stylesheet = StyleSheet()
        for style in self.styles:
            if inherited:
                inherited_style = style.get_copy(inherited)
                if inherited_style:
                    new_stylesheet.add_style(inherited_style)   
            else:
                new_stylesheet.add_style(style.get_copy(inherited))
        for at_rule in self.at_rules:
            new_stylesheet.add_at_rule(at_rule.get_copy())
        return new_stylesheet

    @classmethod
    def parse(cls, inpt):
        # for the parsing order, first comments are removed, then at-rules
        # are handled, then the rest of the styles are handled
        new_stylesheet = StyleSheet()
        # remove comments
        # parse at rules
        offset=0
        for at_rule in cls.parse_at_rules(inpt):
            rule_string = "@{rule_type} {args}".format(
                    rule_type=at_rule['rule_type'],args=at_rule['args'])
            if at_rule['nested']:
                rule_string += "{{{content}}}".format(content=at_rule['content'])
            else:
                rule_string += ";"
            new_stylesheet.add_at_rule(AtRule.parse(rule_string))
            inpt = inpt[:at_rule['span'][0]-offset]+inpt[at_rule['span'][1]-offset:]
            offset += at_rule['span'][1]-at_rule['span'][0]
        # parse rest of styles
        cls._parse_styles(new_stylesheet, inpt)
       
        return new_stylesheet

    def flatten(self, new_style=None):
        if new_style!=None:
            flattened_style = new_style
        else:
            flattened_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
        for style in self.styles:
            flattened_style.merge(style, check_equality=False)
        return flattened_style

    def match(self, element):
        matching = []
        for style in self.styles:
            if style.match(element):
                matching.append(style)
        return matching

    def merge(self, other):
        if isinstance(other, StyleSheet):
            for style in other.styles:
                # if style:
                if style in self.styles:
                    self.styles[self.styles.index(style)].merge(style)
                else:
                    self.styles.append(style)
        elif isinstance(other, Style):
            # if other:
            if other in self.styles:
                self.styles[self.styles.index(other)].merge(other)
            else:
                self.styles.append(other)

    def render(self,flags=0):
        if flags&CSSAbstract.INLINE and flags&CSSAbstract.AT_RULES:
            raise ValueError("INLINE flag may not be passed with AT_RULES flag")
        rendered_string = ""
        if flags&CSSAbstract.INLINE:
            inline_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
            for style in self.styles:
                inline_style.merge(style, False)
            rendered_string+=inline_style.render(flags)
        else:
            if flags&CSSAbstract.AT_RULES:
                for at_rule in self.at_rules:
                    rendered_string+=at_rule.render(flags)
            if flags&CSSAbstract.STYLES:
                for style in self.styles:
                    rendered_string+=style.render(flags)
        return rendered_string
