import functools
import inspect

import page
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

        self._render_rules = []

    def __setattr__(self, name, val):
        if name=="reference_tags_as_attributes":
            self.__dict__[name]= bool(val)
            html.REFERENCE_TAGS_AS_ATTRIBUTES = bool(val)
        else:
            self.__dict__[name]=val

    def _validate_function(self, func):
        argspec = inspect.getargspec(func)
        default_arg_count = len(argspec.defaults or [])
        req_arg_count = len(argspec.args or [])-default_arg_count
        if not ((req_arg_count==1) or 
                (req_arg_count<1 and (argspec.varargs or default_arg_count))):
            raise ValueError(
                "Function '{}' must be able to accept exactly one argument.".format(
                    func.__name__))

    def _get_selector_obj(self, selector):
        selector_obj = None
        if selector:
            if isinstance(selector,str):
                selector_obj = Selector.parse(selector)
            elif not isinstance(selector, Selector):
                selector_obj = None
        return selector_obj

    def html_rule(self,priority=0,selector=None):
        def decorator(func):
            # validate the function signature through inspection
            self._validate_function(func)
            # if provided, construct the selector object
            selector_obj = self._get_selector_obj(selector)
            # the actual decorator
            @functools.wraps(func)
            def inner(element):
                if not selector_obj or selector_obj.match(element):
                    return func(element)

            # add the new function to the list of rules
            new_rule = Rule(inner, priority)
            if new_rule in self._render_rules:
                self._render_rules[self._render_rules.index(new_rule)] = new_rule
            else:
                self._render_rules.append(new_rule)
            return inner
        return decorator

    def configure(self,**kwargs):
        for arg,val in kwargs.items():
            if arg in self.__dict__:
                setattr(self, arg, val)
            else:
                raise AttributeError("Parser object does not have attribute '{}'".format(arg))

    def render(self, fname):
        html_page = page.HTMLPreprocessor(fname, root=self.project_dir, path=self.path).load()
        html_page.apply_css()
        sorted_rules = sorted(self._render_rules,key=lambda r: r.priority)
        for rule in sorted_rules:
            html_page.element_tree.map(rule.func)
        return html_page.element_tree