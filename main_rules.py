from magnolia import Parser
from magnolia.css import Style
from magnolia import html, css,configs

import sys,os

main = Parser(os.path.abspath('.'),path=[r"%appdata%/magnolia/styles/",])
main.configure(
   reference_tags_as_attributes=False,
   auto_close_tags=False,
)

used_styles = css.StyleSheet()

@main.html_rule()
def validate_styles(tag):
    if tag.styles:
        print tag.styles
        print tag.styles.at_rules
        used_styles.merge(tag.styles)
    if tag.has_parent() and tag.get_parent().styles.has_property("mso-hide"):
        tag.add_inline_property("mso-hide",tag.parent.get_property("mso-hide"))

@main.html_rule()
def make_styles_inline(tag):
    if tag.styles:
        tag.set_attribute("style",tag.styles.render(Style.INLINE))

@main.html_rule("td>img")
def check_img_gaps(tag):
    if len(tag.get_post_siblings())==0:
        for child in tag.get_post_text():
            if child.get_empty():
                tag.parent.remove_child(child)         

@main.html_rule(selector="table")
def validate_tables(tag):
    if not tag.has_attribute("cellspacing"):
        tag.set_attribute("cellspacing","0")
    if not tag.has_attribute("cellpadding"):
        tag.set_attribute("cellpadding","0")        
    if not tag.has_attribute("border"):
        tag.set_attribute("border","0")
            
@main.html_rule(pass_num=1)
def remove_disallowed_tags(tag):
    if tag.name in ['style','link','script']:
        tag.parent.remove_child(tag)

@main.html_rule(pass_num=1)
def remove_empty_tags(tag):
    if tag.get_empty():
        if tag.name=="td":
            tag.clear_children()
            tag.add_child(html.TextElement.parse("&nbsp;"))
        elif tag.has_parent() and not tag.name in html.EMPTY_TAGS:
            tag.parent.remove_child(tag)

@main.html_rule("head",pass_num=999)
def add_style_tag(tag):
    new_tag = html.Element("style",type="text/css")
    print used_styles.at_rules
    print used_styles.render(Style.AT_RULES)
    new_tag.add_text(used_styles.render(Style.AT_RULES))
    tag.insert_child(new_tag,0)

main_stdout = sys.stdout
sys.stdout = file(os.devnull,'w')
element_tree = main.render("main.html")
tag = element_tree
sys.stdout = main_stdout
