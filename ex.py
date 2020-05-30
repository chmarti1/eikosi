import pybib

entry = pybib.ArticleEntry('test:2020')

entry.author = pybib.AuthorList([['Christopher', 'Reed', 'Martin'], ['Leo', 'Sylvan', 'Martin']])
entry.title = 'My first example output'
entry.journal = 'Home code'
entry.year = 2020
