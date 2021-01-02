[up](../README.md)  
2. __Use__  
3. [Entries](entries.md)  
4. [Collections](collections.md)  

# 2. <a name=top></a> Use

This section is devoted to how Eikosi allows you to interact with existing collections.  For this section, there are three important vocabulary words:  
- An __entry__ is a single bibliographic record e.g. for a book, article, website, etc...  
- An __item__ is a single piece of data that is part of an entry, e.g. the author, title, journal, etc...  
- A __collection__ is a group of entries and other collections.  
- A collection is a __child__ of a __parent__ collection if it the former is directly linked from the latter.  
- An entry is a __member__ of a collection if it is directly linked to that collection.  
- A collection __belongs__ to (or is __contained__ by) a parent collection if it is a child of the parent or any other collection that __belongs__ to the parent (yes, this is a recursive definition).  
- An entry __belongs__ to (or is __contained__ by) a parent collection if it is a member of it or any collection that belongs to it.  

## Outline

[2.1. Loading](#load)
[2.2. Collections](#explore)
[2.3. Entries](#entries)
[2.4. Edits](#edits)
[2.5. Exporting](#export)


## <a name=load></a> 2.1 Loading
The `eikosi.load()` function is used to import Eikosi data as a `MasterCollection`.   This example imports the example repository in the `example` directory of the `eikosi` package.  The `eikosi.load()` function can accept a path to a directory, a path to a `.eks` file, or a file descriptor of an open `.eks` file.  

```python
>>> import eikosi as ek
>>> ex = ek.load('eikosi_package_dir/example')
MasterCollection.load: Unrecognized collection in entry: eikosi:2020
    Creating collection: eikosi
```

To construct the `MasterCollection` object that it returns, `eikosi.load()` dives into the directory and parses each `.eks` file it finds, importing all of the `Collections` and the various entries defined there.  That process is described more in the [collections](collections.md) section.  The warning printed in the example above alerts us that a collection was created by an entry instead of explicitly with a Collection or SubCollection constructor.  That's nothing to worry about for now.

[top](#top)

## <a name=explore></a> 2.2 Collections

__Listing Collections__  

The collection tree (collections belonging to collections) can be viewed using the `listchildren()` method.  In this example, there are three top-level `Collection` children defined in `example/000.eks`: equipment, fabric, and fiber.  There is a fourth top-level child `Collection`, "eikosi," which was created (implicitly) when it was called out in `eikosi.eks`.  That process is disucssed more in [.eks Files](eks.md).  

```plaintext
>>> ex.listchildren(deep=False)
main (9)
|-> eikosi (1)
|-> equipment
|-> fabric
'-> fiber (1)
```

We can access these child collections as attributes (object notation) or using the `getchild()` method.  Each of them can have children of their own.  For example, the "equipment" `Collection` contains `SubCollections` called "hook," "loom," "needle," and "shuttle."

```plaintext
>>> ex.equipment
Collection('equipment')
>>> ex.getchild('equipment')
Collection('equipment')
>>> ex.equipment.listchildren(deep=False)
equipment
|-> hook (1)
|-> loom
|-> needle (3)
'-> shuttle (1)
```

The numbers that appear next to each collection shows the number of [member](#top) entries in that collection.  Notice that the equipment collection does not appear to have any entries, but its children do.  A `Collection` or `SubCollection` [contains](#top) all the entries that belong directly to it and all of its children, so even if a collection appears empty, it may still "contain" a number of bibliographic entries.  

__The deep Keyword__

The various methods have a number of keyword options that allow the user to adjust their behavior.  These are documented in their in-line documentation, but the `deep` keyword is common to many methods, so it deserves a mention here.  In all the examples above, we've set the `deep` keyword to False when we use `listchildren()`, so only the children of the collection are shown; children of children are not shown.  On the other hand, we did not use the `deep` keyword when calling the `getchild()` method, so the entire tree was included in the retrieval.

When we leave off the `deep` keyword or set it to `True`, we see the entire collection tree all at once.

```plaintext
>>> ex.listchildren()
main (9)
|-> eikosi (1)
|-> equipment
|   |-> hook (1)
|   |-> loom
|   |-> needle (3)
|   '-> shuttle (1)
|-> fabric
|   |-> crocheted (1)
|   |   |-> fiber (1)
|   |   |   |-> silk (1)
|   |   |   |-> synthetic
|   |   |   |   |-> acrylic (1)
|   |   |   |   |-> nylon (1)
|   |   |   |   '-> polyester (1)
|   |   |   '-> wool (1)
|   |   |-> hook (1)
|   |   '-> needle (3)
|   |-> felted
|   |   '-> fiber (1)
|   |       '-> ...
|   |-> knitted (1)
|   |   |-> fiber (1)
|   |   |   '-> ...
|   |   '-> needle (3)
|   |-> knotted (1)
|   |   |-> fiber (1)
|   |   |   '-> ...
|   |   '-> shuttle (1)
|   |-> tatted (1)
|   |   |-> fiber (1)
|   |   |   '-> ...
|   |   |-> hook (1)
|   |   |-> needle (3)
|   |   '-> shuttle (1)
|   '-> woven
|       |-> fiber (1)
|       |   '-> ...
|       |-> loom
|       '-> shuttle (1)
'-> fiber (1)
    '-> ...
```

Notice that each of the "fabric" `SubCollection` instances also contains the entire "fiber" `Collection`.   Collections can be children of multiple others and they can even belong to themselves.  Similarly, the children of "equipment" can be found distributed throughout in ways that might be useful to a reader.

All of the background algorithms that interact with collections have protections against potential infinite searches caused by loops in the collection tree.  Those same protections cause the `listchildren()` method to merely print elipses (...) rather than repeat the tree beneath a colleciton that has already been displayed.

__Retrieving Collections__  

There is one significant difference between the `getchild` and object notation methods for accessing collections.  The `getchild()` method descends into the collection tree for any collection that [belongs](#top) to the parent with a matching name.  Notice in the example below, that "silk" is not a child of the `MasterCollection`, but it is a child of `fabric`, which is.  

```python
>>> ex.getchild('silk')
SubCollection('silk')
>>> ex.fiber.silk
SubCollection('silk')
>>> ex.silk
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/chris/Documents/eikosi/eikosi.py", line 1966, in __getattr__
    raise AttributeError(item)
AttributeError: silk
```

When a retrieval fails, the `getchild()` method returns `None` rather than raising an exception.  This allows the user to decide how to handle the failure.

The `getchild()` also offers a `deep` keyword to suppress recursion into child collections.

__Testing Collection Membership__  

The `haschild()` method tests for membership of a child collection.  It is rouhgly equivlaent to `c.getchild(name) is not None`.  The `haschild()` method also has a `deep` keyword to suppress recursion into child collections.

[top](#top)

## 2.3 Entries

__Listing Entries__

The entry contents of a `MasterCollection`, `Collection`, or `SubCollection` can be explored using the `list()` method just like `listchildren()` allowed us to explore collections.  A collection of any type automatically [contains](#top) all of the entries and collections belonging to it and all of its children.

```python
>>> ex.list()
~
Listing entries in collection: main
~
article:2020
book:2017
conference:2019
eikosi:2020
masters:2017
patent:2016
phd:2015
report:2014
website:2018
```
In this example, there aren't many entries.  A more expansive collection might occupy the entire screen in multiple columns.  The list shows the name of each entry, which, in this case, is the type and year separated by a colon.

By default, they are sorted by author, but they can be rearranged by any bibliographic item.  The `by` keyword can be set to the string name of any bibliographic item (e.g. "year", "author", "title", "journal", etc.).  Any entries that do not have that item will appear last.

Each of these is created by a file in the `example` directory.  By definition, the `MasterCollection` always contains all of the entries anywhere in the collection.  That is not true once we descend into the collection tree.

```python
>>> ex.fiber.list()
~
Listing entries in collection: fiber
~
article:2020
conference:2019
masters:2017
report:2014
website:2018
```

In the examples above, we saw that the "fiber" collection only had one member, but here we see that it has five contents (including all the members of contained collections.  We can see the members by using the `deep` keyword just like in the `listchildren()`.

```python
>>> ex.fiber.list(deep=False)
~
Listing entries in collection: fiber
~
article:2020
```

__Retrieving Entries__

The entries can be retrieved using the `get()` method.

```python
>>> ex.get('article:2020')
ArticleEntry('article:2020')
>>> ex.fiber.get('article:2020')
ArticleEntry('article:2020')
```

The `get()` method recurses into all child collections until a matching name is found or the possibilities are exhausted.  To limit the retrieval to only members of the collection, use `get(deep=False)`.  To make retrieval faster for the `MasterCollection`, it maintains an authoritative dictionary of all entries in the entire colleciton so recursion is not necessary, and the `deep` keyword has no effect.  

__Interacting with Entries__

Entries can be viewed using a `print()` statement, `str()` conversion, or written to plain text files using `write_txt()`.  They can be exported as BibTeX entries using the `write_bib()` method.  They can also generate the code for an `.eks` file that could be used to re-generate the entry using the `write()` method.

```
>>> entry = ex.get('article:2020')
>>> print(entry)
Art A. Author, An astonishingly abstract allegory, Sense and nonsense,
12(4), 115-128, 2020.

>>> entry.write_bib()
@ARTICLE{article:2020,
  author = {Art A. Author},
  title = {An astonishingly abstract allegory},
  journal = {Sense and nonsense},
  year = {2020},
  pages = {115-128},
  volume = {12},
  number = {4},
}

>>> entry.write()
import eikosi

entry = eikosi.ArticleEntry('article:2020')
entry.author = eikosi.AuthorList([['Art', 'Article', 'Author']])
entry.title = 'An astonishingly abstract allegory'
entry.journal = 'Sense and nonsense'
entry.year = 2020
entry.pages = '115-128'
entry.volume = 12
entry.number = 4
entry.collections = ['fiber', 'silk', 'needle']
```

All of the `write_XXX()` methods accept a `target` keyword which can be used to redicrect output from `stdout` to a file.  See their in-line documentation for details.

Note that the `entry.collections` attribute is set to a list of collection names.  The process of assigning collection membership at load time is discussed in the `load()` documentation in the [collections](collections.md) section.

[top](#top)

## 2.4 <a name=edit></a> Edits

The user is free to make whatever edits are appropriate from the command line.  For example, what if we wanted to check and then change the title of the book entry?  The individual items are available as attributes.

```python
>>> entry = ex.get('book:2017')
>>> print(entry)
Bryan Brant, Britany Brown, Buying Buoyant Bottles, 2nd, Blotting
Brothers, Boston, 2018.

>>> entry.title
'Buying Buoyant Bottles'
>>> entry.title = 'Binding Bothersome Books'
>>> # Make the change permanent
>>> entry.write(target='example/book.eks')
```

Entry membership can be changed using the `add()` or `remove()` methods.  Collection membership can be changed using the `addchild()` or `removechild()` methods.  This is addressed in more detail in the [entries](entries.md) and [collections](collections.md) sections.

[top](#top)

## 2.5 Exporting

There are two methods for exporting entire collections: (1) saving the collection into `.eks` files using `save()`, and (2) saving the collection to a BibTeX file using `save_bib()`.  

__save__

Saving can only be performed by a `MasterCollection`.  When the `save()` method is evoked, it builds `.eks` files that, when loaded, create an identical `MasterCollection`.  This can be used to make edits permanent, and it is an alternative to editing the `.eks` files manually.

When `save()` is evoked with a path to a file name or a file descriptor of an open file, all of the entries and collections are written to a single file.  This mode of operation is useful for exporting an entire `MasterCollection` in a way that is portable.

```python
>>> ex.save('/path/to/file.eks')
>>> ex2 = ek.load('/path/to/file.eks')
>>> # This process creates a second identical MasterCollection, ex2
```

When `save()` is evoked with a path to a directory, each entry is given its own `.eks` file, and collections are stored in a file named `000.eks`.  This mode of operation is useful when collections of entries are dispersed in a directory tree along with their corresponding pdfs.

```python
>>> ex.save('/path/to/dir')
>>> ex3 = ek.load('/path/to/dir')
>>> # This process creates a third identical MasterCollection, ex3
```

__savebib__

The contents of any collection (`MasterCollection`, `Collection`, or `SubCollection`) can be exported to a BibTeX database using the `savebib()` method.  The argument should be the path to the `.bib` file to create or overwrite.

```python
>>> # Save the entire MasterColleciton
>>> ex.savebib('example.bib')
>>> # Save only the fiber collection
>>> ex.fiber.savebib('fiber.bib')
```

[top](#top)