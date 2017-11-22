import re

from static import Style
from dynamic import AtRule, AtQuery
from _abstract import CSSAbstract, CSSParserError

class AtRules(CSSAbstract):
    # this should eventually be moved to a separate file
    def __init__(self):
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

    @classmethod
    def _get_styles(cls, inpt):
        print "\ngetting styles\n"
        styles = []
        for style in re.finditer(cls.CSS_TOKENIZER, inpt):
            selectors =  style.group("selector").split(",")
            for selector in selectors:
                selector = selector.strip()
                new_style = Style.parse("{}{{{}}}".format(selector, style.group("rules"))) 
                styles.append(new_style)
        return styles

    def add_rule(self, rule):
        self.rules.append(rule)

    def remove_rule(self, rule):
        if rule in self.rules:
            self.rules.remove(rule)

    def get_copy(self):
        new_rules = AtRules()
        for rule in self.rules:
            new_rules.add_rule(rule.get_copy())
        return new_rules

    @classmethod
    def _parse(cls, inpt, new_rules=None ,query_chain=None):
        """ note that unlike all other css classes, this parse method returns
        a list of multiple at-rule objects. This is because AtRule's behave
        more like stylesheets so it would be odd....


        while I was writing that out, this behaves like a stylesheet so 
        immediately after calling render, it should be merged into a stylesheet
        (it acts like something between a style and stylesheet"""
        if not query_chain:
            query_chain = []
        print "\nSTART:",new_rules, query_chain
        tokenized = cls._parse_css(inpt) 
        # generate new rule
        new_rules = AtRules() if not new_rules else new_rules
        empty = True
        for token in tokenized:
            if not token.head.startswith('@'):
                continue
            print "PARSING: "+str(token)
            # parse each at rule
            empty = False
            s = token['match'].group(0) # the entire AtRule query
            new_chain = query_chain[::-1]+[AtQuery.parse(s)]
            if token['content'] and token['end']=='{':
                print "RECURSING: "+str(new_chain)
                token['content'] = token['content'].strip()
                result = cls._parse(token['content'],new_rules,new_chain)

                if not result: #if we are at the bottom of the chain
                    styles = cls._get_styles(token['content'])
                    if styles:
                        for style in styles:
                            print "CREATING WITH:"+str(new_chain)
                            new_rules.add_rule(AtRule(style,*new_chain))
                    else:
                        print "NULL CREATED:"+str(new_chain)
                        new_rules.add_rule(AtRule(None, *new_chain))
                print "DONE ADDING"
            else:
                new_rules.add_rule(AtRule(None, *new_chain))
        if empty:
            print "empty return"
            return
        # if not tokens:
        print "end reached:"+str(new_rules.rules)
        return new_rules

    @classmethod
    def parse(cls, inpt):
        return cls._parse(inpt)
    
    def match(self, e):
        # for the time being, at rules are completely ignored in computations
        return False 

    def merge(self, other):
        if isinstance(other, AtRules):
            return

    def render(self, flags=0):
        rendered_string = ""
        if flags&CSSAbstract.INLINE:
            raise CSSParserError("At rules can not be rendered inline.")
        elif flags&CSSAbstract.AT_RULES:
            rendered_string += "@"+" ".join((self.rule_type, self.arguments))
            if self.nested:
                rendered_styles = "\n".join(map(lambda s:s.render(flags),
                                                                     self.rules))
                # below is a really hacked way to indent all lines except the last newline
                rendered_string += "{{\n{}}}\n".format("\t"+rendered_styles.replace("\n","\n\t",
                    rendered_styles.count("\n")-1)) 
            else:
                rendered_string += ";\n"
        return rendered_string


class StyleSheet(CSSAbstract):
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
    def _parse(cls, inpt, new_stylesheet=None, query_chain=None):
        # todo make this recursive
        #
        # for the parsing order, first comments are removed, then at-rules
        # are handled, then the rest of the styles are handled
        print
        if new_stylesheet == None:
            print "CREATING NEW Stylesheet: {}".format(new_stylesheet)
            new_stylesheet = StyleSheet()
        if not query_chain:
            query_chain = []

        # parse rest of styles
        for token in cls._parse_css(inpt):
            if token.head.startswith("@"): # is it is an at-rule
                new_chain = query_chain+[AtQuery.parse(token.head)]
                if token.is_block:
                    cls._parse(token.tail,new_stylesheet,new_chain)
                else:
                    new_stylesheet.add_style(AtRule(None,new_chain))
            else:
                selectors =  token.head.split(",")
                for selector in selectors:
                    selector = selector.strip()
                    new_style = Style.parse("{}{{{}}}".format(selector, token.tail)) 
                    if query_chain:
                        new_rule = AtRule(new_style,*query_chain)
                        print "ADDING AT-RULE: {}".format(new_rule in new_stylesheet.styles)
                        new_stylesheet.add_style(new_rule)
                        print new_stylesheet.styles
                    else:
                        new_stylesheet.add_style(new_style)
       
        return new_stylesheet

    @classmethod
    def parse(cls, inpt):
        return cls._parse(inpt)

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