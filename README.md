# eventhubs

[![PyPI](https://img.shields.io/pypi/v/eventhubs.svg)](https://pypi.org/project/eventhubs/)
[![Changelog](https://img.shields.io/github/v/release/zmoog/eventhubs?include_prereleases&label=changelog)](https://github.com/zmoog/eventhubs/releases)
[![Tests](https://github.com/zmoog/eventhubs/workflows/Test/badge.svg)](https://github.com/zmoog/eventhubs/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/zmoog/eventhubs/blob/master/LICENSE)

CLI tool to send and receive event data from Azure Event Hubs

## Installation

Install this tool using `pip`:

    pip install eventhubs

## Usage

### Receiving

For receiving data to an event hub, run:

    eh eventdata receive

### Sending

For sending a single event to an event hub, run:

    eh eventdata send --text '{"message": "Hello Spank"}'

You can also send multiple events in a batch by using `--text` more than once:

    eh eventdata send --text '{"message": "Hello Spank"}' --text '{"message": "Hello Spank (yes, again)"}'

For sending the lines in a text files as event, run:

    eh eventdata send --lines-from-text-file multiline.txt

For sending the lines from `stdin` as event, run:

    cat multiline.txt | eh eventdata send  

## Configuration

You can set up the connection string and event hub name using the command line options:

    eh eventdata receive --connection-string "Endpoint=.." --name "application-insights"

or the environment variables (or a mix of both):

    export EVENTHUB_CONNECTION_STRING="Endpoint=sb://...="
    export EVENTHUB_NAME="application-insights"

    eh eventdata receive

    eh eventdata receive --name "another-name"

Defaults to printing the message payload only, so it is easier to combine output with other tools, like `jq`:

    $ eh eventdata receive | jq '.records[].tenantId' 
    "1de2b364-21e1-4866-bb46-7804f17c417d"
    "1de2b364-21e1-4866-bb46-7804f17c417d"
    "1de2b364-21e1-4866-bb46-7804f17c417d"

But you can still turn on verbose and get more information about what's going on:

    $ eh --verbose eventdata receive
    Receiving events from mbranca
    Received event from partition 0: {"records": [{....

For help, run:

    eventhubs --help

You can also use:

    python -m eventhubs --help

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd eventhubs
    python -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
