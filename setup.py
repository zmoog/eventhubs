from setuptools import setup
import os

VERSION = "0.2.2"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="eventhubs",
    description="CLI tool to send and receive event data from Azure Event Hubs",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Maurizio Branca",
    url="https://github.com/zmoog/eventhubs",
    project_urls={
        "Issues": "https://github.com/zmoog/eventhubs/issues",
        "CI": "https://github.com/zmoog/eventhubs/actions",
        "Changelog": "https://github.com/zmoog/eventhubs/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["eventhubs"],
    entry_points="""
        [console_scripts]
        eh=eventhubs.cli:cli
    """,
    install_requires=[
        "click",
        "azure-eventhub==5.11.5",
    ],
    extras_require={
        "test": ["pytest"]
    },
    python_requires=">=3.7",
)
