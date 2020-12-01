#!/usr/bin/python3
"""The Eikosi module provides classes and data for managing searchable 
collections of bibliographic entries.  The idea behind Eikosi is that 
contemporary scientific communication is performed through papers 
transmitted as pdfs, or data downloaded through repositories; it would 
be nice if one could enter bibliographic data, notes, categorize, and 
cross-link references from a single text file.

While there are many ways that users can implement Eikosi, the intended 
use is for an .eks file to be created alongside each downloaded pdf or 
in each repository being tracked.  An .eks file is just a snipet of 
Python code that records all of the relevant bibliographic data, notes, 
and that organizes bibliographic entries into collections so they can be
conveniently called up later.

For example, these might be the contents of an .eks file:
    import eikosi as ek
    
    entry = ek.ArticleEntry('example:1')
    
    entry.author = 'Mysef {at Large}'
    entry.title = 'An example to demonstrate how entries are defined'
    entry.journal = 'Home Grown Code'
    entry.volume = 15
    entry.number = 1
    entry.year = 2020

There is no need to assemble all of the bibliographic entries in one 
file.  Your library can grow or shrink or merge or... whatever, as long 
as you keep moving around your .eks files along with your pdfs.

The module supplies two functions that are used to load in data:
load()          Read in a repository of Eikosi collections and entries
loadbib()       Construct an Eikosi collection from a BibTeX file

Both of these return a MasterCollection instance, populated with the 
data they read in from their respective sources.  The load() funciton is 
intended to be the primary method for loading data into scripts or the 
command ine.  The laod() function can read in entire directories or 
single files.  For detailed information, see the load() documentation. 

*** ENTRIES ***

The bibliographic data are contained in individual Entry instances.  
Each type of bibliographic entry has its own class for dealing with it.

The Entry classes are:
Entry
|-> ArticleEntry    (for journal articles)
|-> BookEntry       (for books)
|-> ConferenceEntry (for conference papers, like InProceedings)
|-> ManualEntry     (for commercial hardware manuals)
|-> MastersEntry    (for master's theses)
|-> MiscEntry       (for everything else)
|-> PatentEntry     (for patents and patent applicaitons)
|-> PhdEntry        (for phd dissertations)
|-> ReportEntry     (for industrial technical reports or whitepapers)
\-> WebsiteEntry    (for citable websites)

The parent Entry class defines default methods for saving and exporting 
bibliographic data that are usually completely extensible to each of the
child class instances.  

Bibliographic entry "items" are available as attributes
    myentry.title = 'An example journal title'
    myentry.journal = 'Court of public opinion'
    
See the Entry documentation for the details on how Entries deal with
bibliographic item data.

*** COLLECTIONS ***

Entries are always grouped into Collections; even if you only have one 
entry.  At the top of every Collection tree is a MasterCollection that
keeps track of everything in its tree.

The Collection classes are:
ProtoCollection
|-> MasterCollection
|-> Collection
\-> SubCollection

Collections are containers for Entries and other Collections.  Only a 
top-level MasterCollection is required for eikosi to work correctly, but
Collections and SubCollections are useful ways of organizing Entires.
Collections and SubCollections can all belong to each other, forming
complicated interwoven trees, but there is always a single 
MasterCollection at the base of the tree.

MasterCollections are special because they accumulate their own exhaustive
dictionary of every entry that belongs to itself and every Collection or
SubCollection beneath it.  MasterCollections are generated automatically
by the load() and loadbib() functions.

Collections and SubCollections can only belong to one MasterCollection at
a time.  Unlike MasterCollections, Collections and SubCollections only 
track the Entries and children (member Collections) that belong to them
directly.  So, in order to search a Collection for a member Entry, it is
necessary to search it AND all of its member Collections (AND all of their
member collections) until it is found or all possibilities are exhausted.

The only difference between a Collection and a SubCollection is that 
SubCollections are not added as children to a MasterCollection by load().
That means that they are only loaded implicitly through their parent 
Collections.  Otherwise, they are identical; they can belong to one 
another, and their methods are identical.

See important methods for working with Collections:
    add, get, has                   Working with Entries
    addchild, getchild, haschild    Working with child Collections
    collections                     Iterating over children

All collection instances support iteration over their member entries. For
finer control over how iteration is done, see the CollectionIterator 
class.
"""

# To do...
# (1) How to save a collection tree; current algorithm sucks
# (2) Write the find algorithm.


import os, sys
from math import log2, ceil
# reflexive import for forward references
import eikosi as ek
import re


__version__ = '0.1'
EXT = '.eks'



def _initial(part):
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
    
def _fingerprint(text):
    """Helper function to distill a name part into a fingerprint
The returned string will be a modified version of the name part with all non-
alpha characters removed, and all alpha characters translated to lower case.
"""
    return ''.join([char.lower() if char.isalpha() else '' for char in text])



M_DEF_FULL = False
class Month:
    """eikosi Month handler class
m = Month(integer)
    OR
m = Month(month_name)
    OR
m = Month(month_abbrev)

The month class is designed to handle month entries as part of a date 
specification.  The repr() and str() outputs are appropriate for write() and
write_bib(), and the show() method is appropriate for write_txt().

The optional keyword, full, can be used to prompt the Month instance to return
the month's full name instead of the abbreviation.

    m = Month(source, full=True)
    
Or, the attribute may be modified after initialization.

    m.full = False
"""
    months_full = [None, 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
    months_abbrev = [None, 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    def __init__(self, source, full=M_DEF_FULL):
        self.index = None
        self.full = full
        # Parse a string
        if isinstance(source,str):
            # Force lower case and strip out white space
            msource = source.lower().strip()
            # Search for the month in the 
            try:
                self.index = self.months_full.index(msource)
                return
            except ValueError:
                pass
            except:
                raise sys.exc_info()[1]
                
            # The month was not a full month.  Try an abbreviation
            # Strip away any trailing '.'
            msource = msource.strip('.')
            try:
                self.index = self.months_abbrev.index(msource)
                return
            except ValueError:
                pass
            except:
                raise sys.exc_info()[1]
            
            # OK, this doesn't look like a month.  Is it an integer?
            try:
                self.index = int(source)
            except:
                raise ValueError(f'Month: Expected a month name, its abbreviation, or an integer, but received: {msource}\n')
        # Parse an integer
        elif isinstance(source, int):
            self.index = source
        else:
            raise ValueError(f'Month: Expected a month name, its abbreviation, or an integer, but received: {msource}\n')

        # We now have an integer.  Now, make sure it is in-range.
        if self.index < 1 or self.index > 12:
            raise ValueError(f'Month: The month index must be between 1 and 12. Found: {self.index}')

    def __repr__(self):
        if self.full == M_DEF_FULL:
            return f'Month({self.index})'
        else:
            return f'Month({self.index}, full={self.full})'
        
    def __str__(self):
        if self.full:
            return self.months_full[self.index].title()
        else:
            return self.months_abbrev[self.index].title()

    def show(self):
        """Return a string representing the month.  This is a wrapper function for __str__()
"""
        return self.__str__()
        

AL_DEF_FULLFIRST = True
AL_DEF_FULLOTHER = False
class AuthorList:
    """eikosi Author List handler class

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

** COMPARING AUTHOR LISTS **

Comparison operations < > == are provided for author lists that allow 
collections to be alphabetized by author and provide tools for identifying
potentially duplicated entries.

The entry of author names leaves some room for ambiguity (e.g. whether first
name or initial is entered, whether middle name(s) are entered at all, and 
precisely how prefixes like "von" or "de la" are included).  The following 
algorithms reduce (but do not eliminate) sensitivity to these ambiguities.  
First, we need to establish the idea of a "fingerprint" of a string.  Using the
_fingerprint() function, a string is stripped of all non-alpha characters and 
all upper case characters are demoted to lower case.  This makes the string 
difficult for a human to read, but it eliminates all whitespace, punctuation, 
brackets, and other potentially ambiguous pieces of the data element.

Testing for equality... Two AuthorList instances evaluate as "equal" if the 
number of authors is the same, if the fingerprint of the last name of authors
in the same place of each list is the same, and if the first initial (if given)
of the first names of authors in the same place of each list is the same.

Test for less than (or greater than)... Less than (greater than) tests obey the
standard rules for alphabetization for author name.  When two AuthorList 
instances are compared, the fingerprint of their last names are compared.  If 
they are equal, the first initial is compared.  If the first authors are found
to be identical using this method, the process is repeated in order until one of
the authors' names does not match or one of the lists is exhausted.  If the 
lists are of different lengths, and all but the "extra" names match, then the
shorter of the two lists is taken to be less than (first alphabetically).  If
the list lengths are identical, then they are treated as equal.

It should be noted that this test does have difficulty with prefixes (like von 
or de la).
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
        out = 'AuthorList(' + repr(self.names)
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
                    out += _initial(part) + '. '
            # Deal with the middle name(s)
            for part in thisauthor[1:-1]:
                if self.fullother:
                    out += part + ' '
                else:
                    out += _initial(part) + '. '
            # Check to be certain the entry is not empty
            # Append the last name
            if len(thisauthor):
                out += thisauthor[-1]
        return out
        
    # Define comparison operations for sorting algorithms
    def __lt__(self, b):
        for namea, nameb in zip(self.names, b.names):
            # If the last name is different, then we have our answer
            lasta = _fingerprint(namea[-1])
            lastb = _fingerprint(nameb[-1])
            if lasta != lastb:
                return lasta < lastb
            # If either of the names lacks a first name
            if len(namea)==1 or len(nameb)==1:
                pass
            elif _initial(namea[0]) < _initial(nameb[0]):
                return True
        return len(self.names) < len(b.names)

    # Define comparison operations for sorting algorithms
    def __gt__(self, b):
        for namea, nameb in zip(self.names, b.names):
            # If the last name is different, then we have our answer
            lasta = _fingerprint(namea[-1])
            lastb = _fingerprint(nameb[-1])
            if lasta != lastb:
                return lasta > lastb
            # If either of the names lacks a first name
            if len(namea)==1 or len(nameb)==1:
                pass
            elif _initial(namea[0]) > _initial(nameb[0]):
                return True
        return len(self.names) > len(b.names)
        
    def __eq__(self, b):
        if len(self.names) != len(b.names):
            return False
        for namea, nameb in zip(self.names, b.names):
            # If the last name is different, then we have our answer
            if _fingerprint(namea[-1]) != _fingerprint(nameb[-1]):
                return False
            # If either of the names lacks a first name
            if len(namea)==1 or len(nameb)==1:
                pass
            # If the first initials don't match
            elif _initial(namea[0]) != _initial(nameb[0]):
                return False
        return True
            
        
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
                out += _initial(author[0]) + '. '
            # Middle name(s)
            for name in author[1:-1]:
                if self.fullother:
                    out += name + ' '
                else:
                    out += _initial(name) + '. '
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

All entries are initialized using unique string identifiers.

** Built-in attributes **

Entries have five built-in attributes: name, sourcefile, docfile, 
collections, and bib.  Access to additional attributes is described 
below in the next section.

--> name
A string identifying the entry in BibTeX.  This is the tag that appears 
immediately after the opening of an entry in the BibTeX file.  Eikosi 
also uses the name as a unique identifier for the Entry.

--> sourcefile
This is the file from which the entry was loaded.  When entries are 
created in scripts or the commandline, the sourcefile attribute is left 
None.

--> docfile
The docfile attribute is an optional string specifying a means for 
retrieving a copy of the document.  It could be a URL (e.g. 
https://website.com/dir/filename.pdf), a path to the file on the local 
machine, (e.g. /home/username/Documents/filename.pdf).

--> collections
The collections attribute is a list of collections to which the entry is 
supposed to belong.  Entries are expected to be the string name of the 
collection.

--> bib
This is a dict that contains all of the items that will be used to construct the
bibliographic record.  Every member of bib is accessible as an attribute of the
Entry, and writing to a nonexistant attribute creates a new member of bib. (see
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

** The mandatory and optional sets **

The mandatory and optional sets are attributes that must to reside with the 
class object, and that should only be referenced by instances.  They define 
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
    mandatory = set()
    optional = set()
    tag = None

    def __init__(self, name):
        if not isinstance(name, str):
            raise Exception('Entry.__init__: The entry name must be a string.\n')
        
        self.__dict__['name'] = name
        self.__dict__['sourcefile'] = ''
        self.__dict__['docfile'] = ''
        self.__dict__['doc'] = ''
        self.__dict__['collections'] = []
        self.__dict__['bib'] = dict()

    def __str__(self):
        return self.show(doc=True, posix=True, width=80)
        
    def __repr__(self):
        thisclass = self.__class__.__name__
        return f'{thisclass}({repr(self.name)})'

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
        # Test for existence of the key in dict first, then bib
        # The hard attributes always take precedence over the bib entries
        if item in self.__dict__:
            return self.__dict__[item]
        elif item in self.__dict__['bib']:
            return self.__dict__['bib'][item]
        raise AttributeError(item)
        
    def __setattr__(self, item, value):
        # Test for existence of the key in dict first, then bib
        # The hard attributes always take precedence over the bib entries
        # Deny is a list of attributes that are off-limits for writing.
        deny = ['bib']
        if item in self.__dict__:
            if item in deny:
                raise Exception(f'Entry: Permission denied to write to attribute {item}')
            self.__dict__[item] = value
        else:
            self.bib[item] = value
            
    def __contains__(self, item):
        return item in self.__dict__ or item in self.__dict__['bib']

    def _convert(self, item, dtype, fatal):
        """Convert an item to an integer and raise a meaningful error if it fails
value = _convert(item, dtype, fatal)

item is the item to be converted, dtype is the function or class to perform the
conversion, and fatal should be True or False to specify what should be done in 
the event of an error."""
        if item in self.bib:
            try:
                self.bib[item] = dtype(self.bib[item])
            except:
                sys.stderr.write(f'Entry._convert: Unsupported format for {item} in entry {self.name}\n')
                if self.sourcefile:
                    sys.stderr.write(f'Entry._convert: loaded from file: {self.sourcefile}\n')
                if fatal:
                    raise sys.exc_info()[1]
                    
                    
    def _date(self, yearfmt='', normal=''):
        """Build a date from the month, day, and year items
The optional keywords, yearfmt and normal insert formatting text before and 
after the year.
    {month} {day}, {yearfmt}{year}{normal}
The intent is that a posix formatting characters can be inserted to force a bold
year.  By default, they are empty strings."""
        out = ''
        if 'year' in self:
            if 'month' in self:
                if 'day' in self:
                    out += f'{self.month.show()} {self.day}, '
                else:
                    out += f'{self.month.show()}, '

            out += f'{yearfmt}{self.year}{normal}'
        return out

    def post(self, fatal=False, verbose=False, strict=False):
        """Each Entry subclass should define its own post method.  It must adopt the call signature
    post(fatal=False, verbose=False, strict=False)
    
This prototype post entry is intended to be called by subclass entries.  It 
(1) checks for absent mandatory items
(2) checks for unrecognized items (if strict)

Individual subclasses should additionally implement checks on data integrity,
perform any necessary data conversions (e.g. a string to an integer or vice 
versa) to respect mandatory data types.
    
fatal   When True, causes post to raise an error if some aspect of the data 
        record is incorrect.
verbose When True, post may print summary information to stdout
strict  When True, unrecognized parameters should generate an error message.
"""
        # Test for available bibliographic items
        kk = set(self.bib.keys())
        # Are there any missing that are required?
        missing = self.mandatory - kk
        # Are there any that aren't recognized?
        unknown = kk - self.mandatory
        unknown -= self.optional
        err = len(missing) + (len(unknown) if strict else 0)
        for item in missing:
            sys.stderr.write(f'Entry.post: Missing mandatory item {item}\n')
        if strict:
            for item in unknown:
                sys.stderr.write(f'Entry.post: Unrecognized item {item}\n')
        
        # Test the non-bibliographic items
        # Collections must be a list of strings
        if not isinstance(self.collections, list):
            err += 1
            sys.stderr.write(f'Entry.post: The collection attribute must be a list of strings.\n')
        elif any([not isinstance(this,str) for this in self.collections]):
            err += 1
            sys.stderr.write(f'Entry.post: The collection attribute must be a list of strings.\n')
        # Force the docfile to be a string.  Leave valid path testing to the load() algorithm
        elif not isinstance(self.docfile,str):
            err += 1
            sys.stderr.write(f'Entry.post: The docfile attribute must be a string path to a file.\n')
        # Force doc to be a string.
        elif not isinstance(self.doc,str):
            err += 1
            sys.stderr.write(f'Entry.post: The doc attribute must be a string.\n')            
        
        if err:
            sys.stderr.write(f'Entry.post: Found {err} errors in {self.tag} entry {self.name}\n')
            if self.sourcefile:
                sys.stderr.write(f'Entry.post: defined in source file: {self.sourcefile}\n')
            
        if err and fatal:
            raise Exception('Entry.post')
            
        if verbose:
            sys.stdout.write(f'Read in entry {self.name} of type {str(type(self))}\n')
            if self.sourcefile:
                sys.stdout.write(f'from file {self.sourcefile}\n')
             
        
        
    def write(self, target=sys.stdout, addimport=True, varname='entry', module=None):
        """Save the bibliographic entry to a file capable of reconstructing it
    write()
        OR
    write('/path/to/file')
        OR
    write(file_object)

This write method is defined by the base Entry class with the intent that it be 
used by all classes, but subclasses are free to override this method.  

The output is executable python code that can be used to re-construct the object
being "written."  What is written is controlled by keyword arguments:

target  (def: stdout)   Where should the output go?  If it is a string, it is 
        treated as a path to a file.  Files should end with .eks so they can be
        discovered by the load() function.
        
addimport   (def: True) When True, the first line written imports the eikosi
            module. "import eikosi" or "import eikosi as {module}"  See module
            keyword for more information.  When multiple entries are written to
            the same file, only the first need write the import statement.
            
varname     (def: 'entry') This is the variable name that will be used for the 
            entry object.  When multiple entries are written to the same file,
            it is important that they be given unique variable names so that the
            earlier entries are not overwritten.
            
module      (def: None) When set to a string, it is the name that will be used
            for the eikosi module.  If None, then the full "eikosi" module name
            will be used.  Otherwise, the import statement and all subsequent 
            references to the module will use the string specified here.  See
            the addimport keyword for more information.
            
WARNING: items with data for which the repr() function does not produce Python
code defining the data will cause problems.  Classes that need to store such 
data should define their own write() method.
"""
        if isinstance(target,str):
            with open(target,'w') as ff:
                self.write(target=target, addimport=addimport, varname=varname, module=module)

        # Detect the class and module names
        thisclass = self.__class__.__name__
        thismodule = self.__class__.__module__
        
        # Add a line importing the module
        if addimport:
            if module is not None:
                target.write(f'import {thismodule} as {module}\n\n')
            else:
                target.write(f'import {thismodule}\n\n')
            
        # If the module name was not explicitly defined, use the full name
        if module is None:
            module = thismodule
        # Add a line declaring the entry variable
        target.write(f'{varname} = {module}.{thisclass}({repr(self.name)})\n')
        
        # Start with bibliographic items
        for item,value in self.bib.items():
            # if the value is an eikosi value class, prepend the module name
            if isinstance(value, (Month, AuthorList)):
                target.write(f'{varname}.{item} = {module}.{repr(value)}\n')
            else:
                target.write(f'{varname}.{item} = {repr(value)}\n')
        
        if self.collections:
            target.write(f'{varname}.collections = {repr(self.collections)}\n')
        if self.docfile:
            target.write(f'{varname}.docfile = {repr(self.docfile)}\n')
        if self.doc:
            target.write(f'{varname}.doc = """{self.doc}"""\n')
        target.write('\n')
        
        
    def write_bib(self, target=sys.stdout):
        """Creates a BibTeX entry for the entry
    write_bib()
        OR
    write_bib('/path/to/file')
        OR
    write_bib(file_object)

The write_bib() generates BibTeX code to represent the selected entry.  Each 
item in the bib dict is written as its own item in the BibTeX entry.  The tag
defining the entry type is determined by the Entry subclass.

All item values are encased in {} to prevent problems from whitespace or commas
in strings.  If strings contain brackets, they should always be in matching 
pairs or they should be escaped.

WARNING: items with data for which the str() function does not produce an output
that can be parsed by BibTeX will cause errors.  Classes that support such data
should define their own write_bib() method.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        target.write(f'{self.tag}{{{self.name},\n')
        for item,value in self.bib.items():
            target.write(f'  {item} = {{{value}}},\n')
        target.write('}\n')
        
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Returns a formatted string citation
    write_txt(doc=True, width=None, posix=False)
    
Each class that is intended for text output should supply its own write_txt()
method since formatting is always specific to the entry type.  This is a 
placeholder method that does nothing.
"""
        pass


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
#   These are built loosely from the details on https://www.bibtex.com/e/entry-types/
###

# ARTICLE
class ArticleEntry(Entry):
    """Eikosi Article Entry
e = ArticleEntry(name)
"""
    tag = '@ARTICLE'
    mandatory = {'author', 'title', 'journal', 'year', 'pages'}
    optional = {'volume', 'number'}

    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        err = False
        # Either volume or number should be present
        if 'volume' not in self.bib and 'number' not in self.bib:
            sys.stderr.write(f'ArticleEntry.post: No volume or number item in entry {self.name}\n')
            if self.sourcefile:
                sys.stderr.write(f'ArticleEntry.post: defined in file: {self.sourcefile}\n')
            if fatal:
                raise Exception('ArticleEntry.post')
        
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('volume', int, fatal)
        self._convert('number', int, fatal)
        self._convert('month', Month, fatal)
        self._convert('year', int, fatal)
        
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        # First, assemble a string from the volume and number
        vn = ''
        if 'volume' in self:
            if 'number' in self:
                vn = f'{bold}{self.volume}{normal}({self.number})'
            else:
                vn = f'{bold}{self.volume}{normal}'
        elif 'number' in self:
            vn = f'{bold}{self.number}{normal}'
        # Assemble the entire entry
        out = f'{self.author.show()}, {self.title}, {italic}{self.journal}{normal}, {vn}, {self.pages}, {self._date()}.\n'
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)


# BOOK        
class BookEntry(Entry):
    tag = '@BOOK'
    mandatory = {'author', 'title', 'publisher', 'year', 'address'}
    optional = {'edition'}
        
    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('year', int, fatal)

    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        # Assemble the entire entry
        out = f'{self.author.show()}, {italic}{self.title}{normal}'
        if 'edition' in self:
            out += f', {self.edition}'
        out += f', {self.publisher}, {self.address}, {self._date(yearfmt=bold, normal=normal)}.\n'
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)

# INPROCEEDINGS
class ConferenceEntry(Entry):
    """Eikosi Conference Entry
e = ConferenceEntry(name)
"""
    tag = '@INPROCEEDINGS'
    mandatory = {'author', 'title', 'booktitle', 'year'}
    optional = {'series', 'pages', 'publisher', 'address', 'month', 'day'}

    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('year', int, fatal)
        self._convert('month', Month, fatal)

    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        # Assemble the entire entry
        out = f'{self.author.show()}, {self.title}, {italic}{self.booktitle}{normal}'
        if 'publisher' in self:
            out += f', {self.publisher}'
        if 'series' in self:
            out += f', {self.series}'
        if 'address' in self:
            out += f', {self.address}'
        if 'pages' in self:
            out += f', {self.pages}'
        out += f', {self.address}, {self._date(yearfmt=bold, normal=normal)}.\n'
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)

ProceedingsEntry = ConferenceEntry

# MANUAL
class ManualEntry(Entry):
    """Eikosi Manual Entry
e = ManualEntry(name)
"""
    tag = '@MANUAL'
    mandatory = {'title', 'organization', 'year'}
    optional = {'author', 'address'}

    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('year', int, fatal)

    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        out = ''
        # Assemble the entire entry
        if 'author' in self:
            out += f'{self.author.show()}, '
        out += f'{italic}{self.title}{normal}, {self.organization}, '
        if 'address' in self:
            out += f'{self.address}, '
        out += f'{self._date()}.\n'
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)

# MASTERTHESIS
class MastersEntry(Entry):
    """Eikosi Masters Thesis Entry
e = MastersEntry(name)
"""
    tag = '@MASTERSTHESIS'
    mandatory = {'author', 'title', 'school', 'year'}
    optional = {'address', 'month', 'day'}
    
    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('month', Month, fatal)
        self._convert('year', int, fatal)
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        out = f'{self.author.show()}, {italic}{self.title}{normal}, {self.school}, '
        if 'address' in self:
            out += f'{self.address}, '
        if 'month' in self:
            out += f'{self.month.show()}, '
        out += f'{self._date(yearfmt=bold, normal=normal)}.\n'
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)

# MISC
class MiscEntry(Entry):
    tag = '@MISC'
    mandatory = {'title', 'howpublished', 'year'}
    optional = {'note', 'author', 'month', 'day'}
    
    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('month', Month, fatal)
        self._convert('year', int, fatal)
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        out = ''
        if 'author' in self:
            out += f'{self.author.show()}, '
        out += f'{italic}{self.title}{normal}, {self.howpublished}, '
        if 'year' in self:
            out += f'{self._date(yearfmt=bold,normal=normal)}.'
        if 'note' in self:
            out += f' {self.note}'
        out += '\n'
            
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)
    
# PHDTHESIS
class PhdEntry(Entry):
    tag = '@PHDTHESIS'
    mandatory = {'author', 'title', 'school', 'year'}
    optional = {'address', 'month', 'day'}

    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('month', Month, fatal)
        self._convert('year', int, fatal)
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        out = f'{self.author.show()}, {italic}{self.title}{normal}, {self.school}, '
        if 'address' in self:
            out += f'{self.address}, '
        if 'month' in self:
            out += f'{self.month.show()}, '
        out += f'{self._date(yearfmt=bold,normal=normal)}.\n'
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)

# TECHREPORT
class ReportEntry(Entry):
    """Eikosi Report Entry
e = ReportEntry(name)
"""
    tag = '@TECHREPORT'
    mandatory = {'author', 'title', 'year'}
    optional = {'number', 'institution', 'month', 'day', 'address'}

    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('month', Month, fatal)
        self._convert('year', int, fatal)
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        out = f'{self.author.show()}, {italic}{self.title}{normal}, {self.institution}, '
        if 'address' in self:
            out += f'{self.address}, '
        out += f'{self._date(yearfmt=bold,normal=normal)}.\n'
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)

        
# UNPUBLISHED

# CUSTOM PATENT ENTRY
class PatentEntry(Entry):
    """Eikosi Proceedings Entry
e = PatentEntry(name)
"""
    tag = '@MISC'
    mandatory = {'author', 'title', 'number', 'year'}
    optional = {'assignee', 'nationality', 'month', 'day'}
    
    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('month', Month, fatal)
        self._convert('year', int, fatal)
        self._convert('number', str, fatal)
        
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        out = f'{self.author.show()}, {italic}{self.title}{normal}, '
        if 'nationality' in self:
            out += f'{self.nationality} '
        out += f'Pat. {bold}{self.number:,d}{normal}, {self._date()}.'
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)
    
    
    def write_bib(self, target=sys.stdout):
        """Creates a BibTeX entry for the entry
    write_bib()
        OR
    write_bib('/path/to/file')
        OR
    write_bib(file_object)

The write_bib() generates BibTeX code to represent the selected entry.  Each 
item in the bib dict is written as its own item in the BibTeX entry.  The tag
defining the entry type is determined by the Entry subclass.

All item values are encased in {} to prevent problems from whitespace or commas
in strings.  If strings contain brackets, they should always be in matching 
pairs or they should be escaped.

WARNING: items with data for which the str() function does not produce an output
that can be parsed by BibTeX will cause errors.  Classes that support such data
should define their own write_bib() method.
"""
        # Build a miscellaneous entry
        e = MiscEntry(self.name)
        e.author = self.author
        if 'nationality' in self:
            e.howpublished = f'{self.nationality} Patent {self.number}'
        else:
            e.howpublished = f'Patent {self.number}'
        e.year = self.year
        e.title = self.title
        e.write_bib(target=target)
    
# CUSTOM WEBSITE ENTRY
class WebsiteEntry(Entry):
    tag = '@MISC'
    mandatory = {'url'}
    optional = {'title', 'author', 'institution', 'month', 'day', 'year'}

    def post(self, fatal=False, verbose=False, strict=False):
        """Post processing on entry objects.
    e.post(fatal=False, verbose=False, strict=False)

The post() method on each entry is run by a MasterColleciton's load() method
when reading entries into the collection.  It checks the entry for data type and
format.
"""
        # Check for mandatory and/or unrecognized items in the entry
        Entry.post(self, fatal=fatal, verbose=verbose, strict=strict)
        # Force the authors to be an AuthorList item
        self._convert('author', AuthorList, fatal)
        self._convert('month', Month, fatal)
        self._convert('year', int, fatal)
        
        
    def write_txt(self, target=sys.stdout, doc=True, width=None, posix=False):
        """Return a string appropriate for printing to a terminal
    write_txt()
        OR
    write_txt(target = '/path/to/file')
        OR
    write_txt(target = file_object)
    
Writes the bibliographic entry formatted as readable text.  There are keywords 
that configure its behavior:

doc     If True, the notes stored in the doc attribute are also printed.

width   If width is set to an integer, it will determine the maximum line length
        before a line break is inserted.  If it is unset, the string will be
        returned as a single line.
        
posix   If True, posix terminal formatting escape characters will be inserted
        for bold and italic fonts where appropriate.
"""
        if isinstance(target, str):
            with open(target,'w') as ff:
                return self.write_txt(target=ff, doc=doc, width=width, posix=posix)
        
        normal = ''
        italic = ''
        bold = ''
        if posix:
            normal = '\033[0m'
            italic = '\033[3m'
            bold = '\033[1m'
        
        out = ''
        if 'author' in self:
            out += f'{self.author.show()}, '
        if 'title' in self:
            out += f'{italic}{self.title}{normal}, '
        if 'institution' in self:
            out += f'{self.institution}, '
        out += f'{bold}{self.url}{normal}'
        if 'year' in self:
            out += f', accessed: {self._date()}'
        
        
        if doc and self.doc:
            out += self.doc
        # Adjust the line width?
        if width:
            out = self._splitlines(out,width)
        target.write(out)
    
    def write_bib(self, target=sys.stdout):
        """Creates a BibTeX entry for the entry
    write_bib()
        OR
    write_bib('/path/to/file')
        OR
    write_bib(file_object)

The write_bib() generates BibTeX code to represent the selected entry.  Each 
item in the bib dict is written as its own item in the BibTeX entry.  The tag
defining the entry type is determined by the Entry subclass.

All item values are encased in {} to prevent problems from whitespace or commas
in strings.  If strings contain brackets, they should always be in matching 
pairs or they should be escaped.

WARNING: items with data for which the str() function does not produce an output
that can be parsed by BibTeX will cause errors.  Classes that support such data
should define their own write_bib() method.
"""
        # Build a miscellaneous entry
        e = MiscEntry(self.name)
        if 'title' in self:
            e.title = self.title
        if 'author' in self:
            e.author = self.author
        if 'institution' in self:
            e.howpublished = f'{self.institution}, {self.url}'
        else:
            e.howpublished = self.url
        e.note = f'accessed: {self._date()}'
        e.write_bib(target=target)

#####
# Collection and collection-related classes
#####

class CollectionIterator:
    """Use the CollectionIterator to iterate over all child Collections

for this in CollectionIterator(collection_instance):
    ...
    
Optional keywords are:

depthfirst (default False)
When this is True, Collections at the bottom of the Collection tree will 
appear immediately before the Collections that contain them.  When False, all
Collections at the same depth of the tree will appear together in the 
iteration, and higher layers always appear first.

inclusive (default True)
When Falce, the Collection instance used to initiate the iteration is not 
included in the iteration.
"""
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
    # Name contains the string that uniquely identifies the collection
    name = ''
    # The doc string is a place for optional comments on the collection
    doc = ''
    # The entries that belong to the dict are all stored here
    entries = {}
    # The Collections that belong to this collection are all stored here
    children = {}
    # This is a pointer to the MasterCollection that contains this Collection
    master = None
    # This is a record of the file where the Collection was defined
    sourcefile = None
    # _sorted is a dict of all past calls to sort().  Each entry is a list of
    # entry names sorted by the item identified by the key.
    _sorted = {}
    # The _iflag is a boolean indicating if this Collection was already used
    # while assembling a CollectionIterator schedule.
    _iflag = False

    def __init__(self, name):
        # Make explicit local attributes for the most essential elements.
        self.name = ''
        self.entries = {}
        self.children = {}

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
        """Set the value of _iflag for this and all child Collections
    count = c._set_iflag(value)
    
For each child Collection that does not already have its _iflag set to
value, _set_iflag sets its _iflag value and recurses into its children as
well.  _set_iflag() returns the total number of _iflag members whose 
values were set.

This is a method for counting unique Collections in trees that can have
infinite loops.  _set_iflag() is also useful for clearing _iflag values
after an loop iteration is complete.
"""
        count = 0
        if self._iflag != value:
            count += 1
            self._iflag = value
            for child in self.children.values():
                count += child._set_iflag(value)
        return count
        
    def flatten(self, remove=True):
        """Pull in entries from all children
    c.flatten()
        OR
    c.flatten(remove=False)
    
Brings all entries from this collection's children into its dict of 
entries.  Unless the _remove_ keyword is set to False, all child 
collections will also be removed. 
"""
        for c in self.collections(rself=False):
            for newentry in c.entries.values():
                # Check to see if this entry already belongs to self
                if self not in newentry.collections:
                    self.entries[newentry.name] = newentry
                    newentry.collections.append(self)
        if remove:
            self.children = {}
            
        
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
        

    def duplicates(self):
        """DUPLICATES
    dup = c.duplicates()
    
Generates a list of lists of possible duplicate entries in the collection.
"""
        # This iterator returns a tuple pair with a "fingerprint" of each entry
        # so that all entries may be sorted by their fingerprints
        def _dup_iter(self):
            for e in self:
                result = ''
                if 'author' in e:
                    result += e.author.names[0][-1]
                if 'title' in e:
                    result += e.title
                yield (_fingerprint(result), e)
        
        candidates = sorted(_dup_iter(self))
        duplicates = []
        active = False
        last_fp = None
        last_e = None
        
        for fp,e in candidates:
            # Check for a match with the last fingerprint
            # If there is a match, then add it to the duplicates list
            if last_fp == fp:
                # If there is already an active match, append to the last sub-list
                if active:
                    duplicates[-1].append(self)
                # If this is a new match, create a new sub-list
                else:
                    duplicates.append([last_e, e])
                    active=True
            else:
                active=False
                
            last_fp = fp
            last_e = e
            
        return duplicates
        
    def addchild(self, cnew):
        """Add a new subcollection to this collection
    this_collection.addchild(new_collection)
    
New collections must either belong to the same MasterCollection or may not
belong to a MasterCollection.  This operation will join them to the 
current MasterCollection.
"""
        # Check for correct Collection type
        if not isinstance(cnew, (ek.Collection,ek.SubCollection)):
            raise TypeError('ProtoCollection.addcollection: All child collections must be Collection or SubCollection instances.\n') 
        # Check for agreement between the masters
        elif cnew.master is not None:
            if self.master is None:
                raise Exception(f'ProtoCollection.addcollection: Child {cnew.name} belongs to a master, but parent {self.name} does not.')
            elif self.master is not cnew.master:
                raise Exception(f'ProtoCollection.addcollection: Child {cnew.name} and parent {self.name} have different masters.')
        # Check for a name collision
        if self.haschild(cnew.name):
            raise Exception(f'ProtoCollection.addcollection: Parent {self.name} already has a child {cnew.name}.')
        # Add as a member
        self.children[cnew.name] = cnew
        # Force membership to the same master, even if master is None
        cnew.master = self.master
        
        
    def removechild(self, target):
        """Remove a Collection or SubCollection from this collection
    c.removechild(collection_name)
        OR
    c.removechild(collection)
    
Accepts either the Collection's name as a string or the Collection itself.
Unlike the removal of entries, this operation is never recursive.
"""
        # If the target is a name
        if isinstance(target,str):
            cname = target
            target = None
        # If the target is a Collection
        elif isinstance(target, ProtoCollection):
            cname = target.name
        
        # Does this target exist in the collection?
        if cname in self.children:
            # Test for a contradiction in the specified target
            if target is None:
                target = self.children[cname]
            elif target is not self.children[cname]:
                raise Exception(f'ProtoCollection.remove: Contradicting records for Collection {cname}. Aborting.')
            # OK, time to remove. 
            del self.children[cname]
            # If I was this collection's Master and it no longer appears
            # in the Collection tree, then it no longer has a master
            if target.master is self and self.getchild(cname) is None:
                target.master = None
        else:
            raise Exception(f'ProtoCollection.remove: No child found {cname}')
            
            
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
        # If the test is by name, then iterate over all mmeber collections
        if isinstance(ctest,str):
            return self.getchild(ctest) is not None
        # If the test is by identity, use getchild() to search by name
        # Then, test to verify identity.
        elif isinstance(ctest,ProtoCollection):
            return self.getchild(ctest.name) is ctest
        # If the type is an unhandled type
        raise TypeError('Collection.haschild: argument must be a string or collection. Found: ' + repr(type(ctest)))
        
        
    def getchild(self, cname):
        """Retrieve a SubCollection that belongs to this collection.
    c = this_collection.getchild(collection_name)
    
This retrieve operation will succeed if the collection is a member of this or 
any of the sub-collections.  If the name is not found as a child of the evoking
collection, then getchild() returns None.
"""
        for this in CollectionIterator(self, depthfirst=False):
            if this.name == cname:
                return this
        return None
        

    def add(self, newentry):
        """Add an entry to the Collection
    c.add(entry)
    
This adds an entry to this colleciton and, indirectly, to all parent 
collections.  If the Collection is a member of a MasterCollection, the new
Entry will also be added to it.

If the new entry is already a member of the collection, nothing will be 
done unless the entries are different.
"""
        # Test that this is an Entry type
        if not isinstance(newentry,Entry):
            raise Exception('ProtoCollection.add: Requires an Entry, but received: ' + repr(newentry))
        
        # If this Collection does not belong to a MasterColleciton yet
        if self.master is None:
            # Test for a name collision
            test = self.entries.get(newentry.name)
            if test is not None and test is not newentry:
                raise Exception(f'ProtoCollection.add: Entry contradicts an existing entry for: {newentry.name}')
        # If this Collection is part of a MasterCollection, the new entry
        # needs to be checked against the MasterCollection entries
        else:
            # Adding the entry to master will fail if it conflicts
            # with an previous entry
            self.master.add(newentry)
        
        # Add the new entry to this collection
        self.entries[newentry.name] = newentry
        # Finally, adding a new entry invalidates previous sort operaitons
        self._sorted = {}
        
        
    def remove(self, target, recurse=True):
        """Remove an entry from the colleciton
    c.remove(entryname)
        OR
    c.remove(entry)
    
Removing an Entry from a Collection implies removing it from all child
collections as well.  Setting the optional "recurse" keyword to False 
overrides this behavior and only removes the Entry from this Collection
without recursing into its child collecitons.

When operating recursively, Collection tree integrity checks are run as
the search progresses.  Each instance matching the entry name is check to
be certain it is pointing to the same entry and the entry's collections
list is check for the matching collections.  Problems produce descriptive
warnings but not exceptions since removal corrects the errors.
"""
        # Isolate the entry name.  If target is a string, we already have it
        if isinstance(target, str):
            entryname = target
            target = None
        # If it isn't a name, it had better be an entry
        elif isinstance(target, Entry):
            entryname = target.name
        else:
            raise Exception(f'ProtoCollection.remove: Expected an entry or entry name, but got {repr(target)}')


        # At this stage, entryname MUST be a string
        # If target is not None, it is the entry being removed
        # If running recursively,
        if recurse:
            # Keep track of whether the entry was ever found
            nfound = True
            # Loop through all child Collections
            for c in self.collections():
                # Does this collection recognize the entry name?
                if entryname in c.entries:
                    nfound = False
                    # If this is the first time we found a matching entry
                    if target is None:
                        target = c.entries[entryname]
                    elif target is not c.entries[entryname]:
                        sys.stderr.write(f'ProtoCollection.remove: Found conflicting entries for {entryname}. Collection tree may be corrupt; removing.\n')
                    # Finally, remove the entry from the collection
                    del c.entries[entryname]
            if nfound:
                raise Exception(f'ProtoCollection.remove: Entry {entryname} was not found.')
        else:
            # If not operating recursively, then the remove operation only applies
            # to this collection.
            if entryname in self.entries:
                # If the target entry was not supplied, get it
                if target is not None and target is not self.entries[entryname]:
                    raise Exception(f'ProtoCollection.remove: Entry {entryname} contradicts the entry.  Aborting.')
                # Finally, remove the entry from the collection
                del self.entries[entryname]    
            else:
                raise Exception(f'ProtoCollection.remove: Entry {entryname} was not found.  Try running recursively?')



    def get(self, entryname):
        """Retrieve an entry by its name
    entry = c.get(entryname)
    
Returns the entry if it is a member of the collection or any of its child-
collections.  If the entry is not found, returns None instead.
"""
        for this in CollectionIterator(self, depthfirst=False):
            value = this.entries.get(entryname)
            if value is not None:
                return value
        return None


    def has(self, entryname):
        """Test whether the entry belongs to this collection or its children
    TF = c.has(entryname)
        OR
    TF = c.has(entry_instance)
    
If the argument is a string, it is treated as an entry name to search for.  If
it is an Entry instance, then it must also be identical to the Entry found in
the Collection.
"""
        if isinstance(entryname, Entry):
            return self.get(entryname.name) is entryname
        elif isinstance(entryname, str):
            return self.get(entryname) is not None
        raise TypeError('Collection.has: The argument must be a string or an Entry type.\n')
        
    def list(self, by='name', width=80, height=12):
        """Print a list of the Colleciton's entries to standard out
    c.list()

Prints a formatted list of entry names to standard out.  Optional 
parameters are:

by  ('name')
The entry attribute by which to sort the list before printing it.  This 
uses the sort() method, so the sorting result is retained.

width   (80)
The absolute maximum terminal width to occupy with the list

height  (12)
The number of entries before the list will be broken into columns
"""
            
        # We MUST keep it within width columns
        # We will TRY to keep it within height rows
        colwidth = 0 # We will detect the maximum name length in a moment
        
        # Create a sorted list of names
        schedule = self.sort(by)
        N = len(schedule)
        
        # If there needs to be more than one column
        if N > height:
            # Detect the maximum name width
            for thisentry in schedule:
                colwidth = max(len(thisentry.name), colwidth)
            colwidth += 2
            # How many collumns can we tolerate?
            Ncol = width // colwidth    # number of columns
            Nrow = int(ceil(N / Ncol))  # number of rows
            Nfrow = Nrow * (1-Ncol) + N # Number of full rows
            
            # Build a format string for printing the names
            fmtstr = '{:' + str(colwidth) + 's}'
            # Loop through the full rows
            for row in range(Nfrow):
                for col in range(Ncol):
                    sys.stdout.write(fmtstr.format(schedule[row + Nrow*col].name))
                sys.stdout.write('\n')
            # End up with the rows that are missing the right-most name
            for row in range(Nfrow,Nrow):
                for col in range(Ncol-1):
                    sys.stdout.write(fmtstr.format(schedule[row + Nrow*col].name))
                sys.stdout.write('\n')
        else:
            for thisentry in schedule:
                sys.stdout.write(thisentry.name + '\n')
        
    def find(self, **kwarg):
        """Returns a collection of entries that match the search criteria
    THIS IS THE HARD ONE

To be written later.
"""
        pass
        
        
    def sort(self, by, refresh=False, ascending=True, omit=False):
        """Return a sorted list of entries from the collection
    sortedlist = c.sort(by='item')

Returns a list of entries in ascending order by the bibliographic item name 
passed to the "by" keyword.  Values in these entries must have a method for the 
< operation.  Entries that do not have the item are appended to the end of the
list, but they may be omitted by setting the omit keyword to True.

The list may be reversed into descending order by setting the ascending keyword
to False.  

The result of each call to the sort() method is stored in the collection so that
redundant calls to sort() simply return the stored list.  The stored list is 
always constructed in ascending=True, omit=False mode.  When sort() is called on
the same item, but with different keyword flags, the saved list is copied and 
modified appropriately.

If a user application modifies the list returned by sort(by), the modifications
will be persistent, but modifications to the list returned by 
sort(by, omit=True) will not be persistent.  

"""

        # If this sorting doesn't already exist in the _sorted record,
        # create it.
        if by not in self._sorted or refresh:
            def _key(entry):
                if by in entry:
                    return entry.__getattr__(by)
                return None
            self._sorted[by] = sorted(self, key=_key)
        
        # OK, we have a sorted result, now deal with the keyword options
        # If the list needs to be modified, first make a copy
        if omit or not ascending:
            result = self._sorted[by].copy()
            # Search for the last result element that contains by
            for index in range(len(result),-1,-1):
                if by in result[index]:
                    index += 1
                    break
            # index is now the first index where the entry does not have by
            if omit:
                result = result[:index]
                if not ascending:
                    result = result.reverse()
            elif not ascending:
                result[:index] = result[:index].reverse()
            return result
        
        return self._sorted[by]
        

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
        
        if addimport:
            target.write(f'import {thismodule}\n\n')
        target.write(f'{varname} = {thismodule}.{thisclass}(\'{self.name}\')\n')

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
            for entry in self.sort('year'):
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

The MasterCollection class is a special type of collection that supports 
loading and saving of entire directories of Eikosi and BibTeX data files.    

There are some important difference that separate MasterCollections from other
Collections.  An Entry is said to belong to any instance of the Collection sub-
classes if the entry is a member of that Collection or any of its child 
Collections.  In this way, a Collection with no entries of its own could still
posess many entries through its child Collections, but the same is not true of
MasterCollection instances.

All Entries that belong to a MasterCollection MUST be linked directly in its
entries dictionary.  They may also belong to child Collections, but there may
not, under any circumstances, be an Entry that belongs to a child Collection
that is not explicitly registered by the MasterCollection.

This means that Entry operations like get() and has() are faster on 
MasterCollections, but it also means that any additions to child collections 
after load will not be detected unless they are handled by the appropraite
class functions.  See update(), add(), addchild(), merge(),
"""
    def __init__(self):
        # Use the standard initialization algorithm
        ProtoCollection.__init__(self, 'main')
        # but a master always belongs to itself
        self.master = self

    def __iter__(self):
        return self.entries.values().__iter__()
        
    def __len__(self):
        return len(self.entries)
        
    def add(self, newentry):
        """Add an entry to this MasterCollection or subordinate Collections
    mc.add(newentry)
    
The new entry will be added to the MasterCollection if it does not already
exist within the MasterColleciton.  If the entry already agrees with a 
member of the MasterCollection, nothing will be done.  If the entry 
conflicts with a prior entry, an Exception is raised.
"""
        if not isinstance(newentry,Entry):
            raise Exception('MasterCollection.add: Cannot add a non-Entry: ' + repr(type(newentry)))
        # Check for a collision.  If it's safe, go ahead and add the entry
        test = self.get(newentry.name)
        if test is not None and test is not newentry:
            raise Exception('MasterCollection.add: The new entry collides with an existing entry for: ' + newentry.name)
            
        # Add the new entry to this collection
        self.entries[newentry.name] = newentry
        # Add this collection to the entry's list of collections
        newentry.collections.append(self)
        # Adding a new species invalidates previous sort operations
        self._sorted = {}
        
    def get(self, entryname):
        """Get an entry from the MasterCollection
    E = mc.get('name_string')
    
Returns None if the name is not found.
"""
        return self.entries.get(entryname)
        
    def has(self, entryname):
        """Test whether the MasterCollection contains an entry
    tf = mc.has('name_string')
        OR
    tf = mc.has(entry)
    
Accepts either an entry name string or an entry instance.  If the argument is
an entry instance, the entry dict is first searched for a matching name.  If
found, the instances must also be identical.
"""
        if isinstance(entryname, str):
            return entryname in self.entries
        elif isinstance(entryname, Entry):
            return self.get(entryname.name) is entryname
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
        # If called with a string
        if isinstance(target,str):
            # If the target is a directory, scan it for .eks files
            if os.path.isdir(target):
                target = os.path.abspath(target)
                contents = os.listdir(target)
                # Loop over everything in the directory
                for this in contents:
                    newtarget = os.path.join(target, this)
                    # If this is a directory and recursion is active
                    if os.path.isdir(newtarget):
                        if recurse:
                            if verbose:
                                sys.stdout.write(f'MasterCollection.load: Recursing into dir: {newtarget}\n')
                            # recurse into the directory
                            self.load(newtarget, verbose=verbose, recurse=recurse, relax=relax, _top=False)
                    # If this is an eks file, load it!
                    elif this.endswith(EXT):
                        self.load(newtarget, verbose=verbose, recurse=recurse, relax=relax, _top=False)
            # If the target is a filename, load it
            elif os.path.isfile(target):
                with open(target,'r') as ff:
                    self.load(ff, verbose=verbose, relax=relax, _top=False)
            else:
                raise Exception(f'MasterCollection.load: No file or directory named: {target}\n')
        # If this is a file object
        elif hasattr(target,'read') and hasattr(target,'name'):
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
            # Use a state variable to track whether any recognized types were found
            nfound = True
            for name, value in namespace.items():
                # Look for an Entry child instance
                if issubclass(type(value), Entry):
                    # Flag that this file does contain valid entries
                    nfound = False
                    # If this Entry is already in the MasterCollection raise a warning
                    # and DO NOT add it.
                    if value.name in self.entries:
                        sys.stdout.write(f'MasterCollection.load: Found conflicting definitions for entry: {value.name}\n')
                        originfile = self.entries[value.name].sourcefile
                        if originfile:
                            sys.stdout.write(f'MasterCollection.load: Originally defined in file: {originfile}\n')
                        sys.stdout.write(f'MasterCollection.load: Redundant entry found in file: {sourcefile}\n')
                        sys.stdout.write(f'MasterCollection.load: Ignoring the redundant entry!\n')
                    # OK.  Everything seems good.
                    else:
                        # If we're operating verbosely, tell the user what we found
                        if verbose:
                            sys.stdout.write('    --> Found entry: ' + value.name + '\n')
                        # Record the file where the Entry was defined
                        value.sourcefile = sourcefile
                        # Run post-processing
                        value.post(fatal=(not relax))
                        # Add the entry
                        self.entries[value.name] = value
                        # Add this master to the Entry's list of collections
                        value.collections.append(self)
                        # Identify this as the Entry's sole MasterCollection
                        value.master = self
                # Or, look for a Collection
                elif isinstance(value, Collection):
                    nfound = False
                    # Not sure how, but this Collection is already associated with another MasterCollection
                    # Raise a warning and DO NOT add it.
                    if value.master is not None:
                        sys.stdout.write(f'MasterCollection.load: Collection {value.name} is already associated with another MasterCollection\n')
                        sys.stdout.write(f'MasterCollection.load: Defined in file: {sourcefile}\n')
                    # There is already a Collection with this name in the MasterCollection
                    # Raise a warning and DO NOT add it.
                    elif value.name in self.children:
                        sys.stdout.write(f'MasterCollection.load: Found conflicting definitions for Collection: {value.name}\n')
                        originfile = self.children[value.name].sourcefile
                        if originfile:
                            sys.stdout.write(f'MasterCollection.load: Originally defined in file: {originfile}\n')
                        if value.sourcefile:
                            sys.stdout.write(f'MasterCollection.load: Redundant Collection found in file: {value.sourcefile}\n')
                        sys.stdout.write(f'MasterCollection.load: Ignoring the redundant Collection!\n')
                    # OK.  Everything seems acceptable.  Add the collection
                    else:
                        # If we're operating verbosely, tell the user what we found.
                        if verbose:
                            sys.stdout.write('    --> Found collection: ' + value.name + '\n')
                        value.sourcefile = sourcefile
                        value.master = self
                        self.children[value.name] = value
            # Warn the user if there were no objects found.
            if nfound:
                sys.stderr.write(f'MasterCollection.load: No recognized objects in file: {sourcefile}\n')
        else:
            raise TypeError('MasterCollection.load: Requires a string path or a file type.')
        
        # Regardless of how the load() method was evoked, we need to do some
        # post-processing to link entries to their respective collections.
        # Unless this is a recursion call, it's time to check the entries for 
        # membership in collections
        if _top:
            if verbose:
                sys.stdout('MasterCollection.load: Linking entries to their collections.\n')
            # Loop through all of the entries in the MasterCollection
            for entry in self:
                # If the Entry's collections member is not a list, raise warning and move on.
                if not isinstance(entry.collections, list):
                    sys.stderr.write(f'MasterCollection.load: Illegal collections list for entry: {entry.name}\n')
                    if entry.sourcefile:
                        sys.stderr.write(f'MasterCollection.load: Defined in file: {entry.sourcefile}\n')
                # If the list is non-empty
                elif entry.collections:
                    # Loop through all of the Collections requested by the Entry
                    for ii,cname in enumerate(entry.collections):
                        # If the collection appears to be a string collection name
                        if isinstance(cname,str):
                            # Look for the collection in the MasterCollection
                            c = self.getchild(cname)
                            # If it exists, add the entry and replace the collection name
                            # with a pointer to the actual collection instance.
                            if c is not None:
                                c.add(entry)
                            # If it doesn't exist, warn the user!
                            else:
                                sys.stderr.write(f'MasterCollection.load: Error linking entry to its collection: {entry.name}\n' + \
                                        f'MasterCollection.load: Failed to find collection: {cname}\n')
                                if entry.sourcefile:
                                    sys.stderr.write(f'MasterCollectionload: Entry defined in file: {entry.sourcefile}\n')

    def merge(self, target, overwrite=False, relax=False):
        """MERGE
    c1.merge(c2)
        OR
    c1.merge('/path/to/dir')
    
The merge method adds the contents of another MasterCollection object into this
MasterCollection.  If the first argument is a string, it is treated as a path
to a directory to load into a new MasterCollection, which will then be loaded.

Merging is similar to using the update() or addchild() methods, except that 
merging is unique to MasterCollections, and it includes the detection of 
redundant entries and collections.  

See also update(), addchild()
"""
        # Make a recursive call if the argument is a string
        if isinstance(target,str):
            b = MasterCollection()
            b.load(target, relax=relax)
            return self.merge(b)
        elif not isinstance(target, MasterCollection):
            raise Exception('MasterCollection.merge: target is not a MasterCollection!')

        conflict = 0
        # First, check for redundant entries by name
        redundant = set(self.entries.keys()).intersection(set(target.entries.keys()))
        for entry in redundant:
            if not self.entries[entry] is target.entries[entry]:
                conflict += 1
                sys.stderr.write(f'MasterCollection.merge: Conflicting definitions for entry: {entry}\n')

        # Now check for redundant collections
        redundant = set(self.children.keys()).intersection(set(target.children.keys()))
        for collection in redundant:
            if not self.children[collection] is target.children[collection]:
                conflict += 1
                sys.stderr.write(f'MasterCollection.merge: Conflicting definitions for collection: {collection}\n')
           
        if conflict:
            if overwrite:
                sys.stderr.write(f'MasterCollection.merge: Overwriting {conflict} conflicts.\n')
            else:
                sys.stderr.write(f'MasterCollection.merge: Identified {conflict} conflicts.\n')
                sys.stderr.write(f'MasterCollection.merge: Set overwrite=True to suppress this exception.\n')
                raise Exception(f'MasterCollection.merge: Redundant entries')
                    
        self.update(target)
        
    def addchild(self, cnew):
        """Add a collection to the MasterCollection
    mc.addchild(cnew)
    
The new member class must be a Collection (not a SubCollection or 
MasterCollection), and the entries must be unique or consistent.  Entries that
are redundant with Entries in this MasterCollection will not raise an Exception
if they point to identical istances.  Otherwise, an exception is raised.
"""
        if isinstance(cnew, Collection):
            # Is this Collection already associated with another MasterCollection
            if cnew.master is not None and cnew.master is not self:
                raise Exception(f'MasterCollection.addchild: Collection {cnew.name} is already associated with another MasterCollection.')
            # Does this collide with a previous collection name?
            elif cnew.name in self.children:
                raise Exception(f'MasterCollection.addchild: There is already a collection with the name: {cnew.name}')
            # Look for any new entries in the new collection
            for newentry in cnew:
                # Does the entry already belong to this MasterCollection?
                oldentry = self.entries.get(newentry.name)
                # If so, make sure it's the same entry
                if oldentry is not None and oldentry is not newentry:
                    raise Exception(f'MasterCollection.addchild: There are contradictory entries for: {newentry.name}')
                # If the entry does not exist, add it.
                else:
                    self.entries[newentry.name] = newentry
        else:
            raise Exception('MasterCollection.addchild: Only Collections can be added as a child of a MasterCollection')
        

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


def load(target, *varg, **kwarg):
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
    mc = MasterCollection()
    mc.load(target, *varg, **kwarg)
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

    output = MasterCollection()
    output.doc = 'Created by eikosi.loadbib()'

    # Recognized types
    entrytypes = {
        '@ARTICLE': ArticleEntry,
        '@INPROCEEDINGS': ConferenceEntry,
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
