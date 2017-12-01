import os

import html
import css

class HTMLPreprocessor:
    def __init__(self, fileName, root=None, path=[]):
        self.fileName = fileName
        self.base = os.path.dirname(os.path.abspath(fileName))
        if root:
            self.root = root
        else:
            self.root = self.base

        if isinstance(path, list):
            self.path = path
        elif hasattr(path, "__iter__"):
            self.path = list(path)
        else:
            self.path = [path]
        self.path = [os.path.normpath(os.path.expandvars(os.path.expanduser(p))) 
                        for p in self.path]
        self.element_tree = None
        self.stylesheets = []

    def _get_segments(self, p):
        out = []
        while p.endswith('/') or p.endswith('\\'):
            p=p[:-1]
        split_dir = os.path.split(p)
        if split_dir[0]:
            out.extend(self._get_segments(split_dir[0]))
        out.append(split_dir[1])
        return out

    def _directory_search(self, fname, p):
        segs = self._get_segments(fname)
        found = True
        start_path = p
        for s in segs:
            if s in os.listdir(p):
                p = os.path.join(p,s)
            else:
                found = False
                break
        if found:
            return os.path.normpath(os.path.realpath(os.path.join(start_path,fname)))

    def _search_path(self, fname):
        found_dir = None

        if self._directory_search(fname,self.base):
            found_dir = self.base
        elif self._directory_search(fname, self.root):
            found_dir = self.root
        else:
            for d in self.path:
                if self._directory_search(fname, d):
                    found_dir=d
                    break
        if found_dir:
            return os.path.abspath(os.path.normpath(os.path.join(found_dir, fname)))
        else:
            raise IOError("Could not find file '{}'".format(fname))

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
                        fname = self._search_path(fname)
                    stylesheet_path = os.path.abspath(os.path.normpath(fname))
                    stylesheet_text = None
                    try:
                        with open(stylesheet_path,'r') as f:
                            stylesheet_text = f.read()
                    except IOError:
                        print "Warning: Could not read from '{}'".format(stylesheet_path)
                    if stylesheet_text:
                        print "PARSING FILE '{}'\n".format(stylesheet_path)
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
            print '-'*35+"\nSTART STYLESHEET\n"+'-'*35
            self.element_tree.apply_styles(stylesheet)
            print '-'*35+"\nEND STYLESHEET\n"+'-'*35
        self.element_tree.apply_styles(html.Element.INLINE_STYLES)