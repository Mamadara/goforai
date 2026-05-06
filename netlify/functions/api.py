import sys
import os

project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.chdir(project_root)

from app import app
from serverless_wsgi import handle_request

def handler(event, context):
    return handle_request(app, event, context)
