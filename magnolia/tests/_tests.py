from __future__ import print_function
import sys,os

from ..css import static
from ..css.static import Style
from ..css import dynamic
from ..css import containers

from .. import html
from .. import page
from .. import parser

from ..configs import config


FILE_TEMPLATE  = "Testing '{}':"
GROUP_TEMPLATE = " +- Testing {}"

first_file = True

FAIL_TEMPLATE = (" |    FAILED: {}\n"
                 " |           got: '{result}'\n"
                 " |      expected: '{expected}'\n"
                 " | ")
PASS_TEMPLATE  = " |    PASSED: {}."
PASS_ERR_TEMPLATE = " |     (error msg: '{}')"

def test(verbosity,stmt, expected, msg=None,*args,**kwargs):
    if callable(expected) and isinstance(expected(), Exception):
        try:
            result = stmt(*args, **kwargs)
        except expected as e:
            if verbosity>0:
                print(PASS_TEMPLATE.format(msg))
            if verbosity>1:
                print(PASS_ERR_TEMPLATE.format(e.message))
        else:
            print(FAIL_TEMPLATE.format(msg,expected=expected,result=result), file=sys.stderr) 
    else:
        try:
            assert stmt==expected
        except AssertionError:
            if msg!=None:
                print(FAIL_TEMPLATE.format(msg,expected=expected,result=stmt), file=sys.stderr)
            else:
                raise
        else:
            if verbosity>0:
                print(PASS_TEMPLATE.format(msg))
            pass


def test_html_element(verbosity=0):
    print(GROUP_TEMPLATE.format("Element"))

    # test element parsing and rendering
    element = html.Element.parse("<td></td>")
    test(verbosity,element.render(),
        "<td></td>",
        "Standard Element")
    test(verbosity,len(element.get_elements()),1,
        "Standard Element child count")

    element = html.Element.parse("<div></div>")
    test(verbosity,element.render(),
        "<div></div>",
        "Standard Element")
    test(verbosity,len(element.get_elements()),1,
        "Standard Element child count")        

    element = html.Element.parse("<span></span>")
    test(verbosity,element.render(),
        "<span></span>",
        "Standard Element")
    test(verbosity,len(element.get_elements()),1,
        "Standard Element child count")    
    
    element = html.Element.parse("<a></a>")
    test(verbosity,element.render(),
        "<a></a>",
        "Standard Element")
    test(verbosity,len(element.get_elements()),1,
        "Standard Element child count")    
    
    element = html.Element.parse("<foo></foo>")
    test(verbosity,element.render(),
        "<foo></foo>",
        "Standard Element")
    test(verbosity,len(element.get_elements()),1,
        "Standard Element child count")    
    
    element = html.Element.parse("<camelTag></camelTag>")
    test(verbosity,element.render(),
        "<camelTag></camelTag>",
        "Standard Element")
    test(verbosity,len(element.get_elements()),1,
        "Standard Element child count")    
    
    element = html.Element.parse("<dash-tag></dash-tag>")
    test(verbosity,element.render(),
        "<dash-tag></dash-tag>",
        "Standard Element")
    test(verbosity,len(element.get_elements()),1,
        "Standard Element child count")    
    
    element = html.Element.parse("<---></--->")
    test(verbosity,element.render(),
        "<---></--->",
        "Standard Element")
    test(verbosity, len(element.get_elements()),1,
        "Standard Element child count")

    element = html.Element.parse("<div>Lorem</div>Ipsum<div>Dolor</div>")
    test(verbosity,element.render(),
        "<div>Lorem</div>Ipsum<div>Dolor</div>",
        "Two parentless tags")
    test(verbosity, len(element.get_elements()),2,
        "Two parentless tags child count")

    element = html.Element.parse("This is<div>some long<div>text between</div>div tags</div> fin")
    test(verbosity,element.render(),
        "This is<div>some long<div>text between</div>div tags</div> fin",
        "Text between tags")
    test(verbosity,len(element.get_elements()),1,
        "Text between tags child count")

    element = html.Element.parse("\n\t<div>\n\t\tcontent\n\t</div>\n")
    test(verbosity,element.render(),
        "\n\t<div>\n\t\tcontent\n\t</div>\n",
        "Lots of whitespace")
    test(verbosity,len(element.get_elements()),1,
        "Lots of whitespace child count")

    element = html.Element.parse("there is no tag here")
    test(verbosity,element.render(),
        "there is no tag here",
        "Text without tags")
    test(verbosity,len(element.get_elements()),0,
        "Text without tags child count")

    element = html.Element.parse("&gt;span&lt;this looks like a tag&gt;/span&lt;")
    test(verbosity,element.render(),
        "&gt;span&lt;this looks like a tag&gt;/span&lt;",
        "Text without tags")
    test(verbosity, len(element.get_elements()),0,
        "Text without tags child count")

    element = html.Element.parse("<img>")
    test(verbosity,element.render(),
        "<img/>",
        "Void element")
    test(verbosity,len(element.get_elements()),1,
        "Void element child count")

    element = html.Element.parse("<img />")
    test(verbosity,element.render(),
        "<img/>",
        "Self-closing void element")
    test(verbosity,len(element.get_elements()),1,
        "Self-closing void element child count")

    element = html.Element.parse("<img/>")
    test(verbosity,element.render(),
        "<img/>",
        "Self-closing void element (no trailing space)")
    test(verbosity,len(element.get_elements()),1,
        "Self-closing void element (no trailing space) child count")

    element = html.Element.parse("<mglyph />")
    test(verbosity,element.render(),
        "<mglyph/>",
        "Self-closing mathML tag")
    test(verbosity, len(element.get_elements()),1,
        "Self-closing mathML tag child count")

    element = html.Element.parse("<div><img></div>")
    test(verbosity,element.render(),
        "<div><img/></div>",
        "Nested sngleton tag")
    test(verbosity, len(element.get_elements()),1,
        "Nested void element tag child count")

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Disallowed self-closing element (name not allowed)",
        "<td />")

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Mismatched end tag",
        "<div></td>")

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Missing end tag",
        "<div>")

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Missing end tag",
        "<div>Lorem ipsum dolor sit amet")

    config.AUTO_CLOSE_ELEMENTS=True
    element = html.Element.parse("<div><td></div>")
    test(verbosity,element.render(),
        "<div><td></td></div>",
        "Auto-closed tag")
    test(verbosity,len(element.get_elements()),1,
        "Auto-closed tag child count")
    
    element = html.Element.parse("<div>")
    test(verbosity,element.render(),
        "<div></div>",
        "Auto-closed tag")
    test(verbosity, len(element.get_elements()),1,
        "Auto-closed tag child count")

    element = html.Element.parse("<div>Lorem ipsum dolor sit amet")
    test(verbosity,element.render(),
        "<div>Lorem ipsum dolor sit amet</div>",
        "Auto-closed tag with content")
    test(verbosity, len(element.get_elements()),1,
        "Auto-closed tag with content child count")

    element = html.Element.parse("<div>Lorem ipsum<span>dolor sit amet")
    test(verbosity,element.render(),
        "<div>Lorem ipsum<span>dolor sit amet</span></div>",
        "Auto-closed tags with content")
    test(verbosity, len(element.get_elements()),1,
        "Auto-closed tags with content child count")

    element = html.Element.parse("<table><tr><td></tr></table>")
    test(verbosity,element.render(),
        "<table><tr><td></td></tr></table>",
        "Auto-closing tags with incorrect closed tag")
    test(verbosity, len(element.get_elements()),1,
        "Auto-closing tags with incorrect closed tag child count")

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Closing correct tag after already auto-closed",
        "<table><tr><td></tr></td></table>")

    config.AUTO_CLOSE_ELEMENTS=False

    # test the get_[[relation]] methods for elements
    
    tree = html.Element.parse("<div><tr></tr><td><span></span></td><img><a></a></div>")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("tr")[0].get_pre_siblings()),
        0,"Element pre sibling count (first child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("tr")[0].get_post_siblings()),
        3,"Element post sibling count (first child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("tr")[0].get_siblings()),
        3,"Element sibling count (first child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("tr")[0].get_parents()),
        1,"Element parent count (first child)")
    test(verbosity, tree.get_elements("div")[0].get_elements("tr")[0].get_parent(),
        tree.get_elements("div")[0],"Element parent (first child)")

    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0].get_pre_siblings()),
        1,"Element pre sibling count (middle child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0].get_post_siblings()),
        2,"Element post sibling count (middle child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0].get_siblings()),
        3,"Element sibling count (middle child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0].get_parents()),
        1,"Element parent count (middle child)")
    test(verbosity, tree.get_elements("div")[0].get_elements("td")[0].get_parent(),
        tree.get_elements("div")[0],"Element parent (middle child)")

    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0]\
        .get_elements("span")[0].get_pre_siblings()),0,
        "Element pre sibling count (grand-child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0]\
        .get_elements("span")[0].get_post_siblings()),0,
        "Element post sibling count (grand-child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0]\
        .get_elements("span")[0].get_siblings()),0,
        "Element sibling count (grand-child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("td")[0]\
        .get_elements("span")[0].get_parents()),2,
        "Element parent count (grand-child)")
    test(verbosity, tree.get_elements("div")[0].get_elements("td")[0]\
        .get_elements("span")[0].get_parent(),tree.get_elements("div")[0].get_elements("td")[0],
        "Element parent (grand-child)")

    test(verbosity, len(tree.get_elements("div")[0].get_elements("img")[0].get_pre_siblings()),
        2,"Element pre sibling count (self-closing child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("img")[0].get_post_siblings()),
        1,"Element post sibling count (self-closing child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("img")[0].get_siblings()),
        3,"Element sibling count (self-closing child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("img")[0].get_parents()),
        1,"Element parent count (self-closing child)")
    test(verbosity, tree.get_elements("div")[0].get_elements("img")[0].get_parent(),
        tree.get_elements("div")[0],"Element parent (self-closing child)")

    test(verbosity, len(tree.get_elements("div")[0].get_elements("a")[0].get_pre_siblings()),
        3,"Element pre sibling count (last child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("a")[0].get_post_siblings()),
        0,"Element post sibling count (last child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("a")[0].get_siblings()),
        3,"Element sibling count (last child)")
    test(verbosity, len(tree.get_elements("div")[0].get_elements("a")[0].get_parents()),
        1,"Element parent count (last child)")
    test(verbosity, tree.get_elements("div")[0].get_elements("a")[0].get_parent(),
        tree.get_elements("div")[0],"Element parent (last child)")

    # test child addition/removal methods
    
    tree = html.Element.parse("<div></div>")
    tree.get_elements("div")[0].add_element("span")
    test(verbosity, tree.render(), "<div><span></span></div>",
        "Add child element")
    tree.get_elements("div")[0].add_element("span")
    test(verbosity, tree.render(), "<div><span></span><span></span></div>",
        "Add second child element")
    tree.get_elements("div")[0].insert_element("img",1)
    test(verbosity, tree.render(), "<div><span></span><img/><span></span></div>",
        "Add void element")
    tree.get_elements("div")[0].insert_element("notATag",1)
    test(verbosity, tree.render(), "<div><span></span><notATag></notATag><img/><span></span></div>",
        "Add homemade element")
    tree.get_elements("div")[0].clear_children()
    test(verbosity, tree.render(), "<div></div>",
        "Clear children")

    tree.get_elements("div")[0].add_text("Hello")
    test(verbosity, tree.render(),"<div>Hello</div>",
        "Add text")
    tree.get_elements("div")[0].add_text(", world!")
    test(verbosity, tree.render(),"<div>Hello, world!</div>",
        "Add more text")
    tree.get_elements("div")[0].add_text("  \t  \n  \t\t  ")
    test(verbosity, tree.render(),"<div>Hello, world!  \t  \n  \t\t  </div>",
        "Add whitespace")
    tree.get_elements("div")[0].add_text("")
    test(verbosity, tree.render(),"<div>Hello, world!  \t  \n  \t\t  </div>",
        "Add empty string")
    test(verbosity, len(tree.get_elements("div")[0]._children),3,
        "Add empty string child count")
    tree.get_elements("div")[0].clear_children()

    tree.get_elements("div")[0].add_element("span",spacing=0,border=1)
    test(verbosity, tree.render(),'<div><span border="1" spacing="0"></span></div>',
        "Add child with attributes")
    tree.get_elements("div")[0].clear_children()

    # test empty methods

    test(verbosity, tree.get_elements("div")[0].get_empty(),True,
        "Get if element is empty (True)")
    tree.get_elements("div")[0].add_text("     ")
    test(verbosity, tree.get_elements("div")[0].get_empty(),True,
        "Get if element is empty (True - contains only whitespace)")
    tree.get_elements("div")[0].add_text("hello")
    test(verbosity, tree.get_elements("div")[0].get_empty(),False,
        "Get if element is empty (False - contains non whitespace text)")
    tree.get_elements("div")[0].clear_children()
    tree.get_elements("div")[0].add_element("td")
    test(verbosity, tree.get_elements("div")[0].get_empty(),False,
        "Get if element is empty (False - contains element)")
    tree.get_elements("div")[0].clear_children()

    # test get methods for text
    
    # note: the way text is handled will be changed eventually and these will 
    # need to be changed
    tree = html.Element.parse(
        "Lorem<div>Ipsum<span>Dolor</span>Sit<td></td>  \n  <img></div>Consiquetur")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0].get_pre_text()]),
        "Lorem","Top level element pre text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0].get_post_text()]),
        "Consiquetur","Top level element post text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0].get_encapsulating_text()]),
        "LoremConsiquetur","Top level element encapsulating text")

    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("span")[0].get_pre_text()]),
        "Ipsum","First child element encapsulating text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("span")[0].get_post_text()]),
        "Sit","First child element encapsulating text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("span")[0].get_encapsulating_text()]),
        "IpsumSit","First child element encapsulating text")

    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("td")[0].get_pre_text()]),
        "Sit","Middle child element encapsulating text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("td")[0].get_post_text()]),
        "  \n  ","Middle child element encapsulating text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("td")[0].get_encapsulating_text()]),
        "Sit  \n  ","Middle child element encapsulating text")

    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("img")[0].get_pre_text()]),
        "  \n  ","Void element encapsulating text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("img")[0].get_post_text()]),
        "","Void element encapsulating text")
    test(verbosity, 
        ''.join([t.render() for t in tree.get_elements("div")[0]\
            .get_elements("img")[0].get_encapsulating_text()]),
        "  \n  ","Void element encapsulating text")

    # test attribute parsing and rendering

    element = html.Element.parse('<img attr1="attr1" attr2="attr2">')
    test(verbosity,element.render(),
        '<img attr1="attr1" attr2="attr2" />',
        "Standard atributes")
    test(verbosity, len(element.get_elements()),1,
        "Standard atributes child count")

    element = html.Element.parse(
        '<img first-attribute="Lorem Ipsum" second-attribute=Lorem Ipsum >')
    test(verbosity,element.render(),
        '<img Ipsum first-attribute="Lorem Ipsum" second-attribute="Lorem" />',
        "Standard atributes")
    test(verbosity,len(element.get_elements()),1,
        "Standard atributes child count")

    # test all attribute types in all orders

    element = html.Element.parse('<hr attr1 attr2=\'val2\' attr3="val3" attr4=val4 />')
    test(verbosity,element.render(),
        '<hr attr1 attr2="val2" attr3="val3" attr4="val4" />',
        "Standard atributes")
    test(verbosity,len(element.get_elements()),1,
        "Standard atributes child count")

    element = html.Element.parse('<hr attr4=val4 attr1 attr2=\'val2\' attr3="val3" />')
    test(verbosity,element.render(),
        '<hr attr1 attr2="val2" attr3="val3" attr4="val4" />',
        "Standard atributes")
    test(verbosity,len(element.get_elements()),1,
        "Standard atributes child count")

    element = html.Element.parse('<hr attr3="val3" attr4=val4 attr1 attr2=\'val2\' />')
    test(verbosity,element.render(),
        '<hr attr1 attr2="val2" attr3="val3" attr4="val4" />',
        "Standard atributes")
    test(verbosity, len(element.get_elements()),1,
        "Standard atributes child count")

    element = html.Element.parse('<hr attr2=\'val2\' attr3="val3" attr4=val4 attr1 />')
    test(verbosity,element.render(),
        '<hr attr1 attr2="val2" attr3="val3" attr4="val4" />',
        "Standard atributes")
    test(verbosity, len(element.get_elements()),1,
        "Standard atributes child count")

    # other misc attribute tests

    # for the moment this next test will always fail due (as in not raise an 
    # error) to the shortcomings of regex when I change it over to a 
    # traditional parser, this should be fixed
    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Invalid self-closing element (no trailing space)",
        "<img attr1=foo/>")

    element = html.Element.parse('<div value="<td>content"></div>')
    test(verbosity,element.render(),
        '<div value="<td>content"></div>',
        "Attibute with html value")
    test(verbosity, len(element.get_elements()),1,
        "Attibute with html value child count")

    element = html.Element.parse('<div\nvalue="foo"></div>')
    test(verbosity,element.render(),
        '<div value="foo"></div>',
        "Tag on two lines")
    test(verbosity,len(element.get_elements()),1,
        "Tag on two lines child count")

    element = html.Element.parse('<div value="foo\nbar"></div>')
    test(verbosity,element.render(),
        '<div value="foo\nbar"></div>',
        "Attribute value on two lines")
    test(verbosity, len(element.get_elements()),1,
        "Attribute value on two lines child count")

    element = html.Element.parse('<div value="Lorem \'ipsum\' dolor"></div>')
    test(verbosity,element.render(),
        '<div value="Lorem \'ipsum\' dolor"></div>',
        "Attribute value with nested quotes")
    test(verbosity,len(element.get_elements()),1,
        "Attribute value with nested quotes child count")

    element = html.Element.parse('<div value=\'Lorem "ipsum" dolor\'></div>')
    test(verbosity,element.render(),
        '<div value=\'Lorem "ipsum" dolor\'></div>',
        "Attribute value with nested quotes")
    test(verbosity,len(element.get_elements()),1,
        "Attribute value with nested quotes child count")

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Attribute value with both nested quotes",
        '<div value="Lorem \'ipsum\' "dolor" sit"></div>')

    bad_attribute_quotes = html.Element.parse('<div></div>')
    # this is normally will throw an error during parsing, so the attribute
    # must be set manually
    bad_attribute_quotes.get_elements()[0]._attributes["value"] = "Lorem 'ipsum' \"dolor\" sit" 
    test(verbosity,bad_attribute_quotes.render(),
        '<div value="Lorem \'ipsum\' &quot;dolor&quot; sit"></div>',
        "Attribute value with nested quotes")

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Attribute value with unescaped qoute",
        '<div attr1="foo" bar" attr2="Lorem ipsum"></div>')

    test(verbosity,html.Element.parse,
        html.HTMLParserError,
        "Attribute value with unescaped qoute",
        "<div attr1='foo' bar' attr2=\"Lorem ipsum\"></div>")

    element = html.Element.parse('<div\t\t   attr1  =\t "value1"\t\n\t></div>')
    test(verbosity, element.render(),
        '<div attr1="value1"></div>',
        "Attribute with lots of whitespace")
    test(verbosity, len(element.get_elements()),1,
        "Attribute with lots of whitespace child count")

    # note that these next 4 tests (all raising errors) are caught by the tag
    # parser as opposed to the attribute parser... a more userful error
    # message will be created for this case once I finish moving from regex
    test(verbosity, html.Element.parse,
        html.HTMLParserError,
        "Attribute with missing close quotes (two words)",
        '<div attr1="Lorem Ipsum></div>')

    test(verbosity, html.Element.parse,
        html.HTMLParserError,
        "Attribute with missing close quotes",
        '<div attr1="Lorem></div>')

    test(verbosity, html.Element.parse,
        html.HTMLParserError,
        "Attribute with missing close quotes (two words)",
        "<div attr1='Lorem Ipsum></div>")

    test(verbosity, html.Element.parse,
        html.HTMLParserError,
        "Attribute with missing close quotes",
        "<div attr1='Lorem></div>")


def test_static_property(verbosity=0):
    print(GROUP_TEMPLATE.format("Property"))

    # test property parsing and rendering
    test(verbosity,static.Property.parse("text-align:right;").render(), 
         "\ttext-align:right;", 
         "Standard Property")

    test(verbosity,static.Property.parse("margin:0px 0px 5px 5px;").render(), 
         "\tmargin:0px 0px 5px 5px;", 
         "Standard Property")

    test(verbosity,static.Property.parse('content: "foo";').render(), 
         '\tcontent:"foo";', 
         "Standard Property")

    test(verbosity,static.Property.parse('font-family: Times New Roman, Serif;').render(), 
         "\tfont-family:Times New Roman, Serif;", 
         "Standard Property")

    test(verbosity,static.Property.parse("--does-not-exist:foobar;").render(), 
         "\t--does-not-exist:foobar;", 
         "Standard Property")

    test(verbosity,static.Property.parse("text-align:right;").render(Style.INLINE), 
         "text-align:right;",
         "Inline Property")

    test(verbosity,
         static.Property.parse("\n\ntext-align  :\n\n       right    \t\n  ;").render(Style.INLINE), 
         "text-align:right;",
         "Property with lots of whitespace")

    test(verbosity,
         static.Property.parse('content:"content:\'lorem ipsum\';";').render(Style.INLINE), 
         'content:"content:\'lorem ipsum\';";',
         "Nested Property")

    test(verbosity,static.Property.parse("text-align:right;").render(Style.INLINE), 
         "text-align:right;",
         "Property missing semicolon")

    test(verbosity,static.Property.parse("text-align:right!important;").render(), 
         "\ttext-align:right!important;",
         "Property with important modifier")

    test(verbosity,static.Property.parse("text-align:right!important;").render(Style.INLINE), 
         "text-align:right!important;",
         "Inline Property with important modifier")

    # test property priority
    # its a weak test but we have to hope this works for now
    # we will confirm it works in later tests
    property_style = static.Style.parse("*{}")
    # define relevant properties
    normal_property = static.Property(property_style, "font-size","0px")
    inherited_property = static.Property(property_style, "font-size","1px")
    inherited_property.inherited = True
    inline_property = static.Property(property_style, "font-size","2px")
    inline_property.inline = True
    important_property = static.Property(property_style, "font-size","3px",important=True)
    mismatched_property = static.Property(property_style, "margin","20px")

    # priority calculations
    test(verbosity,inherited_property.get_priority(normal_property),[0,0,0],
         "Inherited Property get_priority")

    test(verbosity,important_property.get_priority(normal_property),[1,0,0],
         "Important Property get_priority")

    test(verbosity,inline_property.get_priority(normal_property),[1,1,0],
         "Inline Property get_priority")

    # all the priority comparisons
    test(verbosity,inherited_property.compare_priority(normal_property),-1,
        "Compare inherited Property priority to normal Property")

    test(verbosity,inherited_property.compare_priority(inherited_property),0,
        "Compare inherited Property priority to normal Property")

    test(verbosity,inherited_property.compare_priority(inline_property),-1,
        "Compare inherited Property priority to inline Property")

    test(verbosity,inherited_property.compare_priority(important_property),-1,
        "Compare inherited Property priority to important Property")

    test(verbosity,inherited_property.compare_priority(mismatched_property),-1,
        "Compare inherited Property priority to non-matching Property")

    test(verbosity,inline_property.compare_priority(normal_property),1,
        "Compare inline Property priority to normal Property")

    test(verbosity,inline_property.compare_priority(important_property),1,
        "Compare inline Property priority to important Property")

    test(verbosity,inline_property.compare_priority(mismatched_property),1,
        "Compare inline Property priority to non-matching Property")

    test(verbosity,important_property.compare_priority(normal_property),0,
        "Compare important Property to normal Property")

    test(verbosity,important_property.compare_priority(mismatched_property),0,
        "Compare important Property to non-matching Property")

    # get_copy
    test(verbosity,normal_property.get_copy().render(Style.INLINE), "font-size:0px;",
        "Duplicate normal Property")

    test(verbosity,inherited_property.get_copy().render(Style.INLINE), "font-size:1px;",
        "Duplicate inherited Property")

    test(verbosity,inline_property.get_copy().render(Style.INLINE), "font-size:2px;",
        "Duplicate inline Property")

    test(verbosity,important_property.get_copy().render(), "\tfont-size:3px!important;",
        "Duplicate important Property")

    # merging
    important_property.merge(normal_property)
    test(verbosity,important_property.render(),"\tfont-size:3px!important;",
        "Merge important Property with normal Property (dest)")
    test(verbosity,normal_property.render(),"\tfont-size:0px;",
        "Merge important Property with normal Property (src)")

    inline_property.merge(normal_property)
    test(verbosity,inline_property.render(),"\tfont-size:2px;",
        "Merge inline Property with normal Property (dest)")
    test(verbosity,normal_property.render(),"\tfont-size:0px;",
        "Merge inline Property with normal Property (src)")

    normal_property.merge(inherited_property)
    test(verbosity,normal_property.render(),"\tfont-size:0px;",
        "Merge normal property with inherited Property (dest)")
    test(verbosity,inherited_property.render(),"\tfont-size:1px;",
        "Merge normal property with inherited Property (src)")

    important_property.merge(inline_property)
    test(verbosity,important_property.render(),"\tfont-size:3px!important;",
        "Merge important Property with inline Property (dest)")
    test(verbosity,inline_property.render(),"\tfont-size:2px;",
        "Merge important Property with inline Property (src)")

    inline_property.merge(important_property)
    test(verbosity,inline_property.render(),"\tfont-size:3px;",
        "Merge inline Property with important Property (dest)")
    test(verbosity,important_property.render(),"\tfont-size:3px!important;",
        "Merge inline Property with important Property (src)")

    normal_property.merge(inline_property)
    test(verbosity,normal_property.render(),"\tfont-size:3px;",
        "Merge normal Property with inline Property (dest)")
    test(verbosity,inline_property.render(),"\tfont-size:3px;",
        "Merge normal Property with inline Property (src)")

    inherited_property.merge(normal_property)
    test(verbosity,inherited_property.render(),"\tfont-size:3px;",
        "Merge inherited Property with normal Property (dest)")
    test(verbosity,normal_property.render(),"\tfont-size:3px;",
        "Merge inherited Property with normal Property (src)")

    inherited_property.merge(mismatched_property)
    test(verbosity,inherited_property.render(),"\tfont-size:3px;",
        "Merge inherited Property with non-matching Property (dest)")
    test(verbosity,mismatched_property.render(),"\tmargin:20px;",
        "Merge inherited Property with non-matching Property (src)")


def test_static_attribute_filter(verbosity=0):
    print(GROUP_TEMPLATE.format("AttributeFilter"))
    # test parsing and rendering


def run():
    verbosity=0

    config.save()

    print(FILE_TEMPLATE.format("html.py"))
    test_html_element(verbosity)

    #this should test html before css
    print(FILE_TEMPLATE.format("static.py"))
    test_static_property(verbosity)
    test_static_attribute_filter(verbosity)

    config.load()
