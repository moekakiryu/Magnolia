from CSSParser import Parser
from CSSParser.Structure import Style

main = Parser.Parser(r"C:\Users\creed1701\Documents\_personal\py_files")

@main.render_rule()
def make_styles_inline(tag):
	if tag.has_styles():
		tag.set_attribute("style",tag.styles.render(Style.INLINE))

@main.render_rule()
def remove_style_tags(tag):
	if tag.name=="style" or tag.name=="link":
		tag.parent.remove_child(tag)

@main.render_rule()
def remove_empty_styles(tag):
	if tag.get_empty():
		tag.parent.remove_child(tag)

element_tree = main.render("main.html")

