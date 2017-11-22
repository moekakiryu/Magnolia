import re
import abc

AT_RULES = ["charset","import","namespace","media","supports","document",
            "page","font-face","keyframes","viewport","counter-style",
            "font-feature-values","swash","ornaments","annotation",
            "stylistic","styleset","character-variant"]

INHERITED_ATTRIBUTES = ["caption-side","caret-color","color","cursor",
                        "direction","empty-cells","font","font-family",
                        "font-feature-settings","font-kerning",
                        "font-language-override","font-size","font-size-adjust",
                        "font-stretch","font-style","font-synthesis",
                        "font-variant","font-variant-alternates",
                        "font-variant-caps","font-variant-east-asian",
                        "font-variant-ligatures","font-variant-numeric",
                        "font-variant-position","font-weight",
                        "hanging-punctuation","hyphens","image-orientation",
                        "image-rendering","letter-spacing","line-height",
                        "list-style","list-style-image","list-style-position",
                        "list-style-type","object-position","orphans",
                        "overflow-wrap","pointer-events","quotes","ruby-align",
                        "ruby-position","tab-size","text-align",
                        "text-align-last","text-combine-upright","text-indent",
                        "text-justify","text-orientation","text-rendering",
                        "text-shadow","text-transform",
                        "text-underline-position","visibility","white-space",
                        "widows","word-break","word-spacing","word-wrap",
                        "writing-mode"]

PSEUDO_CLASSES = ["active","any","checked","default","dir","disabled","empty",
                  "enabled","first","first-child","first-of-type","fullscreen",
                  "focus","hover","indeterminate","in-range","invalid","lang",
                  "last-child","last-of-type","left","link","not","nth-child",
                  "nth-last-child","nth-last-of-type","nth-of-type",
                  "only-child","only-of-type","optional","out-of-range",
                  "read-only","read-write","required","right","root","scope",
                  "target","valid","visited"]

PSEUDO_ELEMENTS = ["after","before","cue","first-letter","first-line",
                   "selection","backdrop","placeholder","marker",
                   "spelling-error","grammar-error"]

# sorting longest to shortest will ensure short-circuit matches do not occur
# for example, 'first' matching 'first-child'
PSEUDO_CLASSES.sort(key=lambda i:len(i),reverse=True)
PSEUDO_ELEMENTS.sort(key=lambda i:len(i),reverse=True)

class CSSParserError(Exception):
    pass

class SearchToken:
    def __init__(self, head, tail, span, is_block):
        self.head = head
        self.tail = tail
        self.span = span
        self.is_block = is_block 

class CSSAbstract():
    __metaclass__ = abc.ABCMeta
    AT_RULE_SELECTOR = re.compile(r"@(?P<name>[_a-zA-Z\-]+)\s+(?P<arguments>.*?)" 
                                  r"(?:;\s*$|(?P<nested>\{))",re.DOTALL|re.MULTILINE)

    AT_RULE_TOKENIZER = re.compile(r"@\s*(?P<name>{rules})\s+(?P<arguments>.*)"
                                   r"".format(rules="|".join(AT_RULES)),
                                re.DOTALL|re.MULTILINE)

    # the 3 re patters below could be fit into one, but they are messy enough as it is
    # https://www.w3.org/TR/CSS21/grammar.html
    SELECTOR_TOKENIZER = re.compile(r"(?P<type>[#.]?)(?P<name>(?:-?[_a-zA-Z]+[_a-zA-Z0-9\-]*|\*)?)"
                                    r"(?P<attribute>(?:\[.*?\])?)"
                                    r"(?P<pseudo_class>(?:::?(?:{pseudo_classes})(?:\(.*?\))?)?)"
                                    r"(?P<pseudo_element>(?:::?(?:{pseudo_elems})(?:\(.*?\))?)?)"
                                    r"(?:\s*(?P<conn_type>[> +~])\s*)?".format(
                                        pseudo_classes="|".join(PSEUDO_CLASSES),
                                        pseudo_elems="|".join(PSEUDO_ELEMENTS)),
                                    re.DOTALL)

    FILTER_TOKENIZER = re.compile(r"\[(?P<name>-?[_a-zA-Z]+[_a-zA-Z0-9-]*)"
            r"(?:(?P<type>[*~|$^]?)=)['\"](?P<value>-?[_a-zA-Z]+[_a-zA-Z0-9-]*)['\"]\]",re.DOTALL)

    PSEUDO_TOKENIZER = re.compile(r"::?(?P<name>{pseudo_names})"
                                  r"(?:\((?P<argument>.*?)\))?".format(
                                   pseudo_names="|".join(PSEUDO_CLASSES+PSEUDO_ELEMENTS)),re.DOTALL)

    INLINE = 1
    AT_RULES = 2
    STYLES = 4

    @classmethod
    def _parse_css(cls, inpt):
        def unescaped_char(sub_string,i):
            return inpt[i]==sub_string and (i==0 or (i>0 and inpt[i-1]!="\\"))
        inpt = inpt.strip()
        while inpt:
            i = hs = he = ts = te = 0
            in_comment = False
            at_rule = False
            string_start = None
            while i<len(inpt):
                if not in_comment:
                    if inpt[i-2:i]=="/*":
                        in_comment = True
                    elif unescaped_char('"',i) or unescaped_char("'",i):
                        # strings are treated somewhat like comments,
                        # in that css constructs inside them are ignored
                        if string_start:
                            if inpt[i]==string_start:
                                string_start = None
                        else:
                            string_start = inpt[i]    
                    elif inpt[i]=='{':
                        break
                    elif inpt[i]=='@':
                        at_rule=True
                    elif at_rule and inpt[i]==";":
                        break
                else:
                    if inpt[i-2:i]=="*/":
                        hs=i
                        in_comment = False

                i+=1
            # i is now at first valid {
            if inpt[i]==";":
                yield SearchToken(inpt[hs:i],"",i-hs+1, False)
                inpt = inpt[i+1:]
                continue
            he = i
            ts = i+1 if i!=len(inpt)-1 else i
            nest_layer = 1
            while nest_layer>0:
                i += 1
                if unescaped_char('"',i) or unescaped_char("'",i):
                    if string_start:
                        if inpt[i]==string_start:
                            string_start = None
                    else:
                        string_start = inpt[i]  
                elif not string_start:
                    if inpt[i]=="}" and (i==0 or (i>0 and inpt[i-1]!="\\")):
                        nest_layer -= 1
                    elif inpt[i]=="{" and (i==0 or (i>0 and inpt[i-1]!="\\")):
                        nest_layer +=1
            te = i
            yield SearchToken(inpt[hs:he].strip(),inpt[ts:te].strip(),te-hs,True)
            inpt = inpt[te+1:].strip()

    @classmethod
    def _tokenize_selector(cls, inpt):
            results = re.finditer(cls.SELECTOR_TOKENIZER, inpt)
            found = []
            for result in results:
                if any(result.groups()):
                    found.append(result)
            return iter(found)

    @classmethod
    def _parse_at_rules(cls, inpt):
        while inpt:
            find = re.finditer(cls.AT_RULE_SELECTOR,inpt)
            if find:
                next_find = find.next()
            else:
                break
            rule_dict = {'name':next_find.group("name"),
                         'arguments':next_find.group("arguments"),
                         'end':next_find.group("nested"),
                         'match':next_find,
                         'span':(0,0),
                         'content':None}
            if next_find.group("nested"):
                nest_layer = 1
                i = next_find.end()
                while nest_layer>0:
                    i+=1
                    if inpt[i]=="{":
                        nest_layer+=1
                    elif inpt[i]=="}":
                        nest_layer-=1
                rule_dict['content'] = inpt[next_find.end():i]
                rule_dict['span'] = (next_find.start(),i)
            else:
                rule_dict['span'] = next_find.span()
            yield rule_dict # this is supposed to mimic the behavior of finditer
            inpt = inpt[i:]

    @abc.abstractmethod
    def get_copy(self):
        return

    @abc.abstractmethod
    def parse(self, inpt):
        return

    @abc.abstractmethod
    def match(self, element):
        return

    @abc.abstractmethod
    def merge(self, other):
        return

    @abc.abstractmethod
    def render(self, flags=0):
        return
        