
from setuptools import setup
from os import path
base_dir = path.abspath(path.dirname(__file__))
setup(
  name='lexz',
  packages=['lexz'],
  include_package_data=True,
  version='0.1',
  license='Apache-2.0',
  description='Time traveler for obfuscation or another purpose',
  author='Krypton Byte',
  author_email='rosid6434@gmail.com',
  url='https://github.com/krypton-byte/lexz',
  long_description=open(
    path.join(base_dir, "README.md"),
    encoding="utf-8"
  ).read(),
  keywords=[
    'obfuscation',
    'lexer',
    'variable',
    'ast',
    'tree',
    'graph'
  ],
  install_requires=[
          'git+https://github.com/krypton-byte/dict2object'
      ],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3.9',
  ],
)
