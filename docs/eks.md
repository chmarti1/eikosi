# 5 .eks Files

Eikosi's data are stored in files with the `.eks` extension.  These files are merely python code that will be loaded and executed by the `eikosi.load()` function.  It is important to emphasize that, while convenient, this is a potential security risk.  Never load `.eks` files that you do not trust!

1. [Conventions and Rules](#rules)
2. [Writing Manually](#manual)
3. [Writing Automatically](#auto)

## 5.1 <a name=rules></a> Conventions and Rules

Data from collections and entries may be split across many `.eks` files or concentrated in a single large file.  It is the design intent that all collecitons be defined in a single file and that each entry be defined in its own `.eks` file, but there is nothing to enforce that.  After the  `eikosi.load(...)` funciton executes each `.eks` file, all `Collection` instances and all types of entries are added as members to the `MasterCollection`.

For example, `example/article.eks` appears
```
import eikosi as ek

# The variable name is irrelevant.
entry = ek.ArticleEntry('article:2020')
# required
entry.author = 'Art Article Author'
entry.title = 'An astonishingly abstract allegory'
entry.journal = 'Sense and nonsense'
entry.year = 2020
entry.pages = '115-128'
# optional (volume OR number required)
entry.volume = 12
entry.number = 4
entry.collections = ['fiber', 'silk', 'needle']
```

