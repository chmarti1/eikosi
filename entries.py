#
#   ENTRIES.PY
#
#   Provides the Entry class and its children
#   These are the workhorse classes for bibliographic data management.

import os,sys
import items

__version__ = '0.0'

class Entry:
    """Parent Eikosi entry class
pbe = Entry(name)

Entry 

** The mandatory and optional dicts **

The mandatory and optional dicts are attributes that are supposed to reside with
the class object, and that should only be referenced by instances.  They define
which bibliography entry items are required and allowed, they specify a handler
to convert data entered in the source file, they specify which data types are
allowed for that entry, and they specify comment text to be written to data 
files before that item line.

Each element of the mandatory and optional lists must be a tuple with five 
elements: 
mandatory[itemname] = [AllowedTypes, InputHandler, CodeHandler, OutputHandler]

--> ItemName
The element name is a string that identifies the bibliographic item (like 
'author' or 'title').  

--> AllowedTypes
The allowed types list is expected to be a class or type of data that is 
expected for this entry.  Alternately, AllowedTypes may be a tuple of types.  
Valid data types for this item should pass the test:
    isinstance(data, AllowedTypes).

--> InputHandler
The input handler is a function or class that will be used to process the item 
data specified by a source file.  If it is None, then the data will be left 
alone.  Otherwise, it must be a callable object, and it must return the data 
that will be written to the bibliographic item in the entry.
    self.bib[ElementName] = InputHandler(data)

When the input handler is None, the data are not modified, but stored as-loaded
in the bibliographic dictionary.
    
--> CodeHandler
Code handlers are used to construct a bibliographic record file that can be
reloaded later.  The code handler must be a callable object that accepts the 
bibliographic item data as its only argument, and it must return a string 
representation of the data that is executable Python code.  Each item assignment
statement takes the form:
    "{entry:}.{item:} = {value:}"
where the entry object will have already been created in the python file.  The
act of writing to member "item" will create that item in the bibliographic 
dictionary.

When the code handler for the item is not None, then
    value = codehandler(self.bib[item])
is run to construct the value string.  Otherwise, the value is passed verbatim
to the format function used to construct the output.
    
--> OutputHandler
Output handlers are used to condition the item data for output to a bibtex 

** The default member **
Like the mandatory and optional member lists, the default list is a static 
attribute that resides in the parent class (and not the instance).  It defines
handlers for items that are not recognized as members of mandatory or optional.
It must be of the form
    [allowedtypes, inputhandler, codehandler, outputhandler]

"""
    mandatory = {}
    optional = {}
    default = [str, None, repr, None]
    tag = '@MISC'

    def __init__(self, name):
        if not isinstance(name, str):
            raise Exception('Entry.__init__: The entry name must be a string.')
        
        self.__dict__['name'] = name
        self.__dict__['sourcefile'] = None
        self.__dict__['bib'] = dict()

    def __lt__(self, other):
        if not issubclass(type(other), Entry):
            raise Exception('Entry.__lt__: comparison is only allowed between entries.')
        return self.name < other.name

    def __gt__(self, other):
        if not issubclass(type(other), Entry):
            raise Exception('Entry.__gt__: comparison is only allowed between entries.')
        return self.name > other.name

    def __eq__(self, other):
        if not issubclass(type(other), Entry):
            raise Exception('Entry.__eq__: comparison is only allowed between entries.')
        return self.name == other.name
        
    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]
        bib = self.__dict__['bib']
        if item in bib:
            return bib[item]
        raise AttributeError(item)
        
    def __setattr__(self, item, value):
        if item in self.__dict__:
            self.__dict__[item] = value
        else:
            self.bib[item] = value

    def post(self, fatal=True, verbose=False, strict=False):
        """Post processing algorithm
The post method is intended to be run on entries after they are defined in their
source files.  Each Entry sub-class defines its own post algorithm.  The default
Entry post method only runs check_bib() verbosely and fatally.
"""
        err = False
        handled = []
        # Loop through the mandatory items
        for itemname,(allowedtypes,inputhandler,codehandler,outputhandler) in self.mandatory.items():
            if isinstance(allowedtypes,type):
                allowedtypes = (allowedtypes,)
                
            # Check that each mandatory item exists and is a legal type
            if itemname not in self.bib:
                err = True
                if verbose or fatal:
                    sys.stderr.write('Entry.post: Mandatory item "{}" was not found in entry "{}"\n'.format(itemname, self.name))
                if fatal:
                    raise Exception('Missing mandatory item')
            elif not isinstance(self.bib[itemname], allowedtypes):
                err = True
                if verbose or fatal:
                    sys.stderr.write('Entry.post: Item {} is type {}.\n'.format(itemname, repr(type(self.bib[itemname]))))
                    sys.stderr.write('    Legal types are:')
                    for this in allowedtypes:
                        sys.stderr.write(' ' + repr(this))
                    sys.stderr.write('\n')
                if fatal:
                    raise Exception('Entry.post: Illegal item type')
            elif inputhandler is not None:
                try:
                    self.bib[itemname] = inputhandler(self.bib[itemname])
                except:
                    sys.stderr.write('Entry.post: Input processing failure on entry "{}", item "{}".\n'.format(self.name, itemname))
                    raise sys.exc_info()[1]
            handled.append(itemname)
               
        # Loop through the optional items
        for itemname,(allowedtypes,inputhandler,codehandler,outputhandler) in self.optional.items():
            if isinstance(allowedtypes, type):
                allowedtypes = (allowedtypes,)
            
            if itemname not in self.bib:
                pass
            elif not isinstance(self.bib[itemname], allowedtypes):
                err = True
                if verbose or fatal:
                    sys.stderr.write('Entry.post: Item {} is type {}.\n'.format(itemname, repr(type(self.bib[itemname]))))
                    sys.stderr.write('    Legal types are:')
                    for this in allowedtypes:
                        sys.stderr.write(' ' + repr(this))
                    sys.stderr.write('\n')
                if fatal:
                    raise Exception('Entry.post: Illegal item type')
            elif inputhandler is not None:
                try:
                    self.bib[itemname] = inputhandler(self.bib[itemname])
                except:
                    sys.stderr.write('Entry.post: Input processing failure on entry "{}", item "{}".\n'.format(self.name, itemname))
                    raise sys.exc_info()[1]
            handled.append(itemname)
            
        # Loop over the remaining items
        allowedtypes,inputhandler,codehandler,outputhandler = self.default
        for itemname,value in self.bib.items():
            if itemname not in handled:
                if strict:
                    raise Exception('Entry.post: Run in strict and found unrecognzied item: ' + itemname)
                elif not isinstance(value,allowedtypes):
                    raise Exception('Entry.post: Default data type requirement violated by item: ' + itemname)
                if inputhandler:
                    self.bib[itemname] = inputhandler(value)
        return err
        
    def save(self, target, addimport=True, entry='entry'):
        """Save the bibliographic entry to a file capable of reconstructing it
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.save(ff, addimport=addimport, entry=entry)
        
        # Detect the class and module names
        thisclass = self.__class__.__name__
        thismodule = self.__class__.__module__
        
        args = {'e':entry, 'c':thisclass, 'm':thismodule, 'n':self.name}
        
        if addimport:
            target.write('import {m:s}\n\n'.format(**args))
        
        target.write('{e:s} = {m:s}.{c:s}(\'{n:s}\')\n\n'.format(**args))
        
        handled = []
        for item,(allowedtypes,inputhandler,codehandler,outputhandler) in self.mandatory.items():
            if item in self.bib:
                if codehandler:
                    value = codehandler(self.bib[item])
                else:
                    value = self.bib[item]
                target.write('{e:s}.{i:s} = {v:}\n'.format(i=item, v=value, **args))
                handled.append(item)
        for item,(allowedtypes,inputhandler,codehandler,outputhandler) in self.optional.items():
            if item in self.bib:
                if codehandler:
                    value = codehandler(self.bib[item])
                else:
                    value = self.bib[item]
                target.write('{e:s}.{i:s} = {v:}\n'.format(i=item, v=value, **args))
                handled.append(item)
        allowedtypes, inputhandler, codehandler, outputhandler = self.default
        for item,value in self.bib.items():
            if item not in handled:
                if codehandler:
                    value = codehandler(value)
                target.write('{e:s}.{i:s} = {v:}\n'.format(i=item, v=value, **args))
                
    def savebib(self, target):
        """Save the bibliographic entry as a bibtex entry"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.export(ff)
                
        handled = []
        target.write(self.tag + '{' + self.name + '\n')
        for item,(allowed,inputhandler,codehandler,outputhandler) in self.mandatory.items():
            if item in self.bib:
                if outputhandler:
                    value = outputhandler(self.bib[item])
                else:
                    value = self.bib[item]
                target.write('    {i:s} = {{{v:}}},\n'.format(i=item,v=value))
                handled.append(item)
        for item,(allowed,inputhandler,codehandler,outputhandler) in self.optional.items():
            if item in self.bib:
                if outputhandler:
                    value = outputhandler(self.bib[item])
                else:
                    value = self.bib[item]
                target.write('    {i:s} = {{{v:}}},\n'.format(i=item,v=value))
                handled.append(item)
        allowedtypes, inputhandler, codehandler, outputhandler = self.default
        for item,value in self.bib.items():
            if item not in handled:
                if outputhandler:
                    value = outputhandler(value)
                target.write('    {i:s} = {{{v:}}},\n'.format(i=item,v=value))
        target.write('}\n\n')
        
    def get_rules(self,item):
        """Return the appropriate rules for the item
    allowed, inputhandler, codehandler, outputhandler = ee.get_rules('itemname')
"""
        if item in self.mandatory:
            return self.mandatory[item]
        elif item in self.optional:
            return self.optional[item]
        else:
            return self.default



###
# Entry definitions
###

class ArticleEntry(Entry):
    """Eikosi Article Entry
pba = ArticleEntry(name)
"""
    tag = '@ARTICLE'
    mandatory = {
        'author':((str,list,tuple,items.AuthorList), items.AuthorList, repr, str),
        'title': (str, None, repr, None),
        'journal': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'volume': ((str,int), int, repr, repr),
        'number': ((str,int), int, repr, repr),
        'page': (str, None, repr, None)}

class ReportEntry(Entry):
    """Eikosi Report Entry
pba = ReportEntry(name)
"""
    tag = '@TECHREPORT'
    mandatory = {
        'author':((str,list,tuple,items.AuthorList), items.AuthorList, repr, str),
        'title': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'institution': (str, None, repr, None),
        'month': (str, None, repr, None),
        'day': ((str,int), int, repr, repr)}
        
class ProceedingsEntry(Entry):
    """Eikosi Proceedings Entry
pba = ProceedingsEntry(name)
"""
    tag = '@INPROCEEDINGS'
    mandatory = {
        'author': ( (str,list,tuple,items.AuthorList), items.AuthorList, repr, str),
        'title': ( str, None, repr, None),
        'booktitle': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'volume': ((str,int), int, repr, repr),
        'number': ((str,int), int, repr, repr),
        'page': (str, None, repr, repr)}

class PatentEntry(Entry):
    """Eikosi Proceedings Entry
pba = PatentEntry(name)
"""
    tag = '@MISC'
    mandatory = {
        'author': ((str,list,tuple,items.AuthorList), items.AuthorList, repr, str),
        'title': (str, None, repr, None),
        'number': ((int,str), int, repr, repr),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'assignee': (str, None, repr, None),
        'nationality': (str, None, repr, None)}

    # Overload the export method
    def savebib(self, target):
        """Save the bibliographic entry as a bibtex entry"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.export(ff)
                
        target.write(self.tag + '{' + self.name + ',\n')
        # Manually construct the entry
        if 'author' in self.bib:
            target.write('    author = {' + str(self.bib['author']) + '},\n')
        if 'title' in self.bib:
            target.write('    title = \{{title:}\},\n'.format(**self.bib))
        if 'assignee' in self.bib:
            target.write('    note = \{{assignee:}\},\n'.format(**self.bib))
        if 'number' in self.bib:
            if 'nationality' in self.bib:
                target.write('    howpublished = \{{nationality:} Pat. N. {number:d}\},\n'.format(**self.bib))
            else:
                target.write('    howpublished = \{Pat. N. {number:d}\},\n'.format(**bib))
        if 'year' in self.bib:
            target.write('    year = {year:d},\n'.format(**bib))
        
        handled = ['author', 'title', 'assignee', 'number', 'year']
        for item,value in self.bib.items():
            if item not in handled:
                target.write('    {i:s} = {v:},\n'.format(i=item,v=repr(value)))
        target.write('}\n\n')
        
        
class BookEntry(Entry):
    tag = '@BOOK'
    mandatory = {
        'author': ((str,list,tuple,items.AuthorList), items.AuthorList, repr, str),
        'title': (str, None, repr, None),
        'publisher': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'address': (str, None, repr, repr),
        'edition': (str, None, repr, repr)}
        
        
class WebsiteEntry(Entry):
    tag = '@MISC'
    mandatory = {
        'url': (str, None, repr, None)}
    optional = {
        'title': (str, None, repr, None),
        'author': ((str, list, tuple, items.AuthorList), items.AuthorList, repr, str),
        'institution': (str, None, repr, None),
        'accessed': (str, None, repr, None)}


class MiscEntry(Entry):
    tag = '@MISC'

    
