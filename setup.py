import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

INSTALL_REQUIRES = [
    "aiocometd>=0.3.0,<0.4.0",
    "aiohttp>=3.1,<4.0"
]
TESTS_REQUIRE = [
    "asynctest>=0.12.0,<1.0.0",
    "coverage>=4.5,<5.0"
]
DOCS_REQUIRE = [
    "Sphinx>=1.7,<2.0",
    "sphinxcontrib-asyncio>=0.2.0"
]
DEV_REQUIRE = [
    "flake8",
    "pylint"
]


def read(file_path):
    with open(os.path.join(here, file_path)) as file:
        return file.read().strip()


metadata = {}
metadata_path = os.path.join(here, "aiosfstream/_metadata.py")
exec(read(metadata_path), metadata)


setup(
    name=metadata["TITLE"],
    version=metadata["VERSION"],
    description=metadata["DESCRIPTION"],
    long_description='\n\n'.join((read('DESCRIPTION.rst'),
                                  read('docs/source/changes.rst'))),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Framework :: AsyncIO",
        "License :: OSI Approved :: MIT License"
    ],
    keywords=metadata["KEYWORDS"],
    author=metadata["AUTHOR"],
    author_email=metadata["AUTHOR_EMAIL"],
    url=metadata["URL"],
    license="MIT",
    packages=find_packages(exclude=("tests*", )),
    python_requires=">=3.6.0",
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    extras_require={
        "tests": TESTS_REQUIRE,
        "docs": DOCS_REQUIRE,
        "dev": DEV_REQUIRE + TESTS_REQUIRE + DOCS_REQUIRE
    },
    include_package_data=True,
    test_suite="tests"
)
