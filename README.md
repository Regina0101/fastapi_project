To view the project in the "src" folder you need to create a "conf" folder, 
put the "config.py" file in it and display the following code:
class Config:
    DB_URL = "postgresql+asyncpg://your postgresql database"
    SECRET_KEY = "your secret key for JWT"
    ALGORITHM = "JWT Algorithm"


config = Config()
