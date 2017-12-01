from static import Style
from dynamic import AtRule, AtQuery
from _abstract import StaticAbstract, CSSParserError

class AtRuleContainer(StaticAbstract):
    # this should eventually be moved to a separate file
    def __init__(self):
        raise NotImplementedError("This class has been deprecated. Please instead use StyleSheet class")
        self.rules = []

    def __repr__(self):
        return "CSS At-Rules Container ({} rules)".format(len(self.rules))

    # def __eq__(self, other):
    #     return isinstance(other, AtRule) and self.rule_type==other.rule_type \
    #         and self.arguments==other.arguments and self.nested==other.nested

    # def __ne__(self, other):
    #     return not self==other

    # def get_copy(self):
    #     new_at_rule = AtRule(self.rule_type, self.arguments, self.nested)
    #     for style in self.styles:
    #         new_at_rule.add_style(style.get_copy())
    #     return new_at_rule

    def add_rule(self, rule):
        self.rules.append(rule)

    def remove_rule(self, rule):
        if rule in self.rules:
            self.rules.remove(rule)

    def get_copy(self):
        new_rules = AtRuleContainer()
        for rule in self.rules:
            new_rules.add_rule(rule.get_copy())
        return new_rules

    @classmethod
    def parse(cls, inpt):
        new_container = AtRuleContainer
        for token in cls._parse_css(inpt):
            if token.head.startswith("@"):
                new_container.add_rule(AtRule.parse(token.text))
        return new_container
    
    def match(self, e):
        # for the time being, at rules are completely ignored in computations
        return False 

    def merge(self, other):
        if isinstance(other, AtRuleContainer):
            return

    def render(self, flags=0):
        if flags&StaticAbstract.AT_RULES:
            return "\n".join([rule.render(flags) for rule in self.rules])
        else:
            return ""


class StyleSheet(StaticAbstract):
    def __init__(self):
        self.styles = []
        self.at_rules = []

    def __repr__(self):
        return "CSS Stylesheet ({} styles, {} at-rules)".format(len(self.styles), 
                                                                len(self.at_rules))

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

    def add_style(self, style):
        self.styles.append(style)

    def remove_style(self, style):
        self.styles.remove(style)

    def has_property(self, name):
        for style in self.styles:
            if style.has_property(name):
                return True
        return False

    def get_property(self, name):
        self.flatten().get_property(name)

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
    def _parse(cls, inpt, new_stylesheet=None):
        # todo make this recursive
        #
        # for the parsing order, first comments are removed, then at-rules
        # are handled, then the rest of the styles are handled
        new_stylesheet = StyleSheet()
        for token in cls._parse_css(inpt):
            if token.head.startswith("@"):
                new_stylesheet.at_rules.append(AtRule.parse(token.text))
            else:
                selectors = [s.strip() for s in token.head.split(",")]
                for selector in selectors:
                    new_stylesheet.add_style(Style.parse("{}{{{}}}".format(selector, token.tail)))
        return new_stylesheet

    @classmethod
    def parse(cls, inpt):
        # this is set up to allow for recursive parsing later on
        return cls._parse(inpt)

    def flatten(self, new_style=None):
        if new_style!=None:
            flattened_style = new_style
        else:
            flattened_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
        for style in self.styles:
            flattened_style.merge(style, check_equality=False)
        return flattened_style

    def match(self, element, stylesheet=None):
        matching = []
        for style in self.styles:
            if style.match(element):
                matching.append(style)
        for at_rule in self.at_rules:
            rule_match = at_rule.match(element)
            if rule_match:
                matching.append(rule_match)
        return matching

    def merge(self, other):
        print "(Merging Stylesheets)"
        if isinstance(other, StyleSheet):
            for style in other.styles:
                # if style:
                if style in self.styles:
                    self.styles[self.styles.index(style)].merge(style)
                else:
                    self.styles.append(style)
            for at_rule in other.at_rules:
                if at_rule in self.at_rules:
                    self.at_rules[self.at_rules.index(at_rule)].merge(at_rule)
                else:
                    self.at_rules.append(at_rule)
        elif isinstance(other, Style):
            # if other:
            if other in self.styles:
                self.styles[self.styles.index(other)].merge(other)
            else:
                self.styles.append(other)
        elif isinstance(other, AtRule):
            print "Merging at-rule",other, self.at_rules
            if other in self.at_rules:
                self.at_rules[self.at_rules.index(other)].merge(other)
            else:
                self.at_rules.append(other)
            print "merged: {}".format(self.at_rules)

    def render(self,flags=0):
        if flags&StaticAbstract.INLINE and flags&StaticAbstract.AT_RULES:
            raise ValueError("INLINE flag may not be passed with AT_RULES flag")
        rendered_string = ""
        if flags&StaticAbstract.INLINE:
            inline_style = Style.parse(Style.UNIVERSAL_EMPTY_STYLE)
            for style in self.styles:
                inline_style.merge(style, False)
            rendered_string+=inline_style.render(flags)
        else:
            if flags&StaticAbstract.AT_RULES:
                for at_rule in self.at_rules:
                    rendered_string+=at_rule.render(flags)
            if flags&StaticAbstract.STYLES:
                for style in self.styles:
                    rendered_string+=style.render(flags)
        return rendered_string