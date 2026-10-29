import bootstrap
from alembic.config import Config
from alembic import command
if __name__=='__main__':command.upgrade(Config(str(bootstrap.ROOT/'alembic.ini')),'head')
