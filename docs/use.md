[up](../README.md) 
[next](eks.md)

# 2. <a name=top></a> Use

### 2.1 Loading Collections
The `load` function is used to import Eikosi data as a MasterCollection.

```python
>>> import eikosi as ek
>>> mc = ek.load('/path/to/directory/')
```
To construct the `MasterCollection` object, `load()` dives into the directory and parses each `.eks` file it finds.  That process is described more in the [.eks Files](eks.md) section.

[top](#top)

### 2.2 Exploring Collections

The entries can be listed by name using the `list()` method.  They can also be sorted by other bibliographic items (like year or journal) using list's `by` keyword.  To see the other parameters that let you configure the behavior of `list()`, view the method's help documentation, `help(mc.list)`.

```python
>>> mc.list()
~
Listing entries in collection: main
~
anderson:patent:1960    henein:2010             martin:patent:2018      
andreasson:2005         holm:1999               martin:plate            
andrews:1972            holzl:1979              martin:wj:2017          
badawy:2012             hu:2000                 mason:1988              
...


>>> mc.list(by='year')
~
Listing entries in collection: main
~
thompson:1906           clements:1970a          roland:2012              
richardson:1916         fissan:1971             weinberg:2013           
wilson:1916             andrews:1972            martin:flamesense1      
langmuir:1923           clements:1973           platvoet:2013           
...

```

The collections that belong to the `MasterCollection` can be viewed using the `listchildren()` method.

```python
>>> mc.listchildren()

```

[top](#top)