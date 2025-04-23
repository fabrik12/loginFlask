from datetime import datetime

blacklist = {}

def add_token(token, expires_at):
    # Add token to blacklist, and expiration datetime
    blacklist[token] = expires_at

def is_token_blacklisted(token):
    # If the token is in blacklist and is valited 
    # If the token expires, this clean it
    if token not in blacklist:
        return False
    
    if datetime.utcnow() > blacklist[token]:
        del blacklist[token]
        return False
    
    return True