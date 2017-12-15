import re
import abc
from os import path
import string


class Trie(object):
    # __slots__ = ["trie","_seg_d","_seg_i"]
    def __init__(self, *items):
        self.trie = {}
        self._seg_d = self.trie
        self._seg_i = 0
        if items:
            for i in items:
                self.add(i)

    def add(self, item):
        cur_d = self.trie
        for n,c in enumerate(item):
            if not c in cur_d:
                inserted = False
                for k in cur_d.keys():
                    if k.startswith(c):
                        cur_d[c]={}
                        if len(k)>1:
                            cur_d[c][k[1:]] = {}
                        del cur_d[k]
                        inserted = True
                        break
                if not inserted:
                    cur_d[item[n:]] = {}
                    break
            cur_d = cur_d[c]

    def seg_contains(self,c):
        if isinstance(self._seg_d, dict):
            if not c in self._seg_d:
                for k in self._seg_d.keys():
                    if k.startswith(c):
                        self._seg_d = k
                        return
                self.seg_reset()
                return False
            elif len(self._seg_d[c])<1:
                self.seg_reset()
                return True
            else:
                self._seg_d = self._seg_d[c]
        elif isinstance(self._seg_d,str):
            self._seg_i+=1
            if self._seg_i>=len(self._seg_d)-1:
                self.seg_reset()
                return True
            elif not c==self._seg_d[self._seg_i]:
                self.seg_reset()
                return False

    def seg_reset(self):
        self._seg_d = self.trie
        self._seg_i = 0

    def contains(self, item):
        cur_d = self.trie
        for n,c in enumerate(item):
            if not c in cur_d:
                for k in cur_d.keys():
                    if k.startswith(c):
                        return k==item[n:]
                return False
            elif len(cur_d[c])<1:
                return True
            else:
                cur_d = cur_d[c]
        return False


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

PC_TRIE = Trie(*PSEUDO_CLASSES)
PE_TRIE = Trie(*PSEUDO_ELEMENTS)


class CSSParserError(Exception):
    pass

class CSSToken:
    def __init__(self, text, head, tail, span, is_block):
        self.head = head
        self.tail = tail
        self.span = span
        self.text = text
        self.is_block = is_block 

class SelectorToken:
    def __init__(self):
        self.type = ''
        self.name = ''
        self.attribute = ''
        self.pseudo_class = ''
        self.pseudo_element = ''
        self.conn_type = ''

    def __str__(self):
        return "Match('{}','{}','{}','{}','{}','{}')".format(self.type,self.name,self.attribute,
                                                             self.pseudo_class,self.pseudo_element,
                                                             self.conn_type)
    def __repr__(self):
        return self.__str__()

    def __bool__(self):
        return bool(self.name or self.attribute or self.pseudo_class or self.pseudo_element)

    def __nonzero__(self):
        return self.__bool__()

    def joined(self):
        s = "{}{}{}{}{}{}".format(self.type,self.name,self.attribute,self.pseudo_class,
                                 self.pseudo_element,self.conn_type)
        return s

class CSSAbstract():
    __metaclass__ = abc.ABCMeta

    INLINE = 1
    AT_RULES = 2
    STYLES = 4

    _instance_counter = 0

    def __init__(self):
        self._instance_no = CSSAbstract._instance_counter
        CSSAbstract._instance_counter += 1

    def __cmp__(self, other):
        if not isinstance(other, CSSAbstract):
            raise TypeError("Type '{}' uncomparable to type 'CSSAbstract'".format(type(other)))
        return self._instance_no - other._instance_no

    def __gt__(self,other):
        return self.__cmp__(other)>0

    def __lt__(self,other):
        return self.__cmp__(other)<0

    def __gte__(self,other):
        return self.__cmp__(other)>=0

    def __lte__(self,other):
        return self.__cmp__(other)<=0

    @classmethod
    def _parse_css(cls, inpt,src=None):
        def unescaped_char(sub_string,i):
            return inpt[i]==sub_string and (i==0 or (i>0 and inpt[i-1]!="\\"))
        inpt = inpt.strip()
        while inpt:
            # i = hs = he = ts = te = 0
            k=i=0
            head = tail = ""
            in_comment = False
            at_rule = False
            string_start = None
            while i<len(inpt):
                if in_comment:
                    if inpt[i-2:i]=="*/":
                        k=i
                        in_comment = False
                else:
                    if inpt[i:i+2]=="/*":
                        head += inpt[k:i]
                        in_comment = True
                        continue
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
                i+=1
            head += inpt[k:i]
            if i>=len(inpt):
                raise StopIteration
            # i is now at first valid { or ;
            if inpt[i]==";":
                yield CSSToken(inpt[:i+1],head,"",i+1, False)
                inpt = inpt[i+1:]
                continue
            # he = i
            k = i+1 if i!=len(inpt)-1 else i
            nest_layer = 1
            while i<len(inpt):
                i += 1
                if in_comment:
                    if inpt[i-2:i]=="*/":
                        k=i
                        in_comment = False
                else:
                    if inpt[i:i+2]=="/*":
                        tail+=inpt[k:i]
                        in_comment=True
                        continue
                    elif unescaped_char('"',i) or unescaped_char("'",i):
                        if string_start:
                            if inpt[i]==string_start:
                                string_start = None
                        else:
                            string_start = inpt[i]  
                    elif not string_start:
                        if inpt[i]=="}" and (i==0 or (i>0 and inpt[i-1]!="\\")):
                            nest_layer -= 1
                            if nest_layer<=0:
                                break
                        elif inpt[i]=="{" and (i==0 or (i>0 and inpt[i-1]!="\\")):
                            nest_layer +=1
            tail += inpt[k:i]
            yield CSSToken(inpt[:i+1].strip(),head.strip(),tail.strip(),i,True)
            inpt = inpt[i+1:].strip()

    @abc.abstractmethod
    def get_copy(self):
        return

    @abc.abstractmethod
    def parse(self, inpt):
        return

    @abc.abstractmethod
    def render(self, flags=0):
        return


class StaticAbstract():
    __metaclass__ = abc.ABCMeta
    # the 2 re patters below could be fit into one, but they are messy enough as it is
    # https://www.w3.org/TR/CSS21/grammar.html
    FILTER_TOKENIZER = re.compile(r"\[(?P<name>-?[_a-zA-Z]+[_a-zA-Z0-9-]*)"
            r"(?:(?P<type>[*~|$^]?)=['\"](?P<value>[_a-zA-Z0-9-]*)['\"])?\]",re.DOTALL)

    PSEUDO_TOKENIZER = re.compile(r"::?(?P<name>{pseudo_names})"
                                  r"(?:\((?P<argument>.*)\))?".format(
                                   pseudo_names="|".join(PSEUDO_CLASSES+PSEUDO_ELEMENTS)),re.DOTALL)

    @classmethod
    def _tokenize_selector(cls,inpt):
        matches = []
        k = i = 0
        cur_match = SelectorToken()
        while i<len(inpt):
            if inpt[i] in "#.":
                if (cur_match.type or cur_match.name or cur_match.attribute
                    or cur_match.pseudo_class):
                    matches.append(cur_match)
                    cur_match=SelectorToken()
                cur_match.type=inpt[i]

            elif inpt[i]=="[":
                while i<len(inpt) and inpt[i]!=']':
                    i+=1
                cur_match.attribute = inpt[k:i+1]

            elif inpt[i] in "-_"+string.ascii_letters and not cur_match.name:
                if inpt[i]=='-':
                    i+=1
                if not inpt[i] in "_"+string.ascii_letters:
                        raise CSSParserError("Malformed class name at position {}.".format(i))
                i+=1
                while i<len(inpt) and inpt[i] in "_-"+string.ascii_letters+string.digits:
                    i+=1
                cur_match.name=inpt[k:i]
                k=i
                continue

            elif inpt[i] in "*":
                cur_match.name=inpt[i]

            elif inpt[i]==":":
                k=i
                i+=1
                if inpt[i]==":":
                    i+=1
                cls_res = None
                while cls_res==None and i<len(inpt):
                    cls_res = PC_TRIE.seg_contains(inpt[i])
                    i+=1
                PC_TRIE.seg_reset()
                if cls_res:
                    if i<len(inpt) and inpt[i]=="(":
                        p_count = 1
                        while p_count>0 and i<len(inpt):
                            i+=1
                            if inpt[i]=="(":
                                p_count+=1
                            elif inpt[i]==")":
                                p_count-=1
                        i+=1
                    if cur_match.pseudo_class:
                        matches.append(cur_match)
                        cur_match = SelectorToken()
                    cur_match.pseudo_class = inpt[k:i]
                    k=i
                    continue
                if cur_match.name or cur_match.attribute or cur_match.pseudo_class:
                    ele_res = None
                    i=k
                    while ele_res==None and i<len(inpt):
                        ele_res = PE_TRIE.seg_contains(inpt[i])
                        i+=1
                    PE_TRIE.seg_reset()
                    if ele_res:
                        if i<len(inpt) and inpt[i]=="(":
                            p_count = 1
                            while p_count>0 and i<len(inpt):
                                i+=1
                                if inpt[i]=="(":
                                    p_count+=1
                                elif inpt[i]==")":
                                    p_count-=1
                            i+=1
                        cur_match.pseudo_element = inpt[k:i]
                        k=i
                        continue
                i=k

            elif inpt[i] in ">+~":
                cur_match.conn_type=inpt[i]
                matches.append(cur_match)
                cur_match = SelectorToken()

            elif inpt[i] in string.whitespace:
                while i<len(inpt) and inpt[i] in string.whitespace:
                    i+=1
                k=i
                if (i>len(inpt) or (
                  (cur_match.name or cur_match.attribute or cur_match.pseudo_class) 
                  and not inpt[i] in ">+~")):
                    cur_match.conn_type = ' '
                    matches.append(cur_match)
                    cur_match = SelectorToken()
                    k=i
                continue
            i+=1
            k=i
        if cur_match:
            matches.append(cur_match)
        return matches

    @abc.abstractmethod
    def match(self, element):
        return

    @abc.abstractmethod
    def merge(self, other):
        return

class DynamicAbstract():
    __metaclass__ = abc.ABCMeta

    AT_RULE_SELECTOR = re.compile(r"@(?P<name>[_a-zA-Z\-]+)(?:\s+(?P<arguments>.*?))?" 
                                  r"(?:;\s*$|(?P<nested>\{))",re.DOTALL|re.MULTILINE)

    AT_RULE_TOKENIZER = re.compile(r"@\s*(?P<name>[_a-zA-Z\-]+)(?:\s+(?P<arguments>.*))?".format(
                                   rules="|".join(AT_RULES)),re.DOTALL|re.MULTILINE)

    @abc.abstractmethod
    def evaluate(self, environment=None):
        return

class ContainerAbstract():
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def add(self, item):
        return

    @abc.abstractmethod
    def remove(self, item):
        return

    @abc.abstractmethod
    def has(self, item):
        return

    @abc.abstractmethod
    def flatten(self):
        return