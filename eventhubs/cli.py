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
@click.pass_context
def cli(ctx: click.Context, connection_string: str, consumer_group: str, name: str):
    "CLI tool to send and receive event data from Azure Event Hubs"
    ctx.ensure_object(dict)
    ctx.obj['connection_string'] = connection_string
    ctx.obj['consumer_group'] = consumer_group
    ctx.obj['name'] = name    


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

    client = EventHubConsumerClient.from_connection_string(
        ctx.obj['connection_string'],
        ctx.obj['consumer_group'],
        eventhub_name=ctx.obj['name'],
    )

    def on_event(partition_context, event: EventData):
        print(f"Received event from partition {partition_context.partition_id}: {event.body_as_str()}")
        partition_context.update_checkpoint(event)

    with client:
        print("Receiving events from Azure Event Hubs")
        client.receive(
            on_event=on_event,
            starting_position=starting_position,
        )    


@eventdata.command(name="send")
@click.option(
    "--text",
    required=True,
)
@click.pass_context
def send(ctx: click.Context, text: str):
    """Send a single event data to Azure Event Hubs"""

    client = EventHubProducerClient.from_connection_string(
        ctx.obj['connection_string'],
        eventhub_name=ctx.obj['name'],
    )

    print("Sending event data to Azure Event Hubs")
    with client:
        client.send_event(EventData(text))
