import asyncio
import logging

import click
from aiohttp import ClientSession

from . import auth, connection, logger

# TRACE messages in logs
logger.setLevel(logging.HS_TRACE)
logger.addHandler(logging.StreamHandler())


OPTION_USERNAME = click.option(
    "--username", required=True, help="Username for HubSpace"
)
OPTION_PASSWORD = click.option(
    "--password", required=True, help="Password for HubSpace"
)


async def run_workflow_auth(ctx):
    hs_auth = auth.HubSpaceAuth(ctx.obj["username"], ctx.obj["password"])
    sess = ClientSession()
    try:
        await hs_auth.token(sess)
    except Exception:
        logger.exception("Unable to auth")
    finally:
        await sess.close()


async def run_workflow_hs(ctx):
    sess = ClientSession()
    hs = connection.HubSpaceConnection(
        ctx.obj["username"], ctx.obj["password"], websession=sess
    )
    try:
        click.echo(await hs.get_account_id())
    except Exception:
        logger.exception("Unable to auth")
    finally:
        await sess.close()


@click.group()
@OPTION_USERNAME
@OPTION_PASSWORD
@click.pass_context
def workflow(ctx, username, password):
    ctx.ensure_object(dict)
    ctx.obj["username"] = username
    ctx.obj["password"] = password


@workflow.command()
@click.pass_context
def auth_flow(ctx):
    try:
        loop = asyncio.get_event_loop()
    except Exception:
        loop = asyncio.new_event_loop()
    loop.run_until_complete(run_workflow_auth(ctx))


@workflow.command()
@click.pass_context
def hs_conn(ctx):
    try:
        loop = asyncio.get_event_loop()
    except Exception:
        loop = asyncio.new_event_loop()
    loop.run_until_complete(run_workflow_hs(ctx))


if __name__ == "__main__":
    workflow(obj={})
