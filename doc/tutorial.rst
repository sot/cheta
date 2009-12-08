.. include:: references.rst

================================
Ska Engineering Archive Tutorial
================================

Overview
--------

This document gives a tutorial introduction to the Ska Engineering Archive,
including basic configuration and a number of examples.

The telemetry archive consists of:

* Tools to ingest and compress telemetry from the CXC Chandra archive products.
* Compressed telemetry files in HDF5 format.  Each MSID has three associated products:

  - Full time-resolution data: time, value, quality
  - 5-minute statistics: min, max, mean, sampled value, number of samples
  - Daily statistics: min, max, mean, sampled value, standard deviation, percentiles (1,
    5, 16, 50, 84, 95, 99), number of samples.

* A python module to retrieve telemetry values.


Configure 
-----------------------------

The first requirement is to make sure that your local machine is set up to run
X11.  On a Microsoft windows PC that probably means having `Cygwin/X <http://x.cygwin.com/>`_
installed and running.  On a Mac you will need X11 installed.  If you don't
have this already the best option is to install X11.pkg from 
`<http://xquartz.macosforge.org/trac/wiki/Releases>`_.  From Linux you are
already set with X-windows.

To set up and to use the archive it is best to start with a "clean" environment
by opening a new X-terminal window.  It is assumed you are using ``csh`` or
``tcsh``.

The first step is to log in to the machine ``ccosmos`` on the HEAD LAN and
configure the Ska runtime environment and make a new xterm window with a black
background::

  ssh -Y <username>@ccosmos.cfa.harvard.edu
   <Enter password>
  xterm -bg black -fg green &

Now focus on the new xterm window and set up your path and various environment
variables so all the tools are accessible and use the correct libraries.::

  source /proj/sot/ska/bin/ska_envs.csh

If you have not used Python and matplotlib on the HEAD LAN before you should do the 
following setup to ensure that the right plotting backend (Tk) is used::

  mkdir -p ~/.matplotlib
  cp /proj/sot/ska/data/eng_archive/matplotlibrc ~/.matplotlib/

Basic Functionality Test
----------------------------------------------

To test the basic functionality of your setup, try the following at the linux
shell prompt.  In this tutorial all shell commands are shown with a "% "
to indicate the shell prompt.  Your prompt may be different and you should
not include the "% " when copying the examples.::

  % ipython -pylab
  
You should see something that looks like::

  Python 2.6.2 (r262:71600, Nov  2 2009, 16:06:12) 
  Type "copyright", "credits" or "license" for more information.

  IPython 0.10 -- An enhanced Interactive Python.
  ?         -> Introduction and overview of IPython's features.
  %quickref -> Quick reference.
  help      -> Python's own help system.
  object?   -> Details about 'object'. ?object also works, ?? prints more.

    Welcome to pylab, a matplotlib-based Python environment.
    For more information, type 'help(pylab)'.

  In [1]: 

Now read some data and make a simple plot by copying the following lines in ``ipython``::

  import Ska.engarchive.fetch as fetch
  tephin = fetch.MSID('tephin', '2009:001', '2009:002')
  plot(tephin.times, tephin.vals)
  
You should get a figure like:

.. image:: fetchplots/basic_func.png

Tools overview
----------------------------------------------
There are four key elements that are the basis for doing plotting and analysis
with the engineering archive.

* Ska.engarchive.fetch: module to read and manipulate telemetry data
* `IPython`_: interactive python interpreter
* `matplotlib`_: python plotting package with an interface similar to Matlab
* `NumPy`_: python numerical package for fast vector and array math

Ska.engarchive.fetch
~~~~~~~~~~~~~~~~~~~~~~
.. include:: fetch_tutorial.rst

IPython
~~~~~~~~~~
`IPython`_ is a command-line tool that provides a python prompt
that is the basis for interactive analysis.  At the core it provides
an interpreter for python language commands but with the addition of 
external packages like `matplotlib`_ and `numpy`_ it becomes a full-featured
data analysis environment.  `IPython`_ is similar in many ways to the command-line interface in Matlab or IDL.

**Links**

* `Main documentation page <http://ipython.scipy.org/doc/manual/html/index.html>`_
* `Tutorial (newer) <http://ipython.scipy.org/doc/manual/html/interactive/tutorial.html>`_
* `Tutorial (older but good) <http://onlamp.com/pub/a/python/2005/01/27/ipython.html>`_

.. include:: ipython_tutorial.rst

NumPy
~~~~~~~~
Even though it was not explicit we have already been using `NumPy`_ arrays in
the examples so far.  NumPy is a Python library for working with
multidimensional arrays. The main data type is an array. An array is a set of
elements, all of the same type, indexed by a vector of nonnegative integers.

.. include:: numpy_tutorial.rst

Matplotlib
~~~~~~~~~~~
.. include:: matplotlib_tutorial.rst

