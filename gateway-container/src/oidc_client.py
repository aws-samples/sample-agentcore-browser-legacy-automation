# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Generic OIDC M2M token client for integration test authentication.

Supports any OAuth2-compliant IdP (Auth0, Okta, Cognito, Entra ID, Keycloak,
etc.) via parameters that capture endpoint and credential delivery differences
across vendors.

Auth method reference:
    - client_secret_post: credentials in request body (Auth0, Entra ID default)
    - client_secret_basic: HTTP Basic auth header (Cognito, Okta)
"""

import base64

import requests


def get_m2m_token(
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    scope: str = "",
    audience: str = "",
    auth_method: str = "client_secret_post",
) -> str:
    """Obtain JWT from any OIDC provider using client_credentials grant.

    Args:
        token_endpoint: Full URL to the provider's token endpoint.
        client_id: M2M application client ID.
        client_secret: M2M application client secret.
        scope: Space-separated scopes (Okta, Cognito, Entra ID).
        audience: API audience identifier (Auth0).
        auth_method: How to send credentials:
            - "client_secret_post": credentials in form/JSON body
            - "client_secret_basic": HTTP Basic auth header

    Returns:
        Access token string.

    Raises:
        requests.HTTPError: If the token request fails.
        KeyError: If the response does not contain access_token.
    """
    if auth_method == "client_secret_basic":
        credentials = "%s:%s" % (client_id, client_secret)
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic %s" % encoded,
        }
        data = {"grant_type": "client_credentials"}
        if scope:
            data["scope"] = scope
        if audience:
            data["audience"] = audience

        response = requests.post(
            token_endpoint, headers=headers, data=data, timeout=30
        )
    else:
        # client_secret_post — credentials in form body
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scope:
            data["scope"] = scope
        if audience:
            data["audience"] = audience

        response = requests.post(
            token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

    response.raise_for_status()
    return response.json()["access_token"]
