import html
import css

class StyleParser:
    def __init__(self, fileName):
        self.fileName = fileName

    def render(self):
        element_tree = None
        with open(self.fileName,'r') as f:
            element_tree = html.Element.parse(f.read())
        link_elements = []