import re

from _abstract import INHERITED_ATTRIBUTES, PSEUDO_ELEMENTS
from _abstract import CSSAbstract, CSSParserError


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
        tokenized = cls._tokenize_selector(inpt).next()
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
        elif self.name == "not":
            return not Selector.parse(self.argument).match(element)

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
        tokens = list(cls._tokenize_selector(inpt))
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

    def add_property(self,prop,value=None):
        if isinstance(prop,str):
            if value:
                self.properties.append(Property(self,prop, value))   
        elif isinstance(prop,Property):
            self.properties.append(prop)        

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
        match_obj = cls._parse_css(inpt)
        if match_obj:
            match_obj = match_obj.next()
        else:
            return None
        selector = Selector.parse(match_obj.head)
        new_style = Style(selector)
        for attribute in match_obj.tail.split(";"):
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
