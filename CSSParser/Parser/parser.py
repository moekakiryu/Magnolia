from ..Structure import css, html, page
import functools

class Parser:
    """ This is mainly to be imported and used with its decorators

    ie.
    import Parser
    project_dir = "C:/path/to/project/"
    main = Parser(project_dir)

    @main.render_rule(pass_number=3)
    def foo(tag):
        do_stuff()

    main.render()
    """
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.file_filter = "" # to be used later

        self._render_rules = {}

    # the below function is shamelessly copied from: 
    # https://stackoverflow.com/questions/10176226/how-to-pass-extra-arguments-to-python-decorator
    def render_rule(self,n=0):
        def decorator(func):
            if hasattr(func,"__name__"):
                print func.__name__
            @functools.wraps(func)
            def inner(*args, **kwargs):
                return func(*args, **kwargs)
            if not self._render_rules.has_key(n):
                self._render_rules[n] = []
            self._render_rules[n].append(inner)
            return inner
        return decorator

    def render(self, fname):
        html_page = page.Page(fname, base=self.project_dir).load()
        html_page.apply_css()

        sorted_rules = sorted(self._render_rules.items(),key=lambda i: i[0])
        for layer in sorted_rules:
            for rule in layer[1]:
                html_page.element_tree.map(rule)
        return html_page.element_tree