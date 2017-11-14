import os
import html
import css

class Page:
    def __init__(self, fileName, base=None, root=None):
        self.fileName = fileName
        if base:
            self.base = base
        else:
            self.base = os.path.dirname(os.path.abspath(fileName))
            
        if root:
            self.root = root
        else:
            self.root = self.base
        self.element_tree = None
        self.stylesheets = []

    def load(self):
        def handle_tag(tag):
            # this is basically going to brute force the special case tags
            if tag.name == "link":
                if (tag.has_attribute("rel") and tag.get_attribute("rel")=="stylesheet"
                    and tag.has_attribute("href")):
                    fname = tag.get_attribute("href")
                    if fname.startswith("/"):
                        fname = fname[1:]
                        fname = os.path.join(self.root, fname)
                    else:
                        fname = os.path.join(self.base, fname)
                    stylesheet_path = os.path.abspath(os.path.normpath(fname))
                    stylesheet_text = None
                    try:
                        with open(stylesheet_path,'r') as f:
                            stylesheet_text = f.read()
                    except IOError:
                        print "Warning: Could not read from '{}'".format(stylesheet_path)
                    if stylesheet_text:
                        new_stylsheet = css.StyleSheet.parse(stylesheet_text)
                        self.stylesheets.append(new_stylsheet)
            elif tag.name == "style":
                content = ""
                for child in tag._children:
                    content += child.render()
                if content.strip():
                    self.stylesheets.append(css.StyleSheet.parse(content))

        with open(os.path.join(self.root, self.fileName), 'r') as f:
            data = f.read()
        self.element_tree = html.Element.parse(data)
        self.element_tree.map(handle_tag)
        return self

    def apply_css(self):
        for stylesheet in self.stylesheets:
            self.element_tree.apply_styles(stylesheet)
        self.element_tree.apply_styles(html.Element.INLINE_STYLES)