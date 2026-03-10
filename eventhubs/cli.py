import signal
import sys
import threading
from typing import List, Optional, TextIO, Union

import click

from azure.eventhub import EventData

from eventhubs.auth import make_consumer, make_producer
from eventhubs.config import (
    VALID_CREDENTIAL_TYPES,
    load_config,
    save_config,
    get_current_context,
    get_context,
)
from eventhubs import config as config_module


def _resolve_settings(ctx: click.Context) -> dict:
    """Merge config-file context with CLI flags/env vars.

    Precedence (highest wins):
      1. CLI flags / env vars (if explicitly provided)
      2. Named context (--context flag)
      3. current-context from config file
    """
    cfg = load_config()

    context_name = ctx.params.get("context")
    if context_name:
        context_values = get_context(cfg, context_name)
        if context_values is None:
            raise click.ClickException(f"context '{context_name}' not found in config")
    else:
        context_values = get_current_context(cfg) or {}

    key_map = {
        "connection-string": "connection_string",
        "fully-qualified-namespace": "fully_qualified_namespace",
        "credential": "credential",
        "eventhub-name": "name",
        "consumer-group": "consumer_group",
    }

    settings = {}
    for config_key, settings_key in key_map.items():
        settings[settings_key] = context_values.get(config_key)

    cli_source = ctx.get_parameter_source
    params = ctx.params
    overrides = {
        "connection_string": "connection_string",
        "fully_qualified_namespace": "fully_qualified_namespace",
        "credential": "credential",
        "name": "name",
        "consumer_group": "consumer_group",
    }
    for param_name, settings_key in overrides.items():
        source = cli_source(param_name)
        if source in (
            click.core.ParameterSource.COMMANDLINE,
            click.core.ParameterSource.ENVIRONMENT,
        ):
            settings[settings_key] = params[param_name]
        elif source == click.core.ParameterSource.DEFAULT and settings.get(settings_key) is None:
            settings[settings_key] = params[param_name]

    return settings


def _validate_settings(settings: dict) -> None:
    has_conn_str = bool(settings.get("connection_string"))
    has_fqns = bool(settings.get("fully_qualified_namespace"))
    has_credential = bool(settings.get("credential"))

    if has_conn_str and has_fqns:
        raise click.ClickException(
            "--connection-string and --fully-qualified-namespace are mutually exclusive"
        )

    if not has_conn_str and not has_fqns:
        raise click.ClickException(
            "either --connection-string or --fully-qualified-namespace is required "
            "(via flag, env var, or config context)"
        )

    if has_fqns and not has_credential:
        raise click.ClickException(
            "--credential is required when using --fully-qualified-namespace"
        )

    if not settings.get("name"):
        raise click.ClickException(
            "--name is required (via flag, env var, or config context)"
        )


# ---------------------------------------------------------------------------
# Root CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option()
@click.option(
    "--connection-string",
    required=False,
    envvar="EVENTHUB_CONNECTION_STRING",
    default=None,
    help="Event Hub connection string.",
)
@click.option(
    "--fully-qualified-namespace",
    required=False,
    envvar="EVENTHUB_FULLY_QUALIFIED_NAMESPACE",
    default=None,
    help="Event Hub namespace (e.g. mynamespace.servicebus.windows.net).",
)
@click.option(
    "--credential",
    required=False,
    envvar="EVENTHUB_CREDENTIAL",
    default=None,
    type=click.Choice(VALID_CREDENTIAL_TYPES, case_sensitive=False),
    help="Credential type for token-based auth.",
)
@click.option(
    "--consumer-group",
    required=False,
    default="$Default",
    envvar="EVENTHUB_CONSUMER_GROUP",
)
@click.option(
    "--name",
    required=False,
    default=None,
    envvar="EVENTHUB_NAME",
    help="Event Hub name.",
)
@click.option(
    "--context",
    "context",
    required=False,
    default=None,
    help="Use a named context from the config file.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enables verbose mode.",
    default=False,
    envvar="EVENTHUB_VERBOSE",
)
@click.pass_context
def cli(
    ctx: click.Context,
    connection_string: Optional[str],
    fully_qualified_namespace: Optional[str],
    credential: Optional[str],
    consumer_group: str,
    name: Optional[str],
    context: Optional[str],
    verbose: bool,
):
    """CLI tool to send and receive event data from Azure Event Hubs."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Config subcommands and --help don't need connection settings.
    if ctx.invoked_subcommand == "config" or ctx.resilient_parsing:
        return

    # Defer resolution when a subcommand will handle --help itself.
    if any(arg in ("--help", "-h") for arg in sys.argv[1:]):
        return

    settings = _resolve_settings(ctx)
    _validate_settings(settings)

    ctx.obj.update(settings)


# ---------------------------------------------------------------------------
# events command group
# ---------------------------------------------------------------------------

@cli.group()
def events():
    """Send and receive events."""


@events.command(name="receive")
@click.option(
    "--starting-position",
    default="-1",
)
@click.pass_context
def receive(ctx: click.Context, starting_position: str):
    """Receive event data from Azure Event Hubs."""
    consumer = make_consumer(ctx.obj)

    def on_event(partition_context, event: EventData):
        if event is None:
            return
        if ctx.obj["verbose"]:
            sys.stdout.write(f"Received event from partition {partition_context.partition_id}: {event.body_as_str()}\n")
        else:
            sys.stdout.write(event.body_as_str() + "\n")
        sys.stdout.flush()
        partition_context.update_checkpoint(event)

    def on_error(partition_context, error: Exception):
        sys.stderr.write(f"Error on partition {partition_context.partition_id}: {error}\n")
        sys.stderr.flush()

    with consumer:
        if ctx.obj["verbose"]:
            print(f"Receiving events from {ctx.obj['name']}")
        consumer.receive(
            on_event=on_event,
            on_error=on_error,
            starting_position=starting_position,
            max_wait_time=5,
        )

        stop = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        stop.wait()


@events.command(name="send")
@click.option("--text", required=False)
@click.option("--partition-key", required=False)
@click.pass_context
def send(ctx: click.Context, text: Union[str, TextIO], partition_key: Optional[str] = None):
    """Send a single event."""
    producer = make_producer(ctx.obj)

    if text:
        event = text
    else:
        event = sys.stdin.read()

    if not isinstance(event, str):
        raise TypeError(f"only 'str' is supported (found: {type(event)})")

    with producer:
        if ctx.obj["verbose"]:
            print(f"Sending one event to {ctx.obj['name']}")

        producer.send_event(EventData(event), partition_key=partition_key)

        if ctx.obj["verbose"]:
            print("event sent successfully")


@events.command(name="send-batch")
@click.option("--text", required=False, multiple=True, default=None)
@click.option(
    "--lines-from-text-file",
    help="Text file to read lines from. If not provided, stdin will be used.",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="-",
)
@click.option("--batch-size", default=10)
@click.pass_context
def send_batch(ctx: click.Context, text: List[str], lines_from_text_file: Union[str, TextIO], batch_size: int):
    """Send a batch of event data to Azure Event Hubs."""
    producer = make_producer(ctx.obj)

    if text:
        events = text
    else:
        if lines_from_text_file in ("-", "stdin"):
            content = sys.stdin.read()
        else:
            with open(lines_from_text_file, "r") as f:
                content = f.read()

        if not isinstance(content, str):
            raise TypeError(f"only 'str' is supported (found: {type(content)})")

        events = content.splitlines()

    with producer:
        if ctx.obj["verbose"]:
            print(f"Sending {len(events)} events to {ctx.obj['name']}")

        for i in range(0, len(events), batch_size):
            batch = producer.create_batch()
            for event in events[i : i + batch_size]:
                try:
                    batch.add(EventData(event))
                except ValueError:
                    if ctx.obj["verbose"]:
                        print("Event data batch is full ({} events).".format(len(batch)))

            if ctx.obj["verbose"]:
                print(f"sending batch of {len(batch)} events")

            producer.send_batch(batch)

            if ctx.obj["verbose"]:
                print("batch sent successfully")


# ---------------------------------------------------------------------------
# config command group
# ---------------------------------------------------------------------------

@cli.group(name="config")
def config_group():
    """Manage CLI configuration and contexts."""


@config_group.command(name="get-contexts")
def config_get_contexts():
    """List all configured contexts."""
    cfg = load_config()
    contexts = cfg.get("contexts", {})
    current = cfg.get("current-context", "")

    if not contexts:
        click.echo("No contexts configured.")
        return

    for name, values in contexts.items():
        marker = "*" if name == current else " "
        if values.get("connection-string"):
            auth = "connection-string"
        elif values.get("fully-qualified-namespace"):
            auth = f"{values.get('credential', '?')}@{values['fully-qualified-namespace']}"
        else:
            auth = "incomplete"
        click.echo(f"{marker} {name:20s}  {values.get('eventhub-name', ''):20s}  {auth}")


@config_group.command(name="current-context")
def config_current_context():
    """Show the current context name."""
    cfg = load_config()
    current = cfg.get("current-context", "")
    if not current:
        click.echo("No current context is set.")
    else:
        click.echo(current)


@config_group.command(name="use-context")
@click.argument("name")
def config_use_context(name: str):
    """Switch to a different context."""
    cfg = load_config()
    try:
        config_module.use_context(cfg, name)
    except ValueError as e:
        raise click.ClickException(str(e))
    save_config(cfg)
    click.echo(f"Switched to context '{name}'.")


@config_group.command(name="set-context")
@click.argument("name")
@click.option("--connection-string", default=None)
@click.option("--fully-qualified-namespace", default=None)
@click.option(
    "--credential",
    default=None,
    type=click.Choice(VALID_CREDENTIAL_TYPES, case_sensitive=False),
)
@click.option("--eventhub-name", default=None)
@click.option("--consumer-group", default=None)
def config_set_context(
    name: str,
    connection_string: Optional[str],
    fully_qualified_namespace: Optional[str],
    credential: Optional[str],
    eventhub_name: Optional[str],
    consumer_group: Optional[str],
):
    """Create or update a named context."""
    cfg = load_config()
    values = {
        "connection-string": connection_string,
        "fully-qualified-namespace": fully_qualified_namespace,
        "credential": credential,
        "eventhub-name": eventhub_name,
        "consumer-group": consumer_group,
    }
    config_module.set_context(cfg, name, values)
    save_config(cfg)
    click.echo(f"Context '{name}' updated.")


@config_group.command(name="delete-context")
@click.argument("name")
def config_delete_context(name: str):
    """Delete a named context."""
    cfg = load_config()
    try:
        config_module.delete_context(cfg, name)
    except ValueError as e:
        raise click.ClickException(str(e))
    save_config(cfg)
    click.echo(f"Context '{name}' deleted.")
