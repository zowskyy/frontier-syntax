# Frontier Quickstart Guide

## Installation

```bash
curl -sSL frontier.dev/install | sh
```

## Migrate Your First Project

```bash
frontier migrate --input /path/to/your/project --output /path/to/migrated
```

## Run Your First Frontier Project

```bash
frontier run /path/to/migrated/project/main.frontier
```

## Deploy to Production

```bash
frontier deploy --target cloud /path/to/migrated/project
```

For full documentation, visit https://frontier.dev/docs
