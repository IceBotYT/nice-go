"""AWS Cognito authentication and identity management."""

import logging
from concurrent.futures import ThreadPoolExecutor

import boto3
from aiobotocore.session import get_session
from pycognito import AWSSRP  # type: ignore[import-untyped]

from nice_go.authentication_tokens import AuthenticationTokens

_LOGGER = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=5)


class AwsCognitoAuthenticator:
    def __init__(
        self,
        region_name: str,
        client_id: str,
        pool_id: str,
        identity_pool_id: str,
    ) -> None:
        self.region_name = region_name
        self.identity_pool_id = identity_pool_id
        self.client_id = client_id
        self.pool_id = pool_id
        self.session = get_session()

    """ Regenerates the token by providing a refresh token. """

    def refresh_token(self, refresh_token: str) -> AuthenticationTokens:
        cognito_identity_provider = boto3.client("cognito-idp", self.region_name)
        resp = cognito_identity_provider.initiate_auth(
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={
                "REFRESH_TOKEN": refresh_token,
            },
            ClientId=self.client_id,
        )
        _LOGGER.debug("Authentication response %s", resp)
        return AuthenticationTokens(resp["AuthenticationResult"])

    """ Gets the initial token by providing username and password. """

    def get_new_token(self, username: str, password: str) -> AuthenticationTokens:
        cognito_identity_provider = boto3.client("cognito-idp", self.region_name)
        # Start the authentication flow
        aws_srp = AWSSRP(
            username=username,
            password=password,
            pool_id=self.pool_id,
            client_id=self.client_id,
            client=cognito_identity_provider,
        )

        auth_params = aws_srp.get_auth_params()
        resp = cognito_identity_provider.initiate_auth(
            AuthFlow="USER_SRP_AUTH",
            AuthParameters=auth_params,
            ClientId=self.client_id,
        )

        challenge_response = aws_srp.process_challenge(
            resp["ChallengeParameters"],
            auth_params,
        )

        # Respond to PASSWORD_VERIFIER
        resp = cognito_identity_provider.respond_to_auth_challenge(
            ClientId=self.client_id,
            ChallengeName="PASSWORD_VERIFIER",
            ChallengeResponses=challenge_response,
        )
        _LOGGER.debug("Authentication result %s", resp)
        return AuthenticationTokens(resp["AuthenticationResult"])
