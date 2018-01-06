import sys,os
import time
import urllib2
import threading
import Queue

from magnolia import Parser
from magnolia.css import Style
from magnolia import html, css
from magnolia import tests

running_in_idle = 'idlelib.run' in sys.modules

class ShellColors:
    _base = "\33[{bold:1d};{color}m"
    reset = "\33[m"
    red = _base.format(color=31, bold=False)
    green = _base.format(color=32, bold=False)
    yellow = _base.format(color=33, bold=False)
    blue = _base.format(color=34, bold=False)
    pink = _base.format(color=35, bold=False)
    teal = _base.format(color=36, bold=False)
    white = _base.format(color=37, bold=False)

    bred = _base.format(color=31, bold=True)
    bgreen = _base.format(color=32, bold=True)
    byellow = _base.format(color=33, bold=True)
    bblue = _base.format(color=34, bold=True)
    bpink = _base.format(color=35, bold=True)
    bteal = _base.format(color=36, bold=True)
    bwhite = _base.format(color=37, bold=True)

    @staticmethod
    def colorify(string, color):
        return color+str(string)+ShellColors.reset

# configure the parser

main = Parser(os.path.abspath('.'),path=[r"%appdata%/magnolia/styles/",])
main.configure(
   reference_elements_as_attributes=False,
   auto_close_elements=False,
)
used_styles = css.StyleSheet()

# set up multiprocessing stuff

NUM_THREADS = 5
url_queue = Queue.Queue()

def url_worker(queue):
    while True:
        tag,url = queue.get()
        if not tag or not url:
            break
        req = urllib2.Request(url)
        req.get_method = lambda:"HEAD"
        try:
            resp = urllib2.urlopen(req,timeout=5)
            resp_code = resp.getcode()
        except urllib2.HTTPError as e:
            resp_code = e.getcode()
        except urllib2.URLError as e:
            print "  {}:'{}' ({})".format(ShellColors.colorify("t/o",ShellColors.yellow),
                                          url,tag.name)            
            continue
        if resp_code/100==2:
            print "  {}:'{}' ({})".format(ShellColors.colorify(resp_code,ShellColors.green),
                                          url,tag.name)
        else:
            print "  {}:'{}' ({})".format(ShellColors.colorify(resp_code,ShellColors.red),
                                          url,tag.name)

# Define the rules

@main.html_rule()
def validate_styles(tag):
    if tag.styles:
        used_styles.merge(tag.styles)
    if tag.has_parent() and tag.get_parent().styles.has_property("mso-hide"):
        tag.add_inline_property("mso-hide",tag.parent.get_property("mso-hide"))

@main.html_rule()
def validate_urls(tag):
    if tag.has_attribute("href"):
        url = tag.get_attribute("href").lower()
        if url.startswith("http://") or url.startswith("https://"):
            url_queue.put((tag,url))
    if tag.has_attribute("src"):
        url = tag.get_attribute("src").lower()
        if url.startswith("http://") or url.startswith("https://"):
            url_queue.put((tag,url))
    if tag.has_attribute("data"):
        url = tag.get_attribute("data").lower()
        if url.startswith("http://") or url.startswith("https://"):
            url_queue.put((tag,url))

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
def remove_disallowed_elements(tag):
    if tag.name in ['style','link','script']:
        tag.parent.remove_child(tag)

@main.html_rule(pass_num=1)
def remove_empty_elements(tag):
    if tag.get_empty():
        if tag.name=="td":
            tag.clear_children()
            tag.add_child(html.TextElement.parse("&nbsp;"))
        elif tag.has_parent() and not tag.name in html.VOID_ELEMENTS:
            tag.parent.remove_child(tag)

@main.html_rule("html>head:first-child",pass_num=999)
def add_style_tag(tag):
    new_tag = html.Element("style",type="text/css")
    new_tag.add_text(used_styles.render(Style.AT_RULES))
    tag.insert_child(new_tag,0)

# run the program
print "Running tests:\n"+'-'*25
tests.run()
# sys.exit()

s_time = time.time()
print "\nParsing element tree:\n"+'-'*25

if not running_in_idle:
    threads = []
    for n in range(NUM_THREADS):
        t = threading.Thread(target=url_worker, args=(url_queue,))
        t.setDaemon(True)
        t.start()
        threads.append(t)
    # url_process_pool = multiprocessing.Pool(NUM_THREADS,url_worker,initargs=(url_queue,))

element_tree = main.render("main2.html")

if not running_in_idle:
    for process in range(NUM_THREADS):
        url_queue.put((None, None))
    # url_queue.close()
    for thread in threads:
        thread.join()
    # url_process_pool.close()
    # url_process_pool.join()

e_time = time.time()
print "\nFinished in {:.2f}s".format(e_time-s_time)
