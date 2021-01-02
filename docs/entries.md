[up](../README.md)  
2. [Use](use.md)  
3. __Entries__
4. [Collections](collections.md)  

# 3. Entries

Each __entry__ references a single bibliographic source (e.g. a book, article, website, etc...).  Special classes are defined for each different type of bibliographic entry, but each is descended from the `Entry` prototype class.  

__Outline__  

1. [Entry Prototype](#entry)  
    1. Attributes
    2. Methods
    3. AuthorList Class
    4. Month Class
2. [ArticleEntry](#article)  
3. [BookEntry](#book)  
4. [ConferenceEntry](#conference)  
5. [ManualEntry](#manual)  
6. [MastersEntry](#masters)  
6. [MiscEntry](#misc)  
7. [PatentEntry](#patent)  
8. [PhdEntry](#phd)  
9. [Proceedings](#proceedings)  
10. [ReportEntry](#report)  
11. [WebsiteEntry](#web)  


## 3.1 <a name=items></a> The Entry Prototype

The `eikosi.Entry` class is the prototype for all other entry classes.  It should not be used itself, but it defines the structure for all of the other entries.

__Attributes__  

Regardless of type, all entries have built-in attributes:  

| Attribute | Description |
|:---------:|:------------|
|`bib` | a dicitonary of all bibliographic items in the entry |
|`collecitons` | a list of the colleciton names to which the entry should be added at load time.|
|`doc` | an optional string for user notes |
|`docfile` | an optional path to a pdf copy of the document being | referenced.|
|`name` | the string name of the entry|
|`mandatory` | a set of mandatory bibliographic items|
|`optional`| a set of recognized but optional bibliographic items |
|`sourcefile`| the path to the .eks file from which the entry was loaded (if any)|
|`tag` | the tag used to start a BibTeX entry (e.g. @ARTICLE)|

Reading or writing to other attributes are redirected to/from the `bib` dictionary, so that bibliographic items can be directly accessed as attributes.  For example,
```python
>>> entry.title = 'This is a title'
>>> print(entry.bib['title'])
This is a title
```
is equivalent to
```python
>>> entry.bib['title'] = 'This is a title'
>>> print(entry.title)
This is a title
```
Be careful, though, because the built-in attributes will always have precedence.
```python
>>> entry.bib['collections'] = ['foo', 'bar']
>>> entry.collections
[]
>>> entry.bib['collections']
['foo', 'bar']
```

Most bibliographic entries are simple strings or integers (e.g. a title or a volume number), but there are special data types for "author" and "month" entries that allow them to be more flexible in how they are displayed and loaded.

__Methods__

All entry instances have certain essential methods:

| Method | Description |
|:------:|:------------|
|`post()`| Perform post-processing checks and type conversions on the entry's bibliographic items |
|`write()`| Write Python code appropriate for outputting to an .eks file |
|`write_bib()`| Writes a complete BibTeX entry appropriate for building .bib files|
|`write_txt()`| Writes formatted human-readable citation |

<a name=authorlist></a>
__AuthorList Class__

To assist with parsing author names into parts for alphabetization, searching, and building appropriately formatted strings, the `AuthorList` class is used to process all `author` items in all entries.  An `AuthorList` instance accepts author names in four formats:  

(1) in a BibTeX style and-separated string 
```python
>>> a = eikosi.AuthorList('Albert Baker and Christina Delfonte')
```

(2) as a list of individual authors
```python
>>> a = eikosi.AuthorList(['Albert Baker', 'Christina Delfonte'])
```

(3) as a nested list breaking each author's name into parts
```python
>>> a = eikosi.AuthorList([['Albert', 'Baker'], ['Christina', 'Delfonte']])
```

(4) as another `AuthorList` object
```python
>>> b = eikosi.AuthorList(a)
```

In `post()` method of each entry class that has an `author` item, the data is passed directly to an `AuthorList` class, so these form the legal formats for an `author` item entry.

An `AuthorList` is assembled for BibTeX entries using `str()`, they are assembled into Python code for saving in `.eks` files using `repr()`, and they are assembled into formatted strings using their own `show()` method.

```python
>>> str(a)
'Albert Baker and Christina Delfonte'
>>> repr(a)
"AuthorList([['Albert', 'Baker'], ['Christina', 'Delfonte']])"
>>> a.show()
'Albert Baker, Christina Delfonte'
>>> a.fullfirst=False
>>> a.show()
'A. Baker, C. Delfonte'
```

The behavior of `show()` is changed by the `fullfirst` and `fullother` attributes.  These may be set by identically named keywords during initialization (e.g. `AuthorList(..., fullfirst=False)`) or they may be changed directly as above.  When they are set to `False`, the first and middle (other) names will be replaced by their leading initial.  This supports names with many more than three parts, but only the first name is given special treatment.

<a name=month></a>
__Month__

Months in dates pose an awkward challenge since they can be expressed as an integer (1-12), an abbreviation (Jan-Dec), or in full (January-December).  The `Month` class initializer can accept:  

(1) an integer from 1 to 12
```python
>>> m = eikosi.Month(11)
```

(2) the month name in full (spelling must be correct, but case is irrelevant)
```python
>>> m = eikosi.Month('nOveMbeR')
```

(3) the three-letter month abbreviation (trailing "." and case are irrelevant)
```python
>>> m = eikosi.Month('nov.')
```

Just like the `AuthorList` class, the `Month` class is assembled for BibTeX entries using `str()`, they are assembled into Python code for saving in `.eks` files using `repr()`, and they are assembled into formatted strings using their own `show()` method.

[top](#top)

## 3.2 <a name=article></a> ArticleEntry

`AuthorEntry` instances export to the `@ARTICLE` tag  in BibTeX.  They are intended to represent journal articles or articles in other periodicals.

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| title | `str` | - | |
| journal | `str` | - |  |
| volume | - | `int` | volume OR number is mandatory |
| number | - | `int` | volume or number is mandatory |
| year | - | `int` | |
| pages | `str` | - | Supports range or number (e.g. '12-24' or 12) |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |

[top](#top)

## 3.3 <a name=book></a> BookEntry

`BookEntry` instances export to the `@BOOK` tag in BibTeX.  They are intended to represent books.

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| title | `str` | - | |
| publisher | `str` | - |  |
| address | `str` | - |  |
| year | - | `int` | |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| edition | `str` | - |  |

[top](#top)

## 3.4 <a name=conference></a> ConferenceEntry

`ConferenceEntry` instances export to the `@INPROCEEDINGS` tag in BibTeX.  They are intended to represent conference presentations or papers.  See also the [ProceedingsEntry](#proceedings).

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| title | `str` | - | |
| booktitle | `str` | - | The name of the conference/proceedings |
| address | `str` | - |  |
| year | - | `int` |  |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| series | `str` | - |  |
| pages | `str` | - |  |
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |
| day | - | `int` |  |

[top](#top)

## 3.5 <a name=manual></a> ManualEntry

`ManualEntry` instances export to the `@MANUAL` tag in BibTeX.  They are intended to represent equipment manuals, technical manuals, standard operating proceedures, or other documents that are not published through traditional academic channels but may be of importance.

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| title | `str` | - | |
| organization | `str` | - | The company or institution |
| year | - | `int` |  |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| address | `str` | - |  |

[top](#top)

## 3.6 <a name=masters></a> MastersEntry

`MastersEntry` instances export to the `@MASTERSTHESIS` tag in BibTeX.  They are intended to represent masters' theses.

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| title | `str` | - | |
| school | `str` | - | The name of the university |
| year | - | `int` |  |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| address | `str` | - |  |
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |
| day | - | `int` |  |

[top](#top)

## 3.7 <a name=misc></a> MiscEntry

`MiscEntry` instances export to the `@MISC` tag in BibTeX.  These are catch-all types for entries that are not explicitly supported.  See also [PatentEntry](#patent) and [WebEtry](#web).

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| title | `str` | - | |
| howpublished | `str` | - | A string naming the source (e.g. "website", "book", "interview", etc.) |
| year | - | `int` |  |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| note | `str` | - | Anything else? (e.g. patent #, URL, DOI, etc.) |
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |
| day | - | `int` | |

[top](#top)

## 3.8 <a name=patent></a> PatentEntry

`PatentEntry` instances export to the `@MISC` tag in BibTeX.  They are intended to represent patents.  Though some widely used BibTeX styles support patent tags, the entry type is not standardized across BibTeX.  Instead, it is more stable to use the `@MISC` tag.  See also [MiscEntry](#misc) and [WebEtry](#web).

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | Inventors; See the [AuthorList](#authorlist) documentaiton |
| title | `str` | - | |
| number | - | `str` | Patent, provisional, or application number |
| year | - | `int` |  |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| assignee | `str` | - | Similar to "organization" |
| nationality | `str` | - | |
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |
| day | - | `int` | |

[top](#top)

## 3.9 <a name=phd></a> PhdEntry

`PhdEntry` instances export to the `@PHDTHESIS` tag in BibTeX.  They are intended to represent PhD theses.

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| title | `str` | - | |
| school | - | `str` | The name of the university |
| year | - | `int` | |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| address | `str` | - | Similar to "organization" |
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |
| day | - | `int` | |

[top](#top)

## 3.10 <a name=proceedings></a> ProceedingsEntry

The `ProceedingsEntry` is merely a pointer to the `ConferenceEntry`, so evoking it will create a `ConferenceEntry` instance.  See the [ConferenceEntry](#conference) documentation for use.

[top](#top)

## 3.11 <a name=report></a> ReportEntry


`ReportEntry` instances export to the `@TECHREPORT` tag in BibTeX.  They are intended to represent reports (e.g. laboratory reports) that may be internal to an organization or may not otherwise have been published through academic channels.

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| title | `str` | - | |
| year | - | `int` | |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| number | `str`, `int` | - | Many institutions use report number systems |
| institution | `str` | - | Company or organization name |
| address | `str` | - |  |
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |
| day | - | `int` | |

[top](#top)

## 3.12 <a name=web></a> WebsiteEntry

`WebsiteEntry` instances export to the `@MISC` tag in BibTeX.  They are intended to represent websites.  Because these are not static entities, it is important to name the date at which the data were accessed.  Though some widely used BibTeX styles support a website entry, the style is not standardized across BibteX, so it is more stable to use the `@MISC` tag.  See also ([MiscEntry](#misc) or [PatentEntry](#patent)).

These tables show the _mandatory_ and _optional_ items in this entry.  Mandatory items are required in order for a bibliographic display to be constructed using the `write_txt()` method.  Optional items are recognized by `write_txt()` but not required.  Items not in the table will still be recorded and exported to BibTeX and `.eks` files, but they are ignored otherwise.

The "stored as" column of each table names the data type that is used to store the item after the entry's `post()` method has been run.  In each case, the data there will be passed to the type's constructor (e.g. an "author" item will be stored as `self.author = AuthorList(self.author)`).  If the "stored as" column is empty, then the item is not modified by `post()`.

The "expects" column lists the data types that may be written to the item for the entry to display properly.  If it is blank, then it may be any data type recognized by the "stored as" type.  If the "stored as" column is blank, then Eikosi depends on the user to set the type correctly.

__Mandatory Items__  

| Item | Expects | Stored as | Description |
|:----:|:-------:|:-------:|:-------------|
| url | `str` | - | The unique resource locator (URL) or the website |
| year | - | `int` | |
| month | `str`, `int`, `Month` | `Month` | See the [Month](#month) documentaiton |

__Optional Items__  

| Item | Expects | Stored as |  Description |
|:----:|:-------:|:-------:|:-------------|
| title | `str` | - | |
| author | `str`,`list`,`AuthorList` | `AuthorList` | See the [AuthorList](#authorlist) documentaiton |
| day | - | `int` | |
| institution | `str` | - | Company or organization name |



[top](#top)

