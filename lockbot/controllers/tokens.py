from jwt import InvalidTokenError
from starlette.requests import Request
from starlette.responses import JSONResponse

from .. import database
from ..helpers import validate_request_password, get_token_from_request
from ..jwt import decode_status_token, create_access_token, create_status_token
from ..logging import logger

log = logger.getChild('Tokens')


async def request(req: Request) -> JSONResponse:
    """Request for a new token."""
    idx, nicename = database.create_token_request()
    data = await req.json()
    password = data.get('password', None)

    if not validate_request_password(password):
        return JSONResponse({
            'status': 'Invalid password!'
        }, status_code=401)

    token = create_status_token(idx)
    log.getChild('Request')\
        .info(f'New token request. {idx}:"{nicename}"')
    return JSONResponse({
        'token': token,
        'nicename': nicename
    }, status_code=202)


async def status(req: Request) -> JSONResponse:
    try:
        token = get_token_from_request(req)
    except KeyError:
        return JSONResponse({
            'status': 'No token provided!'
        }, status_code=401)
    except AssertionError:
        return JSONResponse({
            'status': 'Invalid authentication type!'
        }, status_code=401)
    try:
        data = decode_status_token(token)
    except InvalidTokenError:
        log.getChild('Status')\
            .error(f'Rejected. Invalid token. ({token})')
        return JSONResponse({
            'status': 'Invalid token!'
        }, status_code=401)

    request_id = data['id']

    approved, name = database.is_request_approved(request_id)
    if approved is None:
        return JSONResponse({
            'status': 'Unknown ID.'
        }, status_code=400)
    elif not approved:
        return JSONResponse({
            'status': 'Awaiting approval...',
            'approved': False
        }, status_code=202)

    # The request has been approved!
    access_token = create_access_token(name)

    return JSONResponse({
        'status': 'Approved!',
        'approved': True,
        'token': access_token,
        'name': name
    })
