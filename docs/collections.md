[up](../README.md)  
2. [Use](use.md)  
3. [Entries](entries.md)  
4. __Collections__  

# 4. Collections

Collections serve as the basic "containers" for groups of entries.  A collection can contain any number of entries, and it can also contain other collections.  An introduction to that system is given in [2. Use](#use.md).

## Outline  

1. [The ProtoCollection](#proto)  
    1. Attributes  
    2. Child Collections  
    3. Methods  
    4. Iterating  
2. [The MasterCollection](#master)  
    1. Rules  
    2. Loading  
    3. Saving  
    4. Special Methods  
3. [The Collection](#collection)  
4. [The SubCollection](#sub)  

## 4.1. The ProtoCollection

Though it is never intended to be used directly, the `ProtoCollection` is the parent class for all of the collection types.  It provides most of the attributes and methods that are common to all of the collection classes: `Collection`, `SubCollection`, and `MasterCollection`.

__Attributes__  

None of the collections' attributes are intended to be edited directly.  Only the methods that "write" to collections should ever be used to change them.  For example, there is nothing preventing a user from writing to the `name` attribute with a new string, but now the collection's name would disagree with its listing in every other collection that references it.

Attributes that begin with an underscore (`_`) should be considered private; they should not be accessed direclty.  instead, there are methods for accessing these data.

| Attribute | Description |
|:---------:|:------------|
| `doc` | An optional document string for user description or notes |
| `master` | A pointer to the collection tree's `MasterCollection` |
| `name` | The colleciton's name |
| `sourcefile` | A path to the `.eks` that defined this collection (if any) |
| `_children` | A dictionary of collections that belong to this collection |
| `_entries` | A dictionary of the entries that belong directly to this colleciton |
| `_iflag` | A boolean flag used to "lock" collections during iteration |
| `_sorted` | A record of the results of prior calls to `sort()` |

__Child Collections__  

Collections that belong to a __parent__ colleciton are called __children__.  A child collection can be accessed directly by its name as if it were an attribute.

```python
>>> parent.child
SubCollection('child')
```

This approach to accessing children has obvious advantages, but it causes problem if there is a name collision with one of the build-in attributes (e.g. `doc` or `name`) or if special characters are included in the name (e.g. ':' or '-').  For that reason (and others), the `getchild()` method may be better suited to retrieving children in general.

__Methods__

All collection instances have certain essential methods.  For details about their use, access their in-line documentation using `help()`.

| Method | Description |
|:------:|:------------|
| `add()` | Add an entry to the colleciton |
| `addchild()` | Add a child collection to this parent collection |
| `collecitons()` | Spawn an iterator over all collections that belong to this colleciton |
| `copy()` | Spawn a copy of this collection with identical contents |
| `createchild()` | Create a `SubCollectoin` and add it as a child to this parent |
| `duplicates()` | Form a list of possible duplicate entries in the colleciton |
| `find()` | Search for an entry by certain criteria (not implemented) |
| `flatten()` | Add the entries of all children to the parent's entry dictionary |
| `get()` | Return a entry by its name |
| `getchild()` | Return a child collection by its name |
| `has()` | Test whether an entry belongs to the collection |
| `haschild()` | Test whether a child collection belongs to the collection |
| `list()` | Print a formatted list of all entries in the collection |
| `listchildren()` | Print a formatted list of all children in the collection |
| `merge()` | Bring in a `MasterCollection` as a child of this collection |
| `remove()` | Remove an element from this collection |
| `removechild()` | Remove a child collection from this parent |
| `savebib()` | Export the entries in this collection to a BibTeX file |
| `sort()` | Return a list of entries sorted by the item specified |
| `write()` | Write an `.eks` file entry that constructs this collection |

__Iterating__

A collection is naturally an iterator over all the entries that belong to it.

```python
>>> for entry in collection:
>>>    # do things with entry ...
```

When iterating over `Colleciton` and `SubCollection` instances, the same entry might appear multiple times if it is a member of multiple collections.  This is not an issue with `MasterCollection` instances.  If it is important to avoid this behavior, the `sort()` method should be used, which automatically deduplicates.

```python
>>> for entry in colleciton.sort('name'):
...     # do things with entry ...
```

Sorting can be computationally expensive, but since the results are stashed for later use, repeated calls to `sort()` are cheap.

Alternatively, it is also possible to micromanage the iteration process by iterating over the member collections themselves.  The `collections()` method returns a `CollectionIterator` instance, which iterates over all of the child collections of a parent.  It exposes optional keywords that adjust the behavior of the iteration with `True`/`False` values: `depthfirst` recurse to the bottom of the tree before working back to the top, `rself` exclude the parent from the iteration, `deep` include children of children.

```python
>>> parent.createchild('child_a').createchild('child_aa')
SubCollection('child_aa')
>>> parent.createchild('child_b').createchild('child_bb')
SubCollection('child_bb')
>>> parent.listchildren()
parent
|-> child_a
|   '-> child_aa
'-> child_b
    '-> child_bb
>>> # By default, iteration includes the parent and is depth-last
>>> for child in parent.collections():
...     print(child.name)
... 
parent
child_a
child_b
child_aa
child_bb
>>> # But that can be changed!
>>> for child in parent.collections(depthfirst=True,rself=False):
...     print(child.name)
... 
child_aa
child_a
child_bb
child_b
```

## 4.2 <a name=master></a> The MasterCollection

__Rules__  

`MasterCollection` instances have all the same abilities and properties as their counterparts, but there are some additional special rules that apply to them.  
1. A `MasterCollection` may not be a child of any other collection.  
2. Only `Collection` instances may be children of a `MasterColleciton`.  
3. If any entry belongs to any member collection (including children of children), it _must_ be directly joined to the `MasterCollection`.  

When these rules are obeyed, there is a unique `MasterCollection` at the top of a collection tree.  `SubCollections` and `Collections` may belong to one another, but only `Collections` are directly linked as children to the `MasterCollection`.

__Loading__

The `eikosi.load()` function creates an empty `MasterCollection` instance, and then calls its `load()` method.  The `eikosi.load()` function is described in [2.1 Use::Loading](use.md#load).  The `MasterCollection.load()` method is nearly identical, but it can be called multiple times to join multiple files or directories into a single `MasterCollection`.  See the `MasterCollection.load()` in-line documentation for more information.

When an `.eks` file is loaded, it is read and passed to `exec()`.  Never load an `.eks` file that is not trusted, because this can create security concerns.  The local variables declared in the script are scanned for children of `Entry` or `Collection` instances.  All entries and `Collection` instances are added to the `MasterCollection` directly.  `SubCollections` are ignored, so they _must_ be added as children to the `Collection` instances in the `.eks` files, or they will not be included in the collection tree.

Like saving, loading can be performed in one of two modes: single file or directory.  When the argument to `load()` is a path to a directory, every `.eks` file in the directory tree will be loaded recursively in single-file mode and the results will be aggregated into the `MasterCollection`.  When the argument is a path to a file or a file descriptor, only that file is parsed.

After loading is complete, the entries are scanned for non-empty lists in their `collections` attribute.  The list is presumed to contain string names of `Collection` or `SubCollection` instances to which the entry should belong.  This approach allows entries to nominate themselves for membership in collections rather than splitting that data across files.  By default, if these collecitons do not exist, they are created with a warning.

__Saving__

A `MasterCollection` has a unique `save()` method, that can be used to write `.eks` file(s) that, once loaded, would recreate the collection and its members.  There are two modes of operation: directory and single-file.  

When saving to a directory, each entry is assigned its own `.eks` file based on its name and all collections are written to `000.eks` by default.  The awkward name is deliberate so the collections `.eks` file will appear at or near the top of a directory listing.

When saving to a single `.eks` file, all collections and entires are written to a single file.  Especially for a collection of significant size, this can get ungainly for human editing, but it is extremely convenient for exporting and sharing collections with others.

__Special Methods__

Saving and loading are only two of the special methods that are unique to `MasterCollections`.  Here is a complete list of the public methods that are defined or redefined by the `MasterCollection` class.

| Method | Description |
|:------:|:------------|
| `add()` | Faster and simpler than the prototype `add()` method |
| `addchild()` | Requires a `Collection` instance |
| `get()` | Faster and simpler than the prototype `get()` method |
| `has()` | Faster and simpler than the prototype `has()` method |
| `load()` | Responsible for loading `.eks` files |
| `save()` | Responsible for saving `.eks` files |

## 4.3 <a name=collection></a>The Collection

A `Collection` instance is the only kind of colleciton 

## 4.4 <a name=subcollection></a>The SubCollection