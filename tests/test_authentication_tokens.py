from nice_go._authentication_tokens import AuthenticationTokens


async def test_authentication_tokens() -> None:
    data = {"IdToken": "test_token", "RefreshToken": "refresh_token"}
    tokens = AuthenticationTokens(data)
    assert tokens.id_token == "test_token"
    assert tokens.refresh_token == "refresh_token"
    data = {"IdToken": "test_token"}
    tokens = AuthenticationTokens(data)
    assert tokens.id_token == "test_token"
    assert tokens.refresh_token is None
