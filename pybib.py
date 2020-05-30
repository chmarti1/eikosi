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
import entries



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
                            raise Exception('AuthorList.__init__: Unrecognized name part: ' + repr(part))
                    self.names.append(this)
        # If called with an existing author list
        elif isinstance(raw,AuthorList):
            # Do not copy the content; point to it.
            self.names = raw.names
        else:
            raise Exception('AuthorList.__init__: Unhandled input: ' + repr(raw))
        
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
        raise Exception('AuthorList._initial: Failed to find a valid alpha character from: ' + part)
        
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
                            raise Exception('AuthorList._str_parse: Leading "and" separator.')
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
                    raise Exception('AuthorList._str_parse: Found } with no matching {.')
            elif tchar == '"' and bracket==0 and squote==0:
                quote = 0 if quote else 1
            elif tchar == "'" and bracket==0 and quote==0:
                squote = 0 if squote else 1
        # Was there unhanlded text when the string terminated?
        if jj+1>ii:
            text = raw[ii:]
            if text == 'and':
                raise Exception('AuthorList._str_parse: Trailing "and" separator.')
            this.append(text)
        return authors



class Collection:
    """PyBib Collection
pbc = Collection()
    
"""
    def __init__(self):
        self.members = []
        self.collections = []
        self._flag = False
        
    def add(self, newentry, fatal=True):
        """Add an entry or a collection to this collection
    
"""
        if issubclass(type(newentry), Entry):
            if self in self.members:
                raise Exception('Collection.add: Entry is already a member.')
            self.members.append(newentry)
        elif isinstance(entry, Collection):
            if newentry is self:
                raise Exception('Collection.add: Cannot add a collection to itself.')
            elif newentry in self.collections:
                raise Exception('Collection.add: Collectino is already a member.')
            self.collections.append(newentry)
        elif fatal:
            raise Exception('Collection.add: Unable to add a member of type: ' + repr(type(new)))

    def remove(self, item):
        pass

    def _clear_flags(self):
        # Accumulate a count of the number of flags
        count = 0
        # Only permit recursion if our flag is set
        if self._flag:
            # Increment the count once for our flag
            count += 1
            for this in self.collections:
                count += this._clear_flags()
        # Force our flag clear
        self._flag = False
        return count
        

def load(target, verbose=False):
    """Execute a python file or files containing entries and extract the entries

"""
    if isinstance(target,str):
        if verbose:
            sys.stdout.write('load: opening file: ' + target + '\n')
        with open(target,'r') as ff:
            return load(ff, verbose=verbose)

    sourcefile = os.path.abspath(target.name)
    namespace = {}
    if verbose:
        sys.stdout.write('load: executing file: ' + sourcefile + '\n')
    try:
        exec(target.read(), None, namespace)
    except:
        sys.stderr.write('loadentry: Error while executing file: ' + sourcefile)
        raise sys.exc_info()[1]
    
    c = Collection()
    for var,entry in namespace.items():
        if issubclass(type(entry), Entry):
            if verbose:
                sys.stdout.write('load: found entry: ' + entry.name + '\n')
            entry.sourcefile = sourcefile
            c.add(entry)
        elif isinstance(entry, Collection):
            c.add(entry)
    return c


def loadbib(target, verbose=False):
    if isinstance(target,str):
        if verbose:
            sys.stdout.write('load: opening file: ' + target + '\n')
        with open(target,'r') as ff:
            return loadbib(ff, verbose=verbose)

    output = []

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
                output.append(newentry)
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
        sys.stderr.write('        type: {}\n  entry name: {}\n        item: {}\n\n'.format(activetype, activename, activeitem))
        sys.stderr.write('  Check for an unclosed bracket or quote?\n\n')
        raise Exception('loadbib: Unexpected end-of-file.')
        
    return output
