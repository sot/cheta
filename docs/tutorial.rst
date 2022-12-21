.. include:: references.rst

================================
Ska Analysis Tutorial
================================

Overview
--------

This document gives a tutorial introduction to analysis using the Ska analysis
environment, including basic configuration and a number
of examples.

The Ska analysis environment consists of a full-featured Python installation with
interactive analysis, plotting and numeric capability along with the Ska engineering
telemetry archive.

The telemetry archive consists of:

* Tools to ingest and compress telemetry from the CXC Chandra archive products.
* Compressed telemetry files in HDF5 format.  Each MSID has three associated products:

  - Full time-resolution data: time, value, quality
  - 5-minute statistics: min, max, mean, sampled value, number of samples
  - Daily statistics: min, max, mean, sampled value, standard deviation, percentiles (1,
    5, 16, 50, 84, 95, 99), number of samples.


Configure
-----------------------------

To set up for using the Ska3 environment, visit the `Ska3 configuration hints
<https://github.com/sot/skare3/wiki/Ska3-runtime-environment-for-users#configuration-hints>`_
page.

Basic Functionality Test
----------------------------------------------

Once you have done the configuration setup that was just described, open a new
xterm window and get into the Ska3 environment by use the ``ska3`` alias::

  % ska3

To test the basic functionality of your setup, try the following at the linux
shell prompt.  In this tutorial all shell commands are shown with a "% "
to indicate the shell prompt.  Your prompt may be different and you should
not include the "% " when copying the examples.::

  % ipython --matplotlib

You should see something that looks like::

  Python 3.8.3 (default, Jul  2 2020, 11:26:31)
  Type 'copyright', 'credits' or 'license' for more information
  IPython 7.16.1 -- An enhanced Interactive Python. Type '?' for help.

  In [1]:

Now read some data and make a simple plot by copying the following lines in ``ipython``::

  import cheta.fetch as fetch
  import matplotlib.pyplot as plt
  tephin = fetch.MSID('tephin', '2009:001', '2009:002')
  plt.plot(tephin.times, tephin.vals)

You should get a figure like:

.. image:: fetchplots/basic_func.png

Tools overview
----------------------------------------------
There are four key elements that are the basis for doing plotting and analysis
with the engineering archive.

* cheta.fetch: module to read and manipulate telemetry data
* `IPython`_: interactive python interpreter
* `matplotlib`_: python plotting package with an interface similar to Matlab
* `NumPy`_: python numerical package for fast vector and array math

cheta.fetch
~~~~~~~~~~~~~~~~~~~~~~
The tools to access and manipulate telemetry with the Ska engineering archive
are described in the :doc:`fetch_tutorial`.

IPython
~~~~~~~~~~
`IPython`_ is a command-line tool that provides a python prompt
that is the basis for interactive analysis.  At the core it provides
an interpreter for python language commands but with the addition of
external packages like `matplotlib`_ and `numpy`_ it becomes a full-featured
data analysis environment.  `IPython`_ is similar in many ways to the command-line interface in Matlab or IDL.

See the `IPython documentation page <https://ipython.readthedocs.io/en/stable/>`_.

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
