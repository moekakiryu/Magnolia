from magnolia import Parser
from magnolia.css import Style
from magnolia.html import TextElement

import os

main = Parser(os.path.abspath('.'),path=[r"%appdata%/magnolia/styles/",])
main.configure(
   reference_tags_as_attributes=False,
#    style_format=
# "{selector}{attribute} {{"
# "    {properties}"
# "}}",
#     element_format="<{end:/<1.0}{name} {attributes}>",
)

@main.html_rule()
def make_styles_inline(tag):
    if tag.styles:
        tag.set_attribute("style",tag.styles.render(Style.INLINE))

@main.html_rule(selector="table")
def validate_tables(tag):
    if not tag.has_attribute("cellspacing"):
        tag.set_attribute("cellspacing","0")
    if not tag.has_attribute("cellpadding"):
        tag.set_attribute("cellpadding","0")        
    if not tag.has_attribute("border"):
        tag.set_attribute("border","0")
            
@main.html_rule()
def remove_style_tags(tag):
    if tag.name=="style" or tag.name=="link":
        tag.parent.remove_child(tag)

@main.html_rule()
def remove_js(tag):
    if tag.name=="script":
        tag.parent.remove_child(tag)

@main.html_rule()
def remove_empty_styles(tag):
    if tag.get_empty():
        if tag.name=="td":
            tag.clear_children()
            tag.add_child(TextElement.parse("&nbsp;"))
        else:
            tag.parent.remove_child(tag)

element_tree = main.render("main.html")
tag = element_tree

