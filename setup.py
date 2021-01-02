import setuptools
import eikosi
import os

long_description = """The Eikosi citation management system is much like other citation management 
systems; it lets you organize your citations into collections and it generates 
Bibtex databases on request.  There are a few big differences:

- All entries and meta data are saved in human-readable Python scripts  
- There is a collection system that allows structured keyword organization  
- The interface is designed to be used from the Python command line  

When I find a new pdf I want to include, I download it into a folder.  I have 
a special set of directories in my home directory where I keep all the papers 
and reference guides that are important to me --- everything from hardware 
manuals to journal articles.  

As I read the new pdf, I construct an `.eks` file with all the important 
bibliographic information.  If there are important details I want to remember, 
I add notes and reminders to myself in that file.  Then, when I'm done, I add 
the file to the appropriate collections.  

Later, when I'm writing a paper of my own and I remember I have a citation 
that would be great, I call up Eikosi and load up all the `.eks` files in my 
collection and I search them for the one I'm looking for.  

Eikosi also lets me import from and export to bibtex `.bib` files.  That's a 
big deal for me because I've tried maintaining my citations natively in bibtex 
format, but invariably, I wind up with contradictory copies of bib files 
floating around in different directories.  Corrections to erroneous or out-of-
date files don't always get copied correctly.  

With Eikosi, the record for each bibliography entry only lives in one place, 
so changes to it will be universally applied from then on.  
"""

data_files = [os.path.join('example', this) for this in os.listdir('example')]

setuptools.setup(
    name="eikosi",
    version=eikosi.__version__,
    author="Christopher R. Martin",
    author_email="crm28@psu.edu",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license = "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    url="https://github.com/chmarti1/eikosi",
    #packages=['eikosi'],
    py_modules = ['eikosi'],
    data_files = [('example', data_files)],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Topic :: Database",
    ],
    python_requires='>=3.0',
)
