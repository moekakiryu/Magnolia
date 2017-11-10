import re
from css import StyleSheet,Style

# To be used as command line args 
# ~~~~~~~~~~~~~~~~~~~~~ #

AUTO_CLOSE_TAGS = True

# General globs
# ~~~~~~~~~~~~~~~~~~~~~ #

# src: https://developer.mozilla.org/en-US/docs/Glossary/Empty_element
EMPTY_TAGS = ["area","base","br","col",
              "embed","hr","img","input",
              "keygen","link","meta","param",
              "source","track","wbr"]


class HTMLParserError(Exception):
    pass

class Element(object):
    HTML_TOKENIZER = re.compile(r"<\s*(?P<end_tag>/)?\s*(?P<name>[a-zA-Z\-]+)\s*"
                                r"(?P<attributes>(?:\s+[a-zA-Z0-9\-]+=[\"'].*?[\"'])*)"
                                r"\s*(?P<self_closing>/?)\s*>",re.DOTALL)

    def __init__(self, tag, parent=None, **attributes):
        self.tag = tag
        self.element_styles = StyleSheet()
        self.inline_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
        self.attributes = attributes
        self.parent = parent
        self.children = []

        self.inline_style.inline =True

    def __repr__(self):
        return "HTMLElement('{}',{} children)".format(self.tag, len(self.children))

    def __str__(self):
        return self.__repr__()

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self,attr)
        except AttributeError:
            found = []
            for child in object.__getattribute__(self,"children"):
                if child.tag==attr:
                    found.append(child)
            if found:
                return found
            else:
                raise

    def add_child(self, child):
        self.children.append(child)

    def remove_child(self, child):
        self.children.remove(child)

    def get_children(self, name):
        found = []
        for child in self.children:
            if child.tag == name:
                found.append(child)
        return found

    def has_parent(self):
        return bool(self.parent)

    def get_parent(self):
        return self.parent

    def get_parents(self):
        parents = []
        curr_node = self
        while curr_node.parent:
            parents.append(curr_node.parent)
            curr_node = curr_node.parent
        return parents

    def get_pre_siblings(self):
        if not self.parent:
            return []
        siblings = []
        for sibling in self.parent.children[:self.parent.children.index(self)]:
            if not sibling is self:
                siblings.append(sibling)
            else:
                break
        return siblings

    def get_post_siblings(self):
        if not self.parent:
            return []
        siblings = []
        for sibling in self.parent.children[self.parent.children.index(self)+1:]:
            if not sibling is self:
                siblings.append(sibling)
        return siblings

    def has_attribute(self, attribute):
        return attribute in self.attributes.keys()

    def get_attribute(self, attribute):
        if self.has_attribute(attribute):
            return self.attributes[attribute]
        else:
            return None

    def get_siblings(self):
        return self.get_pre_siblings()+self.get_post_siblings()

    def _apply_styles(self, stylesheet, inherited_styles=None):
        inline_selector = "{}>{}>Inline-Style {{}}".format(
            ">".join([parent.tag for parent in self.get_parents()[::-1]]),self.tag)
        if inherited_styles:
            self.element_styles.merge(inherited_styles)
        for style in stylesheet.match(self):
            print "Merging {} into element: {}".format(style, self)
            self.element_styles.merge(style)
        if self.has_attribute("style"):
            print "Parsing inline styles for: "+self.tag
            self.inline_style = Style.from_rules(self.get_attribute("style"),inline_selector)
            print "Added inline styles for: "+self.inline_style.render(StyleSheet.STYLES)
            self.inline_style.inline = True
            self.element_styles.merge(self.inline_style)
        # print "MAKING INHERITED COPY"
        inherited_styles = self.element_styles.get_copy(inherited=True)
        # if inherited_styles.styles:
        #     print inherited_styles.styles[-1].inherited
        for child in self.get_tags():
            child._apply_styles(stylesheet,inherited_styles)

    def apply_styles(self, stylesheet):
        self._apply_styles(stylesheet)     

    def reset_styles(self):
        self.element_styles = StyleSheet()
        for child in self.children:
            child.reset_styles()

    def get_tags(self, name=None):
        if name:
            return filter(lambda e: not isinstance(e, TextElement) and e.tag==name, self.children)
        else:
            return filter(lambda e: not isinstance(e, TextElement),self.children)

    def get_empty(self):
        for child in self.children:
            if not isinstance(child, TextElement):
                return False
            elif child.text.strip() != "":
                return False
        return True

    @staticmethod
    def _parse_attributes(attribute_string):
        if not attribute_string:
            return {}
        return {key.strip():val.strip() for key,val in 
            re.findall(r"(?P<name>[a-zA-Z0-9\-]+)=[\"'](?P<value>.*?)[\"']",attribute_string)}

    @staticmethod
    def _raise_end_tag_error(inpt, tag, error_string, *args, **kwargs):
        err_msg = "Unexpected end tag on line {{}}, col {{}}. {}".format(error_string.format( 
                                                                         *args, **kwargs))
        raise HTMLParserError(err_msg.format(inpt[:tag.start()].count("\n")+1,
                                             tag.start()-inpt.rfind("\n",0, tag.start())))

    @staticmethod
    def _get_next_tag(inpt,found_tags,last_tag,head):
        try:
            tag = found_tags.next()
        except StopIteration:
            return None
        if last_tag:
            head.add_child(TextElement(inpt[last_tag.end():tag.start()],head))
            # print "add 2: '{}'".format(inpt[last_tag.end():tag.start()])
        return tag

    @classmethod
    def _parse(cls, inpt, found_tags=None, prev_find=None, head=None):
        if not found_tags:
            found_tags = re.finditer(Element.HTML_TOKENIZER, inpt)
        tag = found_tags.next()
        if head:
            # add the text between the parent tag and the current tag
            if prev_find: 
                head.add_child(TextElement(inpt[prev_find.end():tag.start()],head))
                # print "add 1: '{}'".format(inpt[prev_find.end():tag.start()])
            # handle open tags
            last_tag = None
            while not tag.group("end_tag"):
                child = Element(tag.group("name"),parent=head,
                    **cls._parse_attributes(tag.group("attributes")))
                head.add_child(child)
                if tag.group("self_closing") or child.tag in EMPTY_TAGS:
                    last_tag = tag
                    tag = cls._get_next_tag(inpt,found_tags,last_tag,head)
                    # print "self closing"
                    if tag:
                        continue
                    else:
                        return
                last_tag = Element._parse(inpt, found_tags,tag,child)
                # if the closing tag did not match the opening tag return 
                # until it does 
                if last_tag and (last_tag.group("name") != child.tag) and head:
                    return last_tag
                elif not head:
                    # we should never reach this as the recursive search has 
                    # already confirmed a matching node somewhere in the tree
                    raise HTMLParserError("Could not find matching end node.")
                # print "for content: {}:{} {}:{}".format(last_tag.group("name"),last_tag.group("end_tag"),tag.group("name"),tag.group("end_tag"))
                tag = cls._get_next_tag(inpt,found_tags,last_tag,head)
                if not tag:
                    return
                    
            # handle end tags
            # if the end tag does not match its corresponding open tag
            if tag.group("end_tag"):
                if tag.group("name") in EMPTY_TAGS:
                    cls._raise_end_tag_error(inpt, tag,
                        "'{}' can not have an end tag.", tag.group("name"))
                elif tag.group("name") != head.tag:
                    # look up the tree and see if it matches anything
                    if not (tag.group("name") in map(lambda e:e.tag, head.get_parents()) and \
                        AUTO_CLOSE_TAGS):
                            cls._raise_end_tag_error(inpt, tag, 
                                "Expected '{}', got '{}'.",head.tag, tag.group("name"))
            return tag
        else:
            # if a head node has not been created yet
            if not tag.group("end_tag"):
                head = Element(tag.group("name"),head,
                    **cls._parse_attributes(tag.group("attributes")))
                Element._parse(inpt, found_tags,tag,head)
                return head
            else:
                return None
        # this is a failsafe, we should never get here 
        return None

    @classmethod
    def parse(cls, inpt,head=None):
        return cls._parse(inpt,head=head)
       
    def render(self, inline_style=False):
        attribute_string = ""
        attribute_format = '{}="{}"'
        for name, val in self.attributes.items():
            if isinstance(val,str):
                attribute_string += attribute_format.format(name,val)
            elif hasattr(val, "render"):
                pass
        if self.tag in EMPTY_TAGS:
            output_string = "<{} {}/>"
        else:
            output_string = "<{} {}>"
        output_string = output_string.format(self.tag, " ".join(
            [attribute_format.format(key,val) for key,val in self.attributes.items()]))
        for child in self.children:
            output_string += child.render(inline_style)
        if not self.tag in EMPTY_TAGS: 
            output_string+="</{}>".format(self.tag)
        return output_string



class TextElement(Element,object):
    def __init__(self, text, parent=None, **attributes):
        super(TextElement,self).__init__("", parent, **attributes)
        self.text = text

    def __repr__(self):
        return "HTMLText({} chars)".format(len(self.text))

    def __str__(self):
        return self.__repr__()

    def only_has_whitespace(self):
        return not bool(self.text.strip())

    def render(self, inline_style=False):
        return self.text
