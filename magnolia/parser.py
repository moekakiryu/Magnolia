import functools
import inspect

import page
from configs import config
from css import Selector
import html

class HTMLTestError(Exception):
    pass

class Rule:
    def __init__(self, func, priority):
        self.func = func
        self.priority = priority

    def __eq__(self, other):
        return isinstance(other, Rule) and self.func.__name__==other.func.__name__ 

class Parser:
    """ This is mainly to be imported and used with its decorators

    ie.
    import Parser
    project_dir = "C:/path/to/project/"
    main = Parser(project_dir)

    @main.render_rule(priority=3)
    def foo(tag):
        do_stuff()

    main.render()
    """
    def __init__(self, project_dir, path=[]):
        self.project_dir = project_dir
        if isinstance(path, list):
            self.path = path
        elif hasattr(path, "__iter__"):
            self.path = list(path)
        else:
            self.path = [path]
        self.file_filter = "" # to be used later

        self.reference_tags_as_attributes = False

        self._render_rules = {}

    def _get_selector_obj(self, selector):
        selector_obj = None
        if selector:
            if isinstance(selector,str):
                selector_obj = Selector.parse(selector)
            elif not isinstance(selector, Selector):
                selector_obj = None
        return selector_obj

    def html_rule(self,selector=None,pass_num=0):
        def decorator(func):
            # validate the function signature through inspection
            argspec = inspect.getargspec(func)
            default_arg_count = len(argspec.defaults or [])
            req_arg_count = len(argspec.args or [])-default_arg_count
            if not ((req_arg_count==1) or 
                    (req_arg_count<1 and (argspec.varargs or default_arg_count))):
                raise ValueError(
                    "Function '{}' must be able to accept exactly one argument.".format(
                        func.__name__))
            # if provided, construct the selector object
            selector_obj = self._get_selector_obj(selector)
            # the actual decorator
            @functools.wraps(func)
            def inner(element):
                if not selector_obj or selector_obj.match(element):
                    if element and (not element.has_parent() or element.get_parent().has_child(element)):
                        return func(element)

            # add the new function to the list of rules
            new_rule = Rule(inner, pass_num)
            if not new_rule.priority in self._render_rules:
                self._render_rules[new_rule.priority] = []
            if new_rule in self._render_rules[new_rule.priority]:
                self._render_rules[new_rule.priority]\
                                  [self._render_rules.index(new_rule)] = new_rule
            else:
                self._render_rules[new_rule.priority].append(new_rule)
            return inner
        return decorator

    def configure(self,**kwargs):
        for key,val in kwargs.items():
            if config.has_key(key.upper()):
                config[key.upper()] = val
            else:
                raise AttributeError("Parser object does not have attribute '{}'".format(key))

    def _func_caller(self, tag, rules):
        for rule in rules:
            rule.func(tag)

    def render(self, fname):
        html_page = page.HTMLPreprocessor(fname, root=self.project_dir, path=self.path).load()
        html_page.apply_css()
        priority_list = sorted(self._render_rules.items(), key=lambda r: r[0])

        print '-'*35+"\nAPPLYING RULES\n"+'-'*35
        for priority,rules in priority_list:
            print "\nLayer {}\n".format(priority)+'-'*15
            html_page.element_tree.map(lambda tag: self._func_caller(tag,rules))
        return html_page.element_tree