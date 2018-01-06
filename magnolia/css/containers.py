from bisect import insort as sorted_insert 

from static import Style
from dynamic import AtRule, AtQuery
from _abstract import (CSSAbstract, ContainerAbstract, 
                      StaticAbstract, CSSParserError)

class StyleSheet(CSSAbstract, ContainerAbstract, StaticAbstract):
    def __init__(self):
        super(StyleSheet,self).__init__()
        self._items = []
        
        self._style_map = {}
        self._styles = []
        self._at_rules = [] #todo: make this a map

    def __repr__(self):
        return "CSS Stylesheet ({} styles)".format(len(self._items))

    def __str__(self):
        return self.__repr__()

    def __bool__(self):
        return bool(self._items)

    def __nonzero__(self):
        return self.__bool__()

    def has(self, item):
        return item in self._items

    def add(self, item):
        sorted_insert(self._items, item)
        if isinstance(item, Style):
            sorted_insert(self._styles, item)
            if not item.selector.tail in self._style_map:
                self._style_map[item.selector.tail] = []
            sorted_insert(self._style_map[item.selector.tail],item)
        elif isinstance(item, AtRule):
            sorted_insert(self._styles, item)
            sorted_insert(self._at_rules, item)
        else:
            raise TypeError("'item' must be of type 'Style' or type 'AtRule'")

    def remove(self, item):
        if self.has(item):
            self._items.remove(item)
            if isinstance(item,Style) and item in self._styles:
                self._styles.remove(item)
                self._style_map[item.selector.tail].remove(item)
                if not self._style_map[item.selector.tail]:
                    del self._style_map[item.selector.tail]
            elif isinstance(item, AtRule):
                self._at_rules.remove(item)


    def has_property(self, name):
        for item in self._items:
            if isinstance(item, Style):
                if item.has_property(name):
                    return True
        return False

    def get_property(self, name):
        self.flatten().get_property(name)

    def get_copy(self, inherited=False):
        new_stylesheet = StyleSheet()
        new_stylesheet._instance_no = self._instance_no
        for item in self._items:
            if isinstance(item, Style):
                inherited_style = item.get_copy(inherited)
                if inherited_style:
                    new_stylesheet.add(inherited_style)
            elif isinstance(item, AtRule):
                new_stylesheet.add(item.get_copy())
        return new_stylesheet

    @classmethod
    def _parse(cls, inpt, new_stylesheet=None, src=None):
        # todo make this recursive
        #
        # for the parsing order, first comments are removed, then at-rules
        # are handled, then the rest of the styles are handled
        new_stylesheet = StyleSheet()
        for token in cls._parse_css(inpt,src=src):
            if token.head.startswith("@"):
                new_item = AtRule.parse(token.text)
                new_stylesheet.add(new_item)
            else:
                selectors = [s.strip() for s in token.head.split(",")]
                for selector in selectors:
                    new_stylesheet.add(Style.parse("{}{{{}}}".format(selector, token.tail)))
        return new_stylesheet

    @classmethod
    def parse(cls, inpt,src=None):
        # this is set up to allow for recursive parsing later on
        return cls._parse(inpt,src=src)

    def flatten(self, new_style=None):
        if new_style!=None:
            flattened_style = new_style
        else:
            flattened_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
        for item in self._items:
            if isinstance(item, Style):
                flattened_style.merge(item, check_equality=False)
        return flattened_style

    def match(self, element):
        matching = []
        for style_stub in self._style_map:
            if style_stub.match(element):
                for style in self._style_map[style_stub]:
                    if style.match(element):
                        matching.append(style)
        for at_rule in self._at_rules:
            child_match = at_rule.match(element)
            if child_match:
                matching.append(child_match)
        return matching

    def merge(self, other):
        if isinstance(other, StyleSheet):
            for item in other._items:
                if item in self._items:
                    self._items[self._items.index(item)].merge(item)
                else:
                    self.add(item)
        elif isinstance(other, (Style,AtRule)):
            if other in self._items:
                self._items[self._items.index(other)].merge(other)
            else:
                self.add(other)

    def render(self,flags=0):
        if flags&CSSAbstract.INLINE and flags&CSSAbstract.AT_RULES:
            raise ValueError("INLINE flag may not be passed with AT_RULES flag")
        rendered_string = ""
        if flags&CSSAbstract.INLINE:
            inline_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
            for item in self._items:
                if isinstance(item, Style):
                    if not item.inherited or flags&CSSAbstract.INHERITED:
                        inline_style.merge(item, False)
            rendered_string+=inline_style.render(flags)
        else:
            for item in self._items:
                if flags&CSSAbstract.AT_RULES and isinstance(item, AtRule):
                    rendered_string+=item.render(flags)
                if flags&CSSAbstract.STYLES and isinstance(item, Style):
                    if not item.inherited or flags.CSSAbstract.INHERITED:
                        rendered_string+=item.render(flags)
        return rendered_string