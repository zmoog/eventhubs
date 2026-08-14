"""Factory functions to build Event Hub clients from resolved settings."""

from typing import Any, Dict

from azure.eventhub import EventHubConsumerClient, EventHubProducerClient


def _make_credential(credential_type: str):
    """Create an azure-identity credential from a type name."""
    from azure.identity import (
        AzureCliCredential,
        DefaultAzureCredential,
        EnvironmentCredential,
        ManagedIdentityCredential,
    )

    credentials = {
        "default": DefaultAzureCredential,
        "azurecli": AzureCliCredential,
        "environment": EnvironmentCredential,
        "managedidentity": ManagedIdentityCredential,
    }

    cls = credentials.get(credential_type)
    if cls is None:
        raise ValueError(
            f"unknown credential type '{credential_type}', "
            f"must be one of: {', '.join(credentials)}"
        )
    return cls()


def make_consumer(settings: Dict[str, Any]) -> EventHubConsumerClient:
    if settings.get("connection_string"):
        return EventHubConsumerClient.from_connection_string(
            settings["connection_string"],
            settings["consumer_group"],
            eventhub_name=settings["name"],
        )

    return EventHubConsumerClient(
        fully_qualified_namespace=settings["fully_qualified_namespace"],
        eventhub_name=settings["name"],
        consumer_group=settings["consumer_group"],
        credential=_make_credential(settings["credential"]),
    )


def make_producer(settings: Dict[str, Any]) -> EventHubProducerClient:
    if settings.get("connection_string"):
        return EventHubProducerClient.from_connection_string(
            settings["connection_string"],
            eventhub_name=settings["name"],
        )

    return EventHubProducerClient(
        fully_qualified_namespace=settings["fully_qualified_namespace"],
        eventhub_name=settings["name"],
        credential=_make_credential(settings["credential"]),
    )
