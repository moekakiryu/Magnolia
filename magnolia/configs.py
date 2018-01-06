import collections
global config

class _Configs(collections.MutableMapping):
    def __init__(self,*args,**kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))
        self._save = {}
        self._no_new_attrs = True

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        elif 'store' in self.__dict__ and attr in self.__dict__['store']:
            return self.__dict__['store'][attr]
        else:
            raise AttributeError("{} instance does not have attribute '{}'".format(
                self.__class__.__name__,attr))

    def __setattr__(self,attr,val):
        if attr in self.__dict__:
            self.__dict__[attr] = val
        elif 'store' in self.__dict__ and attr in self.__dict__['store']:
            self.__dict__['store'][attr] = val
        elif '_no_new_attrs' in self.__dict__ and self.__dict__['_no_new_attrs']==True:
            raise AttributeError("{} instance can not create attribute {}".format(
                self.__class__.__name__,attr))
        else:
            self.__dict__[attr] = val

    def __bool__(self):
        return bool(self.store)

    def __nonzero__(self):
        return self.__bool__()

    def __cmp__(self, other):
        if isinstance(other,_Configs):
            return cmp(self.store,other.store)
        elif isinstance(other, dict):
            return cmp(self.store,other)
        return False

    def __eq__(self, other):
        if isinstance(other,_Configs):
            return self.store == other.store
        elif isinstance(other, dict):
            return self.store == other
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        if isinstance(other,_Configs):
            return self.store >= other.store
        elif isinstance(other, dict):
            return self.store >= other
        return False

    def __gt__(self, other):
        if isinstance(other,_Configs):
            return self.store > other.store
        elif isinstance(other, dict):
            return self.store > other
        return False        

    def __le__(self, other):
        if isinstance(other,_Configs):
            return self.store <= other.store
        elif isinstance(other, dict):
            return self.store <= other
        return False

    def __lt__(self, other):
        if isinstance(other,_Configs):
            return self.store < other.store
        elif isinstance(other, dict):
            return self.store < other
        return False

    def __contains__(self, key):
        return key in self.store

    def __getitem__(self, key):
        return self.store.__getitem__(key)

    def __setitem__(self, key, val):
        self.store.__setitem__(key, val)

    def __delitem__(self, index):
        self.store.__delitem__(index)

    def __len__(self):
        return len(self.store)

    def __iter__(self):
        return iter(self.store)

    def has_key(self, key):
        return self.store.has_key(key)

    def fromkeys(self,S,v=None):
        return dict.fromkeys(S,v)

    def viewkeys(self):
        return self.store.viewkeys()

    def viewvalues(self):
        return self.store.viewvalues()

    def viewitems(self):
        return self.store.viewitems()

    def clear(self):
        self.store.clear()

    def save(self):
        self._save = {}
        for k,v in self.store.items():
            self._save[k]=v

    def load(self):
        self.store = {}
        for k,v in self._save.items():
            self.store[k]=v

    def reset(self):
        self.store = {}
        self._save = {}

config = _Configs(
    REFERENCE_ELEMENTS_AS_ATTRIBUTES=False,
    AUTO_CLOSE_ELEMENTS=True, 
)