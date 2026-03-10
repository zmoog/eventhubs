# Migration guide: v0.4 to v0.5

This guide covers all breaking changes and new features introduced in v0.5.

## Breaking changes

### Command group renamed: `eventdata` → `events`

The `eventdata` subcommand group has been renamed to `events`.

```diff
- eh eventdata receive
+ eh events receive
```

```diff
- eh eventdata send-batch --text '{"msg": "hi"}'
+ eh events send-batch --text '{"msg": "hi"}'
```

### Send command renamed: `send-event` → `send`

The `send-event` command is now simply `send`.

```diff
- eh eventdata send-event --text '{"msg": "hello"}'
+ eh events send --text '{"msg": "hello"}'
```

### `--connection-string` is no longer required

The `--connection-string` flag (and `EVENTHUB_CONNECTION_STRING` env var) is still supported, but it is no longer mandatory. v0.5 introduces token-based authentication as an alternative. If you rely on connection strings, your existing setup continues to work—you just no longer get an error when the flag is omitted (provided a config context supplies the value instead).

### `--name` is no longer positionally required

`--name` is still needed, but it can now come from a config context instead of always being passed on the command line or via `EVENTHUB_NAME`.

## New features

### Token-based authentication (Azure Identity)

You can now authenticate without a connection string by using `--fully-qualified-namespace` and `--credential`:

```bash
eh --fully-qualified-namespace mynamespace.servicebus.windows.net \
   --credential default \
   events receive
```

Supported credential types:

| Value              | Azure Identity class         |
|--------------------|------------------------------|
| `default`          | `DefaultAzureCredential`     |
| `azurecli`         | `AzureCliCredential`         |
| `environment`      | `EnvironmentCredential`      |
| `managedidentity`  | `ManagedIdentityCredential`  |

The corresponding env vars are `EVENTHUB_FULLY_QUALIFIED_NAMESPACE` and `EVENTHUB_CREDENTIAL`.

> **Note:** `--connection-string` and `--fully-qualified-namespace` are mutually exclusive.

### Configuration file and named contexts

v0.5 adds a YAML config file (`~/.config/eventhubs/config.yaml`) with kubectl-style named contexts, so you no longer need to pass connection details on every invocation.

#### Create a context

```bash
eh config set-context prod \
  --connection-string "Endpoint=sb://..." \
  --eventhub-name my-hub \
  --consumer-group "\$Default"
```

Or with token-based auth:

```bash
eh config set-context dev \
  --fully-qualified-namespace mynamespace.servicebus.windows.net \
  --credential azurecli \
  --eventhub-name my-hub
```

#### Switch contexts

```bash
eh config use-context prod
```

#### List and inspect contexts

```bash
eh config get-contexts       # list all contexts (* marks the active one)
eh config current-context    # print the active context name
```

#### Delete a context

```bash
eh config delete-context old-env
```

#### Use a one-off context without switching

```bash
eh --context dev events receive
```

#### Precedence

Settings are resolved in this order (highest wins):

1. CLI flags / environment variables
2. Named context selected with `--context`
3. `current-context` from the config file

This means you can set defaults in a context and override individual values on the command line:

```bash
eh config use-context prod
eh events receive                      # uses everything from "prod"
eh events receive --name other-hub     # overrides just the hub name
```

#### Custom config file location

Set the `EVENTHUB_CONFIG` env var to use a config file in a non-default location:

```bash
export EVENTHUB_CONFIG=/path/to/my/config.yaml
```

### New dependencies

v0.5 adds two new dependencies:

- `azure-identity` — required for token-based authentication
- `pyyaml` — required for the config file

Both are installed automatically when you upgrade:

```bash
pip install --upgrade eventhubs
```

## Quick migration checklist

1. Replace `eventdata` with `events` in all scripts and aliases.
2. Replace `send-event` with `send`.
3. (Optional) Set up a config context to stop passing `--connection-string` and `--name` on every call.
4. (Optional) Switch from connection strings to token-based auth for better security.
