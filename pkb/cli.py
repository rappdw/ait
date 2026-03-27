"""CLI interface for the Personal Knowledge Base."""

import json
import os
import sys

import click

from .db import DEFAULT_DB_PATH, get_schema_version, init_db, vec_available
from .embeddings import init_embeddings


def _get_db_path(ctx):
    return ctx.obj.get("db_path") or DEFAULT_DB_PATH


@click.group()
@click.option(
    "--db", "db_path", envvar="PKB_DB_PATH", default=None,
    help="Database path (default: kb/pka.db relative to cwd)",
)
@click.pass_context
def cli(ctx, db_path):
    """PKB — Personal Knowledge Base CLI."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the database."""
    db_path = _get_db_path(ctx)
    conn = init_db(db_path)
    version = get_schema_version(conn)
    conn.close()

    click.echo(f"Database initialized at {db_path}")
    click.echo(f"Schema version: {version}")
    click.echo(f"sqlite-vec: {'available' if vec_available() else 'not available (FTS5-only mode)'}")

    backend = init_embeddings()
    if backend:
        click.echo(f"Embeddings: {backend}")
    else:
        click.echo("Embeddings: none (FTS5-only search)")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--tag", "-t", multiple=True, help="Add tags to the item")
@click.option("--category", "-c", multiple=True, help="Assign category paths")
@click.pass_context
def add(ctx, file_path, tag, category):
    """Add a file to the knowledge base."""
    from .ingest import ingest_file

    db_path = _get_db_path(ctx)
    conn = init_db(db_path)
    init_embeddings()

    item_id = ingest_file(
        conn,
        file_path,
        tags=list(tag) if tag else None,
        category_paths=list(category) if category else None,
    )
    conn.close()

    if item_id:
        click.echo(f"Added item {item_id}: {file_path}")
    else:
        click.echo(f"Skipped (duplicate or unsupported): {file_path}")


@cli.command()
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Max results")
@click.option("--type", "type_filter", default=None, help="Filter by type")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.pass_context
def search(ctx, query, limit, type_filter, tag):
    """Search the knowledge base."""
    from .search import search as do_search

    db_path = _get_db_path(ctx)
    conn = init_db(db_path)
    init_embeddings()

    results = do_search(
        conn,
        query,
        limit=limit,
        type_filter=type_filter,
        tags=list(tag) if tag else None,
    )
    conn.close()

    if not results:
        click.echo("No results found.")
        return

    for i, item in enumerate(results, 1):
        score_str = ""
        if "rrf_score" in item and item["rrf_score"]:
            score_str = f" (RRF: {item['rrf_score']:.4f})"
        click.echo(f"\n{i}. [{item['type']}] {item['title']}{score_str}")
        click.echo(f"   ID: {item['id']} | Created: {item['created_at']}")
        if item.get("summary"):
            click.echo(f"   {item['summary'][:120]}")
        elif item.get("content"):
            preview = item["content"][:120].replace("\n", " ")
            click.echo(f"   {preview}...")


@cli.command()
@click.pass_context
def tags(ctx):
    """List all tags with item counts."""
    from .models import list_tags

    db_path = _get_db_path(ctx)
    conn = init_db(db_path)
    tag_list = list_tags(conn)
    conn.close()

    if not tag_list:
        click.echo("No tags found.")
        return

    for t in tag_list:
        click.echo(f"  {t['name']} ({t['count']} items)")


@cli.command()
@click.argument("directory", type=click.Path(exists=True), default=None, required=False)
@click.option("--recursive", "-r", is_flag=True, help="Recurse into subdirectories")
@click.option("--tag", "-t", multiple=True, help="Add tags to ingested items")
@click.pass_context
def ingest(ctx, directory, recursive, tag):
    """Ingest all files from a directory (default: Team Inbox/)."""
    from .ingest import ingest_directory

    if directory is None:
        # Default inbox location
        directory = os.path.join(os.getcwd(), "Team Inbox")
        if not os.path.isdir(directory):
            click.echo(f"Default inbox not found: {directory}")
            click.echo("Specify a directory: pkb ingest <path>")
            sys.exit(1)

    db_path = _get_db_path(ctx)
    conn = init_db(db_path)
    init_embeddings()

    ids = ingest_directory(
        conn,
        directory,
        tags=list(tag) if tag else None,
        recursive=recursive,
    )
    conn.close()

    click.echo(f"Ingested {len(ids)} item(s) from {directory}")


@cli.command()
@click.argument("item_id", type=int)
@click.pass_context
def show(ctx, item_id):
    """Show details of a specific item."""
    from .models import get_item

    db_path = _get_db_path(ctx)
    conn = init_db(db_path)
    item = get_item(conn, item_id)
    conn.close()

    if not item:
        click.echo(f"Item {item_id} not found.")
        sys.exit(1)

    click.echo(f"ID:         {item['id']}")
    click.echo(f"Type:       {item['type']}")
    click.echo(f"Title:      {item['title']}")
    click.echo(f"Created:    {item['created_at']}")
    click.echo(f"Updated:    {item['updated_at']}")
    click.echo(f"Words:      {item['word_count']}")
    click.echo(f"Source:     {item['source_path'] or 'N/A'}")
    click.echo(f"Tags:       {', '.join(item['tags']) if item['tags'] else 'none'}")
    click.echo(f"Categories: {', '.join(item['categories']) if item['categories'] else 'none'}")
    if item.get("content"):
        click.echo(f"\n--- Content ---\n{item['content'][:500]}")


def main():
    cli()


if __name__ == "__main__":
    main()
