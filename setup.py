#!/usr/bin/env python

from distutils.core import setup

setup(name='grizzly',
      version='0.0.2',
      description='Grizzly Bear USB Drivers',
      author='Pioneers in Engineering',
      author_email='engineeringcoordinator@pioneers.berkeley.edu',
      url='http://www.github.com/pioneers/python-grizzly',
      packages=['grizzly'],
      requires=['pyusb'],
      data_files=[('/etc/udev/rules.d', ['grizzly/50-grizzlybear.rules'])],
     )
