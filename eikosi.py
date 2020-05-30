#!/usr/bin/python3
"""The PyBib module provides classes and data for managing searchable collections
of bibliographic entries.  Some terminology used here:
ITEM:   A single datum in an Entry.  For example author, title, year, etc...
ENTRY:  A bibliographic record of a single reference.  An Entry may belong to a 
        colleciton and is composed of items.
COLLECTION: A group of Entries and Collections.
MEMBER: An Entry or Collection that belongs to a Collection or one of the member
        Collections.

The Entry classes are:
Entry
|-> ArticleEntry
|-> ProceedingsEntry
|-> PatentEntry
|-> BookEntry
\-> WebsiteEntry

The parent Entry class defines default methods for saving and exporting 
bibliographic data that are usually completely extensible to each of the child
class instances.  All attributes that are written or read after initialization
are found in the Entry's 'bib' dict.  For example
    pb = pybib.WebsiteEntry('martin:2020')
    pb.url = 'https://github.com/chmarti1/pybib'
    print(pb.url)
is equivalent to
    pb.bib['url'] = 'https://github.com/chmarti1/pybib'
    print(pb.bib['url'])
    
However, note that the name attribute is NOT found in the bib dictionary, and 
obviously, neither is bib itself!  There are three instance attributes that are
accessible, but that are NOT part of the bibliographic entry:
--> name
The tag assigned to the entry in the bibtex entry
--> sourcefile
The file from which the Entry was loaded if loaded by load()
--> bib
The bibliographic dict.  Each item in the bib dict will form an item in the 
bibtex entry.
"""


import os, sys
# reflexive import for forward references
import eikosi as ek

EXT = '.eks'

AL_DEF_FULLFIRST = True
AL_DEF_FULLOTHER = False
class AuthorList:
    """PyBib Author List handler class

al = AuthorList("My L. o'Authors and From Bibtex")
    OR
al = AuthorList(["My L. o'Authors", "As List"])
    OR
al = AuthorList([("My","L.","o'Authors"), ("As", "Nested", "List")])
    OR
al = AuthorList(existing_author_list)

The AuthorList class is designed to handle author list entries automatically.  
The lists may be formatted in a Bibtex style and-separated format, or they may
be already segmented into a list/tuple of strings, or they may be in nested 
list/tuple for separating the name parts, or the argument may be an existing
AuthorList object.

If either of the first two are input, they are automatically split by the "and"
separator and then by whitespace into name parts.  This behavior can be escaped
using LaTex {} brackets and quotes "" or ''.  For example, the author list

    "Albert von Fuddyduddy and Plot de Vice"

would naturally be split into

    [("Albert", "von", "Fuddyduddy), ("Plot", "de", "Vice")]

which is NOT ideal since neither "von" nor "de" were intended as middle names.  
Instead, if the input were

    "Albert {von Fuddyduddy} and Plot {de Vice}"

The brackets are treated as an inseparable unit so the last names are treated
appropriately.

    [("Albert", "{von Fuddyduddy}"), ("Plot", "{de Vice}")]
    
Note that the escape characters are NOT stripped from the name parts.  This
means that when the Bibtex entries are reconstructed, they will be retained.
"""
    def __init__(self, raw, fullfirst=AL_DEF_FULLFIRST, fullother=AL_DEF_FULLOTHER):
        self.fullfirst = fullfirst
        self.fullother = fullother
        self.names = None
        
        # Pre-conditioning... force raw to be a list
        if isinstance(raw,str):
            self.names = self._str_parse(raw)
        # If the input is a tuple, convert it to a list and try again
        elif isinstance(raw,tuple):
            AuthorList.__init__(self, list(raw))
        # If raw is still not a list, dump out of it
        elif isinstance(raw,list):
            # Loop through each author
            # We will convert the entries one-by-one
            self.names = []
            for author in raw:
                if isinstance(author,str):
                    self.names += self._str_parse(author)
                elif isinstance(author,(tuple,list)):
                    # Force the name parts to a list
                    this = list(author)
                    # Test to be certain each part is a string.
                    for part in this:
                        if not isinstance(part,str):
                            raise Exception('AuthorList.__init__: Unrecognized name part: ' + repr(part) + '\n') 
                    self.names.append(this)
        # If called with an existing author list
        elif isinstance(raw,AuthorList):
            # Do not copy the content; point to it.
            self.names = raw.names
        else:
            raise Exception('AuthorList.__init__: Unhandled input: ' + repr(raw) + '\n')
        
    def __repr__(self):
        out = self.__class__.__module__ + '.AuthorList(' + repr(self.names)
        if self.fullfirst != AL_DEF_FULLFIRST:
            out += ', fullfirst=' + repr(self.fullfirst)
        if self.fullother != AL_DEF_FULLOTHER:
            out += ', fullother=' + repr(self.fullother)
        out += ')'
        return out
        
    def __str__(self):
        out = ''
        for thisauthor in self.names:
            # If this is not the first entry
            if out:
                out += ' and '
            # Deal with the first name
            if len(thisauthor)>1:
                part = thisauthor[0]
                if self.fullfirst:
                    out += part + ' '
                else:
                    out += self._initial(part) + '. '
            # Deal with the middle name(s)
            for part in thisauthor[1:-1]:
                if self.fullother:
                    out += part + ' '
                else:
                    out += self._initial(part) + '. '
            # Check to be certain the entry is not empty
            # Append the last name
            if len(thisauthor):
                out += thisauthor[-1]
        return out
        
    def _initial(self, part):
        """Helper function to construct an initial from a name part"""
        escape = False
        for char in part:
            # If this character is escaped, ignore it
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char.isalpha():
                return char.upper()
        raise Exception('AuthorList._initial: Failed to find a valid alpha character from: ' + part + '\n')
        
    def _str_parse(self, raw):
        """Helper funciton for parsing strings in author names"""
        # Initialize a state machine for scanning the string
        bracket = 0     # Bracket level counter
        quote = 0       # Quote level counter
        squote = 0      # Single quote level counter
        ii = 0          # Starting index in the string for the next name part
        authors = [[]]  # Name part list
        this = authors[-1]
        for jj,tchar in enumerate(raw):
            # If a space has been identified outside of an escape sequence
            if tchar.isspace() and bracket==quote==squote==0:
                # If text has been identified
                if ii<jj:
                    text = raw[ii:jj]
                    # If the text is the Bibtex "and" separator
                    if text == 'and':
                        # If the word "and" was the first thing in the list
                        if not authors[-1]:
                            raise Exception('AuthorList._str_parse: Leading "and" separator.\n')
                        authors.append([])
                        this = authors[-1]
                    else:
                        this.append(text)
                ii = jj+1
            elif tchar == '{' and quote==squote==0:
                bracket += 1
            elif tchar == '}' and quote==squote==0:
                bracket -=1
                if bracket < 0:
                    raise Exception('AuthorList._str_parse: Found } with no matching {.\n')
            elif tchar == '"' and bracket==0 and squote==0:
                quote = 0 if quote else 1
            elif tchar == "'" and bracket==0 and quote==0:
                squote = 0 if squote else 1
        # Was there unhanlded text when the string terminated?
        if jj+1>ii:
            text = raw[ii:]
            if text == 'and':
                raise Exception('AuthorList._str_parse: Trailing "and" separator.\n')
            this.append(text)
        return authors

    def show(self):
        """Generate a formatted string of author names
    authorstr = al.show()
    
The formatting of the author string is dependent on the fullfirst and fullother
attributes.  If they are set to False, their respective name parts will be 
truncated to first initials using the _initial() method.  If they are True, then
the respective name part will be written in order without modification.
"""
        first = True
        out = ''
        for author in self.names:
            # Append a comma to the previous author name?
            if first:
                first = False
            else:
                out += ', '
                
            # First name
            if self.fullfirst:
                out += author[0] + ' '
            else:
                out += self._initial(author[0]) + '. '
            # Middle name(s)
            for name in author[1:-1]:
                if self.fullother:
                    out += name + ' '
                else:
                    out += self._initial(name) + '. '
            # Last name
            out += author[-1]
        return out
        

    def hasauthor(lastname=None, firstname=None, othername=None, anyname=None):
        """Test whether an author name is in the author list
    position = al.hasauthor( ... )

Returns -1 if the author is not found in the author list.  If the author is 
found, then position is the author's position in the name list. There is a 
series of keyword arguments that configure the comparison. In order, they are:
    hasauthor(lastname=None, firstname=None, othername=None, anyname=None)

So,
    TF = al.hasauthor('Martin')
returns True only if the author list has an author with the last name Martin. To
modify the test so that any name can be used,
    TF = al.hasauthor(anyname='Martin')
    
When multiple name parts are used simultaneously, they must all match a single 
author in order for the test to succeed.  For example, consider the following
author lists:
    "Paul Anderson and Lawrence Lund"
    "Paul Lund and Lawrence Anderson"
Both lists have an author with the last name "Anderson" and both have an author
with the first name "Paul", but only the first will result in True for
    al.hasauthor("Anderson", "Paul")
    al.hasauthor(lastname="Anderson", firstname="Paul")
    
In the current implementation of hasauthor(), the strings must match exactly.
Special characters like {} or \\ are not processed, and case must match.
"""
        # Loop through each author and check the name
        for index,author in enumerate(self.names):
            # Let test be a state indicating whether a test has failed
            test = True
            # Apply the name tests one-by-one
            if test and lastname is not None:
                test = (lastname == author[-1])
            if test and firstname is not None:
                test = (firstname == author[0])
            if test and othername is not None:
                # Assume the match fails unless a match is found
                test = False
                for name in author[1:-1]:
                    if othername == name:
                        test = True
                        break
            if test and anyname is not None:
                # Assume the match fails unless a match is found
                test = False
                for name in author:
                    if othername == name:
                        test = True
                        break
            if test:
                return index
        return -1


class Entry:
    """Parent Eikosi entry class
pbe = Entry(name)


** Built-in attributes **

Entries have five built-in attributes: name, sourcefile, docfile, collections,
and bib.  Access to additional attributes is described below in the next 
section.

--> name
A string identifying the entry in BibTeX.  This is the tag that appears 
immediately after the opening of an entry in the BibTeX file.  Eikosi also uses
the name as a unique identifier for the Entry.

--> sourcefile
This is the file from which the entry was loaded.  When entries are created in
scripts or the commandline, the sourcefile attribute is left None.

--> docfile
The docfile attribute is an optional string specifying a means for retrieving 
a copy of the document.  It could be a URL (e.g. 
https://website.com/dir/filename.pdf), a path to the file on the local machine, 
(e.g. /home/username/Documents/filename.pdf).

--> collections
The collections attribute is a list of collections to which the entry is 
supposed to belong.  Entries are expected to be the string name of the 
collection.

--> bib
This is a dict that contains all of the items that will be used to construct the
bibliographic record.  Every member of bib is accessible as an attribute of the
Entry, and writing to an nonexistant attribute creates a new member of bib. (see
below).


** Other attributes **

When reading or writing an attributes of an Entry that are not one of the, four
built-in attributes, they are instead treated as members of the bib dict.  For
example:
    import eikosi as ek
    ae = ek.AuthorEntry('my:author')
    ae.title
      ...
      AttributeError: title
    ae.bib['title']
      ...
      KeyError: 'title'
    ae.title = 'My Example Title'
    ae.title
      'My Example Title'
    ae.bib['title']
      'My Example Title'

When BibTeX exports are generated, they are generated explicitly from the keys 
and values in the bib dict.  In this way, the bibliographic data can be 
written and read like attributes, or through the bib dict.  Attribute access is 
usually much more convenient when writing scripts or working at the command 
line.  However, when inspecting the bib dict for bibliographic data, there is no
need to ignore the built-in attributes like name or sourcefile. 

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
    optional = {
        'author':((str,list,tuple,AuthorList), AuthorList, repr, str),
        'title': (str, None, repr, None),
        'journal': (str, None, repr, None),
        'booktitle': (str, None, repr, None),
        'publisher': (str, None, repr, None),
        'howpublished': (str, None, repr, None),
        'address': (str, None, repr, None),
        'year': ((int,str), int, repr, repr),
        'volume': ((str,int), int, repr, repr),
        'number': ((str,int), int, repr, repr),
        'page': (str, None, repr, None)}
    default = [str, None, repr, None]
    tag = '@MISC'

    def __init__(self, name):
        if not isinstance(name, str):
            raise Exception('Entry.__init__: The entry name must be a string.\n')
        
        self.__dict__['name'] = name
        self.__dict__['sourcefile'] = None
        self.__dict__['docfile'] = None
        self.__dict__['doc'] = ''
        self.__dict__['collections'] = []
        self.__dict__['bib'] = dict()

    def __str__(self):
        return self.show(doc=True, posix=True, width=80)

    def __lt__(self, other):
        if not issubclass(type(other), Entry):
            raise Exception('Entry.__lt__: comparison is only allowed between entries.\n')
        return self.name < other.name

    def __gt__(self, other):
        if not issubclass(type(other), Entry):
            raise Exception('Entry.__gt__: comparison is only allowed between entries.\n')
        return self.name > other.name

    def __eq__(self, other):
        if not issubclass(type(other), Entry):
            raise Exception('Entry.__eq__: comparison is only allowed between entries.\n')
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
source files.  Each Entry sub-class can define its own post algorithm.  This 
default Entry.post algorithm verifies that all of the mandatory items have been
defined, checks their data types, and runs the respective inputhandler functions
if they are defined.  If they are defined, the same is done for any optional
items.

post() also attempts to construct an absolute path for the docfile attribute.
The docfile attribute is assumed to be a path to a file (usually a pdf) that
is the target of the citation.  If the docfile attribute is not an absolute path
post() first attempts to treat it as a path relative to the sourcefile 
directory.  If the sourcefile directory is undefined or is not an absolute path,
then post() builds an absolute path relative to the current working dirrectory.
Finally, if the file to which the absolute path points does not exist, an error
condition is created (see fatal and verbose below).

There are are three optional keywords that change how post() operates:

fatal (True)
If there is an error while post processing any item, halt and raise an 
exception.  This is set to False when a collection is loaded with its relax 
option.  The entries will not be gauranteed to be correctly formatted, but the 
operation will still succeed, and the entries can be corrected in memory.

verbose (False)
When verbose is set to False, the post() method will only print to stdout or 
stderr when an exception is raised.  When verbose is set to True, the post() 
method prints a more detailed description of problems intended to help users
identify and fix problems with their source data files.  The same information
is printed when fatal=True, but it is probably a bad idea to run post() with 
BOTH fatal and verbose set to False.

strict (False)
When strict is True, all items in the entry MUST be in the mandatory or optional
lists.  When fatal is also set to True, an unrecognized item will result in an
Exception.  When fatal is not set, running strictly will strip unrecongized 
items from the entry.  Again, unless verbose is set, the user will not be warned
that this is happening.
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
                    sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                    if self.sourcefile:
                        sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                    sys.stderr.write('Entry.post: Mandatory item "{}" was not found in entry "{}"\n'.format(itemname, self.name))
                if fatal:
                    raise Exception('Missing mandatory item\n')
            elif not isinstance(self.bib[itemname], allowedtypes):
                err = True
                if verbose or fatal:
                    sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                    if self.sourcefile:
                        sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                    sys.stderr.write('Entry.post: Item {} is type {}.\n'.format(itemname, repr(type(self.bib[itemname]))))
                    sys.stderr.write('    Legal types are:\n')
                    for this in allowedtypes:
                        sys.stderr.write(' ' + repr(this))
                    sys.stderr.write('\n')
                if fatal:
                    raise Exception('Entry.post: Illegal item type\n')
            elif inputhandler is not None:
                try:
                    self.bib[itemname] = inputhandler(self.bib[itemname])
                except:
                    sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                    if self.sourcefile:
                        sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                    sys.stderr.write('Entry.post: Input handler failure on entry "{}", item "{}".\n'.format(self.name, itemname))
                    if fatal:
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
                    sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                    if self.sourcefile:
                        sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                    sys.stderr.write('Entry.post: Item {} is type {}.\n'.format(itemname, repr(type(self.bib[itemname]))))
                    sys.stderr.write('    Legal types are:\n')
                    for this in allowedtypes:
                        sys.stderr.write(' ' + repr(this))
                    sys.stderr.write('\n')
                if fatal:
                    raise Exception('Entry.post: Illegal item type\n')
            elif inputhandler is not None:
                try:
                    self.bib[itemname] = inputhandler(self.bib[itemname])
                except:
                    sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                    if self.sourcefile:
                        sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                    sys.stderr.write('Entry.post: Input processing failure on entry "{}", item "{}".\n'.format(itemname))
                    if fatal:
                        raise sys.exc_info()[1]
            handled.append(itemname)
            
        # Loop over the remaining items
        allowedtypes,inputhandler,codehandler,outputhandler = self.default
        for itemname,value in self.bib.items():
            if itemname not in handled:
                if strict:
                    if fatal or verbose:
                        sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                        if self.sourcefile:
                            sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                        sys.stderr.write('Entry.post: Found an unrecognzied item, and post() was run strictly: {}\n'.format(itemname))
                    if fatal:
                        raise Exception('Entry.post: Unrecognzied item\n')
                    else:
                        del self.bib[itemname]
                elif not isinstance(value,allowedtypes):
                    raise Exception('Entry.post: Default data type requirement violated by item: ' + itemname)
                if inputhandler:
                    try:
                        self.bib[itemname] = inputhandler(value)
                    except:
                        sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                        if self.sourcefile:
                            sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                        sys.stderr.write('Entry.post: Input processing failure on item: {}\n'.format(itemname))
                        if fatal:
                            raise sys.exc_info()[1]
                            
            # Inspect the docfile value if it is set
            if self.docfile:
                # Is it a relative path?
                # If so, attempt to construct an absolute path.
                if not os.path.isabs(self.docfile):
                    # If the sourcefile is set, get the containing directory there
                    if self.sourcefile and os.path.isabs(self.sourcefile):
                        sourcedir = os.path.split(self.sourcefile)
                        self.docfile = os.path.join(sourcedir, self.sourcefile)
                    # Otherwise, attempt to construct an absolute path using the pwd
                    else:
                        self.docfile = os.path.abspath(self.docfile)
                # Does the docfile exist?
                if not os.path.isfile(self.docfile):
                    if verbose or fatal:
                        sys.stderr.write('Entry.post: Error processing entry: {}\n'.format(self.name))
                        if self.sourcefile:
                            sys.stderr.write('Entry.post: Defined in file: {}\n'.format(self.sourcefile))
                        sys.stderr.write('Entry.post: The docfile was not found: {}\n'.format(self.docfile))
                    if fatal:
                        raise Exception('Entry.post: docfile not found.\n')
        return err
        
        
    def save(self, target, addimport=True, varname='entry'):
        """Save the bibliographic entry to a file capable of reconstructing it
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.save(ff, addimport=addimport, varname=varname)
        
        # Detect the class and module names
        thisclass = self.__class__.__name__
        thismodule = self.__class__.__module__
        
        args = {'e':varname, 'c':thisclass, 'm':thismodule, 'n':self.name}
        
        if addimport:
            target.write('import {m:s}\n\n'.format(**args))
        
        target.write(f'{varname} = {thismodule}.{thisclass}(\'{self.name}\')\n')
        
        handled = []
        for item,(allowedtypes,inputhandler,codehandler,outputhandler) in self.mandatory.items():
            if item in self.bib:
                if codehandler:
                    value = codehandler(self.bib[item])
                else:
                    value = self.bib[item]
                target.write(f'{varname}.{item} = {value}\n')
                handled.append(item)
        for item,(allowedtypes,inputhandler,codehandler,outputhandler) in self.optional.items():
            if item in self.bib:
                if codehandler:
                    value = codehandler(self.bib[item])
                else:
                    value = self.bib[item]
                target.write(f'{varname}.{item} = {value}\n')
                handled.append(item)
        allowedtypes, inputhandler, codehandler, outputhandler = self.default
        for item,value in self.bib.items():
            if item not in handled:
                if codehandler:
                    value = codehandler(value)
                target.write(f'{varname}.{item} = {value}\n')
            
        # finally, deal with the non-bibliographic meta data
        if self.docfile:
            target.write(f'{varname}.docfile = {self.docfile}\n')
        if self.collections and isinstance(self.collections,list):
            target.write(f'{varname}.collections = {self.collections!r}\n')
        if self.doc and isinstance(self.doc, str):
            target.write(f'{varname}.doc = """\n{self._splitlines(self.doc,74)}"""\n')
        target.write('\n')
                
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

    def show(self, doc=True, width=None, posix=False):
        """Returns a formatted string citation
"""
        first = True
        out = ''
        # Build the format string
        lookfor = ['author', 'title', 'publisher', 'journal', 'booktitle', 'howpublished', 'address', 'number', 'volume', 'pages', 'year']
        for item in lookfor:
            if item in self.bib:
                allowed, inputh, codeh, outputh = self.get_rules(item)
                if first:
                    first = False
                    if outputh:
                        out += outputh(self.bib[item])
                    else:
                        out += self.bib[item]
                else:
                    if outputh:
                        out += ', ' + outputh(self.bib[item])
                    else:
                        out += ', ' + self.bib[item]
                        
        if doc:
            out += '\n\n' + self.doc
            
        if width:
            return self._splitlines(out,width)
        return out

    def _splitlines(self, raw, width):
        """Split a string by whitespace and insert newlines as necessary to ensure each 
line is no longer than WIDTH characters long.
"""
        first = True
        out = ''
        raw_split = raw.split('\n\n')
        for paragraph in raw_split:
            # If this is the first paragraph
            if first:
                first = False
            else:
                out += '\n\n'
            # Construct the lines
            linelength = 0
            for word in paragraph.split():
                wordlength = len(word)
                # If this is the first word of the paragraph
                if linelength == 0:
                    linelength = wordlength
                    out += word
                else:
                    linelength += wordlength + 1
                    if linelength > width:
                        linelength = wordlength
                        out += '\n' + word
                    else:
                        out += ' ' + word
        # End with a single newline
        out += '\n'
        return out
                

###
# Entry definitions
###

class ArticleEntry(Entry):
    """Eikosi Article Entry
pba = ArticleEntry(name)
"""
    tag = '@ARTICLE'
    mandatory = {
        'author':((str,list,tuple,AuthorList), AuthorList, repr, str),
        'title': (str, None, repr, None),
        'journal': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'volume': ((str,int), int, repr, repr),
        'number': ((str,int), int, repr, repr),
        'page': (str, None, repr, None)}
        
    def show(self, doc=True, width=None, posix=False):
        out = ', "{title:s}," '
        if posix:
            out += '\033[3m{journal:s}\033[0m, '
            if 'volume' in self.bib:
                out += '\033[1m{volume:}\033[0m'
                if 'number' in self.bib:
                    out += '({number:}), '
                else:
                    out += ', '
            elif 'number' in self.bib:
                out += '\033[1m{number:}\033[0m, '
        else:
            out += '{journal:s}, '
            if 'volume' in self.bib:
                out += '{volume:}'
                if 'number' in self.bib:
                    out += '({number:}), '
                else:
                    out += ', '
            elif 'number' in self.bib:
                out += '{number:}, '

        if 'page' in self.bib:
            out += '{page:}, '
        out += '{year:}.'
        out = self.author.show() + out.format(**self.bib)
        if doc and self.doc:
            out += '\n' + self.doc
            
        if width:
            return self._splitlines(out,width)
        return out

class ReportEntry(Entry):
    """Eikosi Report Entry
pba = ReportEntry(name)
"""
    tag = '@TECHREPORT'
    mandatory = {
        'author':((str,list,tuple,AuthorList), AuthorList, repr, str),
        'title': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'number': (str, None, repr, None),
        'institution': (str, None, repr, None),
        'month': (str, None, repr, None),
        'day': ((str,int), int, repr, repr)}
        
    def show(self, doc=True, width=None, posix=False):
        out = ', "{title:s}," '
        if posix:
            out += '\033[3m{institution:s}\033[0m, '
        else:
            out += '{institution:s}, '

        months = ['?? ', 'Jan. ', 'Feb. ', 'Mar. ', 'Apr. ', 'May ', 'June ', 'July ', 'Aug. ', 'Sep. ', 'Nov. ', 'Dec. ']
        if 'day' in self.bib:
            out += '{day:d} '
        if 'month' in self.bib:
            out += months[self.bib['month']]
        out += '{year:d}.'

        out = self.author.show() + out.format(**self.bib)
        if doc and self.doc:
            out += '\n' + self.doc
        if width:
            return self._splitlines(out,width)
        return out
        
class ProceedingsEntry(Entry):
    """Eikosi Proceedings Entry
pba = ProceedingsEntry(name)
"""
    tag = '@INPROCEEDINGS'
    mandatory = {
        'author': ( (str,list,tuple,AuthorList), AuthorList, repr, str),
        'title': ( str, None, repr, None),
        'booktitle': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'volume': ((str,int), int, repr, repr),
        'number': ((str,int), int, repr, repr),
        'page': (str, None, repr, repr)}

    def show(self, doc=True, width=None, posix=False):
        out = ', "{title:s}," '
        if posix:
            out += '\033[3m{booktitle:s}\033[0m, '
            if 'volume' in self.bib:
                out += '\033[1m{volume:}\033[0m'
                if 'number' in self.bib:
                    out += '({number:}), '
                else:
                    out += ', '
            elif 'number' in self.bib:
                out += '\033[1m{number:}\033[0m, '
        else:
            out += '"{title:s}," {journal:s}, '
            if 'volume' in self.bib:
                out += '{volume:}'
                if 'number' in self.bib:
                    out += '({number:}), '
                else:
                    out += ', '
            elif 'number' in self.bib:
                out += '{number:}, '

        if 'address' in self.bib:
            out += '{address:}, '

        if 'page' in self.bib:
            out += '{page:}, '
        out += '{year:}.'
        
        out = self.author.show() + out.format(**self.bib)
        if doc and self.doc:
            out += '\n' + self.doc

        if width:
            return self._splitlines(out,width)
        return out
        

class PatentEntry(Entry):
    """Eikosi Proceedings Entry
pba = PatentEntry(name)
"""
    tag = '@MISC'
    mandatory = {
        'author': ((str,list,tuple,AuthorList), AuthorList, repr, str),
        'title': (str, None, repr, None),
        'number': (str, None, repr, None),
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
            target.write(f'    author = {{{str(self.author)}}},\n')
        if 'title' in self.bib:
            target.write(f'    title = {{{self.title}}},\n')
        if 'assignee' in self.bib:
            target.write(f'    note = {{{self.assignee:}}},\n')
        if 'number' in self.bib:
            if 'nationality' in self.bib:
                target.write(f'    howpublished = {{{self.nationality} Pat. N. {self.number}}},\n')
            else:
                target.write(f'    howpublished = {{Pat. N. {self.number:d}}},\n')
        if 'year' in self.bib:
            target.write(f'    year = {{{self.year}}},\n')
        
        handled = ['author', 'title', 'assignee', 'number', 'year', 'nationality']
        for item,value in self.bib.items():
            if item not in handled:
                target.write(f'    {item} = {{{value}}},\n')
        target.write('}\n\n')
        
    def show(self, doc=True, width=None, posix=False):
        out = ', "{title:s}," '
        if 'nationality' in self.bib:
            out += '{nationality:s} '
        out += 'Patent {number:}, ' 
        if 'assignee' in self.bib:
            out += 'asgn. {assignee:s}, '
        out += '{year:}.'
        
        out = self.author.show() + out.format(**self.bib)
        if doc and self.doc:
            out += '\n' + self.doc

        if width:
            return self._splitlines(out,width)
        return out
        
        
class BookEntry(Entry):
    tag = '@BOOK'
    mandatory = {
        'author': ((str,list,tuple,AuthorList), AuthorList, repr, str),
        'title': (str, None, repr, None),
        'publisher': (str, None, repr, None),
        'year': ((int,str), int, repr, repr)}
    optional = {
        'address': (str, None, repr, None),
        'edition': (str, None, repr, None)}
        
    def show(self, doc=True, width=None, posix=False):
        out = ', "{title:s}," '
        if 'edition' in self.bib:
            out += '{edition:s}, '
        out += '{publisher:s}, '
        if 'address' in self.bib:
            out += '{address:s}, '
        out += '{year:}.'
        
        out = self.author.show() + out.format(**self.bib)
        if doc and self.doc:
            out += '\n' + self.doc

        if width:
            return self._splitlines(out,width)
        return out
        
class WebsiteEntry(Entry):
    tag = '@MISC'
    mandatory = {
        'url': (str, None, repr, None)}
    optional = {
        'title': (str, None, repr, None),
        'author': ((str, list, tuple, AuthorList), AuthorList, repr, str),
        'institution': (str, None, repr, None),
        'accessed': (str, None, repr, None)}

    def show(self, doc=True, width=None, posix=False):
        
        out = ''
        if 'title' in self.bib:
            out += '{title:s}, '
            
        if posix:
            out = '\033[4m{url:s}\044[0m'
        else:
            out = '{url:s}'
            
        if 'institution' in self.bib:
            out += ', {institution:s}'
        if 'accessed' in self.bib:
            out += ', [Accessed {accessed:s}]'
        out += '.'
        out = out.format(**self.bib)
        if 'author' in self.bib:
            out = author.show() + ', ' + out
        if doc and self.doc:
            out += '\n' + self.doc

        if width:
            return self._splitlines(out,width)
        return out
        
            
class MiscEntry(Entry):
    tag = '@MISC'

    def show(self, doc=True, width=None, posix=False):
        return 'MiscEntry(' + self.name + ')'


#####
# Collection and collection-related classes
#####

class CollectionIterator:
    def __init__(self, target, depthfirst = False, inclusive=True):
        self.target = target
        self.schedule = []
        if depthfirst:
            self._depth_first(target)
            if not inclusive:
                del self.schedule[-1]
        else:
            target._iflag = True
            if inclusive:
                self.schedule.append(target)
            self._depth_last(target)
        count = target._set_iflag(False)
        if count != len(self.schedule):
            raise Exception('CollectionIterator: There was an irregularity in the _iflag state of the collections.\n')
            
    def __iter__(self):
        return self
        
    def _depth_last(self, target):
        """Accumulate children in a depth-last ordered list"""
        for child in target.children.values():
            if not child._iflag:
                child._iflag = True
                self.schedule.append(child)
        for child in target.children.values():
            self._depth_last(child)
                
    def _depth_first(self, target):
        """Accumulate children in a depth-first ordered list"""
        if not target._iflag:
            target._iflag = True
            for child in target.children.values():
                self._depth_first(child)
            self.schedule.append(target)
        
    def __next__(self):
        if self.schedule:
            return self.schedule.pop(0)
        raise StopIteration


####
# Collection classes
####

class ProtoCollection:
    """Eikosi Prototype Collection
    c = Collection(name)
        OR
    c = Collection(collection_instance)

Collections can be created using two methods: with a string name that will be
used to identify the collection later, or as a copy of another collection.

There are three Collection classes that are derived from the ProtoCollection 
template: MasterCollection, Collection, and SubCollection.  A collection of
any type has a dictionary, entries, which contains member Entry objects indexed
by their names, and a dictionary, children, of collections indexed by their 
names.  

MasterCollections are not intended to be defined in scripts or by users; they 
are only returned by the load() and loadbib() functions.  loadbib() populates 
the MasterCollection with the entries in BibTeX files.  load() executes Python
files, and all Entry or Collection instances are added to the MasterCollection
that is returned.  All MasterCollection and SubCollection objects are ignored.  
There are other differences that are covered in the individual class 
documentation.

Collection instances are generic collections with entries and children 
dictionaries as well.  They are recognized and when building a MasterCollection,
so they appear at the top of a system of collections.  A Collection instance
may not be added to another Collection instance using the addchild() method.
Instead, only SubCollections may be added in this way.

SubCollection instances are identical to Collection instances, except they are 
not loaded into MasterCollections. SubCollections are intended to be children
of Collections and other SubCollections.  This permits trees of Collection 
objects, and loops in the tree are permitted.

"""
    def __init__(self, name):
        self.name = ''
        self.doc = ''
        self.entries = {}
        self.children = {}
        self._iflag = False

        if isinstance(name, ProtoCollection):
            self.name = name.name
            self.doc = str(name.doc)
            self.entries.update(name.entries)
            self.children.update(name.children)
        elif isinstance(name,str):
            self.name = name
        else:
            raise TypeError('Collection.__init__: The collection name must be a string.\n')
        
    def __iter__(self):
        for c in CollectionIterator(self, depthfirst=False):
            for entry in c.entries.values():
                yield entry
        
    def _set_iflag(self, value):
        count = 0
        if self._iflag != value:
            count += 1
            self._iflag = value
            for child in self.children.values():
                count += child._set_iflag(value)
        return count
        
    def flatten(self):
        """Pull in entries from all children and remove all children.
    c.flatten()
    
After running flatten, the collection will no longer have child SubCollections, 
but all of their entries will have been added to this Collection.
"""
        for c in self.collections():
            if c is not self:
                self.entries.update(c.entries)
        self.children = {}
            
        
    def update(self, source):
        """Read data from the source into this collection
    c.update(c2)
    
Similar to a dictionary's update method, this reads data from the argument
Collection into this Collection.  Only the collections and entries dicts are
affected.
"""
        if not isinstance(source, ProtoCollection):
            raise TypeError('Collection.update: requires a Collection type.')
        c.entries.update(source.entries)
        c.children.update(source.children)
        
    def copy(self):
        """Return a copy of the collection
    c2 = c.copy()
    
This is equivalent to
    c2 = c.__class__(c)
    
To change the type of collection, use the respective class initializer instead.
    c2 = Collection(c)
    c2 = SubCollection(c)
    c2 = MasterCollection(c)
"""
        return self.__class__(self) 

        
    def collections(self, depthfirst=False, rself=True):
        """Return an iterator over this and all child collections
    for this_collection in c.collections():
        ...

This iterates over all unique Collections and SubCollections that are 
descendants of this Collection.  The behavior of collections() is adjustable
using optional keywords:

depthfirst (False)
Return collections at the bottom of the tree first?

rself (True)
Include self in the iteration?
"""
        return CollectionIterator(self, depthfirst=depthfirst, inclusive=rself)
        
    def addchild(self, cnew):
        """Add a new subcollection to this collection
    this_collection.addchild(new_collection)
    
Only SubCollection instances may be added to Collections of any kind using the
addcollection() method.  Collection names must be unique; any child of the same
name will cause an Exception.
"""
        if not isinstance(cnew, ek.SubCollection):
            raise TypeError('Colleciton.addcollection: All child collections must be SubCollection instances.\n') 
        elif self.haschild(cnew):
            raise Exception('Colleciton.addcollection: In collection, "{}", there is already a child with name, "{}".'.format(self.name, cnew.name))
        self.children[cnew.name] = cnew
        
    def haschild(self, ctest):
        """Test whether a collection or collection name is a child of the collection.
    TF = this_collection.haschild(test_collection)
        OR
    TF = this_collection.haschild(collection_name)
    
The ischild() method accepts either a string or a collection object.  If the 
argument is a string, then all child collection names are compared, and True
is returned if one matches.  False is returned otherwise.

If the argument is one of the Collection classes, the children are compared by
their id() values instead (using the method: collection1 is collection2)
"""
        if isinstance(ctest,str):
            for this in CollectionIterator(self, depthfirst=False):
                if this.name == cname:
                    return True
        elif isinstance(ctest,ProtoCollection):
            for this in CollectionIterator(self, depthfirst=False):
                if this is ctest:
                    return True
        else:
            raise TypeError('Collection.haschild: argument must be a string or collection. Found: ' + repr(type(ctest)))
        return False
        
        
    def getchild(self, cname):
        """Retrieve a SubCollection that belongs to this collection.
    c = this_collection.getchild(collection_name)
    
This retrieve operation will succeed if the collection is a member of this or 
any of the sub-collections.  If the name is not found as a child of the evoking
collection, then a KeyError is raised.
"""
        for this in CollectionIterator(self, depthfirst=False):
            if this.name == cname:
                return this
        raise KeyError(entryname)
        
        
    def add(self, enew):
        """Add an entry to this collection
    c.add(entry)
    
This method should only be used on entries already in the MasterCollection
containing this Collection or SubCollection.  If entries are added that do not
belong ot the MasterCollection, opeations at the master level will not find it.
"""
        if isinstance(enew, Entry):
            if enew.name in self.entries:
                raise Exception('Collection.add: Entry is already a member.\n')
            self.entries[enew.name] = enew
        else:
            raise TypeError('Collection.add: Unable to add a member of type: ' + repr(type(newentry)))


    def get(self, entryname):
        """Retrieve an entry by its name
    entry = c.get(entryname)
    
Returns the entry if it is a member of the collection or any of its sub-
collections.
"""
        for this in CollectionIterator(self, depthfirst=False):
            try:
                return this.entries[entryname]
            except KeyError:
                pass
            except:
                raise sys.exc_info()[1]
        raise KeyError(entryname)


    def has(self, entryname):
        """Test whether the entry belongs to this collection or its children
    TF = c.has(entryname)
        OR
    TF = c.has(entry_instance)
"""
        if isinstance(entryname, Entry):
            for this in CollectionIterator(self, depthfirst=False):
                if entryname in this.entries.values():
                    return True
        elif isinstance(entryname, str):
            for this in CollectionIterator(self, depthfirst=False):
                if entryname in this.entries:
                    return True
        else:
            raise TypeError('Collection.has: The argument must be a string or an Entry type.\n')
        return False

    def save(self, target, addimport=True, varname='c'):
        """Save the collection to an executable python file that is capable of re-defining it
    c.save('/path/to/file.eks')
"""
        if isinstance(target,str):
            if not target.endswith(EXT):
                target += EXT
            with open(target,'w') as ff:
                return self.save(ff, addimport=addimport, varname=varname)
        elif not hasattr(target,'write'):
            raise TypeError('Collection.save: Arguments must be either a file descriptor or a path to a file.\n')
        
        # Detect the class and module names
        thisclass = self.__class__.__name__
        thismodule = self.__class__.__module__
        args = {'c':thisclass, 'm':thismodule, 'n':self.name, 'v':varname}
        
        if addimport:
            target.write('import {m:s}\n\n'.format(**args))
        target.write('{v:s} = {m:s}.{c:s}(\'{n:s}\')\n'.format(**args))

    def savebib(self, target):
        """Export the members of this collection to a BibTeX file
    c.savebib('/path/to/file.bib')
        OR
    c.savebib(file_descriptor)
"""
        if isinstance(target,str):
            with open(target,'w') as ff:
                return self.savebib(ff)
        elif hasattr(target, 'write'):
            for entry in self:
                entry.savebib(target)
        else:
            raise TypeError('Collection.savebib: The argument must be either a path or a file descriptor.')
            

class Collection(ProtoCollection):
    """Collection
    c = Collection('collection:name')
    
A Collection is a group of entries and SubCollections.  These are used to 
organize bibliographic entries.  When a bibliographic record is loaded, all
Collections will automatically be added to the MasterCollection.

SubCollections are just like Collections, but they are ignored by the 
MasterCollection at load time.  They must be a child of a Collection (see the
addchild() method), or they will not be loaded.

For details on interacting with Collections, see the in-line help for their
methods:
    add         Add an Entry instance to the Collection
    get         Get an Entry instance from the Collection
    has         Test whether an Entry is in the Collection
    addchild    Add a SubCollection instance to the Collection
    getchild    Get a SubCollection instance from the Collection
    haschild    Test whether a SubCollection is in the Collection

It is also possible to iterate over collection and its children
>>> for thiscollection in mycollection:
...     print(thiscollection.name)

This will loop over all SubCollections (including the parent, mycollection) in
a depth-last order.  Using the CollectionIterator class, it is possible to 
specify a depth-first approach instead.
"""
    pass

class SubCollection(ProtoCollection):

    pass

class MasterCollection(ProtoCollection):
    """MASTERCOLLECTION
    mc = MasterCollection(name)

The MasterCollection class is a special type of collection that supports loading
and saving of entire directories of Eikosi and BibTeX data files.    

The master collection class is similar to a collection, but with some important
differences.  The MasterCollection is assumed only to be created by load 
operations.  When Collections and SubCollections process a get() request, they
are required to check all of their children as well, but MasterCollections 
assume that their entries[] dict has a comprehensive list of all entries loaded,
and do not recurse into their child collections.

This means that Entry operations like get() and has() are faster on 
MasterCollections, but it also means that any additions to child collections 
after load will not be detected.
"""

    def __iter__(self):
        return self.entries.values().__iter__()

    def get(self, entryname):
        return self.entries[entryname]
        
    def has(self, entryname):
        if isinstance(entryname, str):
            return entryname in self.entries
        elif isinstance(entryname, Entry):
            return entryname in self.entries.values()
        raise TypeError('MasterCollection.has: The argument must be a string or an Entry type.\n')

    def load(self, target, verbose=False, recurse=False, relax=False, _top=True):
        """Load Entries and Collections into the MasterCollection
    mc.load('/path/to/file.eks')
        OR
    mc.load('/path/to/dir')
        OR
    mc.load(file_descriptor)
    
Optional keywords change the load behavior:
verbose (False)
Operate verbosely

recurse (False)
If the target is the path to a directory, this option will prompt the load() 
method to also look at sub-directories.

relax (False)
Load entries and collections in a relaxed mode, so unrecongized entries do not
cause the process to halt with an exception.
"""
        if isinstance(target,str):
            # If the target is a directory, scan it for .eke files
            if os.path.isdir(target):
                target = os.path.abspath(target)
                contents = os.listdir(target)
                for this in contents:
                    newtarget = os.path.join(target, this)
                    isdir = os.path.isdir(newtarget)
                    if this.endswith(EXT) or (recurse and isdir):
                        if verbose and isdir:
                            sys.stdout.write(f'MasterCollection.load: Recursing into dir: {newtarget}\n')
                        self.load(newtarget, verbose=verbose, recurse=recurse, relax=relax, _top=False)
            # If the target is a filename, load it
            elif os.path.isfile(target):
                with open(target,'r') as ff:
                    self.load(ff, verbose=verbose, relax=relax, _top=False)
            else:
                raise Exception(f'MasterCollection.load: No file or directory named: {target}\n')

        elif hasattr(target,'read'):
            # What was the name of the source file?
            sourcefile = os.path.abspath(target.name)
            # Initialize a local name space; we'll search it for Entries or Collections
            namespace = {}
            if verbose:
                sys.stdout.write('MasterCollection.load: Executing file: ' + sourcefile + '\n')
            try:
                exec(target.read(), None, namespace)
            except:
                sys.stderr.write('\nMasterCollection.load: Error while executing file: ' + sourcefile + '\n\n')
                raise sys.exc_info()[1]
            # Loop over the variables declared while executing the file
            nfound = True
            for name, value in namespace.items():
                if issubclass(type(value), Entry):
                    nfound = False
                    if verbose:
                        sys.stdout.write('    --> Found entry: ' + value.name + '\n')
                    value.sourcefile = sourcefile
                    value.post(fatal=(not relax), verbose=relax)
                    self.entries[value.name] = value
                elif isinstance(value, Collection):
                    nfound = False
                    if not isinstance(value, Collection):
                        raise Exception('MasterCollection.load: Only Collections may be defined in files. Found: {}\n'.format(repr(type(entry))))
                    if verbose:
                        sys.stdout.write('    --> Found collection: ' + value.name + '\n')
                    self.children[value.name] = value
        else:
            raise TypeError('MasterCollection.load: Requires a string path or a file type.')
        
        # Unless this is a recursion call, it's time to check the entries for 
        # membership in collections
        if _top:
            if verbose:
                sys.stdout('MasterCollection.load: Linking entries to their collections.\n')
            for entry in self:
                if not isinstance(entry.collections, list):
                    sys.stderr.write(f'MasterCollection.load: Illegal collections list for entry: {entry.name}\n')
                    if entry.docfile:
                        sys.stderr.write(f'MasterCollection.load: Defined in file: {entry.docfile}\n')
                elif entry.collections:
                    for ii,cname in enumerate(entry.collections):
                        if isinstance(cname,str):
                            try:
                                c = self.getchild(cname)
                                c.add(entry)
                                entry.collections[ii] = c
                            except:
                                sys.stderr.write(f'MasterCollection.load: Error linking entry to its collection: {entry.name}\n' + \
                                        f'MasterCollection.load: Failed to find collection: {cname}\n')
                                if entry.docfile:
                                    sys.stderr.write(f'MasterCollectionload: Entry defined in file: {entry.docfile}\n')
                

    def save(self, target, directory=False, verbose=True, overwrite=True):
        """SAVE
    c.save('/path/to/dir', directory=True)
        OR
    c.save('/path/to/file.eks')
        OR
    c.save(file_descriptor)
    
Save the collection's members to python file(s) that can be re-loaded by a 
colleciton later.  The save algorithm works in two modes controlled by the
'directory' keyword value:

** Single File **
    c.save('/path/to/file')
        OR
    c.save(file_descriptor)

By default, save() treats the argument as a file descriptor or a path to a file.
If the path to the file does not end in the .eks extension, it will be appended.
Note that if an incorrect extension is supplied, it will not be removed.  

In this mode of operation, all entries and collections are written to a single 
file.

** Directory Mode **
    c.save('/path/to/dir', directory=True)

When the directory keyword is set to True, each entry is saved as a separate 
file, and the argument must be a string path to an existing directory.  
Collections are still saved in a single file called 'collections.eks'
"""
        if directory:
            if not isinstance(target, str) and not os.path.isdir(target):
                raise Exception('MasterCollection.save: In directory mode, the argument must be a path to an existing directory.\n')
            target = os.path.abspath(target)
            
            # First, purge all existing eks files
            if verbose:
                sys.stdout.write('MasterCollection.save: Removing files...\n')
            for filename in os.listdir(target):
                if filename.endswith(EXT):
                    fullfilename = os.path.join(target,filename)
                    if verbose:
                        sys.stdout.write('    ' + fullfilename + '\n')
                    os.remove(fullfilename)
            
            if verbose:
                sys.stdout.write('MasterCollection.save: Saving entries...\n')
            # Iterate over all the entries
            for entry in self:
                # Build a file name from the entry name
                # Strip out all but alpha numeric and _ - characters
                filename = ''
                for char in entry.name:
                    if char.isalnum() or char in '_-':
                        filename += char
                # Make sure the name hasn't already been created
                fullfilename = os.path.join(target,filename + EXT)
                for count in range(1,101): 
                    if not os.path.exists(fullfilename):
                        break
                    fullfilename = os.path.join(target, filename + '_' + str(count) + EXT)
                if count == 100:
                    raise Exception('MasterCollection.save: Failed to find a unique file name in 100 attempts with entry: {}'.format(entry.name))
                # Save the entry
                if verbose:
                    sys.stdout.write(entry.name + ' --> ' + fullfilename + '\n')
                entry.save(fullfilename)

            # Move on to the collections
            # First, come up with a safe filename
            filename = 'collections'
            # Make sure the name hasn't already been created
            fullfilename = os.path.join(target,filename + EXT)
            for count in range(1,101): 
                if not os.path.exists(fullfilename):
                    break
                fullfilename = os.path.join(target, filename + '_' + str(count) + EXT)
            if count == 100:
                raise Exception('MasterCollection.save: Failed to find a unique file name in 100 attempts with entry: {}'.format(entry.name))
            
            # Save the collections
            if verbose:
                sys.stdout.write('Saving collecitons to: ' + fullfilename + '\n')
            first = True    # Write the import statement on the first collection only
            crecord = {}    # keep track of the varaible names assigned
            with open(fullfilename,'w') as ff:
                for ii,c in enumerate(self.collections()):
                    # Disallow re-calling a master collection save algorithm
                    if not isinstance(c, MasterCollection):
                        v = 'c{:03d}'.format(ii)
                        crecord[v] = c
                        c.save(ff, addimport=first, varname = v)
                        first = False
                    
                # Link the collections
                for v,c in crecord.items():
                    # Loop over this collection's sub-collections
                    # This is horribly inefficient, but it will only be an issue
                    # if the user creates LOTS of collections
                    for sv,sc in crecord.items():
                        if sc.name in c.children:
                            ff.write('{v:s}.addchild({sv:s})\n'.format(v=v,sv=sv))
                        
        # Single-file mode with a string input
        elif isinstance(target, str):
            # Check for an overwrite error
            if not overwrite and os.path.isfile(target):
                raise Exception('MasterCollection.save: File exists. Rename or set the overwrite keyword to True: ' + target)
            if not target.endswith(EXT):
                target += EXT
            # Get started...
            target = os.path.abspath(target)
            if verbose:
                sys.stdout.write('MasterColleciton.save: Opening file: ' + target + '\n')
            with open(target, 'w') as ff:
                self.save(ff, directory=False, verbose=verbose, overwrite=overwrite)
        # Single file mode with an open file descriptor
        elif hasattr(target,'write'):
            first = True
            for ii,entry in enumerate(self):
                entry.save(target, addimport=first, varname='e{:03d}'.format(ii))
                first = False
            
            # Write the collections
            # Keep a record of all the variable names used
            crecord = {}
            for ii,c in enumerate(self.collections()):
                if not isinstance(c, MasterCollection):
                    v = 'c{:03d}'.format(ii)
                    crecord[v] = c
                    c.save(target, addimport=False, varname=v)
                
            # Link the collections
            for v,c in crecord.items():
                # Loop over this collection's sub-collections
                # This is horribly inefficient, but it will only be an issue
                # if the user creates LOTS of collections
                for sv,sc in crecord.items():
                    if sc.name in c.children:
                        target.write('{v:s}.addchild({sv:s})\n'.format(v=v,sv=sv))

        else:
            raise TypeError('MasterCollection.save: The target must be a string path or a file descriptor. Received: ' + str(type(target)))

####
# Utility functions
####


def load(target):
    """Load Entries and Collections into a MasterCollection
    mc = load('/path/to/file.eks')
        OR
    mc = load('/path/to/dir')
        OR
    mc = load(file_descriptor)
    
Optional keywords change the load behavior:
verbose (False)
Operate verbosely

recurse (False)
If the target is the path to a directory, this option will prompt the load() 
method to also look at sub-directories.

relax (False)
Load entries and collections in a relaxed mode, so unrecongized entries do not
cause the process to halt with an exception.
"""
    mc = MasterCollection('main')
    mc.load(target)
    return mc



def loadbib(target, verbose=False):
    """LOADBIB
    c = loadbib('/path/to/file.bib')
    
Returns a collection containing entries loaded from the bib file.  This bibtex
parser respects the rules described on the BibTeX site:
    http://www.bibtex.org/Format/
    
The loadbib funciton accepts a single optional keyword argument, verbose.  When 
True, the funciton prints its findings to stdout.
"""

    if isinstance(target,str):
        if verbose:
            sys.stdout.write('load: opening file: ' + target + '\n')
        with open(target,'r') as ff:
            return loadbib(ff, verbose=verbose)

    output = MasterCollection('loadbib')
    output.doc = 'Created by eikosi.loadbib()'

    # Recognized types
    entrytypes = {
        '@ARTICLE': ArticleEntry,
        '@INPROCEEDINGS': ProceedingsEntry,
        '@TECHREPORT': ReportEntry,
        '@BOOK': BookEntry,
        '@MISC': MiscEntry,
    }

    # Special characters 
    special = '"{},@#='

    # create some state variables
    # The reading state indicates how the stream of characters should be 
    # interpreted.  What are we reading in?
    # state=0       Consume whitespace while looking for a type
    #       Increment the state on a @ character.  Raise an error for any other
    #       non-whitespace character.
    #       Exit gracefully on EOF
    # state=1       Read in the entry type
    #       Read in alpha characters
    #       On { increment two states (skip state 2)
    #       On whitespace, increment the state
    #       Raise an error on non-alpha characters or EOF
    # state=2       Consume whitespace looking for the leading { of an entry.
    #       On { increment the state.
    #       Raise an error on any other non-whitespace character or EOF
    # state=3       Consume whitespace looking for the entry name
    #       Increment the state on any non-whitespace character
    #       raise an error on EOF or special
    # state=4       Read the entry name
    #       Increment the state on ,
    #       Complete the entry and revert to state=0 on }
    #       Warn on whitespace: ignore whitespace
    #       Raise an error on special
    # state=5       Consume whitespace while looking for an item name
    #       Increment the state on alpha
    #       Complete the entry and revert to state=0 on }
    #       Raise an error on EOF or non-alpha or non-whitespace
    # state=6       Read in an item name
    #       Read in alpha characters
    #       Increment the state by 2 on = (skip state 7)
    #       Increment the state on whitespace
    #       Raise an error on non-alpha
    # state=7       Consume whitespace searching for =
    #
    # state=8       Consume whitespace searching for item data
    #
    # state=9       Read item data
    #       Strip off outer {} or ""
    #       Raise an error on unescaped special characters
    #       Increment the state on unescaped whitespace or closing {} ""
    #       Return to state 0 if } reduces to 0 bracket count
    # state=10      Post item data
    #       Consume whitespace
    #       Return to state=8 on # (string concatenation)
    #       Return to state=5 on ,
    #       Return to state=0 on }
    #       Raise an error on any other non-whitespace character
    # state=11      Comments
    #       Consume all text while counting brackets pop back to state 0 when
    #       brackets are closed.
    
    state = 0       # The state index
    activetype = ''
    activename = ''
    activeitem = ''
    activedata = ''
    word = ''
    endofentry = False  # Flag that the data are ready to be processed
    endofitem = False   # Flag that an item is ready to be processed
    endofword = False   # Flag that a word is ready to be processed
    comment = False
    string = {}
    bib = {}
    bracket = 0     # Bracket pair depth
    quote = False   # Quote pair active?
    line = 1
    col = 1

    data = target.read()
    for char in data:
        
        ## Really handy for debugging...
        # print(state, char)
        
        # Detect the beginning of a comment
        if not quote and not bracket and char=='%':
            comment = True
        # Case out the state conditions
        # If we're in a comment, bypass all state handling
        if comment:
            if char == '\n':
                comment = False
        # STATE 0: Burn whitespace looking for an entry
        elif state == 0:
            if bib or activename or activetype or activeitem:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected ineternal error. Failed to re-initialize the state memory after the last entry.'.format(line, col))
            if char.isspace():
                pass
            elif char == '@':
                activetype = char
                state += 1
            else:
                raise Exception('loadbib: On line {:d} col {:d}, expected @ starting a new entry.'.format(line, col))
        # STATE 1: New entry... Read in the entry type
        elif state == 1:
            if char.isalpha():
                activetype += char.upper()
            elif char.isspace():
                state += 1
            elif char == '{':
                if activetype == '@STRING':
                    # Skip looking for the entry name
                    state = 5
                elif activetype == '@COMMENT':
                    # Special rules for reading in comments
                    state = 11
                else:
                    state += 2
                bracket = 1
            else:
                raise Exception('loadbib: On line {:d} unexpected character while reading the entry type: {}'.format(line, col, char))
        # STATE 2: Burn whitespace while looking for the { opening the entry
        elif state == 2:
            if char.isspace():
                pass
            elif char == '{':
                if activetype == '@STRING':
                    # Skip looking for the entry name
                    state = 5
                elif activetype == '@COMMENT':
                    # Special rules for reading in comments
                    state = 11
                else:
                    state += 1
                bracket=1
            else:
                raise Exception('loadbib: On line {:d} expected \{ to start the entry but found character: {}'.format(line, col,char))
        # STATE 3: Burn whitespace looking for the entry name
        elif state == 3:
            if activename:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected internal error.  Failed to initialize the activename state.'.format(line, col))
            if char.isspace():
                pass
            elif char in special:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected character in entry name: {}\n'.format(line, col,char))
            else:
                activename = char
                state += 1
        # STATE 4: Read in the entry name
        elif state == 4:
            if char == '}':
                bracket = 0                    
                endofentry = True
            elif char == ',':
                state += 1
            elif char.isspace():
                sys.stderr.write('loadbib: On line {:d} col {:d}, ignoring unexpected whitespace in entry name.\n'.format(line, col))
            elif char in special:
                raise Exception('loadbib: On line {:d} col {:d}, illegal special character in the entry name.\n'.format(line, col))
            else:
                activename += char
            
        # STATE 5: Burn whitespace looking for an item name
        elif state == 5:
            if activeitem:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected internal error.  Failed to initialize the activeitem state.'.format(line, col))
            if char.isspace():
                pass
            elif char == '}':
                bracket = 0
                endofentry = True
            elif char.isalpha():
                state += 1
                activeitem = char
            elif char in special:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected character, {}, while parsing entry: {}\n'.format(line, col,char, activename))
        # STATE 6: Read in the item name
        elif state == 6:
            if quote or bracket != 1:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected internal error; failure to close quotes or brackets.'.format(line, col))
            if char == '=':
                activedata = ''
                word = ''
                state += 2
            elif char.isalpha():
                activeitem += char
            elif char.isspace():
                state += 1
            else:
                raise Exception('loadbib: On line {:d} col {:d}, illegal character in item name.\n'.format(line, col))
        # STATE 7: Burn whitespace looking for =
        elif state == 7:
            if char == '=':
                activedata = ''
                word = ''
                state += 1
            elif char.isspace():
                pass
            else:
                raise Exception('loadbib: On line {:d} col {:d}, expected =, but found: {}.\n'.format(line, col, char))
        # STATE 8: Burn whitespace looking for item data
        elif state == 8:
            if bracket != 1:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected error. Bracket count is not 1!\n'.format(line, col))
            # Do not record leading { or "
            if char == '{':
                bracket += 1
                state += 1
            elif char == '"':
                quote = True
                state += 1
            elif char == ',':
                activedata = ''
                endofitem = True
            elif char.isspace():
                pass
            elif char in special:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected special character: {}.'.format(line,col,char))
            else:
                word = char
                state += 1
        # Read in item data
        elif state == 9:
            if char == '{':
                bracket += 1
                word += char
            elif char == '}':
                # Treat brackets inside of quotes as regular characters
                if quote:
                    word += char
                else:
                    bracket -= 1
                    if bracket == 1:
                        state += 1 # Do not record trailing brackets.
                        activedata += word
                    else:
                        word += char
            elif char == '"':
                # Inside of brackets, regard quotes like any other character
                if bracket > 1:
                    word += char
                # Do not record trailing quotes
                elif quote:
                    quote = False
                    state += 1
                    activedata += word
                else:
                    raise Exception('loadbib: On line {:d} col {:d}, illegal start of quote in the middle of item data.'.format(line, col))
            elif char == ',':
                if quote or bracket>1:
                    word += char
                elif word in string:
                    activedata += string[word]
                    endofitem = True
                else:
                    activedata += word
                    endofitem = True
            elif char.isspace():
                # A space in quotes or brackets is just another character
                if quote or bracket>1:
                    word += char
                # Otherwise, it's the end of a word; look it up?
                elif word in string:
                    activedata += string[word]
                    state += 1
                # Ok, this is just the end of a word.
                else:
                    activedata += word
                    state += 1
            else:
                word += char
                
        # Read trailing whitespace unitl , or #
        elif state == 10:
            if quote or bracket != 1:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected internal error; failure to close quotes or brackets.'.format(line, col))
            if char == ',':
                endofitem = True
            elif char == '}':
                bracket = 0
                endofitem = True
                endofentry = True
            elif char == '#':
                word = ''
                state = 8
            elif char.isspace():
                pass
            else:
                raise Exception('loadbib: On line {:d} col {:d}, unexpected character parsing entry {}, item {}. Missing quote, bracket or comma?'.format(line, col, activename, activeitem))
        # Reading in a comment.  Keep reading until bracket == 0
        elif state == 11:
            if char == '{':
                bracket += 1
            elif char == '}':
                bracket -= 1
                if bracket == 0:
                    endofentry = True
        
        if endofitem:
            if activeitem in bib:
                sys.stderr.write('loadbib: Redundant entry for item {} in entry {}.  Overwriting.\n'.format(activeitem, activename))
            if quote or bracket > 1:
                raise Exception('loadbib: Unexpected error in entry {}. Unclosed quote or bracket?\n'.format(activename))
            elif activetype == '@STRING':
                string[activeitem] = activedata
            elif activetype not in entrytypes:
                raise Exception('loadbib: Unrecognized entry type {} in entry {}.'.format(activetype, activename))
            else:
                et = entrytypes[activetype]
                allowed,inputhandler,codehandler,outputhandler = et.get_rules(et,activeitem)
                if not isinstance(activedata,allowed):
                    raise Exception('loadbib: On line {:d}, illegal data type for item {} in entry type {}.'.format(line,activeitem,activetype))
                bib[activeitem] = activedata
                
            # Reset the item state
            activeitem = ''
            activedata = ''
            word = ''
            endofitem = False
            state = 5
            
        # If the entry is complete
        # Process all of the items one-by-one
        if endofentry:
            if activetype == '@STRING':
                pass
            elif activetype == '@COMMENT':
                pass
            # If this is a recognized entry type
            elif activetype in entrytypes:
                # Create the entry instance
                newentry = entrytypes[activetype](activename)
                newentry.bib = bib
                newentry.post()
                output.add(newentry)
            else:
                raise Exception('loadbib: Unrecognized entry type: {}.'.format(activetype))
            # Reset the entry state
            state = 0
            bracket = 0
            quote = 0
            bib = {}
            activename = ''
            activetype = ''
            activeitem = ''
            activedata = ''
            word = ''
            endofentry = False
            endofitem = False
            
        # Keep track of the line and column number
        col += 1
        if char == '\n':
            line += 1
            col = 1
    
    if bracket != 0 or state!=0:
        sys.stderr.write('loadbib: Reached end-of-file while still parsing:\n')
        sys.stderr.write('         type: {}\n  entry name: {}\n        item: {}\n\n'.format(activetype, activename, activeitem))
        sys.stderr.write('         Check for an unclosed bracket or quote?\n\n')
        raise Exception('loadbib: Unexpected end-of-file.\n')
        
    return output
