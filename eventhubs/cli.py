import sys
from typing import List, Optional, TextIO, Union

import click

from azure.eventhub import EventHubConsumerClient, EventHubProducerClient, EventData


@click.group()
@click.version_option()
@click.option(
    "--connection-string",
    required=True,
    envvar="EVENTHUB_CONNECTION_STRING",
)
@click.option(
    "--consumer-group",
    required=True,
    default="$Default",
    envvar="EVENTHUB_CONSUMER_GROUP",
)
@click.option(
    "--name",
    required=True,
    envvar="EVENTHUB_NAME",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enables verbose mode",
    default=False,
    envvar="EVENTHUB_VERBOSE",
)
@click.pass_context
def cli(ctx: click.Context, connection_string: str, consumer_group: str, name: str, verbose: bool):
    """CLI tool to send and receive event data from Azure Event Hubs"""
    ctx.ensure_object(dict)
    ctx.obj['connection_string'] = connection_string
    ctx.obj['consumer_group'] = consumer_group
    ctx.obj['name'] = name
    ctx.obj['verbose'] = verbose


@cli.group()
def eventdata():
    return "Event data commands"


@eventdata.command(name="receive")
@click.option(
    "--starting-position",
    default="-1",  # "-1" is from the beginning of the partition.
)
@click.pass_context
def receive(ctx: click.Context, starting_position: str):
    """Receive event data from Azure Event Hubs"""

    consumer = EventHubConsumerClient.from_connection_string(
        ctx.obj['connection_string'],
        ctx.obj['consumer_group'],
        eventhub_name=ctx.obj['name'],
    )

    def on_event(partition_context, event: EventData):
        if ctx.obj['verbose']:
            print(f"Received event from partition {partition_context.partition_id}: {event.body_as_str()}")
        else:
            print(event.body_as_str())
        partition_context.update_checkpoint(event)

    with consumer:
        if ctx.obj['verbose']:
            print(f"Receiving events from {ctx.obj['name']}")
        consumer.receive(
            on_event=on_event,
            starting_position=starting_position,
        )    


@eventdata.command(name="send-event")
@click.option(
    "--text",
    required=False
)
@click.option(
    "--partition-key",
    required=False
)
@click.pass_context
def send_event(ctx: click.Context, text: Union[str, TextIO], partition_key: Optional[str] = None):
    """Send a single event data to Azure Event Hubs"""

    producer = EventHubProducerClient.from_connection_string(
        ctx.obj['connection_string'],
        eventhub_name=ctx.obj['name'],
    )

    if text:
        event = text
    else:
        event = sys.stdin.read()

    if not isinstance(event, str):
        # supporting only str-based input, we'll
        # evaluate bytes later on
        raise TypeError(f"only 'str' is supported (found: {type(event)})")

    with producer:
        if ctx.obj['verbose']:
            print(f"Sending one event to {ctx.obj['name']}")

        producer.send_event(EventData(event), partition_key=partition_key)

        if ctx.obj['verbose']:
            print(f"event sent successfully")


@eventdata.command(name="send-batch")
@click.option(
    "--text",
    required=False,
    multiple=True,
    default=None,
)
@click.option(
    "--lines-from-text-file",
    help="Text file to read lines from. If not provided, stdin will be used.",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="-",
)
@click.option(
    "--batch-size",
    default=10,
)
@click.pass_context
def send_batch(ctx: click.Context, text: List[str], lines_from_text_file: Union[str, TextIO], batch_size: int):
    """Send a batch of event data to Azure Event Hubs"""

    producer = EventHubProducerClient.from_connection_string(
        ctx.obj['connection_string'],
        eventhub_name=ctx.obj['name'],
    )

    if text:
        # text contains a list of events since the
        # option is defined as `multiple=True`
        events = text
    else:
        # we look for a str to split in line from stdin or
        # a text file
        if lines_from_text_file in ("-", "stdin"):
            content = sys.stdin.read()
        else:
            with open(lines_from_text_file, "r") as f:
                content = f.read()

        if not isinstance(content, str):
            # supporting only str-based input, we'll
            # evaluate bytes later on
            raise TypeError(f"only 'str' is supported (found: {type(content)})")

        events = content.splitlines()

    with producer:
        if ctx.obj['verbose']:
            print(f"Sending {len(events)} events to {ctx.obj['name']}")

        # send the events in batches of `batch_size`
        for i in range(0, len(events), batch_size):
            batch = producer.create_batch()
            for event in events[i:i+batch_size]:
                # if ctx.obj['verbose']:
                #     print(f"adding {event}")
                try:
                    batch.add(EventData(event))
                except ValueError as e:
                    # if the batch is full, we send the
                    # current one and the create a brand
                    # new one for the remaining events
                    if ctx.obj['verbose']:
                        print("Event data batch is full ({} events).".format(len(batch)))
            
            if ctx.obj['verbose']:
                print(f"sending batch of {len(batch)} events")
            
            # producer.send_batch(batch, partition_key="whatever")
            producer.send_batch(batch)

            if ctx.obj['verbose']:
                print(f"batch sent successfully")
