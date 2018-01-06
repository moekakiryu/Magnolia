import re
import string

from configs import config
from css import StyleSheet
from css import Style
from css import Selector

# General locals
# ~~~~~~~~~~~~~~~~~~~~~ #
INHERITED_STYLE_SELECTOR = "__inherited_style"
INLINE_STYLE_SELECTOR = "__inline_style"

MASTER_ELEMENT_NAME = "__head__"

# src: https://developer.mozilla.org/en-US/docs/Glossary/Empty_element
VOID_ELEMENTS = ["area","base","br","col",
                 "embed","hr","img","input",
                 "keygen","link","meta","param",
                 "source","track","wbr"]

# src: https://developer.mozilla.org/en-US/docs/Web/SVG/Element
SVG_ELEMENTS = ["a","altGlyph","altGlyphDef","altGlyphItem","animate",
                "animateColor","animateMotion","animateTransform","audio",
                "canvas","circle","clipPath","color-profile","cursor","defs",
                "desc","discard","ellipse","feBlend","feColorMatrix",
                "feComponentTransfer","feComposite","feConvolveMatrix",
                "feDiffuseLighting","feDisplacementMap","feDistantLight",
                "feDropShadow","feFlood","feFuncA","feFuncB","feFuncG",
                "feFuncR","feGaussianBlur","feImage","feMerge","feMergeNode",
                "feMorphology","feOffset","fePointLight","feSpecularLighting",
                "feSpotLight","feTile","feTurbulence","filter","font",
                "font-face","font-face-format","font-face-name",
                "font-face-src","font-face-uri","foreignObject","g","glyph",
                "glyphRef","hatch","hatchpath","hkern","iframe","image","line",
                "linearGradient","marker","mask","mesh","meshgradient",
                "meshpatch","meshrow","metadata","missing-glyph","mpath",
                "path","pattern","polygon","polyline","radialGradient","rect",
                "script","set","solidcolor","stop","style","svg","switch",
                "symbol","text","textPath","title","tref","tspan","unknown",
                "use","video","view","vkern"]

# src: https://developer.mozilla.org/en-US/docs/Web/MathML/Element
MATHML_ELEMENTS = ["math","maction","maligngroup","malignmark","menclose",
                   "merror","mfenced","mfrac","mglyph","mi","mlabeledtr",
                   "mlongdiv","mmultiscripts","mn","mo","mover","mpadded",
                   "mphantom","mroot","mrow","ms","mscarries","mscarry",
                   "msgroup","msline","mspace","msqrt","msrow","mstack",
                   "mstyle","msub","msup","msubsup","mtable","mtd","mtext",
                   "mtr","munder","munderover","semantics","annotation",
                   "annotation-xml"]

class HTMLParserError(Exception):
    pass

class Element(object):
    # I am sorry bobince
    # https://stackoverflow.com/questions/1732348/regex-match-open-elements-except-xhtml-self-contained-elements#answer-1732454
    #
    # on a serious note, this needs to be removed in favour of a traditional 
    # parser
    HTML_TOKENIZER = re.compile(r"<\s*(?P<end_tag>/)?"
                        r"\s*(?P<name>[^\s\0\"'></=]+)\s*"
                        r"(?P<attributes>(?:[^\s\0\"'></=]+"
                        r"(?:\s*=\s*(?:(?P<oq>['\"])[^\4]*?(?P=oq)|(?P<unquot>[^\s\0\"'></=]+)))?\s*?)*)"
                        r"(?P<self_closing>(?:(?(unquot)\s)\s*?/)?)\s*>",re.DOTALL)
    INLINE_STYLES = 1

    def __init__(self, element_name, parent=None, **attributes):
        self.name = element_name
        self.parent = parent
        self.styles = StyleSheet()

        self._attributes = {str(k):str(v) for k,v in attributes.items()}
        self._inline_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
        self._children = []
        self._self_closing = False

        self._inline_style.inline =True

    def __repr__(self):
        return "HTMLElement('{}',{} children)".format(self.name, len(self._children))

    def __str__(self):
        return self.__repr__()

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self,attr)
        except AttributeError:
            if config.REFERENCE_ELEMENTS_AS_ATTRIBUTES:
                found = []
                for child in object.__getattribute__(self,"_children"):
                    if child.name==attr:
                        found.append(child)
                if found:
                    return found
                else:
                    raise
            else:
                raise

    def map(self, func):
        func(self)
        for child in self.get_elements():
            child.map(func)

    def filter(self, func):
        found = []
        if isinstance(func, str):
            func = Selector.parse(func)
        if isinstance(func,Selector):
            if func.match(self):
                found.append(self)
        else:
            if func(self): 
                found.append(self)
        for child in self.get_elements():
            found.extend(child.filter(func))
        return found

    def insert_child(self, child, index=-1, **attributes):
        if isinstance(child,str):
            new_child = Element(child, self, **attributes)
        elif isinstance(child, Element):
            new_child = child
            new_child.parent = self
        else:
            return
        if index<0:
            self._children.append(new_child)
        else:
            self._children.insert(index,new_child)

    def add_child(self,child, **attributes):
        self.insert_child(child,-1,**attributes)

    def remove_child(self, child):
        self._children.remove(child)

    def clear_children(self):
        self._children = []

    def has_child(self, child=None):
        if not child:
            return bool(self._children)
        else:
            return child in self._children

    def get_elements(self, name=None):
        if name:
            return filter(lambda e: not isinstance(e, TextElement) and e.name==name, self._children)
        else:
            return filter(lambda e: not isinstance(e, TextElement),self._children)

    def insert_element(self, element, index=-1, **attributes):
        if isinstance(element, str):
            new_child = Element(element,self,**attributes)
        elif isinstance(element, Element):
            new_child = element
            new_child.parent = self
        else:
            return
        if index<0:
            if len(self._children):
                target_index = self._children.index(self.get_elements()[-1])
                self._children.insert(target_index+1, new_child) # a weird case where you add after
            else:
                self._children.append(new_child)
        else:
            # convert the element index to the child index
            if self.get_elements():
                target_index = self._children.index(self.get_elements()[index])
            else:
                target_index = 0
            self._children.insert(target_index, new_child)    

    def add_element(self, element, **attributes):
        self.insert_element(element,-1, **attributes)

    def _get_empty(self, first_call=True):
        if not first_call and isinstance(self, Element):
            return False
        else:
            return all([child._get_empty(False) for child in self._children])

    def get_empty(self, ignore_void_elements=False):
        if ignore_void_elements and self.name in VOID_ELEMENTS:
            return False   
        return self._get_empty()   
   
    def get_pre_siblings(self):
        if not self.parent:
            return []
        siblings = []
        for sibling in self.parent._children[:self.parent._children.index(self)]:
            if not sibling is self:
                if not isinstance(sibling, TextElement):
                    siblings.append(sibling)
            else:
                break
        return siblings

    def get_post_siblings(self):
        if not self.parent:
            return []
        siblings = []
        for sibling in self.parent._children[self.parent._children.index(self)+1:]:
            if not sibling is self:
                if not isinstance(sibling, TextElement):
                    siblings.append(sibling)
        return siblings

    def get_pre_text(self):
        if not self.parent:
            return []
        siblings = []
        for sibling in self.parent._children[:self.parent._children.index(self)]:
            if not sibling is self:
                if isinstance(sibling, TextElement):
                    siblings.append(sibling)
                elif type(sibling) is Element:
                    siblings = []
            else:
                break
        return siblings

    def get_post_text(self):
        if not self.parent:
            return []
        siblings = []
        for sibling in self.parent._children[self.parent._children.index(self)+1:]:
            if not sibling is self:
                if isinstance(sibling, TextElement):
                    siblings.append(sibling)
                elif type(sibling) is Element:
                    break
        return siblings

    def add_text(self, text):
        if text:
            self._children.append(TextElement(text, self))

    def get_encapsulating_text(self):
        return self.get_pre_text()+self.get_post_text()

    def get_siblings(self):
        return self.get_pre_siblings()+self.get_post_siblings()

    def add_pre_sibling(self, element, **attributes):
        if isinstance(element, Element):
            self.parent.add_child

    def has_parent(self):
        return bool(self.parent)

    def get_parent(self):
        return self.parent

    def get_parents(self):
        parents = []
        curr_node = self
        while curr_node.parent and curr_node.parent.name != MASTER_ELEMENT_NAME:
            parents.append(curr_node.parent)
            curr_node = curr_node.parent
        return parents

    def has_attribute(self, attribute):
        return attribute in self._attributes.keys()

    def get_attribute(self, attribute):
        if self.has_attribute(attribute):
            return self._attributes[attribute]
        else:
            return None

    def set_attribute(self, attribute, value):
        self._attributes[attribute] = str(value)

    def has_styles(self):
        return bool(self.styles)

    def _apply_styles(self, inherited_style=None, *stylesheets):
        special_selector = "{}>{}>{{}} {{{{}}}}".format(
            ">".join([parent.name for parent in self.get_parents()[::-1]]),self.name)

        if inherited_style:
            self.styles.merge(inherited_style)
        if stylesheets:
            for stylesheet in stylesheets:
                for style in stylesheet.match(self):
                    self.styles.merge(style)
        elif self.has_attribute("style"):
            self._inline_style = Style.from_properties(self.get_attribute("style"),
                special_selector.format(INLINE_STYLE_SELECTOR))
            self._inline_style.inline = True
            self.styles.merge(self._inline_style)

        inherited_style = self.styles.flatten(Style.parse(
            special_selector.format(INHERITED_STYLE_SELECTOR)))
        inherited_style.inherited = True
        for child in self.get_elements():
            child._apply_styles(inherited_style, *stylesheets)

    def apply_styles(self, *stylesheets):
        self._apply_styles(None, *stylesheets)   

    def reset_styles(self):
        self.styles = StyleSheet()
        for child in self._children:
            child.reset_styles()

    def add_inline_property(self, name, value):
        self._inline_style.add_property(name, value)

    @staticmethod
    def _parse_attributes(attribute_string):
        if not attribute_string:
            return {}
        else:
            # we're parsing this baby
            # parsing as per https://www.w3.org/TR/2011/WD-html5-20110525/syntax.html#syntax-attribute-name
            attrs = {}
            k=i=0
            attr = val = ""
            string_char=None
            update_k = False
            passed_whitespace = False
            waiting_for_value = False
            while i<len(attribute_string):
                if (attribute_string[i] in "'\"" and (not string_char
                  or attribute_string[i]==string_char)):
                    if not attr:
                        raise HTMLParserError("Unexpected string encountered in element attribute")
                    elif string_char:
                        val = attribute_string[k:i]
                        if attr:
                            attrs[attr]=val
                            attr=val=""
                        else:
                            raise HTMLParserError("Attribute value encountered before name")
                        string_char = None
                    else:
                        string_char = attribute_string[i]
                    update_k = True

                elif string_char:
                    # if we are in a string
                    #
                    # note: there are very few rules for strings that I will 
                    #       be enforcing at the moment, so ignore all 
                    #       characters in string
                    pass

                elif attribute_string[i] in string.whitespace:
                    # if we are in unquoted value and encounter whitespace
                    passed_whitespace = True

                elif attribute_string[i]=="=":
                    if attr:
                        raise HTMLParserError("Unexpected '=' encountered,"
                                              " expected attribute value")
                    else:
                        attr = attribute_string[k:i].strip()
                        update_k = True
                        waiting_for_value = True
                        passed_whitespace = False

                # checking for some of these characters is redundant, but this
                # is done for consistency with the W3C html5 specs (at least
                # as much as possible)
                elif not string_char and attribute_string[i] in "'\"=<>`\0":
                    raise HTMLParserError("Invalid attribute character '{}' encountered".format(
                        attribute_string[i]))
                else:
                    # this should only be unquoted valid chars
                    if passed_whitespace:
                        if waiting_for_value and attribute_string[k:i].strip() and attr:
                            attrs[attr] = attribute_string[k:i].strip()
                            attr=val=""
                            k=i
                        elif attribute_string[k:i].strip():
                            attr = attribute_string[k:i].strip()
                            # this needs to be changed to 'None' eventually
                            attrs[attr] = ""
                            attr=val=""
                            k=i
                        passed_whitespace = False
                i+=1
                if update_k:
                    k=i
                    update_k = False
            if k<len(attribute_string):
                if attribute_string[k:i].strip():
                    if attr:
                        attrs[attr]=attribute_string[k:i].strip()
                    else:
                        attrs[attribute_string[k:i].strip()]=""
            return attrs

    @staticmethod
    def _raise_end_tag_error(inpt, element, error_string, *args, **kwargs):
        err_msg = "Unexpected end element on line {{}}, col {{}}. {}".format(error_string.format( 
                                                                         *args, **kwargs))
        raise HTMLParserError(err_msg.format(inpt[:element.start()].count("\n")+1,
                                             element.start()-inpt.rfind("\n",0, element.start())))

    @staticmethod
    def _get_next_element(inpt,found_elements):
        try:
            return found_elements.next()
        except StopIteration:
            return None

    @classmethod
    def _parse(cls, inpt, found_elements, prev_match=None, head=None):
        match = cls._get_next_element(inpt, found_elements)
        target = None
        while match:
            # add text from beore element
            if prev_match:
                head.add_text(inpt[prev_match.end():match.start()])
            else:
                head.add_text(inpt[:match.start()])
            # if it is an end element do not return
            if match.group("end_tag"):
                # also, confirm it matches parent element
                if match.group("name").lower()!=head.name.lower():
                    if ((not config.AUTO_CLOSE_ELEMENTS) or 
                        (not match.group("name").lower() in map(lambda e:e.name.lower(),
                                                                head.get_parents()))):
                        if head.name==MASTER_ELEMENT_NAME:
                            raise HTMLParserError(
                                "Unexpected end tag, got '{}'".format(
                                match.group('name'),head.name))
                        else:
                            raise HTMLParserError(
                                "Mismatched end tag, got '{}' expected '{}'".format(
                                match.group('name'),head.name))
                return match
            # according to https://www.w3.org/TR/2011/WD-html5-20110525/syntax.html#start-tags,
            # any foreign tag can be self-closing. I have made a couple lists of all self closing
            # tags and am using them to validate the html. This method is not ideal
            # and may be changed at a later date.
            elif match.group("self_closing") or match.group("name").lower() in VOID_ELEMENTS:
                if (match.group("name").lower() in VOID_ELEMENTS or (match.group("self_closing")
                  and (match.group("name") in SVG_ELEMENTS or match.group("name") in MATHML_ELEMENTS))):   
                    # if it is valid, add the element to head   
                    new_child = Element(match.group("name"),   
                        **cls._parse_attributes(match.group("attributes")))
                    new_child._self_closing = True
                    head.add_child(new_child)
                    # continue the search
                    # since this is an open and close element, it should not return
                    # but instead add a child and continue on
                    prev_match = match
                    match = cls._get_next_element(inpt, found_elements)
                    continue
                else:
                    raise HTMLParserError(
                        "'{}' can not have a self closing element".format(match.group("name")))
            else:
                target = Element(match.group("name"),
                    **cls._parse_attributes(match.group("attributes")))
                head.add_child(target)
                prev_match = cls._parse(inpt,found_elements,match, target)
            match = cls._get_next_element(inpt, found_elements)
        # if we are not at the top levl of recursion yet
        if head.name != MASTER_ELEMENT_NAME:
            # if we auto-clos elements, return until everything is closed
            if config.AUTO_CLOSE_ELEMENTS:
                if prev_match:
                    head.add_text(inpt[prev_match.end():])
                return
            else:
                raise HTMLParserError("Unexpected EOF, expected '{}' element".format(head.name))
        # if we are at the top level of recursion
        else:
            # add any leftover text at the end
            if prev_match:
                head.add_text(inpt[prev_match.end():])
            # if there are not elements at all, add everything as text
            # this can not be true if prev_match is not None
            elif not len(head._children):
                head.add_text(inpt)
        return head

    @classmethod
    def parse(cls, inpt,head=None):
        return cls._parse(inpt,re.finditer(cls.HTML_TOKENIZER,inpt),
            head=head if head else Element(MASTER_ELEMENT_NAME))
       
    def render(self, _inline_style=False):
        output_string = ""
        dq_format = '{}="{}"'
        sq_format = "{}='{}'"
        if self.name!=MASTER_ELEMENT_NAME:
            output_string = "<{}".format(self.name)
            key=val=None
            for key,val in sorted(self._attributes.items()):
                output_string += " "
                if key and val:
                    if '"' in val:
                        if "'" in val:
                            # any anttribute with both types of quotes should crash
                            # during parsing, but if for some reason a string
                            # makes it through, this will handle it correctly
                            output_string += dq_format.format(key,
                                val.replace('"',"&quot;"))
                        else:
                            output_string += sq_format.format(key,val)
                    else:
                        output_string += dq_format.format(key,val)
                else:
                    output_string += key                 
            if self.name in VOID_ELEMENTS or self._self_closing:
                if key or val:
                    output_string += " />"
                else:
                    output_string += "/>"   
            else:   
                output_string += ">" 
        if not (self.name in VOID_ELEMENTS or self._self_closing): 
            for child in self._children:
                output_string += child.render(_inline_style)
            if self.name!=MASTER_ELEMENT_NAME:
                output_string+="</{}>".format(self.name)
        return output_string   
   


class TextElement(Element,object):
    def __init__(self, text, parent=None, **attributes):
        super(TextElement,self).__init__("", parent, **attributes)
        self.text = text

    def __repr__(self):
        return "HTMLText({} chars)".format(len(self.text))

    def __str__(self):
        return self.__repr__()

    def _get_empty(self, first_call=True):
        return not bool(self.text.strip())

    @classmethod
    def _parse(cls, inpt, found_elements=None, prev_match=None, head=None):
        return TextElement(inpt, parent=head)

    def render(self, _inline_style=False):
        return self.text
