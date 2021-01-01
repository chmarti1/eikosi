[up](../README.md)
2. [Use](docs/use.md)  
3. __ENTRIES__
4. [Collections](docs/collections.md)  

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

[top](#top)

## 3.3 <a name=book></a> BookEntry

[top](#top)

## 3.4 <a name=conference></a> ConferenceEntry

[top](#top)

## 3.5 <a name=manual></a> ManualEntry

[top](#top)

## 3.6 <a name=misc></a> MiscEntry

[top](#top)

## 3.7 <a name=patent></a> PatentEntry

[top](#top)

## 3.8 <a name=phd></a> PhdEntry

[top](#top)

## 3.9 <a name=proceedings></a> ProceedingsEntry

[top](#top)

## 3.10 <a name=report></a> ReportEntry

[top](#top)

## 3.11 <a name=web></a> WebsiteEntry

[top](#top)

