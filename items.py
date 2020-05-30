#
# ITEMS.PY
#
#   Provides classes and tools for special items in bibliographic entries.
#   As of v0.0, the only item class is AuthorList.
#


__version__ = '0.0'

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

